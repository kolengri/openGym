import { afterEach, describe, expect, it, vi } from 'vitest'
import { mkdtemp, readFile, rm, chmod, symlink } from 'node:fs/promises'
import path from 'node:path'
import { CookieJar } from 'tough-cookie'
import { GarminApi, GarminSession } from '../src/garmin-release/api.js'
import { APP_ID, MANIFEST_ID, RELEASE_HOME, publicError } from '../src/garmin-release/contract.js'
import { directory } from '../src/garmin-release/artifact.js'

const dirs = []
afterEach(async () => { for (const dir of dirs.splice(0)) await rm(dir, { recursive: true, force: true }) })
const info = version => ({ manifestAppId: MANIFEST_ID, signatureCheckSuccessFul: true, appType: 'Device App', newAppVersion: version })
const cookie = (name = 'session', value = 'fixture-only', domain = 'apps.garmin.com') => ({ name, value, domain, path: '/', secure: true, httpOnly: true, expires: -1 })
const response = (data, status = 200, headers = {}) => new Response(typeof data === 'string' ? data : JSON.stringify(data), { status, headers })

async function fixture() {
  await directory(path.join(RELEASE_HOME, 'tests'))
  const dir = await mkdtemp(path.join(RELEASE_HOME, 'tests/api-'))
  dirs.push(dir)
  const file = path.join(dir, 'session.json')
  const session = new GarminSession(file)
  await session.import([cookie(), cookie('sso', 'sso-only', 'sso.garmin.com')])
  let version = '0.1.0-beta.2'
  const metadata = {
    betaApp: true, shadowApp: false, devEmail: 'fixture@example.test', category: '277', paymentModel: 0,
    requestingTips: false, requiringExternalSubscription: false,
    selectedCountries: [], selectedActivityTypes: [],
    selectedAntPlusProfiles: { selectedAntPlusProfiles: [], enteredAntPlusProfileComments: 'Keep this' },
    localizedAppModel: [{ appLocale: 'en', appTitle: 'openGym', appDescription: 'Keep description', appWhatsNew: 'Old' }, { appLocale: 'ru', appTitle: 'Зал', appWhatsNew: 'Старое' }],
    appFileCoordinates: { iconUrl: 'private-media' }, screenshotIds: ['keep-screenshot']
  }
  const writes = []
  const fetch = vi.fn(async (url, options) => {
    const u = new URL(url)
    expect(options.redirect).toBe('manual')
    expect(options.signal).toBeInstanceOf(AbortSignal)
    if (options.method !== 'GET') writes.push({ url: u, options })
    if (u.pathname === '/api/ciq-developerservices/developers') return response({ userId: 'owner-fixture', developer: true, ignoredSecret: 'never-return' })
    if (u.pathname.includes('appsLibraryExternalServices')) return response({ id: APP_ID, developerId: 'owner-fixture', betaApp: true, latestExternalVersion: version })
    if (u.pathname.endsWith('/metadata')) {
      expect(u.searchParams.get('isShadowApp')).toBe('false')
      return response({ ...metadata, appIqFileInfoResult: info(version) })
    }
    if (u.pathname.endsWith('/validate')) return response({ tempFileId: 'temporary-fixture', iqFileInfoResult: info(u.searchParams.get('appVersion')) })
    if (u.pathname.endsWith('/version')) {
      expect(options.headers['Content-Type']).toBe('application/json')
      expect(u.searchParams.get('juniorAppUpdate')).toBe('false')
      const body = JSON.parse(options.body)
      expect(body.tempFileId).toBe('temporary-fixture')
      version = body.appVersion
      return response('', 200)
    }
    if (options.method === 'PUT') {
      const changes = JSON.parse(await options.body.get('appMetadata').text())
      Object.assign(metadata, changes)
      return response('', 200)
    }
    throw new Error('Unexpected HTTP request')
  })
  const api = new GarminApi(file, { fetchImpl: fetch, writeImpl: fetch })
  const deploy = overrides => api.deploy({ version: '0.1.0-beta.3', expectedCurrentVersion: '0.1.0-beta.2', releaseNotes: 'Round controls and touch', bytes: Buffer.from('fixture IQ bytes'), beforeUpload: vi.fn(), ...overrides })
  return { dir, file, session, api, fetch, metadata, writes, deploy }
}

