import { MOBILE, isAndroid } from './mobile.js'
import { stravaWorkoutFit } from './strava-export.js'
import { toBase64 } from './media-store-fs.js'

let pluginPromise = null
let draining = null
const CODES = new Set(['auth_required', 'network_error', 'upload_failed', 'unknown_result', 'content_changed', 'invalid_fit', 'session_changed', 'storage_error', 'storage_unavailable', 'receipt_limit', 'cancelled'])
const ownerOf = state => state.user?.id ?? null
const errorCode = error => CODES.has(error?.code) ? error.code : 'upload_failed'
const completed = w => w?.entries?.some(e => e.sets?.some(s => s?.done === true || s?.sides?.L?.done === true || s?.sides?.R?.done === true))

/** Actual Bluetooth samples only. Missing/offline intervals are never filled in. */
export function appendGarminCloudHeartRate(state, sample) {
  const active = state.active
  if (state.garminCloudAuto !== true || !active || active.id !== sample?.wid ||
    !Number.isFinite(sample.at) || sample.at < active.start || !Number.isFinite(sample.bpm) || sample.bpm < 25 || sample.bpm > 250) return false
  const rows = active.garminHrSamples ||= []
  if (rows.length && sample.at <= rows[rows.length - 1][0]) return false
  rows.push([sample.at, Math.round(sample.bpm)])
  if (rows.length > 7200) { rows.splice(0, rows.length - 7200); active.garminHrTruncated = true }
  return true
}

async function plugin() {
  if (!pluginPromise) pluginPromise = (async () => {
    if (!MOBILE || !await isAndroid()) return null
    const { registerPlugin } = await import('@capacitor/core')
    return { client: registerPlugin('GarminCloud') }
  })()
  return pluginPromise
}

export async function garminCloudStatus() {
  const { client: p } = await plugin() || {}
  if (!p) return { available: false, connected: false }
  try { return await p.status() } catch { return { available: false, connected: false } }
}
export async function connectGarminCloud() {
  const { client: p } = await plugin() || {}
  if (!p) throw Object.assign(new Error('Garmin Connect is available in the Android app.'), { code: 'auth_required' })
  return p.connect()
}
export async function disconnectGarminCloud() { return (await plugin())?.client.disconnect() }
export async function garminHealthMetrics() { return (await plugin())?.client.healthMetrics() }
export async function readGarminHealthMetric(options) {
  const { client: p } = await plugin() || {}
  if (!p) throw Object.assign(new Error('Garmin Connect is unavailable.'), { code: 'auth_required' })
  return p.readHealthMetric(options)
}
export async function readGarminHealthArchive(options) {
  const { client: p } = await plugin() || {}
  if (!p) throw new Error('storage_error')
  return p.readHealthArchive(options)
}
export async function writeGarminHealthArchive(options) {
  const { client: p } = await plugin() || {}
  if (!p) throw new Error('storage_error')
  return p.writeHealthArchive(options)
}

/** Stored in the same state write as the completed workout. No historical backfill scan. */
export function queueGarminCloudUpload(state, workout, { manual = false, retry = false } = {}) {
  if (!workout || !completed(workout) || !state.garminCloudSessionId || (!manual && state.garminCloudAuto !== true)) return false
  if (workout.garminCloudUpload?.status === 'uploaded' || workout.garminCloudUpload?.status === 'duplicate') return false
  workout.garminCloudUpload = {
    status: 'pending', sessionId: state.garminCloudSessionId, manual,
    shareWeights: state.stravaShareWeights === true, retryUnknown: retry,
  }
  return true
}

function nextJob(state) {
  return state.S.workouts?.find(w => {
    const job = w.garminCloudUpload
    return completed(w) && job && ['pending', 'uploading'].includes(job.status) &&
      job.sessionId === state.S.garminCloudSessionId && (job.manual || state.S.garminCloudAuto === true)
  })
}

