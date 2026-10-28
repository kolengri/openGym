import path from 'node:path'
import { open, rename, lstat, unlink } from 'node:fs/promises'
import { randomUUID } from 'node:crypto'
import { Cookie, CookieJar } from 'tough-cookie'
import { APP_ID, MANIFEST_ID, versionSchema, fail } from './contract.js'
import { directory, readFileSafe } from './artifact.js'
import { writeOnce } from './http-write.js'

const ORIGIN = 'https://apps.garmin.com'
const USER = '/api/ciq-developerservices/developers'
const APP = `/api/appsLibraryExternalServices/api/asw/apps/${APP_ID}`
const MAX_RESPONSE = 2 * 1024 * 1024
const hosts = new Set(['apps.garmin.com', 'sso.garmin.com'])

function allowedUrl(value) {
  const u = new URL(value)
  if (u.protocol !== 'https:' || !hosts.has(u.hostname) || u.port || u.username || u.password || u.hash) {
    fail('UNSAFE_REDIRECT', 'Garmin authentication redirected outside the pinned HTTPS origins.')
  }
  return u
}

// Cookie parsing, expiry, domain/path matching and rotation belong to tough-cookie.
// No browser process or debugging connection is used by this transport.
export class GarminSession {
  constructor(file) { this.file = file; this.jar = null }

  async load() {
    const stat = await lstat(this.file)
    if (!stat.isFile() || stat.isSymbolicLink() || (stat.mode & 0o077)) fail('PRIVATE_SESSION_REQUIRED', 'The HTTP session must be a private regular file with mode 0600.')
    const data = JSON.parse((await readFileSafe(this.file, 256 * 1024)).toString('utf8'))
    if (data.schemaVersion !== 1 || !data.jar) fail('INVALID_SESSION', 'Import the Garmin cookie session using the local setup command.')
    const jar = await CookieJar.deserialize(data.jar)
    for (const cookie of jar.serializeSync().cookies) {
      if (!hosts.has(cookie.domain) || cookie.hostOnly !== true || cookie.secure !== true) fail('INVALID_SESSION', 'Only secure host-only Garmin Store and SSO cookies are accepted.')
    }
    this.jar = jar
    return this
  }

  async import(cookies) {
    if (!Array.isArray(cookies) || cookies.length > 100) fail('INVALID_SESSION', 'The cookie export is invalid or oversized.')
    const jar = new CookieJar()
    for (const cookie of cookies) {
      // Ignore unrelated domains rather than importing the personal browser profile.
      if (!hosts.has(cookie.domain)) continue
      if (!cookie.secure || typeof cookie.name !== 'string' || typeof cookie.value !== 'string' || /[\x00-\x20\x7f;=]/.test(cookie.name) || /[\x00-\x20\x7f;]/.test(cookie.value) || typeof cookie.path !== 'string' || !cookie.path.startsWith('/') || /[\x00-\x20\x7f;]/.test(cookie.path)) fail('INVALID_SESSION', 'The Garmin cookie export contains invalid fields.')
      const expiry = cookie.expires > 0 ? `; Expires=${new Date(cookie.expires * 1000).toUTCString()}` : ''
      await jar.setCookie(`${cookie.name}=${cookie.value}; Path=${cookie.path}; Secure${cookie.httpOnly ? '; HttpOnly' : ''}${expiry}`, `https://${cookie.domain}${cookie.path}`)
    }
    if (!(await jar.getCookies(ORIGIN)).some(c => c.key === 'session' || c.key === 'refresh_token')) fail('INVALID_SESSION', 'The export contains no Garmin Store session.')
    this.jar = jar
    await this.save()
  }

  async save() {
    await directory(path.dirname(this.file))
    const temp = `${this.file}.${randomUUID()}.tmp`
    let handle
    try {
      handle = await open(temp, 'wx', 0o600)
      await handle.writeFile(JSON.stringify({ schemaVersion: 1, jar: this.jar.serializeSync() }) + '\n')
      await handle.sync()
      await handle.close(); handle = null
      await rename(temp, this.file)
      const parent = await open(path.dirname(this.file), 'r')
      try { await parent.sync() } finally { await parent.close() }
    } finally {
      await handle?.close()
      await unlink(temp).catch(e => { if (e.code !== 'ENOENT') throw e })
    }
  }
}

async function boundedBody(response) {
  const length = response.headers.get('content-length')
  if (length && Number(length) > MAX_RESPONSE) {
    await response.body?.cancel()
    fail('RESPONSE_TOO_LARGE', 'Garmin returned an oversized response.')
  }
  const reader = response.body?.getReader()
  if (!reader) return ''
  const chunks = []
  let size = 0
  try {
    for (;;) {
      const { value, done } = await reader.read()
      if (done) break
      size += value.length
      if (size > MAX_RESPONSE) fail('RESPONSE_TOO_LARGE', 'Garmin returned an oversized response.')
      chunks.push(value)
    }
    return Buffer.concat(chunks).toString('utf8')
  } finally { await reader.cancel() }
}

