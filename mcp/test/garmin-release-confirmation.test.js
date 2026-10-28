import { afterEach, describe, expect, it, vi } from 'vitest'
import path from 'node:path'
import { mkdtemp, rm, writeFile, unlink } from 'node:fs/promises'
import { APP_ID, BASE_VERSION, MANIFEST_ID, PROJECT_ROOT, CONFIRMATION_INTERVAL_MS, CONFIRMATION_WINDOW_MS } from '../src/garmin-release/contract.js'
import { directory, sha256 } from '../src/garmin-release/artifact.js'
import { GarminApi, GarminSession } from '../src/garmin-release/api.js'
import { ReleaseService } from '../src/garmin-release/service.js'
import { ConfirmationMonitor } from '../src/garmin-release/monitor.js'
import { iq, VERSION } from './garmin-release-fixture.js'

const homes = [], monitors = []
afterEach(async () => {
  for (const monitor of monitors.splice(0)) monitor.stop()
  for (const home of homes.splice(0)) await rm(home, { recursive: true, force: true })
})

async function fixture({ failureAt, status = 421 } = {}) {
  const root = path.join(PROJECT_ROOT, 'artifacts/garmin-ux/release/.tests')
  await directory(root)
  const home = await mkdtemp(path.join(root, 'confirmation-'))
  homes.push(home)
  const clock = { value: Date.parse('2026-10-28T00:00:00Z') }, now = () => clock.value
  const remote = { owner: 'confirmation-owner', summary: BASE_VERSION, binary: BASE_VERSION,
    lag: true, notes: 'Previous notes', afterWritesError: null, change: null }
  const writes = []
  const get = vi.fn(async (url, options) => {
    expect(options.method).toBe('GET')
    if (writes.length === 3 && remote.afterWritesError) throw remote.afterWritesError
    const u = new URL(url)
    if (u.pathname.endsWith('/developers')) return Response.json({ userId: remote.owner, developer: true })
    if (u.pathname.includes('appsLibraryExternalServices')) return Response.json({ id: APP_ID, developerId: remote.owner,
      betaApp: true, latestExternalVersion: remote.summary })
    if (u.pathname.endsWith('/metadata')) {
      const data = { betaApp: true, shadowApp: false,
        appIqFileInfoResult: { manifestAppId: MANIFEST_ID, signatureCheckSuccessFul: true, appType: 'Device App', newAppVersion: remote.binary },
        localizedAppModel: [{ appLocale: 'en', appWhatsNew: remote.notes }] }
      if (writes.length >= 2) remote.change?.(data)
      return Response.json(data)
    }
    throw new Error('Unexpected fixture GET')
  })
  const write = vi.fn(async (url, options) => {
    const u = new URL(url)
    const phase = u.pathname.endsWith('/validate') ? 'validation' : u.pathname.endsWith('/version') ? 'version' : 'details'
    writes.push({ phase, method: options.method })
    if (phase === failureAt) return new Response('private rejected body', { status })
    if (phase === 'validation') return Response.json({ tempFileId: 'confirmation-temporary-id',
      iqFileInfoResult: { manifestAppId: MANIFEST_ID, signatureCheckSuccessFul: true, appType: 'Device App' } })
    if (phase === 'version') remote.binary = JSON.parse(options.body).appVersion
    else {
      const metadata = JSON.parse(await options.body.get('appMetadata').text())
      remote.notes = metadata.localizedAppModel[0].appWhatsNew
      if (!remote.lag) remote.summary = remote.binary
    }
    return new Response('')
  })
  const apiFactory = file => new GarminApi(file, { fetchImpl: get, writeImpl: write })
  const service = new ReleaseService({ home, enabled: true, apiFactory, now })
  await service.init()
  await new GarminSession(service.sessionFile).import([{ name: 'session', value: 'confirmation-cookie', domain: 'apps.garmin.com', path: '/', secure: true, httpOnly: true, expires: -1 }])
  await service.writeJson(path.join(service.privateDir, 'session-ready.json'), { appId: APP_ID })
  const bytes = iq(), request = { appId: APP_ID, version: VERSION, sha256: sha256(bytes) }
  await writeFile(path.join(home, 'inbox', `opengym-garmin-${VERSION}.iq`), bytes)
  await service.prepare(request)
  const deployment = { ...request, expectedCurrentVersion: BASE_VERSION, confirmOwnerOnlyBeta: true, confirmSubmissionTerms: true, releaseNotes: 'Exact accepted release notes.' }
  const journalFile = path.join(service.releaseDir(VERSION), 'journal.json')
  const restart = () => new ReleaseService({ home, enabled: false, apiFactory, now })
  return { service, remote, writes, write, get, deployment, journalFile, restart, clock, now }
}

