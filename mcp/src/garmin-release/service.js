import path from 'node:path'
import { open, rename, unlink, lstat, mkdtemp, rm } from 'node:fs/promises'
import { APP_ID, MANIFEST_ID, BASE_VERSION, RELEASE_HOME, CONFIRMATION_INTERVAL_MS, CONFIRMATION_WINDOW_MS, prepareSchema, deploySchema, statusSchema, parse, newerThan, fail, publicError } from './contract.js'
import { directory, readFileSafe, sha256, validateIq } from './artifact.js'
import { GarminApi, GarminSession } from './api.js'

export class ReleaseService {
  constructor({ home = RELEASE_HOME, enabled = process.env.GARMIN_RELEASE_ENABLE_DEPLOY === '1', apiFactory = sessionFile => new GarminApi(sessionFile), now = Date.now } = {}) {
    this.home = home
    this.enabled = enabled
    this.apiFactory = apiFactory
    this.now = now
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
      unresolvedDeployment: active && active.state !== 'deployed' ? { version: active.version, state: active.state,
        ...(active.verification ? { verification: this.verificationResult(active) } : {}) } : null,
      ...(version ? { version, prepared: !!receipt, sha256: receipt?.sha256 ?? null, state: journal?.state ?? (receipt ? 'prepared' : 'missing'),
        ...(journal?.verification ? { verification: this.verificationResult(journal) } : {}) } : {}) }
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
      if (active?.version === request.version) fail('RETRY_BLOCKED', 'The active deployment intent survives a missing per-version journal. No submission may be repeated.')
      const receipt = await this.readJson(path.join(dir, 'receipt.json'))
      if (receipt.appId !== APP_ID || receipt.version !== request.version || receipt.sha256 !== request.sha256) fail('RECEIPT_MISMATCH', 'Prepared receipt does not match this deployment request.')
      const bytes = await readFileSafe(path.join(dir, `opengym-garmin-${request.version}.iq`))
      await validateIq(bytes, request.version, request.sha256)
      const session = await this.optionalJson(path.join(this.privateDir, 'session-ready.json'))
      if (session?.appId !== APP_ID) fail('AUTH_HANDOFF', 'Verify the imported HTTP session with garmin_release_check before deployment.')
      const api = this.apiFactory(this.sessionFile)
      const journal = { schemaVersion: 1, appId: APP_ID, version: request.version, sha256: request.sha256, requestHash,
        request, state: 'uploading', attemptedAt: this.timestamp() }
      let intent = false
      try {
        const evidence = await api.deploy({ ...request, bytes, beforeUpload: async proof => {
          if (intent) fail('RETRY_BLOCKED', 'The HTTP transport cannot start the upload twice in one attempt.')
          journal.confirmation = { ...proof, phase: 'intent' }
          await this.writeJson(this.activeFile, journal)
          intent = true
          await this.writeJson(journalFile, journal)
        }, checkpoint: async update => {
          const previousPhase = { validated: 'intent', version_accepted: 'validated', details_accepted: 'version_accepted' }[update.phase]
          if (!intent || !previousPhase || journal.confirmation.phase !== previousPhase) fail('INVALID_EVIDENCE', 'Release write checkpoints are incomplete or out of order.')
          const acceptedAt = this.now()
          journal.confirmation = { ...journal.confirmation, ...update, [`${update.phase}At`]: this.timestamp(acceptedAt) }
          if (update.phase === 'details_accepted') {
            journal.state = 'awaiting_confirmation'
            journal.verification = { status: 'pending', attempts: 0, failures: 0,
              deadlineAt: this.timestamp(acceptedAt + CONFIRMATION_WINDOW_MS),
              nextCheckAt: this.timestamp(acceptedAt + CONFIRMATION_INTERVAL_MS) }
          }
          await this.saveJournal(journal)
        } })
        if (!intent || evidence.appId !== APP_ID || evidence.version !== request.version || evidence.ownerOnlyBeta !== true || evidence.state !== 'awaiting_confirmation') fail('INVALID_EVIDENCE', 'The HTTP transport did not confirm the beta submission.')
        this.validateConfirmation(journal)
      } catch (error) {
        if (intent) {
          journal.state = 'uncertain'
          journal.failureCode = publicError(error).code
          await this.saveJournal(journal)
          fail('UPLOAD_UNCERTAIN', 'Upload may have reached Garmin. Automatic retry is blocked; inspect the existing beta and private journal manually.')
        }
        throw error
      }
      // Once both write acknowledgements are durable, GET failures must never
      // turn this submission into an ambiguous write or invite resubmission.
      return this.verifyJournal(journal, api)
    })
  }

  timestamp(ms = this.now()) { return new Date(ms).toISOString() }

  async saveJournal(journal) {
    await this.writeJson(path.join(this.releaseDir(journal.version), 'journal.json'), journal)
    await this.writeJson(this.activeFile, journal)
  }

  validateConfirmation(journal) {
    const request = deploySchema.safeParse(journal?.request), proof = journal?.confirmation
    if (!request.success || journal.schemaVersion !== 1 || journal.appId !== APP_ID ||
        request.data.version !== journal.version || request.data.sha256 !== journal.sha256 ||
        sha256(JSON.stringify(request.data)) !== journal.requestHash ||
        !newerThan(journal.version, request.data.expectedCurrentVersion) || !newerThan(journal.version, BASE_VERSION) ||
        proof?.phase !== 'details_accepted' || !/^[a-zA-Z0-9_-]{1,100}$/.test(proof.owner ?? '') ||
        !/^[a-zA-Z0-9_-]{1,200}$/.test(proof.tempFileId ?? '') ||
        proof.previousVersion !== request.data.expectedCurrentVersion || proof.releaseNotes !== request.data.releaseNotes ||
        !['validatedAt', 'version_acceptedAt', 'details_acceptedAt'].every(key => Number.isFinite(Date.parse(proof[key]))) ||
        Date.parse(proof.validatedAt) > Date.parse(proof.version_acceptedAt) ||
        Date.parse(proof.version_acceptedAt) > Date.parse(proof.details_acceptedAt) ||
        Date.parse(journal.verification?.deadlineAt) !== Date.parse(proof.details_acceptedAt) + CONFIRMATION_WINDOW_MS) {
      fail('CONFIRMATION_BLOCKED', 'Durable accepted-write proof is missing or inconsistent. Verification cannot recover or replay an ambiguous attempt.')
    }
  }

  async pendingJournal(version) {
    const active = await this.optionalJson(this.activeFile)
    if (!active) {
      if (version) fail('CONFIRMATION_BLOCKED', 'No active release identity is available for verification.')
      return null
    }
    const parsed = statusSchema.safeParse({ version: active.version })
    if (!parsed.success || (version && version !== active.version)) fail('CONFIRMATION_BLOCKED', 'Verification is restricted to the active release identity.')
    if (active.state === 'deployed') return null
    if (active.state !== 'awaiting_confirmation') fail('RETRY_BLOCKED', 'An ambiguous or legacy attempt requires manual reconciliation. GET verification cannot convert it to an accepted submission.')
    const journal = await this.optionalJson(path.join(this.releaseDir(active.version), 'journal.json'))
    if (!journal || !['awaiting_confirmation', 'deployed'].includes(journal.state) ||
        ['appId', 'version', 'sha256', 'requestHash'].some(key => active[key] !== journal[key])) {
      fail('CONFIRMATION_BLOCKED', 'The active release and private journal do not agree. No network operation is allowed.')
    }
    this.validateConfirmation(journal)
    this.validateConfirmation(active)
    if (JSON.stringify(active.confirmation) !== JSON.stringify(journal.confirmation)) fail('CONFIRMATION_BLOCKED', 'Accepted-write checkpoints do not agree.')
    return journal
  }

  // Offline scheduling information. Never scan other releases or inspect Garmin.
  async pending() {
    await this.init()
    const journal = await this.pendingJournal()
    return journal ? { version: journal.version, ...this.verificationResult(journal),
      ...(journal.state === 'deployed' ? { status: 'finalizing', nextCheckAt: this.timestamp() } : {}) } : null
  }

  async verify(input = {}, { background = false } = {}) {
    const { version } = parse(statusSchema, input)
    return this.exclusive(async () => {
      const journal = await this.pendingJournal(version)
      if (!journal) fail('NO_PENDING_RELEASE', 'There is no accepted beta submission awaiting confirmation.')
      // Complete a crash-interrupted local finalization without repeating reads.
      if (journal.state === 'deployed') { await this.saveJournal(journal); return this.result(journal) }
      return this.verifyJournal(journal, null, { background })
    })
  }

  async verifyJournal(journal, api, { background = false } = {}) {
    const verification = journal.verification
    if (background && this.now() >= Date.parse(verification.deadlineAt)) {
      verification.status = 'timed_out'
      delete verification.nextCheckAt
      await this.saveJournal(journal)
      return this.result(journal)
    }
    if (background && (verification.status === 'timed_out' || verification.retryable === false || this.now() < Date.parse(verification.nextCheckAt))) return this.result(journal)
    verification.attempts++
    verification.checkedAt = this.timestamp()
    try {
      // Bound the entire inspection, including GET-only SSO renewal, rather
      // than multiplying the per-request timeout by every possible redirect.
      const budget = background ? Math.min(90_000, Date.parse(verification.deadlineAt) - this.now()) : 90_000
      const evidence = await (api ?? this.apiFactory(this.sessionFile)).verify(
        { ...journal.confirmation, version: journal.version }, { signal: AbortSignal.timeout(Math.max(1, budget)) })
      if (evidence.appId !== APP_ID || evidence.version !== journal.version || evidence.ownerOnlyBeta !== true ||
          !['deployed', 'awaiting_confirmation'].includes(evidence.state)) fail('INVALID_EVIDENCE', 'Final verification did not establish the requested beta identity.')
      verification.status = evidence.state === 'deployed' ? 'confirmed' : 'pending'
      verification.failures = 0
      delete verification.errorCode
      delete verification.retryable
      if (evidence.state === 'deployed') {
        journal.state = 'deployed'
        journal.verifiedAt = this.timestamp()
        delete verification.nextCheckAt
      }
    } catch (error) {
      verification.status = 'error'
      verification.errorCode = publicError(error).code
      verification.failures = (verification.failures ?? 0) + 1
      verification.retryable = !['OWNER_MISMATCH', 'REMOTE_VERSION_MISMATCH', 'NOTES_MISMATCH', 'INVALID_EVIDENCE', 'INVALID_RESPONSE', 'AUTH_HANDOFF', 'PRIVATE_SESSION_REQUIRED', 'INVALID_SESSION'].includes(verification.errorCode)
    }
    if (journal.state === 'awaiting_confirmation') {
      const backoff = CONFIRMATION_INTERVAL_MS * 2 ** Math.min(Math.max((verification.failures ?? 0) - 1, 0), 2)
      verification.nextCheckAt = this.timestamp(this.now() + backoff)
    }
    await this.saveJournal(journal)
    return this.result(journal)
  }

  verificationResult(journal) {
    const v = journal.verification
    return { status: v.status, attempts: v.attempts, deadlineAt: v.deadlineAt,
      ...(v.checkedAt ? { checkedAt: v.checkedAt } : {}), ...(v.nextCheckAt ? { nextCheckAt: v.nextCheckAt } : {}),
      ...(v.errorCode ? { errorCode: v.errorCode, retryable: v.retryable } : {}) }
  }

  result(journal) {
    return { appId: APP_ID, version: journal.version, sha256: journal.sha256, state: journal.state,
      ...(journal.verifiedAt ? { verifiedAt: journal.verifiedAt } : {}),
      ...(journal.state === 'deployed' ? { ownerOnlyBeta: true } : {}),
      ...(journal.verification ? { verification: this.verificationResult(journal) } : {}) }
  }
}
