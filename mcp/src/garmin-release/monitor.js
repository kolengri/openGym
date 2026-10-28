import { CONFIRMATION_INTERVAL_MS, publicError } from './contract.js'

// One release, one timer, one GET-only check at a time. The durable acceptance
// deadline survives restarts; reconnecting never grants another polling window.
export class ConfirmationMonitor {
  constructor(service, { now = Date.now, schedule = setTimeout, cancel = clearTimeout } = {}) {
    this.service = service
    this.now = now
    this.schedule = schedule
    this.cancel = cancel
    this.timer = null
    this.running = null
    this.starting = null
    this.startRequested = false
    this.generation = 0
    this.state = { state: 'idle' }
  }

  status() { return { ...this.state } }

  async start() {
    if (this.running) { this.startRequested = true; return this.status() }
    if (this.starting) return this.starting
    // Manual verification may have finalized or changed the active release.
    // Re-read its durable schedule without extending the acceptance deadline.
    if (this.timer !== null) this.cancel(this.timer)
    this.timer = null
    const generation = this.generation
    this.starting = (async () => {
      try {
        const pending = await this.service.pending()
        if (generation === this.generation) this.arm(pending, generation)
      } catch (error) {
        if (generation === this.generation) this.state = { state: 'blocked', errorCode: publicError(error).code }
      }
      return this.status()
    })()
    try { return await this.starting } finally { this.starting = null }
  }

  arm(pending, generation, minimumDelay = 0) {
    if (!pending) { this.state = { state: 'idle' }; return }
    const { version, deadlineAt, nextCheckAt } = pending
    if (pending.retryable === false || pending.status === 'timed_out') {
      this.state = { state: 'stopped', version, ...(pending.errorCode ? { errorCode: pending.errorCode } : {}) }
      return
    }
    const deadline = Date.parse(deadlineAt), next = Date.parse(nextCheckAt)
    if (!Number.isFinite(deadline) || !Number.isFinite(next)) {
      this.state = { state: 'blocked', errorCode: 'CONFIRMATION_BLOCKED' }
      return
    }
    const delay = Math.max(0, Math.min(deadline, Math.max(next, this.now() + minimumDelay)) - this.now())
    this.state = { state: 'waiting', version, nextCheckAt: new Date(this.now() + delay).toISOString() }
    this.timer = this.schedule(() => {
      this.timer = null
      this.running = this.tick(version, deadline, generation).finally(async () => {
        this.running = null
        if (this.startRequested && generation === this.generation) {
          this.startRequested = false
          await this.start()
        }
      })
      return this.running
    }, delay)
    this.timer?.unref?.()
  }

  async tick(version, deadline, generation) {
    this.state = { state: 'checking', version }
    try {
      await this.service.verify({ version }, { background: true })
      if (generation !== this.generation) return
      const pending = await this.service.pending()
      if (generation !== this.generation) return
      if (pending && pending.version !== version) {
        this.state = { state: 'blocked', errorCode: 'CONFIRMATION_BLOCKED' }
        return
      }
      this.arm(pending, generation, CONFIRMATION_INTERVAL_MS)
    } catch (error) {
      if (generation !== this.generation) return
      const errorCode = publicError(error).code
      // The operation lock also covers manual checks, preparation and uploads.
      // Busy work is skipped, never overlapped and never treated as permission
      // to clear a crash lock. No lock exists while this timer is sleeping.
      if (errorCode === 'OPERATION_LOCKED' && this.now() < deadline) {
        this.arm({ version, deadlineAt: new Date(deadline).toISOString(), nextCheckAt: new Date(this.now() + CONFIRMATION_INTERVAL_MS).toISOString() }, generation)
        this.state.errorCode = errorCode
      } else this.state = { state: 'blocked', version, errorCode }
    }
  }

  stop() {
    this.generation++
    if (this.timer !== null) this.cancel(this.timer)
    this.timer = null
    this.startRequested = false
    this.state = { state: 'stopped' }
    // An in-flight bounded GET may finish and checkpoint; no new GET follows it.
  }
}
