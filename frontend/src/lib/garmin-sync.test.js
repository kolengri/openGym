// @vitest-environment happy-dom
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { configureGarmin, garminDevices, garminHeartRate, garminSnapshot, garminStatus, isGarminEvent, receiveGarminHeartRate, _resetGarminForTest, _setGarminPluginForTest } from './garmin-sync.js'
import { applyEvents, bindWatchAppActions, bindWatchActions, buildSnapshot, drainWatchEvents, patchSetIn, startWatchSync, _resetWatchSync, _setWatchPluginForTest } from './watch-sync.js'

beforeEach(() => { localStorage.clear(); _resetGarminForTest(); _resetWatchSync() })
const snapshot = () => ({ v: 1, unit: 'kg', restSec: 60, ready: { private: true }, token: 'not-to-send',
  settings: { restHaptics: true, health: true, credential: 'secret' },
  active: { id: 'workout-1', name: 'Training', start: 1800000000000, cur: 0, accountId: 'private', entries: [
    { id: '0025', name: 'Bench', mode: 'reps', last: 'private history', best: { w: 100 }, sets: [{ w: 40, r: 8, done: false, token: 'private' }] },
  ] },
})
const event = (id, type = 'setDone', extra = {}) => ({ id, type, wid: 'workout-1', at: 1800000000000, entryIdx: 0, exId: '0025', setIdx: 0, ...extra })

describe('Garmin snapshot boundary', () => {
  it('sends only the current workout and explicit watch preferences', () => {
    const out = garminSnapshot(snapshot())
    expect(out.active.entries[0].sets).toEqual([{ w: 40, r: 8, done: false }])
    expect(out.settings).toEqual({ restHaptics: true, recording: true })
    expect(JSON.stringify(out)).not.toMatch(/private|secret|accountId|credential|ready|token|last|best/)
  })
  it('preserves paused rests, per-side sets and timed seconds', () => {
    const snap = snapshot()
    snap.active.entries[0].sets = [{ sec: 45, sides: { L: { w: 5, r: 6, done: true }, R: { w: 5, r: 6, done: false } } }]
    const out = garminSnapshot(snap, { timer: { paused: true, left: 20, endsAt: 1800000030000 }, paused: true })
    expect(out.active.watchPaused).toBe(true)
    expect(out.active.rest).toEqual({ paused: true, left: 20, endsAt: 1800000030000 })
    expect(out.active.entries[0].sets[0]).toMatchObject({ sec: 45, sides: { L: { done: true }, R: { done: false } } })
  })
  it('refuses oversized sessions without silently deleting sets', () => {
    const snap = snapshot()
    snap.active.entries[0].sets = Array.from({ length: 1000 }, () => ({ w: 40, r: 8, done: false }))
    expect(() => garminSnapshot(snap)).toThrow('too large')
    expect(snap.active.entries[0].sets).toHaveLength(1000)
  })
  it('marks drop sets and rest-pause sides for explicit phone completion', () => {
    const out = garminSnapshot(snapshot(), { sourceActive: { entries: [{ sets: [{ sides: { L: { type: 'restpause' }, R: {} } }] }] } })
    expect(out.active.entries[0].sets[0].unsupported).toBe(true)
  })
  it('resolves exercise off, per-set overrides, warmups and side rests with the phone helpers', () => {
    const S = { restSec: 90, warmupRestSec: 20, routines: [], workouts: [], active: snapshot().active }
    const entry = S.active.entries[0]
    entry.target = { restOff: true, sideRestSec: 15 }
    entry.sets = [{ w: 20, r: 8, warmup: true }, { w: 30, r: 8, warmup: true }, { w: 40, r: 8, restSec: 30 }, { w: 40, r: 8, restSec: 0 }, { w: 40, r: 8 }]
    const out = garminSnapshot(buildSnapshot(S), { sourceActive: S.active, warmupRestSec: S.warmupRestSec })
    expect(out.active.entries[0]).toMatchObject({ restSec: 0, sideRestSec: 15 })
    expect(out.active.entries[0].sets.map(s => s.restSec)).toEqual([20, 0, 30, 0, 0])
  })
})

describe('live heart rate', () => {
  const at = 1800000000000
  it('accepts only current, valid samples for this exact workout and expires them', () => {
    expect(receiveGarminHeartRate({ wid: 'other', bpm: 120, at }, 'workout-1', at)).toBe(false)
    expect(receiveGarminHeartRate({ wid: 'workout-1', bpm: 900, at }, 'workout-1', at)).toBe(false)
    expect(receiveGarminHeartRate({ wid: 'workout-1', bpm: 120, at }, 'workout-1', at + 16000)).toBe(false)
    expect(receiveGarminHeartRate({ wid: 'workout-1', bpm: 120, at }, 'workout-1', at)).toBe(true)
    expect(garminHeartRate('workout-1', at + 5000)?.bpm).toBe(120)
    expect(garminHeartRate('workout-1', at + 15001)).toBeNull()
    expect(receiveGarminHeartRate({ wid: 'workout-1', bpm: 110, at: at - 1 }, 'workout-1', at)).toBe(false)
  })
})