/** The native receipt survives a lost JS callback. An ambiguous POST never retries silently. */
export function drainGarminCloudUploads(store) {
  if (draining) return draining
  draining = (async () => {
    const { client: p } = await plugin() || {}
    if (!p) return
    while (store.getState().ready !== false) {
      const initial = store.getState()
      const workout = nextJob(initial)
      if (!workout) return
      const owner = ownerOf(initial)
      const sessionId = initial.S.garminCloudSessionId
      const wid = workout.id
      const belongs = () => ownerOf(store.getState()) === owner && store.getState().S.garminCloudSessionId === sessionId
      const patch = fields => {
        if (!belongs()) return
        store.getState().update(s => {
          const w = s.workouts.find(x => x.id === wid)
          if (w?.garminCloudUpload?.sessionId === sessionId) Object.assign(w.garminCloudUpload, fields)
        })
      }
      try {
        const status = await p.status()
        if (!belongs()) return
        if (!status.connected) throw Object.assign(new Error('Sign in to Garmin Connect.'), { code: 'auth_required' })
        if (status.sessionId !== sessionId) throw Object.assign(new Error('Reconnect this profile to Garmin Connect.'), { code: 'session_changed' })
        // Disabling sharing after queueing also removes the weights. Enabling it later cannot
        // broaden an already queued export without a new, deliberate manual action.
        const bytes = stravaWorkoutFit(workout, { ...initial.S, stravaShareWeights: workout.garminCloudUpload.shareWeights === true && initial.S.stravaShareWeights === true }, { heartRateSamples: workout.garminHrSamples })
        if (bytes.length > 2 * 1024 * 1024) throw Object.assign(new Error('FIT export exceeds the upload limit.'), { code: 'invalid_fit' })
        // One explicit action grants one native attempt. Never persist replay permission.
        const retryUnknown = workout.garminCloudUpload.retryUnknown === true
        patch({ status: 'uploading', error: null, retryUnknown: false })
        if (typeof store.getState().saveNow !== 'function') throw Object.assign(new Error('Workout persistence is unavailable.'), { code: 'storage_error' })
        try { await store.getState().saveNow() }
        catch { throw Object.assign(new Error('Workout could not be saved.'), { code: 'storage_error' }) }
        if (!belongs()) return
        const latest = store.getState().S
        const latestWorkout = latest.workouts.find(w => w.id === wid)
        if (latestWorkout?.garminCloudUpload?.sessionId !== sessionId || latestWorkout.garminCloudUpload.status !== 'uploading') return
        if (workout.garminCloudUpload.manual !== true && latest.garminCloudAuto !== true) { patch({ status: 'pending' }); return }
        if (initial.S.stravaShareWeights === true && latest.stravaShareWeights !== true) {
          patch({ status: 'pending' })
          continue
        }
        const result = await p.upload({
          sessionId, workoutId: String(wid), filename: `opengym-${String(wid).replace(/[^a-zA-Z0-9_-]/g, '_').slice(0, 100)}.fit`,
          base64: toBase64(bytes), retryUnknown,
        })
        if (!belongs()) return
        if (!['uploaded', 'duplicate'].includes(result?.status)) throw Object.assign(new Error('Garmin did not confirm this upload.'), { code: 'unknown_result' })
        patch({ status: result.status, activityId: result.activityId || null, error: null, retryUnknown: false })
        await store.getState().saveNow()
      } catch (error) {
        patch({ status: 'failed', error: errorCode(error) })
        try { if (belongs()) await store.getState().saveNow?.() } catch { /* No network retry from an unsaved outcome. */ }
        return
      }
    }
  })().finally(() => { draining = null })
  return draining
}

export async function uploadGarminWorkout(store, wid, { retry = false } = {}) {
  const status = await garminCloudStatus()
  if (!status.connected || status.sessionId !== store.getState().S.garminCloudSessionId) throw Object.assign(new Error('Connect this profile to Garmin Connect first.'), { code: 'auth_required' })
  if (!completed(store.getState().S.workouts.find(w => w.id === wid))) throw Object.assign(new Error('This workout has no completed sets.'), { code: 'invalid_fit' })
  store.getState().update(s => {
    const w = s.workouts.find(x => x.id === wid)
    queueGarminCloudUpload(s, w, { manual: true, retry })
  })
  await store.getState().saveNow()
  return drainGarminCloudUploads(store)
}

/** Start only in the Android shell; profile switches revoke the previous cloud connection. */
export async function startGarminCloudSync(store) {
  if (!await plugin()) return () => {}
  let stopped = false
  const kick = () => { if (!stopped && document.visibilityState !== 'hidden') void drainGarminCloudUploads(store) }
  const retryNetwork = () => {
    if (stopped || document.visibilityState === 'hidden') return
    const state = store.getState()
    if (state.ready === false) return
    const eligible = w => w.garminCloudUpload?.status === 'failed' && w.garminCloudUpload.error === 'network_error' &&
      w.garminCloudUpload.sessionId === state.S.garminCloudSessionId && (w.garminCloudUpload.manual || state.S.garminCloudAuto === true)
    if (state.S.workouts?.some(eligible)) state.update(s => { s.workouts.filter(eligible).forEach(w => { w.garminCloudUpload.status = 'pending' }) })
    kick()
  }
  const unsubscribe = store.subscribe((state, previous) => {
    if (state.ready === false) return
    if (previous.ready !== false && ownerOf(state) !== ownerOf(previous)) {
      void disconnectGarminCloud().catch(() => {})
      state.update(s => { s.garminCloudAuto = false; delete s.garminCloudSessionId })
      return
    }
    kick()
  })
  document.addEventListener('visibilitychange', retryNetwork)
  window.addEventListener('online', retryNetwork)
  retryNetwork()
  return () => { stopped = true; unsubscribe(); document.removeEventListener('visibilitychange', retryNetwork); window.removeEventListener('online', retryNetwork) }
}

export function _setGarminCloudPluginForTest(value) { pluginPromise = Promise.resolve(value ? { client: value } : null); draining = null }
