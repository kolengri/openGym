// @vitest-environment happy-dom
import { beforeEach, expect, it, vi } from 'vitest'
import { appendGarminCloudHeartRate, drainGarminCloudUploads, queueGarminCloudUpload, startGarminCloudSync, uploadGarminWorkout, _setGarminCloudPluginForTest } from './garmin-cloud.js'
import { workoutFit } from './fit-export.js'
import { toBase64 } from './media-store-fs.js'
import { buildCompletedWorkout } from './finish-workout.js'

const start = 1800000000000
const workout = () => ({ id: 'synthetic-workout', start, end: start + 60000, entries: [{ id: '0025', target: { mode: 'reps' }, sets: [{ done: true, w: 40, r: 8, at: start + 30000 }] }] })
function storeOf(extra = {}) {
  const listeners = new Set()
  let state = { ready: true, user: null, S: { workouts: [workout()], garminCloudAuto: true, garminCloudSessionId: 'synthetic-session', ...extra } }
  const store = { getState: () => state, subscribe: fn => { listeners.add(fn); return () => listeners.delete(fn) } }
  state.update = fn => { const previous = state; const S = structuredClone(state.S); fn(S); state = { ...state, S }; listeners.forEach(fn => fn(state, previous)) }
  state.saveNow = vi.fn(async () => {})
  store.switchOwner = id => { const previous = state; state = { ...state, user: { id } }; listeners.forEach(fn => fn(state, previous)) }
  return store
}
let bridge
beforeEach(() => {
  bridge = { status: vi.fn(async () => ({ available: true, connected: true, sessionId: 'synthetic-session' })), upload: vi.fn(async () => ({ status: 'uploaded', activityId: 'synthetic-activity' })), disconnect: vi.fn(async () => {}) }
  _setGarminCloudPluginForTest(bridge)
})

it('queues only deliberately enabled new completions and never uploads plain imported history', async () => {
  const store = storeOf({ garminCloudAuto: undefined })
  expect(queueGarminCloudUpload(store.getState().S, store.getState().S.workouts[0])).toBe(false)
  await drainGarminCloudUploads(store)
  expect(bridge.upload).not.toHaveBeenCalled()
  store.getState().update(s => { s.garminCloudAuto = true; expect(queueGarminCloudUpload(s, s.workouts[0])).toBe(true) })
  await drainGarminCloudUploads(store)
  expect(bridge.upload).toHaveBeenCalledTimes(1)
  expect(store.getState().S.workouts[0].garminCloudUpload).toMatchObject({ status: 'uploaded', sessionId: 'synthetic-session' })
})

it('persists workout and upload intent before handing the weight-free FIT to native code', async () => {
  const store = storeOf()
  queueGarminCloudUpload(store.getState().S, store.getState().S.workouts[0])
  let release
  store.getState().saveNow.mockImplementationOnce(() => new Promise(resolve => { release = resolve }))
  const task = drainGarminCloudUploads(store)
  await vi.waitFor(() => expect(release).toBeTypeOf('function'))
  expect(bridge.upload).not.toHaveBeenCalled()
  release(); await task
  const payload = bridge.upload.mock.calls[0][0]
  expect(payload).toMatchObject({ sessionId: 'synthetic-session', workoutId: 'synthetic-workout', filename: 'opengym-synthetic-workout.fit' })
  expect(payload.base64).toBe(toBase64(workoutFit(workout(), { includeWeights: false })))
  expect(store.getState().saveNow).toHaveBeenCalledTimes(2)
})

it('does not send a workout after failed durable persistence', async () => {
  const store = storeOf()
  queueGarminCloudUpload(store.getState().S, store.getState().S.workouts[0])
  store.getState().saveNow.mockRejectedValue(new Error('synthetic write failure'))
  await drainGarminCloudUploads(store)
  expect(bridge.upload).not.toHaveBeenCalled()
  expect(store.getState().S.workouts[0].garminCloudUpload.error).toBe('storage_error')
})

it('does not broaden queued weight consent, and honors a later switch off', async () => {
  for (const [queued, current] of [[false, true], [true, false]]) {
    const store = storeOf({ stravaShareWeights: queued })
    queueGarminCloudUpload(store.getState().S, store.getState().S.workouts[0])
    store.getState().update(s => { s.stravaShareWeights = current })
    await drainGarminCloudUploads(store)
    expect(bridge.upload.mock.lastCall[0].base64).toBe(toBase64(workoutFit(workout(), { includeWeights: false })))
  }
})