describe('HTTP cookie session', () => {
  it('imports only the pinned secure hosts and never imports a domain-wide browser cookie', async () => {
    const f = await fixture()
    await f.session.import([cookie(), cookie('unrelated', 'private', 'example.test'), cookie('wide', 'private', '.garmin.com')])
    const loaded = await new GarminSession(f.file).load()
    expect(await loaded.jar.getCookieString('https://apps.garmin.com/')).toBe('session=fixture-only')
    expect(await loaded.jar.getCookieString('https://sso.garmin.com/')).toBe('')
    expect(await loaded.jar.getCookieString('http://apps.garmin.com/')).toBe('')
  })
  it('refuses permissive and symlinked session files', async () => {
    const f = await fixture()
    await chmod(f.file, 0o644)
    await expect(f.api.inspect()).rejects.toMatchObject({ code: 'PRIVATE_SESSION_REQUIRED' })
    await chmod(f.file, 0o600)
    const link = path.join(f.dir, 'linked.json')
    await symlink(f.file, link)
    await expect(new GarminSession(link).load()).rejects.toMatchObject({ code: 'PRIVATE_SESSION_REQUIRED' })
  })
  it('persists cookie rotations without exposing credential fields', async () => {
    const f = await fixture(), original = f.fetch.getMockImplementation()
    f.fetch.mockImplementation(async (...args) => {
      const r = await original(...args)
      if (new URL(args[0]).pathname.endsWith('/developers')) r.headers.append('Set-Cookie', 'session=rotated-fixture; Path=/; Secure; HttpOnly')
      return r
    })
    const evidence = await f.api.inspect()
    expect(evidence).toEqual({ appId: APP_ID, manifestId: MANIFEST_ID, version: '0.1.0-beta.2', ownerOnlyBeta: true, transport: 'http' })
    expect(JSON.stringify(evidence)).not.toMatch(/owner-fixture|never-return|rotated-fixture/)
    const loaded = await new GarminSession(f.file).load()
    expect(await loaded.jar.getCookieString('https://apps.garmin.com/')).toBe('session=rotated-fixture')
    const jar = CookieJar.deserializeSync(JSON.parse(await readFile(f.file, 'utf8')).jar)
    expect(jar.getCookiesSync('https://apps.garmin.com/')[0].httpOnly).toBe(true)
  })
  it('respects expiry and does not treat refresh_token as an OAuth bearer token', async () => {
    const f = await fixture()
    await f.session.import([{ ...cookie(), expires: 1 }, cookie('refresh_token', 'encrypted-fixture')])
    await f.api.session.load()
    expect(await f.api.session.jar.getCookieString('https://apps.garmin.com/')).toBe('refresh_token=encrypted-fixture')
  })
})

describe('HTTP authentication renewal', () => {
  it('follows normal SSO redirects, isolates cookies by origin and retries only the user GET', async () => {
    const f = await fixture(), original = f.fetch.getMockImplementation()
    let userReads = 0
    f.fetch.mockImplementation(async (url, options) => {
      const u = new URL(url)
      if (u.pathname.endsWith('/developers') && userReads++ === 0) return response('', 401)
      if (u.pathname === '/login') return response('', 307, { Location: 'https://sso.garmin.com/portal/sso/en-US/sign-in?clientId=APPS_LIBRARY', 'Set-Cookie': 'NEXT_LOCALE=en; Path=/' })
      if (u.hostname === 'sso.garmin.com') {
        expect(options.headers.Cookie).toBe('sso=sso-only')
        return response('', 302, { Location: 'https://apps.garmin.com/api/auth/login?ticket=fixture-only' })
      }
      if (u.pathname === '/api/auth/login') {
        expect(options.headers.Cookie).toBe('session=fixture-only')
        return response('', 302, { Location: '/', 'Set-Cookie': 'session=renewed-fixture; Path=/; HttpOnly; Secure' })
      }
      if (u.pathname === '/') return response('HTML landing page')
      return original(url, options)
    })
    expect(await f.api.inspect()).toMatchObject({ version: '0.1.0-beta.2' })
    expect(userReads).toBe(2)
    expect(f.writes).toHaveLength(0)
    expect((await new GarminSession(f.file).load()).jar.getCookieStringSync('https://apps.garmin.com/')).toContain('session=renewed-fixture')
  })
  it.each(['https://evil.test/collect', 'http://apps.garmin.com/', 'https://apps.garmin.com:444/', 'https://user:pass@sso.garmin.com/'])('blocks an authentication redirect to %s before sending cookies', async location => {
    const f = await fixture()
    f.fetch.mockResolvedValueOnce(response('', 401)).mockResolvedValueOnce(response('', 302, { Location: location }))
    await expect(f.api.inspect()).rejects.toMatchObject({ code: 'UNSAFE_REDIRECT' })
    expect(f.fetch).toHaveBeenCalledTimes(2)
  })
  it('returns a sanitized handoff for Cloudflare and never controls a browser', async () => {
    const f = await fixture()
    f.fetch.mockResolvedValueOnce(response('', 401)).mockResolvedValueOnce(response('secret challenge body', 403, { 'cf-mitigated': 'challenge' }))
    let error
    try { await f.api.inspect() } catch (e) { error = e }
    expect(publicError(error)).toMatchObject({ code: 'AUTH_HANDOFF' })
    expect(JSON.stringify(publicError(error))).not.toContain('secret challenge body')
    expect(f.writes).toHaveLength(0)
  })
  it('bounds redirect loops and does not claim a login page is authenticated', async () => {
    const f = await fixture()
    f.fetch.mockResolvedValueOnce(response('', 403)).mockImplementation(async () => response('', 302, { Location: '/login' }))
    await expect(f.api.inspect()).rejects.toMatchObject({ code: 'AUTH_HANDOFF' })
    expect(f.fetch).toHaveBeenCalledTimes(9)
  })
})