// Fields assigned by Garmin's update form, excluding read-only media/file metadata.
const writableFields = [
  'additionalAndroidAppUrls', 'additionalIosAppUrls', 'androidAppUrl', 'iosAppUrl',
  'betaApp', 'shadowApp', 'category', 'subCategory', 'devEmail', 'hardwareProductUrl',
  'localizedAppModel', 'migrationAllowed', 'policyUrl', 'reviewNotificationActive',
  'selectedActivityTypes', 'selectedAntPlusProfiles', 'selectedCountries', 'sourceUrl',
  'videoUrl', 'paymentModel', 'pricingPartNumber', 'requiringExternalSubscription', 'requestingTips'
]

function validManifest(info) {
  return info?.manifestAppId?.replaceAll('-', '').toLowerCase() === MANIFEST_ID &&
    info.signatureCheckSuccessFul === true && info.appType === 'Device App'
}

export class GarminApi {
  constructor(sessionFile, { fetchImpl = globalThis.fetch, writeImpl = writeOnce } = {}) {
    this.session = new GarminSession(sessionFile)
    this.fetch = fetchImpl
    this.write = writeImpl
  }

  async request(url, { method = 'GET', body, headers = {} } = {}) {
    const u = allowedUrl(new URL(url, ORIGIN))
    if (method !== 'GET' && u.origin !== ORIGIN) fail('UNSAFE_REDIRECT', 'Release writes are restricted to Garmin Store.')
    const cookies = await this.session.jar.getCookieString(u.href)
    const send = method === 'GET' ? this.fetch : this.write
    const response = await send(u.href, {
      method, body, redirect: 'manual', signal: AbortSignal.timeout(30000),
      headers: { Accept: 'application/json', ...headers, ...(cookies ? { Cookie: cookies } : {}), ...(method !== 'GET' ? { Origin: ORIGIN, 'X-Correlation-Id': randomUUID() } : {}) }
    })
    const setCookies = response.headers.getSetCookie()
    try {
      for (const value of setCookies) {
        const parsed = Cookie.parse(value)
        if (!parsed) fail('INVALID_SESSION', 'Garmin returned an invalid cookie.')
        // Locale/analytics and domain-wide cookies are not authentication state.
        if (!parsed.secure || (parsed.domain && parsed.domain !== u.hostname)) continue
        parsed.domain = undefined
        parsed.hostOnly = true
        await this.session.jar.setCookie(parsed, u.href)
      }
      // Persist rotations before another operation, including authentication errors.
      if (setCookies.length) await this.session.save()
      const text = await boundedBody(response)
      if (response.headers.get('cf-mitigated') === 'challenge') fail('AUTH_HANDOFF', 'Garmin requires an interactive security check. No browser is controlled and no upload is retried.')
      return { status: response.status, location: response.headers.get('location'), text }
    } catch (e) { await response.body?.cancel().catch(() => {}); throw e }
  }

  json(response) {
    if (response.status < 200 || response.status >= 300) fail('GARMIN_HTTP_ERROR', 'Garmin rejected the API request. No write is retried automatically.')
    try { return JSON.parse(response.text) } catch { fail('INVALID_RESPONSE', 'Garmin returned an invalid API response.') }
  }

  async renew() {
    // This is the actual Store login entrypoint, not a guessed refresh-token API.
    // Normal SSO redirects may renew an existing SSO session without interaction.
    let url = `${ORIGIN}/login`
    for (let i = 0; i < 8; i++) {
      const response = await this.request(url)
      if (response.status >= 300 && response.status < 400 && response.location) {
        url = allowedUrl(new URL(response.location, url)).href
        continue
      }
      if (new URL(url).origin === ORIGIN && response.status === 200) return
      break
    }
    fail('AUTH_HANDOFF', 'Garmin could not renew the HTTP session without interactive login, MFA or a security check. Import a renewed session locally.')
  }

  async authenticatedUser() {
    let response = await this.request(USER)
    if ([401, 403].includes(response.status) || (response.status >= 300 && response.status < 400)) {
      await this.renew()
      response = await this.request(USER)
    }
    if ([401, 403].includes(response.status)) fail('AUTH_HANDOFF', 'The Garmin HTTP session is no longer authenticated.')
    const user = this.json(response)
    if (user.developer !== true || typeof user.userId !== 'string' || !/^[a-zA-Z0-9_-]{1,100}$/.test(user.userId)) fail('OWNER_MISMATCH', 'The authenticated account is not a Garmin developer.')
    return user.userId
  }