it('keeps ambiguous uploads stopped until an explicit retry of that workout', async () => {
  bridge.upload.mockRejectedValueOnce(Object.assign(new Error('synthetic ambiguity'), { code: 'unknown_result' }))
  const store = storeOf()
  queueGarminCloudUpload(store.getState().S, store.getState().S.workouts[0])
  await drainGarminCloudUploads(store)
  await drainGarminCloudUploads(store)
  expect(bridge.upload).toHaveBeenCalledTimes(1)
  expect(store.getState().S.workouts[0].garminCloudUpload).toMatchObject({ status: 'failed', error: 'unknown_result' })
  await uploadGarminWorkout(store, 'synthetic-workout', { retry: true })
  expect(bridge.upload.mock.lastCall[0].retryUnknown).toBe(true)
  expect(store.getState().S.workouts[0].garminCloudUpload.status).toBe('uploaded')
})

it('leaves old Garmin-session jobs fenced after a reconnect', async () => {
  const store = storeOf()
  queueGarminCloudUpload(store.getState().S, store.getState().S.workouts[0])
  bridge.status.mockResolvedValue({ connected: true, sessionId: 'other-session' })
  await drainGarminCloudUploads(store)
  expect(bridge.upload).not.toHaveBeenCalled()
  expect(store.getState().S.workouts[0].garminCloudUpload.error).toBe('session_changed')
})

it('does not upload a deleted workout or a switched profile after awaiting persistence', async () => {
  for (const change of [store => store.getState().update(s => { s.workouts = [] }), store => store.switchOwner('other-profile')]) {
    const store = storeOf()
    queueGarminCloudUpload(store.getState().S, store.getState().S.workouts[0])
    store.getState().saveNow.mockImplementationOnce(async () => change(store))
    const count = bridge.upload.mock.calls.length
    await drainGarminCloudUploads(store)
    expect(bridge.upload.mock.calls.length).toBe(count)
  }
})

it('revokes the native cloud connection on a live openGym profile switch', async () => {
  const store = storeOf()
  const stop = await startGarminCloudSync(store)
  store.switchOwner('other-profile')
  await vi.waitFor(() => expect(bridge.disconnect).toHaveBeenCalledTimes(1))
  expect(store.getState().S.garminCloudSessionId).toBeUndefined()
  expect(store.getState().S.garminCloudAuto).toBe(false)
  stop()
})

it('does not retry an ambiguous POST on a network event', async () => {
  const store = storeOf()
  queueGarminCloudUpload(store.getState().S, store.getState().S.workouts[0])
  bridge.upload.mockRejectedValueOnce(Object.assign(new Error('synthetic timeout'), { code: 'unknown_result' }))
  const stop = await startGarminCloudSync(store)
  await vi.waitFor(() => expect(store.getState().S.workouts[0].garminCloudUpload.status).toBe('failed'))
  window.dispatchEvent(new Event('online'))
  await drainGarminCloudUploads(store)
  expect(bridge.upload).toHaveBeenCalledTimes(1)
  stop()
})

it('retains real watch samples at completion without filling Bluetooth gaps', () => {
  const S = { garminCloudAuto: true, active: { ...workout(), garminHrSamples: [] } }
  expect(appendGarminCloudHeartRate(S, { wid: 'other', at: start + 1000, bpm: 100 })).toBe(false)
  expect(appendGarminCloudHeartRate(S, { wid: S.active.id, at: start + 5000, bpm: 110 })).toBe(true)
  expect(appendGarminCloudHeartRate(S, { wid: S.active.id, at: start + 5000, bpm: 120 })).toBe(false)
  expect(appendGarminCloudHeartRate(S, { wid: S.active.id, at: start + 55000, bpm: 140 })).toBe(true)
  expect(buildCompletedWorkout(S.active, { end: start + 60000 }).garminHrSamples).toEqual([[start + 5000, 110], [start + 55000, 140]])
})

it('consumes an explicit ambiguous retry before persisting the attempted upload', async () => {
  const store = storeOf()
  store.getState().update(s => { queueGarminCloudUpload(s, s.workouts[0], { manual: true, retry: true }) })
  let saved
  store.getState().saveNow.mockImplementation(async () => { saved = structuredClone(store.getState().S) })
  bridge.upload.mockImplementationOnce(async payload => {
    expect(payload.retryUnknown).toBe(true)
    expect(saved.workouts[0].garminCloudUpload.retryUnknown).toBe(false)
    throw Object.assign(new Error('synthetic interrupted attempt'), { code: 'unknown_result' })
  })
  await drainGarminCloudUploads(store)
  const restored = storeOf(saved)
  restored.getState().update(s => { s.workouts[0].garminCloudUpload.status = 'uploading' })
  await drainGarminCloudUploads(restored)
  expect(bridge.upload.mock.calls[1][0].retryUnknown).toBe(false)
})

it('never awaits the then property of the native Capacitor plugin proxy', async () => {
  bridge.then = vi.fn(() => { throw new Error('native plugin must not be a promise value') })
  const store = storeOf()
  queueGarminCloudUpload(store.getState().S, store.getState().S.workouts[0])
  await drainGarminCloudUploads(store)
  expect(bridge.then).not.toHaveBeenCalled()
  expect(bridge.upload).toHaveBeenCalledOnce()
})
