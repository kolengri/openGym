import { afterEach, describe, expect, it, vi } from 'vitest'
import path from 'node:path'
import { mkdtemp, writeFile, readFile, rm, chmod, symlink, readdir, mkdir } from 'node:fs/promises'
import { APP_ID, BASE_VERSION, RELEASE_HOME, browserConfigSchema, parse, publicError, isTargetUrl } from '../src/garmin-release/contract.js'
import { sha256, validateIq, directory } from '../src/garmin-release/artifact.js'
import { ReleaseService } from '../src/garmin-release/service.js'
import { iq, VERSION, config } from './garmin-release-fixture.js'

const homes = []
afterEach(async () => { for (const home of homes.splice(0)) await rm(home, { recursive: true, force: true }) })

async function fixture(browserDeploy = async ({ beforeUpload, version }) => {
  await beforeUpload()
  return { appId: APP_ID, version, ownerOnlyBeta: true }
}) {
  await directory(path.join(RELEASE_HOME, 'tests'))
  const home = await mkdtemp(path.join(RELEASE_HOME, 'tests/service-'))
  homes.push(home)
  const deploy = vi.fn(browserDeploy)
  const service = new ReleaseService({ home, enabled: true, browserFactory: () => ({ deploy }) })
  await service.init()
  await writeFile(service.configFile, JSON.stringify(config), { mode: 0o600 })
  await service.writeJson(path.join(service.privateDir, 'session-ready.json'), { appId: APP_ID })
  const bytes = iq(), hash = sha256(bytes)
  await writeFile(path.join(home, 'inbox', `opengym-garmin-${VERSION}.iq`), bytes)
  const request = { appId: APP_ID, version: VERSION, sha256: hash }
  const deployment = { ...request, expectedCurrentVersion: BASE_VERSION, confirmOwnerOnlyBeta: true, confirmSubmissionTerms: true, releaseNotes: 'Fix beta watch controls.' }
  return { home, service, deploy, request, deployment, bytes }
}

describe('IQ boundary', () => {
  it('validates the actual manifest identity and hash, with caller-assigned Store version', async () => {
    const bytes = iq()
    expect(await validateIq(bytes, VERSION, sha256(bytes))).toMatchObject({ version: VERSION, bytes: bytes.length,
      archiveFormat: '7z', versionSource: 'caller-assigned-store-metadata', signatureVerification: 'not-verified' })
    await expect(validateIq(bytes, VERSION, '0'.repeat(64))).rejects.toMatchObject({ code: 'HASH_MISMATCH' })
  })
  it.each([
    [{ id: 'f'.repeat(32) }, 'MANIFEST_MISMATCH'],
    [{ type: 'watchface' }, 'MANIFEST_MISMATCH'],
    [{ binary: false }, 'INVALID_IQ'],
    [{ xml: '<!DOCTYPE manifest [<!ENTITY secret SYSTEM "file:///private">]><manifest/>' }, 'INVALID_IQ'],
    [{ xml: '<manifest><application/><application/></manifest>' }, 'INVALID_IQ'],
    [{ xml: '<manifest>' }, 'INVALID_IQ']
  ])('rejects invalid package metadata %j', async (options, code) => {
    const bytes = iq(options)
    await expect(validateIq(bytes, VERSION, sha256(bytes))).rejects.toMatchObject({ code })
  })
})

