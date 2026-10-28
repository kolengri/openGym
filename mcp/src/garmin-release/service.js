import path from 'node:path'
import { open, rename, unlink, lstat, mkdtemp, rm } from 'node:fs/promises'
import { APP_ID, MANIFEST_ID, BASE_VERSION, RELEASE_HOME, prepareSchema, deploySchema, statusSchema, parse, newerThan, fail, publicError } from './contract.js'
import { directory, readFileSafe, sha256, validateIq } from './artifact.js'
import { GarminApi, GarminSession } from './api.js'

export class ReleaseService {
  constructor({ home = RELEASE_HOME, enabled = process.env.GARMIN_RELEASE_ENABLE_DEPLOY === '1', apiFactory = sessionFile => new GarminApi(sessionFile) } = {}) {
    this.home = home
    this.enabled = enabled
    this.apiFactory = apiFactory
    this.privateDir = path.join(home, 'private')
    this.sessionFile = path.join(this.privateDir, 'http-session.json')
    this.activeFile = path.join(this.privateDir, 'active-deployment.json')
  }

  async init() {
    await directory(this.home)
    for (const name of ['inbox', 'releases', 'private']) await directory(path.join(this.home, name))
  }

  async exclusive(operation) {
    await this.init()
    const lockFile = path.join(this.privateDir, 'operation.lock')
    let lock
    try { lock = await open(lockFile, 'wx', 0o600) }
    catch (e) {
      if (e.code === 'EEXIST') fail('OPERATION_LOCKED', 'Another operation or an interrupted process owns the release lock. Inspect locally; never clear it while an upload may be running.')
      throw e
    }
    try {
      await lock.writeFile(JSON.stringify({ pid: process.pid, startedAt: new Date().toISOString() }))
      await lock.sync()
      return await operation()
    } finally { await lock.close(); await unlink(lockFile) }
  }

  releaseDir(version) { return path.join(this.home, 'releases', version) }

  async readJson(file) { return JSON.parse((await readFileSafe(file, 64 * 1024)).toString('utf8')) }

  async writeJson(file, value) {
    const temp = `${file}.tmp`
    const handle = await open(temp, 'wx', 0o600)
    try { await handle.writeFile(JSON.stringify(value, null, 2) + '\n'); await handle.sync() }
    finally { await handle.close() }
    await rename(temp, file)
    const dir = await open(path.dirname(file), 'r')
    try { await dir.sync() } finally { await dir.close() }
  }

  async check() {
    return this.exclusive(async () => {
      const evidence = await this.apiFactory(this.sessionFile).inspect()
      await this.writeJson(path.join(this.privateDir, 'session-ready.json'), { appId: APP_ID, verifiedAt: new Date().toISOString() })
      return evidence
    })
  }

  async optionalJson(file) {
    try { return await this.readJson(file) } catch (e) { if (e.code === 'ENOENT') return null; throw e }
  }

  async status(input = {}) {
    const { version } = parse(statusSchema, input)
    await this.init()
    let configuration
    try { await new GarminSession(this.sessionFile).load(); configuration = 'configured' }
    catch (e) { configuration = e.code === 'ENOENT' ? 'missing' : 'invalid' }
    const session = await this.optionalJson(path.join(this.privateDir, 'session-ready.json'))
    const active = await this.optionalJson(this.activeFile)
    const journal = version ? await this.optionalJson(path.join(this.releaseDir(version), 'journal.json')) : null
    const receipt = version ? await this.optionalJson(path.join(this.releaseDir(version), 'receipt.json')) : null
    let locked = false
    try { await lstat(path.join(this.privateDir, 'operation.lock')); locked = true } catch (e) { if (e.code !== 'ENOENT') throw e }
    return { appId: APP_ID, manifestId: MANIFEST_ID, baselineVersion: BASE_VERSION,
      deploymentEnabled: this.enabled, transport: 'http', httpSession: configuration,
      sessionPreviouslyVerified: session?.appId === APP_ID, operationLocked: locked,
      unresolvedDeployment: active && active.state !== 'deployed' ? { version: active.version, state: active.state } : null,
      ...(version ? { version, prepared: !!receipt, sha256: receipt?.sha256 ?? null, state: journal?.state ?? (receipt ? 'prepared' : 'missing') } : {}) }
  }