function scheduler(f, service = f.service) {
  const tasks = new Map()
  const schedule = vi.fn((fn, delay) => {
    const timer = { at: f.now() + delay, fn, unref: vi.fn() }
    tasks.set(timer, timer)
    return timer
  })
  const monitor = new ConfirmationMonitor(service, { now: f.now, schedule, cancel: timer => tasks.delete(timer) })
  monitors.push(monitor)
  const fire = async () => {
    const timer = [...tasks.values()].sort((a, b) => a.at - b.at)[0]
    expect(timer).toBeDefined()
    tasks.delete(timer)
    f.clock.value = timer.at
    await timer.fn()
  }
  return { monitor, tasks, schedule, fire }
}

describe('durable accepted submission', () => {
  it('returns pending after one verification pass and keeps private phase proof off tool outputs', async () => {
    const f = await fixture()
    const result = await f.service.deploy(f.deployment)
    expect(result).toMatchObject({ state: 'awaiting_confirmation', verification: { status: 'pending', attempts: 1 } })
    expect(f.writes.map(x => x.method)).toEqual(['POST', 'POST', 'PUT'])
    const journal = await f.service.readJson(f.journalFile)
    expect(journal).toMatchObject({ state: 'awaiting_confirmation', request: f.deployment,
      confirmation: { phase: 'details_accepted', owner: 'confirmation-owner', tempFileId: 'confirmation-temporary-id',
        previousVersion: BASE_VERSION, releaseNotes: f.deployment.releaseNotes,
        validatedAt: expect.any(String), version_acceptedAt: expect.any(String), details_acceptedAt: expect.any(String) } })
    const calls = f.get.mock.calls.length
    const offline = await f.service.status({ version: VERSION })
    expect(f.get).toHaveBeenCalledTimes(calls)
    expect(offline).toMatchObject({ state: 'awaiting_confirmation', operationLocked: false })
    expect(JSON.stringify({ result, offline })).not.toMatch(/confirmation-owner|confirmation-temporary-id|confirmation-cookie|Exact accepted/)
  })

  it('preserves accepted proof when subsequent GETs fail, then resumes with GETs only and deploy disabled', async () => {
    const f = await fixture()
    f.remote.afterWritesError = new Error('confirmation-cookie confirmation-temporary-id private body')
    expect(await f.service.deploy(f.deployment)).toMatchObject({ state: 'awaiting_confirmation', verification: { status: 'error', errorCode: 'LOCAL_FAILURE' } })
    expect(await f.service.readJson(f.journalFile)).toMatchObject({ confirmation: { tempFileId: 'confirmation-temporary-id', phase: 'details_accepted' } })
    f.remote.afterWritesError = null
    f.remote.summary = VERSION
    const restarted = f.restart()
    await unlink(path.join(restarted.privateDir, 'session-ready.json'))
    await unlink(path.join(restarted.releaseDir(VERSION), 'receipt.json'))
    const result = await restarted.verify({ version: VERSION })
    expect(result).toMatchObject({ state: 'deployed', verification: { status: 'confirmed' } })
    expect(f.write).toHaveBeenCalledTimes(3)
    expect(await restarted.status()).toMatchObject({ unresolvedDeployment: null, deploymentEnabled: false })
  })

  it('renews only identity GETs during pending verification without replaying any release write', async () => {
    const f = await fixture()
    await f.service.deploy(f.deployment)
    f.remote.summary = VERSION
    const original = f.get.getMockImplementation()
    let identityReads = 0
    f.get.mockImplementation(async (url, options) => {
      const pathname = new URL(url).pathname
      if (pathname.endsWith('/developers') && identityReads++ === 0) return new Response('private expired response', { status: 401 })
      if (pathname === '/login') return new Response('fixture landing page', { headers: { 'Set-Cookie': 'session=confirmation-renewed; Path=/; Secure; HttpOnly' } })
      return original(url, options)
    })
    const result = await f.restart().verify()
    expect(result).toMatchObject({ state: 'deployed' })
    expect(identityReads).toBe(2)
    expect(f.write).toHaveBeenCalledTimes(3)
    expect(JSON.stringify(result)).not.toMatch(/confirmation-renewed|confirmation-owner|private expired/)
  })

  it.each(['validation', 'version', 'details'])('keeps a rejected %s write uncertain with no verification or replay', async failureAt => {
    const f = await fixture({ failureAt })
    await expect(f.service.deploy(f.deployment)).rejects.toMatchObject({ code: 'UPLOAD_UNCERTAIN' })
    const count = f.get.mock.calls.length, writes = f.write.mock.calls.length
    const journal = await f.service.readJson(f.journalFile)
    expect(journal.state).toBe('uncertain')
    if (failureAt !== 'validation') expect(journal.confirmation.tempFileId).toBe('confirmation-temporary-id')
    if (failureAt === 'details') expect(journal.confirmation.phase).toBe('version_accepted')
    await expect(f.restart().verify()).rejects.toMatchObject({ code: 'RETRY_BLOCKED' })
    expect(f.get).toHaveBeenCalledTimes(count)
    expect(f.write).toHaveBeenCalledTimes(writes)
  })

  it('retains the validation ID if the fresh metadata read fails before the details PUT', async () => {
    const f = await fixture()
    f.remote.change = data => { data.appIqFileInfoResult.newAppVersion = BASE_VERSION }
    await expect(f.service.deploy(f.deployment)).rejects.toMatchObject({ code: 'UPLOAD_UNCERTAIN' })
    expect(await f.service.readJson(f.journalFile)).toMatchObject({ state: 'uncertain',
      confirmation: { tempFileId: 'confirmation-temporary-id', phase: 'version_accepted' } })
    expect(f.write).toHaveBeenCalledTimes(2)
  })

  it.each(['notes', 'owner', 'version', 'manifest', 'shadow', 'beta', 'duplicate English'])('never finalizes changed %s evidence', async kind => {
    const f = await fixture()
    await f.service.deploy(f.deployment)
    f.remote.summary = VERSION
    if (kind === 'notes') f.remote.notes = 'Changed by somebody else'
    if (kind === 'owner') f.remote.owner = 'new-owner'
    if (kind === 'version') f.remote.summary = '0.1.0-beta.4'
    f.remote.change = data => {
      if (kind === 'manifest') data.appIqFileInfoResult.manifestAppId = '0'.repeat(32)
      if (kind === 'shadow') data.shadowApp = true
      if (kind === 'beta') data.betaApp = false
      if (kind === 'duplicate English') data.localizedAppModel.push({ appLocale: 'en', appWhatsNew: f.deployment.releaseNotes })
    }
    const result = await f.restart().verify()
    expect(result).toMatchObject({ state: 'awaiting_confirmation', verification: { status: 'error', retryable: false } })
    expect(result).not.toHaveProperty('ownerOnlyBeta')
    expect(f.write).toHaveBeenCalledTimes(3)
    expect(await f.service.status()).toMatchObject({ unresolvedDeployment: { state: 'awaiting_confirmation' } })
  })

  it('blocks a new release and a changed intent until strict finalization', async () => {
    const f = await fixture()
    await f.service.deploy(f.deployment)
    await expect(f.service.deploy({ ...f.deployment, releaseNotes: 'New intent' })).rejects.toMatchObject({ code: 'RETRY_BLOCKED' })
    await expect(f.service.deploy({ ...f.deployment, version: '0.1.0-beta.4' })).rejects.toMatchObject({ code: 'RETRY_BLOCKED' })
    f.remote.summary = VERSION
    expect(await f.service.verify()).toMatchObject({ state: 'deployed' })
    expect(await f.service.deploy(f.deployment)).toMatchObject({ state: 'deployed' })
    expect(f.write).toHaveBeenCalledTimes(3)
  })

  it('does not resubmit a previously confirmed version if its per-version journal disappears', async () => {
    const f = await fixture()
    f.remote.lag = false
    await f.service.deploy(f.deployment)
    await unlink(f.journalFile)
    const count = f.get.mock.calls.length
    await expect(f.service.deploy(f.deployment)).rejects.toMatchObject({ code: 'RETRY_BLOCKED' })
    expect(f.get).toHaveBeenCalledTimes(count)
    expect(f.write).toHaveBeenCalledTimes(3)
  })

  it.each(['missing journal', 'missing proof', 'request notes', 'request owner', 'request version', 'journal hash', 'uncertain journal', 'unknown phase'])('blocks %s without GET or POST/PUT', async kind => {
    const f = await fixture()
    await f.service.deploy(f.deployment)
    const journal = await f.service.readJson(f.journalFile)
    if (kind === 'missing journal') await unlink(f.journalFile)
    else {
      if (kind === 'missing proof') delete journal.confirmation
      if (kind === 'request notes') journal.request.releaseNotes = 'Altered'
      if (kind === 'request owner') journal.confirmation.owner = 'altered-owner'
      if (kind === 'request version') journal.request.version = '0.1.0-beta.4'
      if (kind === 'journal hash') journal.sha256 = '0'.repeat(64)
      if (kind === 'uncertain journal') journal.state = 'uncertain'
      if (kind === 'unknown phase') journal.confirmation.phase = 'published'
      await f.service.writeJson(f.journalFile, journal)
    }
    const count = f.get.mock.calls.length
    await expect(f.restart().verify()).rejects.toMatchObject({ code: 'CONFIRMATION_BLOCKED' })
    expect(f.get).toHaveBeenCalledTimes(count)
    expect(f.write).toHaveBeenCalledTimes(3)
  })

  it.each(['uploading', 'uncertain'])('keeps legacy %s journals blocked during verification and monitoring', async state => {
    const f = await fixture()
    const legacy = { schemaVersion: 1, appId: APP_ID, version: VERSION, requestHash: 'legacy', state }
    await f.service.writeJson(f.journalFile, legacy)
    await f.service.writeJson(f.service.activeFile, legacy)
    await expect(f.restart().verify()).rejects.toMatchObject({ code: 'RETRY_BLOCKED' })
    const s = scheduler(f, f.restart())
    expect(await s.monitor.start()).toMatchObject({ state: 'blocked', errorCode: 'RETRY_BLOCKED' })
    expect(s.tasks.size).toBe(0)
    expect(f.get).not.toHaveBeenCalled()
    expect(f.write).not.toHaveBeenCalled()
  })

  it('preserves offline legacy success and blocks a mismatched requested verification version', async () => {
    const f = await fixture()
    await f.service.deploy(f.deployment)
    const count = f.get.mock.calls.length
    await expect(f.restart().verify({ version: '0.1.0-beta.4' })).rejects.toMatchObject({ code: 'CONFIRMATION_BLOCKED' })
    const legacy = { schemaVersion: 1, appId: APP_ID, version: VERSION, sha256: f.deployment.sha256,
      requestHash: sha256(JSON.stringify(f.deployment)), state: 'deployed', verifiedAt: '2026-10-28T00:00:00Z' }
    await f.service.writeJson(f.journalFile, legacy)
    await f.service.writeJson(f.service.activeFile, legacy)
    expect(await f.service.deploy(f.deployment)).toMatchObject({ state: 'deployed' })
    expect(await f.restart().pending()).toBe(null)
    expect(f.get).toHaveBeenCalledTimes(count)
    expect(f.write).toHaveBeenCalledTimes(3)
  })

  it('repairs a crash-interrupted local finalization without GETs or new write submissions', async () => {
    const f = await fixture()
    await f.service.deploy(f.deployment)
    const oldActive = await f.service.readJson(f.service.activeFile)
    f.remote.summary = VERSION
    await f.service.verify()
    await f.service.writeJson(f.service.activeFile, oldActive)
    const count = f.get.mock.calls.length
    const s = scheduler(f, f.restart())
    await s.monitor.start()
    await s.fire()
    expect(s.tasks.size).toBe(0)
    expect(await f.service.status()).toMatchObject({ unresolvedDeployment: null })
    expect(f.get).toHaveBeenCalledTimes(count)
    expect(f.write).toHaveBeenCalledTimes(3)
  })
})