describe('offline preparation and fixed target', () => {
  it('creates a versioned snapshot and SHA256 receipt, reuses an identical preparation', async () => {
    const f = await fixture()
    const receipt = await f.service.prepare(f.request)
    expect(receipt).toMatchObject({ ...f.request, versionSource: 'caller-assigned-store-metadata', signatureVerification: 'not-verified' })
    expect(receipt.artifact).toContain(`releases/${VERSION}/`)
    expect(await readFile(path.join(f.service.releaseDir(VERSION), `opengym-garmin-${VERSION}.iq`))).toEqual(f.bytes)
    expect(await f.service.prepare(f.request)).toEqual(receipt)
    expect(f.deploy).not.toHaveBeenCalled()
    expect(await f.service.status({ version: VERSION })).toMatchObject({ state: 'prepared', sha256: f.request.sha256 })
  })
  it('never accepts paths, commands, a different app, traversal or an old beta', async () => {
    const { service, request } = await fixture()
    for (const change of [{ appId: 'other' }, { version: '../private' }, { command: 'touch /tmp/unsafe' }, { sourcePath: '/data/db.json' }]) {
      await expect(service.prepare({ ...request, ...change })).rejects.toMatchObject({ code: 'INVALID_INPUT' })
    }
    await expect(service.prepare({ ...request, version: BASE_VERSION })).rejects.toMatchObject({ code: 'VERSION_NOT_NEWER' })
  })
  it('refuses to replace a version with different bytes', async () => {
    const { service, home, request } = await fixture()
    await service.prepare(request)
    const changed = iq({ extra: '<!-- changed -->' })
    await writeFile(path.join(home, 'inbox', `opengym-garmin-${VERSION}.iq`), changed)
    await expect(service.prepare({ ...request, sha256: sha256(changed) })).rejects.toMatchObject({ code: 'VERSION_CONFLICT' })
  })
  it.each(['receipt', 'partial snapshot', 'receipt temp'])('can retry preparation after a %s write failure', async failure => {
    const f = await fixture()
    const writer = vi.spyOn(f.service, 'writeJson').mockImplementationOnce(async file => {
      const staging = path.dirname(file)
      expect(await readFile(path.join(staging, `opengym-garmin-${VERSION}.iq`))).toEqual(f.bytes)
      if (failure === 'partial snapshot') await writeFile(path.join(staging, `opengym-garmin-${VERSION}.iq`), f.bytes.subarray(0, 12))
      if (failure === 'receipt temp') await writeFile(`${file}.tmp`, '{', { mode: 0o600 })
      throw new Error('Injected local preparation failure')
    })
    await expect(f.service.prepare(f.request)).rejects.toThrow('Injected local preparation failure')
    writer.mockRestore()
    expect(await readdir(path.join(f.home, 'releases'))).toEqual([])
    expect(await f.service.status({ version: VERSION })).toMatchObject({ prepared: false, state: 'missing', operationLocked: false })
    expect(await f.service.prepare(f.request)).toMatchObject({ sha256: f.request.sha256, version: VERSION })
    expect(await readFile(path.join(f.service.releaseDir(VERSION), `opengym-garmin-${VERSION}.iq`))).toEqual(f.bytes)
    expect(await f.service.status({ version: VERSION })).toMatchObject({ prepared: true, state: 'prepared' })
    expect(f.deploy).not.toHaveBeenCalled()
  })
  it('ignores abandoned private staging from an interrupted process when preparing a version', async () => {
    const f = await fixture()
    const abandoned = path.join(f.home, 'releases', '.prepare-abandoned')
    await mkdir(abandoned, { mode: 0o700 })
    await writeFile(path.join(abandoned, 'receipt.json.tmp'), '{', { mode: 0o600 })
    await writeFile(path.join(abandoned, `opengym-garmin-${VERSION}.iq`), f.bytes.subarray(0, 12), { mode: 0o600 })
    expect(await f.service.prepare(f.request)).toMatchObject({ sha256: f.request.sha256 })
    expect(await f.service.prepare(f.request)).toMatchObject({ sha256: f.request.sha256 })
    expect(await readFile(path.join(abandoned, 'receipt.json.tmp'), 'utf8')).toBe('{')
    expect(f.deploy).not.toHaveBeenCalled()
  })
  it('rejects symlinked IQ files and directories without reading their targets', async () => {
    const { service, home, request } = await fixture()
    const file = path.join(home, 'inbox', `opengym-garmin-${VERSION}.iq`)
    await rm(file)
    await symlink(service.configFile, file)
    await expect(service.prepare(request)).rejects.toMatchObject({ code: 'ELOOP' })
    const linked = path.join(home, 'linked')
    await symlink(path.join(home, 'private'), linked)
    await expect(directory(path.join(linked, 'nested'))).rejects.toMatchObject({ code: 'UNSAFE_PATH' })
  })
  it('accepts only a reviewed existing Garmin developer listing with a private config', async () => {
    expect(isTargetUrl(`https://apps.garmin.com/en-US/apps/${APP_ID}`)).toBe(true)
    for (const url of ['https://connect.garmin.com/apps/' + APP_ID, 'https://evil.test/apps/' + APP_ID,
      'https://apps-developer.garmin.com/new?app=' + APP_ID, `https://user:pass@apps-developer.garmin.com/apps/${APP_ID}`]) expect(isTargetUrl(url)).toBe(false)
    expect(() => parse(browserConfigSchema, { ...config, reviewedForExistingOwnerBeta: false })).toThrow()
    const { service } = await fixture()
    await chmod(service.configFile, 0o644)
    await expect(service.config()).rejects.toMatchObject({ code: 'PRIVATE_CONFIG_REQUIRED' })
  })
})