  async inspectLoaded() {
    const owner = await this.authenticatedUser()
    const app = this.json(await this.request(APP))
    const metadataPath = `${USER}/${owner}/apps/${APP_ID}/metadata?isShadowApp=false`
    const metadata = this.json(await this.request(metadataPath))
    if (app.id !== APP_ID || app.developerId !== owner || app.betaApp !== true || metadata.betaApp !== true || metadata.shadowApp !== false) fail('OWNER_MISMATCH', 'The existing owner beta identity or visibility changed.')
    const version = versionSchema.safeParse(app.latestExternalVersion)
    if (!version.success || !validManifest(metadata.appIqFileInfoResult) || metadata.appIqFileInfoResult.newAppVersion !== version.data) fail('REMOTE_VERSION_MISMATCH', 'Garmin beta version or signed manifest identity could not be verified.')
    if (!Array.isArray(metadata.localizedAppModel) || !metadata.localizedAppModel.some(x => x.appLocale === 'en')) fail('INVALID_RESPONSE', 'The existing English beta localization is missing.')
    return { owner, metadata, version: version.data, pending: app.hasVersionPendingScan === true }
  }

  async inspect() {
    await this.session.load()
    const { version } = await this.inspectLoaded()
    return { appId: APP_ID, manifestId: MANIFEST_ID, version, ownerOnlyBeta: true, transport: 'http' }
  }

  async deploy({ version, expectedCurrentVersion, releaseNotes, bytes, beforeUpload }) {
    await this.session.load()
    const initial = await this.inspectLoaded()
    if (initial.version !== expectedCurrentVersion) fail('REMOTE_VERSION_MISMATCH', 'The current Garmin beta differs from the expected version.')
    if (initial.pending) fail('VERSION_PENDING', 'Garmin is still processing a previous version.')
    await beforeUpload()
    const binary = new FormData()
    binary.append('appBinaryFile', new Blob([bytes]), `opengym-garmin-${version}.iq`)
    const validation = this.json(await this.request(`/api/ciq-developerservices/iqFiles/validate?${new URLSearchParams({ isNewAppVersion: 'true', appVersion: version, appId: APP_ID })}`, { method: 'POST', body: binary }))
    // The live validation response has no newAppVersion. Store version is assigned
    // by our explicit version POST and verified through app/metadata GETs afterward.
    if (typeof validation.tempFileId !== 'string' || !/^[a-zA-Z0-9_-]{1,200}$/.test(validation.tempFileId) || !validManifest(validation.iqFileInfoResult)) fail('INVALID_RESPONSE', 'Garmin did not validate the expected signed beta artifact.')
    const appPath = `${USER}/${initial.owner}/apps/${APP_ID}`
    // Never renew/replay a write, even if an access session expires between steps.
    const published = await this.request(`${appPath}/version?locale=en-US&juniorAppUpdate=false`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tempFileId: validation.tempFileId, appVersion: version })
    })
    if (published.status < 200 || published.status >= 300) fail('GARMIN_HTTP_ERROR', 'Garmin did not confirm the version publication. Automatic retry is blocked.')
    // Refresh metadata after publication; preserve existing localization and settings.
    const fresh = await this.inspectLoaded()
    if (fresh.owner !== initial.owner || fresh.version !== version) fail('REMOTE_VERSION_MISMATCH', 'Garmin has not confirmed the new beta version under the original owner.')
    const metadata = Object.fromEntries(writableFields.filter(key => Object.hasOwn(fresh.metadata, key)).map(key => [key, fresh.metadata[key]]))
    metadata.localizedAppModel = fresh.metadata.localizedAppModel.map(item => item.appLocale === 'en' ? { ...item, appWhatsNew: releaseNotes } : item)
    metadata.tempFileId = validation.tempFileId
    metadata.externalAppVersion = version
    const detail = new FormData()
    detail.append('appMetadata', new Blob([JSON.stringify(metadata)], { type: 'application/json' }))
    const updated = await this.request(appPath, { method: 'PUT', body: detail })
    if (updated.status < 200 || updated.status >= 300) fail('GARMIN_HTTP_ERROR', 'The beta version may be published but its release notes were not confirmed. Automatic retry is blocked.')
    const final = await this.inspectLoaded()
    if (final.owner !== initial.owner || final.version !== version || final.metadata.localizedAppModel.find(x => x.appLocale === 'en')?.appWhatsNew !== releaseNotes) fail('INVALID_EVIDENCE', 'Garmin did not confirm the updated beta and release notes.')
    return { appId: APP_ID, version, ownerOnlyBeta: true, transport: 'http' }
  }
}
