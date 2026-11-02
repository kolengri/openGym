// @vitest-environment happy-dom
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { create } from 'zustand'
import { bindWatchAppActions, bindWatchActions, drainWatchEvents, startWatchSync, _resetWatchSync, _setWatchPluginForTest } from './watch-sync.js'

let stops = []
beforeEach(() => { localStorage.clear(); _resetWatchSync() })
afterEach(() => { stops.reverse().forEach(fn => fn()); stops = []; _resetWatchSync() })
const event = { id: 'wrist-start', type: 'start', wid: 'from-watch', at: 1800000000000, routineIds: [] }
const rig = async (garmin = false) => {
  let queue = []
  const real = { unit: 'kg', routines: [], workouts: [], active: garmin ? { id: 'from-watch', entries: [{ id: '0025', sets: [{ w: 40, r: 8, done: false }] }] } : null }
  const store = create((set, get) => ({ S: real, ready: true, tourSandbox: null,
    update: fn => { const S = structuredClone(get().S); fn(S); set({ S }) },
    saveNow: vi.fn(async () => {}),
  }))
  const bridge = { status: async () => ({ paired: true, installed: true, enabled: true }),
    addListener: async () => ({ remove() {} }), sendSnapshot: vi.fn(async () => ({ sent: true })),
    drain: vi.fn(async () => ({ events: [...queue] })),
    ack: vi.fn(async ({ ids }) => { queue = queue.filter(e => !ids.includes(e.id)) }),
  }
  const start = vi.fn((_, { id }) => store.getState().update(S => { S.active = { id, entries: [], start: 1800000000000 } }))
  stops.push(bindWatchAppActions({ start }))
  const setDone = vi.fn(() => store.getState().update(S => { S.active.entries[0].sets[0].done = true }))
  if (garmin) stops.push(bindWatchActions({ setDone }))
  _setWatchPluginForTest(bridge, store.getState, { garmin })
  stops.push(await startWatchSync({ useStore: store, useUI: { getState: () => ({}), subscribe: () => () => {} } }))
  await drainWatchEvents()
  const enter = () => { const real = store.getState().S; store.setState({ tourSandbox: { real }, S: { ...real, active: { id: 'practice', entries: [] } } }) }
  const exit = () => { const real = store.getState().tourSandbox.real; store.setState({ tourSandbox: null, S: real }) }
  return { store, bridge, start: garmin ? setDone : start, enter, exit, queued: () => [...queue], enqueue: () => queue.push(garmin ? { ...event, type: 'setDone', exId: '0025', entryIdx: 0, setIdx: 0, w: 45, r: 8 } : event) }
}

it('leaves real watch events queued throughout practice and resumes on exit', async () => {
  const r = await rig(); r.enter(); r.enqueue()
  await drainWatchEvents()
  expect(r.start).not.toHaveBeenCalled()
  expect(r.bridge.ack).not.toHaveBeenCalled()
  expect(r.store.getState().S.active.id).toBe('practice')
  r.exit()
  await vi.waitFor(() => expect(r.bridge.ack).toHaveBeenCalledOnce())
  expect(r.start).toHaveBeenCalledOnce()
  expect(r.store.getState().S.active.id).toBe('from-watch')
})

it('fences a complete practice round trip while native drain is awaiting', async () => {
  const r = await rig(); r.enqueue()
  let resolve
  r.bridge.drain.mockImplementationOnce(() => new Promise(done => { resolve = done }))
  const run = drainWatchEvents()
  await vi.waitFor(() => expect(resolve).toBeTypeOf('function'))
  r.enter(); r.exit()
  const calls = r.bridge.drain.mock.calls.length
  resolve({ events: [event] })
  await run
  await vi.waitFor(() => expect(r.bridge.ack).toHaveBeenCalledOnce())
  expect(r.bridge.drain.mock.calls.length).toBeGreaterThan(calls)
  expect(r.start).toHaveBeenCalledOnce()
  expect(r.store.getState().S.active.id).toBe('from-watch')
})

it('defers ACK during practice entered while saving, without applying the event twice', async () => {
  const r = await rig(true); r.enqueue()
  let saved
  r.store.getState().saveNow.mockImplementationOnce(() => new Promise(done => { saved = done }))
  const run = drainWatchEvents()
  await vi.waitFor(() => expect(saved).toBeTypeOf('function'))
  r.enter(); saved(); await run
  expect(r.bridge.ack).not.toHaveBeenCalled()
  expect(r.store.getState().S.active.id).toBe('practice')
  r.exit()
  await vi.waitFor(() => expect(r.bridge.ack).toHaveBeenCalledOnce())
  expect(r.start).toHaveBeenCalledOnce()
  expect(JSON.parse(r.bridge.ack.mock.calls[0][0].json).active.id).toBe('from-watch')
})

it('keeps a Garmin ACK empty when Watch is disabled during the durable save', async () => {
  const r = await rig(true); r.enqueue()
  let saved
  r.store.getState().saveNow.mockImplementationOnce(() => new Promise(done => { saved = done }))
  const run = drainWatchEvents()
  await vi.waitFor(() => expect(saved).toBeTypeOf('function'))
  r.store.getState().update(S => { S.modules = { watch: false } })
  saved(); await run
  expect(r.bridge.ack).toHaveBeenCalledOnce()
  const ack = JSON.parse(r.bridge.ack.mock.calls[0][0].json)
  expect(ack.active).toBeNull()
  expect(ack).not.toHaveProperty('ready')
})


it('resumes an in-flight drain when another transport binds the same store', async () => {
  const r = await rig(); r.enqueue()
  let resolve
  r.bridge.drain.mockImplementationOnce(() => new Promise(done => { resolve = done }))
  const run = drainWatchEvents()
  await vi.waitFor(() => expect(resolve).toBeTypeOf('function'))
  _setWatchPluginForTest(r.bridge, () => r.store.getState())
  resolve({ events: [event] })
  await run
  await vi.waitFor(() => expect(r.bridge.ack).toHaveBeenCalledOnce())
  expect(r.start).toHaveBeenCalledOnce()
})