  async prepare(input) {
    const request = parse(prepareSchema, input)
    if (!newerThan(request.version, BASE_VERSION)) fail('VERSION_NOT_NEWER', 'The new beta version must be newer than the known beta baseline.')
    return this.exclusive(async () => {
      const bytes = await readFileSafe(path.join(this.home, 'inbox', `opengym-garmin-${request.version}.iq`))
      const metadata = await validateIq(bytes, request.version, request.sha256)
      const dir = this.releaseDir(request.version)
      try {
        const stat = await lstat(dir)
        if (!stat.isDirectory() || stat.isSymbolicLink()) fail('UNSAFE_PATH', 'Release directories must be real directories.')
      } catch (e) { if (e.code !== 'ENOENT') throw e }
      const existing = await this.optionalJson(path.join(dir, 'receipt.json'))
      if (existing) {
        if (existing.sha256 !== request.sha256) fail('VERSION_CONFLICT', 'This version already has a different prepared IQ.')
        return existing
      }
      const receipt = { schemaVersion: 1, appId: APP_ID, ...metadata,
        artifact: `artifacts/garmin-release-mcp/releases/${request.version}/opengym-garmin-${request.version}.iq`,
        preparedAt: new Date().toISOString(), validation: 'manifest-and-hash; signature-and-device-behavior-not-verified' }
      // Publish both files together. Interrupted staging never reserves the version.
      const releases = path.dirname(dir)
      const staging = await mkdtemp(path.join(releases, '.prepare-'))
      try {
        const handle = await open(path.join(staging, `opengym-garmin-${request.version}.iq`), 'wx', 0o600)
        try { await handle.writeFile(bytes); await handle.sync() } finally { await handle.close() }
        await this.writeJson(path.join(staging, 'receipt.json'), receipt)
        await rename(staging, dir)
        const parent = await open(releases, 'r')
        try { await parent.sync() } finally { await parent.close() }
      } finally { await rm(staging, { recursive: true, force: true }) }
      return receipt
    })
  }

  async deploy(input) {
    const request = parse(deploySchema, input)
    if (!this.enabled) fail('DEPLOY_DISABLED', 'Set GARMIN_RELEASE_ENABLE_DEPLOY=1 in the dedicated MCP process configuration to enable explicit deployment.')
    if (!newerThan(request.version, request.expectedCurrentVersion) || !newerThan(request.version, BASE_VERSION)) fail('VERSION_NOT_NEWER', 'The requested version must be newer than both the current beta and the known baseline.')
    return this.exclusive(async () => {
      const dir = this.releaseDir(request.version), journalFile = path.join(dir, 'journal.json')
      const requestHash = sha256(JSON.stringify(request))
      const previous = await this.optionalJson(journalFile)
      if (previous) {
        if (previous.requestHash === requestHash && previous.state === 'deployed') return this.result(previous)
        fail('RETRY_BLOCKED', 'This version already has a deployment intent. Check the private journal and Garmin listing manually; an uncertain upload must never be retried automatically.')
      }
      const active = await this.optionalJson(this.activeFile)
      if (active && active.state !== 'deployed') fail('RETRY_BLOCKED', 'An earlier beta upload remains unresolved. Reconcile the existing Garmin listing before uploading any version.')
      const receipt = await this.readJson(path.join(dir, 'receipt.json'))
      if (receipt.appId !== APP_ID || receipt.version !== request.version || receipt.sha256 !== request.sha256) fail('RECEIPT_MISMATCH', 'Prepared receipt does not match this deployment request.')
      const bytes = await readFileSafe(path.join(dir, `opengym-garmin-${request.version}.iq`))
      await validateIq(bytes, request.version, request.sha256)
      const session = await this.optionalJson(path.join(this.privateDir, 'session-ready.json'))
      if (session?.appId !== APP_ID) fail('AUTH_HANDOFF', 'Verify the imported HTTP session with garmin_release_check before deployment.')
      const api = this.apiFactory(this.sessionFile)
      const journal = { schemaVersion: 1, appId: APP_ID, version: request.version, sha256: request.sha256, requestHash,
        state: 'uploading', attemptedAt: new Date().toISOString() }
      let intent = false
      try {
        const evidence = await api.deploy({ ...request, bytes, beforeUpload: async () => {
          if (intent) fail('RETRY_BLOCKED', 'The HTTP transport cannot start the upload twice in one attempt.')
          await this.writeJson(this.activeFile, journal)
          intent = true
          await this.writeJson(journalFile, journal)
        } })
        if (!intent || evidence.appId !== APP_ID || evidence.version !== request.version || evidence.ownerOnlyBeta !== true) fail('INVALID_EVIDENCE', 'The HTTP transport did not verify the updated existing owner-only beta.')
        journal.state = 'deployed'
        journal.verifiedAt = new Date().toISOString()
        await this.writeJson(journalFile, journal)
        await this.writeJson(this.activeFile, journal)
        return this.result(journal)
      } catch (error) {
        if (intent) {
          journal.state = 'uncertain'
          journal.failureCode = publicError(error).code
          await this.writeJson(journalFile, journal)
          await this.writeJson(this.activeFile, journal)
          fail('UPLOAD_UNCERTAIN', 'Upload may have reached Garmin. Automatic retry is blocked; inspect the existing beta and private journal manually.')
        }
        throw error
      }
    })
  }

  result(journal) { return { appId: APP_ID, version: journal.version, sha256: journal.sha256, state: journal.state, verifiedAt: journal.verifiedAt, ownerOnlyBeta: true } }
}