describe('direct API deployment', () => {
  it('validates, publishes and updates release notes while preserving metadata and translations', async () => {
    const f = await fixture(), beforeUpload = vi.fn()
    const original = f.fetch.getMockImplementation()
    f.fetch.mockImplementation(async (url, options) => {
      if (options.method !== 'GET') expect(beforeUpload).toHaveBeenCalledOnce()
      return original(url, options)
    })
    expect(await f.deploy({ beforeUpload })).toMatchObject({ appId: APP_ID, version: '0.1.0-beta.3', transport: 'http' })
    expect(f.writes.map(x => x.options.method)).toEqual(['POST', 'POST', 'PUT'])
    const binary = f.writes[0].options.body.get('appBinaryFile')
    expect(Buffer.from(await binary.arrayBuffer())).toEqual(Buffer.from('fixture IQ bytes'))
    expect(f.metadata).toMatchObject({ betaApp: true, shadowApp: false, devEmail: 'fixture@example.test', paymentModel: 0, requestingTips: false, selectedAntPlusProfiles: { enteredAntPlusProfileComments: 'Keep this' } })
    expect(f.metadata.localizedAppModel).toEqual([{ appLocale: 'en', appTitle: 'openGym', appDescription: 'Keep description', appWhatsNew: 'Round controls and touch' }, { appLocale: 'ru', appTitle: 'Зал', appWhatsNew: 'Старое' }])
    const sent = JSON.parse(await f.writes[2].options.body.get('appMetadata').text())
    expect(sent).not.toHaveProperty('appIqFileInfoResult')
    expect(sent).not.toHaveProperty('appFileCoordinates')
    expect(sent).not.toHaveProperty('screenshotIds')
  })
  it.each(['owner', 'visibility', 'manifest', 'version'])('refuses changed %s before any upload', async kind => {
    const f = await fixture(), original = f.fetch.getMockImplementation()
    f.fetch.mockImplementation(async (url, options) => {
      const r = await original(url, options), u = new URL(url)
      if (u.pathname.includes('appsLibraryExternalServices')) {
        const data = await r.json()
        if (kind === 'owner') data.developerId = 'another-owner'
        if (kind === 'visibility') data.betaApp = false
        if (kind === 'version') data.latestExternalVersion = '0.1.0-beta.1'
        return response(data)
      }
      if (kind === 'manifest' && u.pathname.endsWith('/metadata')) { const data = await r.json(); data.appIqFileInfoResult.manifestAppId = 'f'.repeat(32); return response(data) }
      return r
    })
    await expect(f.deploy()).rejects.toBeDefined()
    expect(f.writes).toHaveLength(0)
  })
  it.each(['signature', 'identity', 'temporary-id'])('refuses invalid %s validation before publishing', async kind => {
    const f = await fixture(), original = f.fetch.getMockImplementation()
    f.fetch.mockImplementation(async (url, options) => {
      const r = await original(url, options)
      if (!new URL(url).pathname.endsWith('/validate')) return r
      const data = await r.json()
      if (kind === 'signature') data.iqFileInfoResult.signatureCheckSuccessFul = false
      if (kind === 'identity') data.iqFileInfoResult.manifestAppId = '0'.repeat(32)
      if (kind === 'temporary-id') data.tempFileId = '../bad'
      return response(data)
    })
    await expect(f.deploy()).rejects.toMatchObject({ code: 'INVALID_RESPONSE' })
    expect(f.writes).toHaveLength(1)
  })
  it.each([401, 403, 500, 302])('never replays a write or starts renewal after publication status %s', async status => {
    const f = await fixture(), original = f.fetch.getMockImplementation()
    f.fetch.mockImplementation(async (url, options) => {
      const r = await original(url, options)
      return new URL(url).pathname.endsWith('/version') ? response('private failure', status, { Location: '/login' }) : r
    })
    await expect(f.deploy()).rejects.toMatchObject({ code: 'GARMIN_HTTP_ERROR' })
    expect(f.writes.map(x => x.options.method)).toEqual(['POST', 'POST'])
    expect(f.fetch.mock.calls.some(([url]) => new URL(url).pathname === '/login')).toBe(false)
  })
  it('uses freshly read metadata after publication rather than overwriting a concurrent description edit', async () => {
    const f = await fixture(), original = f.fetch.getMockImplementation()
    f.fetch.mockImplementation(async (url, options) => {
      const r = await original(url, options)
      if (new URL(url).pathname.endsWith('/version')) f.metadata.localizedAppModel[0].appDescription = 'Latest edit'
      return r
    })
    await f.deploy()
    expect(f.metadata.localizedAppModel[0].appDescription).toBe('Latest edit')
  })
  it('rejects oversized and invalid JSON responses without returning raw response text', async () => {
    const f = await fixture()
    f.fetch.mockResolvedValueOnce(response('private text'))
    await expect(f.api.inspect()).rejects.toMatchObject({ code: 'INVALID_RESPONSE' })
    f.fetch.mockResolvedValueOnce(response('x'.repeat(2 * 1024 * 1024 + 1)))
    await expect(f.api.inspect()).rejects.toMatchObject({ code: 'RESPONSE_TOO_LARGE' })
  })
})