describe('Garmin wire weight bounds', () => {
  it.each([5001, 10000])('applies weight %s before acknowledging the native command', async w => {
    const S = { active: snapshot().active, workouts: [], routines: [] }
    const ev = event('boundary-weight', 'setDone', { w, r: 8 })
    expect(isGarminEvent(ev)).toBe(true)
    const p = { drain: async () => ({ events: [ev] }), ack: vi.fn(async () => {}) }
    _setWatchPluginForTest(p, () => ({ S, update: fn => fn(S), saveNow: async () => {} }), { garmin: true })
    const stop = bindWatchActions({ setDone: (idx, setIdx, fields) => { Object.assign(S.active.entries[idx].sets[setIdx], fields, { done: true }) } })
    try {
      await drainWatchEvents()
      expect(S.active.entries[0].sets[0]).toMatchObject({ done: true, w, r: 8 })
      expect(p.ack.mock.calls[0][0].ids).toEqual(['boundary-weight'])
    } finally { stop() }
  })
  it('rejects a weight above the shared wire ceiling', () => {
    expect(isGarminEvent(event('too-heavy', 'setDone', { w: 10001 }))).toBe(false)
  })
})

describe('Garmin commands', () => {
  it('matches imported numeric exercise IDs with the watch snapshot string IDs', () => {
    const S = { active: snapshot().active, workouts: [] }
    S.active.entries[0].id = 25
    const setDone = vi.fn()
    bindWatchActions({ setDone })
    applyEvents([event('numeric', 'setDone', { exId: '25' })], () => ({ S }))
    expect(setDone).toHaveBeenCalledTimes(1)
    S.workouts.push(S.active); S.active = null
    expect(patchSetIn(S, { wid: 'workout-1', exId: '25', entryIdx: 0, setIdx: 0 }, { done: true })).toBe(true)
    expect(S.workouts[0].entries[0].sets[0].done).toBe(true)
  })
  it('rejects missing identities, Apple-only actions and invalid numbers', () => {
    expect(isGarminEvent(event('ok'))).toBe(true)
    for (const ev of [event(''), event('x', 'start'), event('x', 'pause', { paused: 'yes' }),
      event('x', 'pause', { paused: true }), event('x', 'pause', { paused: true, rest: { paused: false, left: 70, endsAt: 1800000090000 } }),
      event('x', 'setDone', { wid: '' }), event('x', 'setDone', { setIdx: -1 }), event('x', 'setDone', { w: Infinity })]) expect(isGarminEvent(ev)).toBe(false)
  })
  it('applies absolute navigation and pause once and ignores other workout IDs', () => {
    const S = { active: snapshot().active, workouts: [] }
    const actions = { selectExercise: vi.fn(), pause: vi.fn(), skipRest: vi.fn() }
    bindWatchAppActions(actions)
    const rest = { paused: true, left: 70, total: 90, endsAt: 1800000090000 }
    expect(isGarminEvent(event('p', 'pause', { paused: true, rest }))).toBe(true)
    const events = [event('n', 'selectExercise'), event('p', 'pause', { source: 'garmin', paused: true, rest }), event('s', 'skipRest'), event('bad', 'pause', { wid: 'old', paused: true, rest: null })]
    applyEvents([...events, ...events], () => ({ S }))
    expect(actions.selectExercise).toHaveBeenCalledExactlyOnceWith(0)
    expect(actions.pause).toHaveBeenCalledExactlyOnceWith(true, { rest })
    expect(actions.skipRest).toHaveBeenCalledTimes(1)
  })
  it('keeps commands queued while the store is restoring from disk', async () => {
    const p = { drain: vi.fn(), ack: vi.fn() }
    _setWatchPluginForTest(p, () => ({ ready: false, S: { active: snapshot().active } }), { garmin: true })
    expect(await drainWatchEvents()).toEqual([])
    expect(p.drain).not.toHaveBeenCalled()
    expect(p.ack).not.toHaveBeenCalled()
  })
  it('waits for persistence, then acknowledges with the post-apply state', async () => {
    const S = { active: snapshot().active, workouts: [], routines: [] }
    let persist
    const saved = new Promise(resolve => { persist = resolve })
    const p = { drain: async () => ({ events: [event('tick')] }), ack: vi.fn(async () => {}) }
    _setWatchPluginForTest(p, () => ({ S, update: fn => fn(S), saveNow: () => saved }), { garmin: true })
    bindWatchActions({ setDone: () => { S.active.entries[0].sets[0].done = true } })
    const draining = drainWatchEvents()
    await vi.waitFor(() => expect(S.active.entries[0].sets[0].done).toBe(true))
    expect(p.ack).not.toHaveBeenCalled()
    persist()
    await draining
    expect(p.ack).toHaveBeenCalledTimes(1)
    const ack = p.ack.mock.calls[0][0]
    expect(ack.ids).toEqual(['tick'])
    expect(JSON.parse(ack.json).active.entries[0].sets[0].done).toBe(true)
  })
  it('does not acknowledge a command when durable persistence fails', async () => {
    const S = { active: snapshot().active, workouts: [] }
    const p = { drain: async () => ({ events: [event('tick')] }), ack: vi.fn() }
    _setWatchPluginForTest(p, () => ({ S, update: fn => fn(S), saveNow: async () => { throw new Error('disk full') } }), { garmin: true })
    bindWatchActions({ setDone: vi.fn() })
    await drainWatchEvents()
    expect(p.ack).not.toHaveBeenCalled()
  })
  it('retries a failed save in the same process without reapplying its command', async () => {
    const S = { active: snapshot().active, workouts: [], routines: [] }
    const saveNow = vi.fn().mockRejectedValueOnce(new Error('disk full')).mockResolvedValue(undefined)
    const p = { drain: async () => ({ events: [event('retry')] }), ack: vi.fn(async () => {}) }
    _setWatchPluginForTest(p, () => ({ S, update: fn => fn(S), saveNow }), { garmin: true })
    const apply = vi.fn(() => { S.active.entries[0].sets[0].done = true })
    const stop = bindWatchActions({ setDone: apply })
    await drainWatchEvents()
    expect(p.ack).not.toHaveBeenCalled()
    expect(S.garminAppliedEvents).toEqual(['retry'])
    await drainWatchEvents()
    expect(apply).toHaveBeenCalledTimes(1)
    expect(saveNow).toHaveBeenCalledTimes(2)
    expect(p.ack).toHaveBeenCalledTimes(1)
    stop()
  })
  it('persists only the applied prefix and keeps a concurrent tail for the next drain', async () => {
    const S = { active: snapshot().active, workouts: [], routines: [] }
    let persist
    const firstSave = new Promise(resolve => { persist = resolve })
    const saveNow = vi.fn().mockReturnValueOnce(firstSave).mockResolvedValue(undefined)
    const events = [event('prefix'), event('select', 'selectExercise')]
    const p = { drain: async () => ({ events: [...events] }), ack: vi.fn(async () => {}) }
    _setWatchPluginForTest(p, () => ({ S, update: fn => fn(S), saveNow }), { garmin: true })
    const setDone = vi.fn(() => { S.active.entries[0].sets[0].done = true })
    const stopSets = bindWatchActions({ setDone })
    const first = drainWatchEvents()
    await vi.waitFor(() => expect(saveNow).toHaveBeenCalledTimes(1))
    events.push(event('tail', 'skipRest'))
    expect(S.garminAppliedEvents).toEqual(['prefix'])
    persist()
    await first
    expect(p.ack.mock.calls[0][0].ids).toEqual(['prefix'])
    const selectExercise = vi.fn(), skipRest = vi.fn()
    const stopApp = bindWatchAppActions({ selectExercise, skipRest })
    await drainWatchEvents()
    expect(setDone).toHaveBeenCalledTimes(1)
    expect(selectExercise).toHaveBeenCalledTimes(1)
    expect(skipRest).toHaveBeenCalledTimes(1)
    expect(S.garminAppliedEvents).toEqual(['prefix', 'select', 'tail'])
    stopApp(); stopSets()
  })
})