describe('deployment intent and retry boundaries', () => {
  it('persists upload intent before exposing bytes and replays only an identical verified success', async () => {
    const f = await fixture(async ({ beforeUpload, version, bytes }) => {
      await beforeUpload()
      expect(await f.service.readJson(path.join(f.service.releaseDir(VERSION), 'journal.json'))).toMatchObject({ state: 'uploading', sha256: sha256(bytes) })
      return { appId: APP_ID, version, ownerOnlyBeta: true }
    })
    await f.service.prepare(f.request)
    const result = await f.service.deploy(f.deployment)
    expect(result).toMatchObject({ state: 'deployed', ownerOnlyBeta: true, ...f.request })
    expect(await f.service.deploy(f.deployment)).toEqual(result)
    expect(f.deploy).toHaveBeenCalledTimes(1)
    await expect(f.service.deploy({ ...f.deployment, releaseNotes: 'Different intent.' })).rejects.toMatchObject({ code: 'RETRY_BLOCKED' })
  })
  it('blocks ambiguous failures across service restarts and redacts the browser error', async () => {
    const f = await fixture(async ({ beforeUpload }) => { await beforeUpload(); throw new Error('session cookie secret-value https://private.example') })
    await f.service.prepare(f.request)
    await expect(f.service.deploy(f.deployment)).rejects.toMatchObject({ code: 'UPLOAD_UNCERTAIN' })
    const text = await readFile(path.join(f.service.releaseDir(VERSION), 'journal.json'), 'utf8')
    expect(text).not.toContain('secret-value')
    expect(JSON.parse(text)).toMatchObject({ state: 'uncertain', failureCode: 'LOCAL_FAILURE' })
    const restarted = new ReleaseService({ home: f.home, enabled: true, browserFactory: () => { throw new Error('Must not launch') } })
    await expect(restarted.deploy(f.deployment)).rejects.toMatchObject({ code: 'RETRY_BLOCKED' })
  })
  it('blocks interrupted uploading intents without requiring a new idempotency key', async () => {
    const f = await fixture()
    await f.service.prepare(f.request)
    await f.service.writeJson(path.join(f.service.releaseDir(VERSION), 'journal.json'), { state: 'uploading' })
    await expect(f.service.deploy(f.deployment)).rejects.toMatchObject({ code: 'RETRY_BLOCKED' })
    expect(f.deploy).not.toHaveBeenCalled()
  })
  it('blocks a later version while an earlier upload may still be processing', async () => {
    const f = await fixture(async ({ beforeUpload }) => { await beforeUpload(); throw new Error('timeout') })
    await f.service.prepare(f.request)
    await expect(f.service.deploy(f.deployment)).rejects.toMatchObject({ code: 'UPLOAD_UNCERTAIN' })
    const version = '0.1.0-beta.4', bytes = iq({ version })
    const request = { appId: APP_ID, version, sha256: sha256(bytes) }
    await writeFile(path.join(f.home, 'inbox', `opengym-garmin-${version}.iq`), bytes)
    await f.service.prepare(request)
    await expect(f.service.deploy({ ...f.deployment, ...request })).rejects.toMatchObject({ code: 'RETRY_BLOCKED' })
    expect(await f.service.status()).toMatchObject({ unresolvedDeployment: { version: VERSION, state: 'uncertain' } })
    expect(f.deploy).toHaveBeenCalledOnce()
  })
  it('permits the next version after a verified deployment', async () => {
    const f = await fixture()
    await f.service.prepare(f.request)
    await f.service.deploy(f.deployment)
    const version = '0.1.0-beta.4', bytes = iq({ version })
    const request = { appId: APP_ID, version, sha256: sha256(bytes) }
    await writeFile(path.join(f.home, 'inbox', `opengym-garmin-${version}.iq`), bytes)
    await f.service.prepare(request)
    expect(await f.service.deploy({ ...f.deployment, ...request, expectedCurrentVersion: VERSION })).toMatchObject({ state: 'deployed', version })
    expect(f.deploy).toHaveBeenCalledTimes(2)
    expect(await f.service.status()).toMatchObject({ unresolvedDeployment: null })
  })
  it('allows safe retry after a preflight failure that never handed over the file', async () => {
    const f = await fixture(async () => { throw new Error('Login required') })
    await f.service.prepare(f.request)
    await expect(f.service.deploy(f.deployment)).rejects.toThrow('Login required')
    expect(await f.service.status({ version: VERSION })).toMatchObject({ state: 'prepared' })
    f.deploy.mockImplementationOnce(async ({ beforeUpload, version }) => { await beforeUpload(); return { appId: APP_ID, version, ownerOnlyBeta: true } })
    expect(await f.service.deploy(f.deployment)).toMatchObject({ state: 'deployed' })
  })
  it('refuses disabled, unpaired, unconfirmed and non-increasing deployments', async () => {
    const f = await fixture()
    await f.service.prepare(f.request)
    f.service.enabled = false
    await expect(f.service.deploy(f.deployment)).rejects.toMatchObject({ code: 'DEPLOY_DISABLED' })
    f.service.enabled = true
    await expect(f.service.deploy({ ...f.deployment, confirmOwnerOnlyBeta: false })).rejects.toMatchObject({ code: 'INVALID_INPUT' })
    await expect(f.service.deploy({ ...f.deployment, confirmSubmissionTerms: false })).rejects.toMatchObject({ code: 'INVALID_INPUT' })
    const withoutTerms = { ...f.deployment }; delete withoutTerms.confirmSubmissionTerms
    await expect(f.service.deploy(withoutTerms)).rejects.toMatchObject({ code: 'INVALID_INPUT' })
    await expect(f.service.deploy({ ...f.deployment, expectedCurrentVersion: VERSION })).rejects.toMatchObject({ code: 'VERSION_NOT_NEWER' })
    await rm(path.join(f.service.privateDir, 'session-ready.json'))
    await expect(f.service.deploy(f.deployment)).rejects.toMatchObject({ code: 'AUTH_HANDOFF' })
    expect(f.deploy).not.toHaveBeenCalled()
  })
  it('rehashes the exact prepared buffer before handing it to the browser', async () => {
    const f = await fixture()
    await f.service.prepare(f.request)
    await writeFile(path.join(f.service.releaseDir(VERSION), `opengym-garmin-${VERSION}.iq`), iq({ extra: '<!-- swapped -->' }))
    await expect(f.service.deploy(f.deployment)).rejects.toMatchObject({ code: 'HASH_MISMATCH' })
    expect(f.deploy).not.toHaveBeenCalled()
  })
  it('rejects concurrent operations across service instances without resetting the lock', async () => {
    let entered, finish
    const ready = new Promise(resolve => { entered = resolve })
    const wait = new Promise(resolve => { finish = resolve })
    const f = await fixture(async ({ beforeUpload, version }) => {
      await beforeUpload(); entered(); await wait
      return { appId: APP_ID, version, ownerOnlyBeta: true }
    })
    await f.service.prepare(f.request)
    const first = f.service.deploy(f.deployment)
    await ready
    const second = new ReleaseService({ home: f.home, enabled: true })
    try {
      await expect(second.deploy(f.deployment)).rejects.toMatchObject({ code: 'OPERATION_LOCKED' })
      expect(await second.status({ version: VERSION })).toMatchObject({ operationLocked: true, state: 'uploading' })
    } finally { finish(); await first }
  })
  it('treats missing remote beta evidence after file selection as uncertain', async () => {
    const f = await fixture(async ({ beforeUpload, version }) => { await beforeUpload(); return { appId: APP_ID, version, ownerOnlyBeta: false } })
    await f.service.prepare(f.request)
    await expect(f.service.deploy(f.deployment)).rejects.toMatchObject({ code: 'UPLOAD_UNCERTAIN' })
    expect(publicError(new Error('private cookie'))).toEqual({ code: 'LOCAL_FAILURE', message: expect.not.stringContaining('cookie') })
  })
})