describe('bounded confirmation monitor', () => {
  it('cancels a sleeping monitor after an explicit final verification', async () => {
    const f = await fixture()
    await f.service.deploy(f.deployment)
    const s = scheduler(f)
    await s.monitor.start()
    f.remote.summary = VERSION
    expect(await f.service.verify()).toMatchObject({ state: 'deployed' })
    expect(await s.monitor.start()).toMatchObject({ state: 'idle' })
    expect(s.tasks.size).toBe(0)
    expect(f.write).toHaveBeenCalledTimes(3)
  })

  it('resumes after restart at durable spacing, performs no overlapping work and finalizes with GET only', async () => {
    const f = await fixture()
    await f.service.deploy(f.deployment)
    const s = scheduler(f, f.restart())
    await Promise.all([s.monitor.start(), s.monitor.start()])
    expect(s.tasks.size).toBe(1)
    expect(s.schedule.mock.calls[0][1]).toBe(CONFIRMATION_INTERVAL_MS)
    expect(await f.service.status()).toMatchObject({ operationLocked: false })
    await f.service.exclusive(async () => {
      const count = f.get.mock.calls.length
      await s.fire()
      expect(s.monitor.status()).toMatchObject({ state: 'waiting', errorCode: 'OPERATION_LOCKED' })
      expect(f.get).toHaveBeenCalledTimes(count)
    })
    f.remote.summary = VERSION
    await s.fire()
    expect(s.monitor.status()).toMatchObject({ state: 'idle' })
    expect(s.tasks.size).toBe(0)
    expect(f.write).toHaveBeenCalledTimes(3)
    expect(await f.service.status()).toMatchObject({ unresolvedDeployment: null, operationLocked: false })
  })

  it('serializes concurrent manual verification and allows stop during an in-flight GET', async () => {
    const f = await fixture()
    await f.service.deploy(f.deployment)
    const s = scheduler(f, f.restart())
    await s.monitor.start()
    let entered, finish
    const ready = new Promise(resolve => { entered = resolve })
    const held = new Promise(resolve => { finish = resolve })
    const original = f.get.getMockImplementation()
    f.get.mockImplementationOnce(async (...args) => { entered(); await held; return original(...args) })
    const running = s.fire()
    await ready
    try {
      await expect(f.service.verify()).rejects.toMatchObject({ code: 'OPERATION_LOCKED' })
      await s.monitor.start()
      expect(s.tasks.size).toBe(0)
      s.monitor.stop()
    } finally { finish(); await running }
    expect(s.tasks.size).toBe(0)
    expect(s.monitor.status()).toMatchObject({ state: 'stopped' })
    expect(await f.service.status()).toMatchObject({ operationLocked: false, unresolvedDeployment: { state: 'awaiting_confirmation' } })
    expect(f.write).toHaveBeenCalledTimes(3)
  })

  it('backs off transient GET errors and stops on identity errors', async () => {
    const f = await fixture()
    f.remote.afterWritesError = new Error('private diagnostic')
    await f.service.deploy(f.deployment)
    const s = scheduler(f)
    await s.monitor.start()
    await s.fire()
    expect(s.schedule.mock.calls.at(-1)[1]).toBe(120_000)
    await s.fire()
    expect(s.schedule.mock.calls.at(-1)[1]).toBe(240_000)
    f.remote.afterWritesError = null
    f.remote.owner = 'different-owner'
    await s.fire()
    expect(s.monitor.status()).toMatchObject({ state: 'stopped', errorCode: 'OWNER_MISMATCH' })
    expect(s.tasks.size).toBe(0)
    expect(f.write).toHaveBeenCalledTimes(3)
  })

  it('stops on an authentication handoff and requires explicit verification after a renewed import', async () => {
    const f = await fixture()
    await f.service.deploy(f.deployment)
    const original = f.get.getMockImplementation()
    let expired = true
    f.get.mockImplementation(async (url, options) => {
      if (expired && new URL(url).pathname.endsWith('/developers')) return new Response('', { status: 401 })
      if (new URL(url).pathname === '/login') return new Response('private challenge', { status: 403, headers: { 'cf-mitigated': 'challenge' } })
      return original(url, options)
    })
    const s = scheduler(f, f.restart())
    await s.monitor.start()
    await s.fire()
    expect(s.monitor.status()).toMatchObject({ state: 'stopped', errorCode: 'AUTH_HANDOFF' })
    expect(s.tasks.size).toBe(0)
    expired = false
    f.remote.summary = VERSION
    expect(await f.restart().verify()).toMatchObject({ state: 'deployed' })
    expect(f.write).toHaveBeenCalledTimes(3)
  })

  it('times out at the original 25-minute deadline across restarts and permits explicit later GET verification', async () => {
    const f = await fixture()
    const initial = await f.service.deploy(f.deployment)
    const deadline = Date.parse(initial.verification.deadlineAt)
    expect(deadline - f.now()).toBe(CONFIRMATION_WINDOW_MS)
    const s = scheduler(f, f.restart())
    f.clock.value += 24 * CONFIRMATION_INTERVAL_MS
    await s.monitor.start()
    await s.fire()
    expect(s.schedule.mock.calls.at(-1)[1]).toBe(CONFIRMATION_INTERVAL_MS)
    const count = f.get.mock.calls.length
    await s.fire()
    expect(f.now()).toBe(deadline)
    expect(f.get).toHaveBeenCalledTimes(count)
    expect(await f.service.status()).toMatchObject({ unresolvedDeployment: { state: 'awaiting_confirmation', verification: { status: 'timed_out', deadlineAt: initial.verification.deadlineAt } } })
    expect(s.tasks.size).toBe(0)
    const again = scheduler(f, f.restart())
    await again.monitor.start()
    expect(again.tasks.size).toBe(0)
    f.remote.summary = VERSION
    expect(await f.restart().verify()).toMatchObject({ state: 'deployed' })
    expect(f.write).toHaveBeenCalledTimes(3)
  })

  it('cancels a sleeping timer without acquiring the operation lock', async () => {
    const f = await fixture()
    await f.service.deploy(f.deployment)
    const s = scheduler(f)
    await s.monitor.start()
    const count = f.get.mock.calls.length
    s.monitor.stop()
    expect(s.tasks.size).toBe(0)
    expect(f.get).toHaveBeenCalledTimes(count)
    expect(await f.service.status()).toMatchObject({ operationLocked: false })
  })
})