describe('explicit connection', () => {
  it('keeps the link during owner restoration, but disables it on a live account switch', async () => {
    let state = { ready: false, S: { unit: 'kg', routines: [], workouts: [], active: null }, user: null }
    let listener
    let enabled = true
    const bridge = {
      status: async () => ({ paired: true, installed: true, enabled }),
      configure: vi.fn(async config => { enabled = config.enabled; return { enabled } }),
      addListener: async () => ({ remove() {} }), drain: async () => ({ events: [] }),
      sendSnapshot: async () => ({ sent: true }),
    }
    _setGarminPluginForTest(bridge)
    _setWatchPluginForTest(bridge, () => state, { garmin: true })
    const stop = await startWatchSync({
      useStore: { getState: () => state, subscribe: fn => { listener = fn; return () => {} } },
      useUI: { getState: () => ({ timer: null }), subscribe: () => () => {} },
    })
    try {
      const prev = state
      state = { ...state, ready: true, user: { id: 'synthetic-owner' } }
      listener(state, prev)
      await Promise.resolve()
      expect(bridge.configure).not.toHaveBeenCalled()
      const restored = state
      state = { ...state, user: { id: 'synthetic-other-owner' } }
      listener(state, restored)
      await vi.waitFor(() => expect(bridge.configure).toHaveBeenCalledExactlyOnceWith({ enabled: false }))
    } finally { stop() }
  })
  it('keeps setup in the native private bridge and never enables a watch from a status check', async () => {
    const bridge = { status: vi.fn(async () => ({ available: true, enabled: false })), devices: async () => ({ devices: [{ id: 'synthetic', name: 'Test watch' }] }), configure: vi.fn(async () => ({ enabled: true })) }
    _setGarminPluginForTest(bridge)
    expect((await garminStatus()).enabled).toBe(false)
    expect(await garminDevices()).toHaveLength(1)
    expect(bridge.configure).not.toHaveBeenCalled()
    await configureGarmin({ enabled: true, deviceId: 'synthetic' })
    expect(bridge.configure).toHaveBeenCalledExactlyOnceWith({ enabled: true, deviceId: 'synthetic' })
  })
})
