// @vitest-environment happy-dom
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { create } from 'zustand'

const h = vi.hoisted(() => ({ platform: 'android' }))
vi.mock('./mobile.js', () => ({ MOBILE: true, nativePlatform: async () => h.platform }))
vi.mock('./rest-alert.js', async original => ({
  ...(await original()),
  updateWorkoutNotification: vi.fn(async () => true),
  armRestAlert: vi.fn(async () => true),
  disarmRestAlert: vi.fn(),
}))
import { armRestAlert, disarmRestAlert, updateWorkoutNotification } from './rest-alert.js'
import { buildWorkoutNotification, startWorkoutNotificationSync } from './workout-notification.js'

const active = () => ({ id: 'w1', name: 'Push', cur: 0, entries: [
  { id: '0025', sets: [{ w: 60, r: 8, done: true }, { w: 62.5, r: 8, done: false }], target: { mode: 'reps' } },
  { id: 'custom', name: 'Cable thing', sets: [{ r: 10, done: false }], target: { mode: 'reps' } },
] })
const state = (A = active()) => ({ active: A, unit: 'kg', accent: 'lime', restSec: 90, sound: true })
let stop
beforeEach(() => { h.platform = 'android'; vi.clearAllMocks() })
afterEach(() => { stop?.(); stop = null })
const stores = (S = state(), ready = true) => ({
  useStore: create(() => ({ S, ready })),
  useUI: create(() => ({ timer: null, work: null })),
})

describe('the workout notification snapshot', () => {
  it('shares the localized exercise, next set and target formatting with the workout activity', () => {
    expect(buildWorkoutNotification(state())).toMatchObject({
      wid: 'w1', title: 'Push', exercise: 'Barbell Bench Press', done: 1, total: 3,
    })
    expect(buildWorkoutNotification(state()).detail).toMatch(/^Set 2 of 2 · .*62[.,]5/)
  })
  it('already exists for an empty workout, and ends for finished/discarded sessions or history edits', () => {
    expect(buildWorkoutNotification(state({ id: 'new', entries: [] }))).toMatchObject({ wid: 'new', total: 0 })
    expect(buildWorkoutNotification(state(null))).toBeNull()
    expect(buildWorkoutNotification(state({ ...active(), editingWorkoutId: 'history' }))).toBeNull()
  })
})

describe('Android workout notification lifetime', () => {
  it('waits for private storage restoration, then starts before any timer, updates exercises and stops on finish', async () => {
    const s = stores(state(), false)
    stop = await startWorkoutNotificationSync(s)
    expect(updateWorkoutNotification).not.toHaveBeenCalled()
    s.useStore.setState({ ready: true })
    expect(updateWorkoutNotification).toHaveBeenLastCalledWith(expect.objectContaining({ wid: 'w1', exercise: 'Barbell Bench Press' }))
    s.useStore.setState({ S: state({ ...active(), cur: 1 }) })
    expect(updateWorkoutNotification).toHaveBeenLastCalledWith(expect.objectContaining({ exercise: 'Cable thing' }))
    // A rest tick/pause is native timer state; it never creates another workout card.
    const count = updateWorkoutNotification.mock.calls.length
    s.useUI.setState({ timer: { endsAt: Date.now() + 90000, left: 90, total: 90 } })
    s.useUI.setState({ timer: { left: 80, total: 90, paused: true } })
    expect(updateWorkoutNotification).toHaveBeenCalledTimes(count)
    s.useStore.setState({ S: state(null) })
    expect(updateWorkoutNotification).toHaveBeenLastCalledWith(null)
  })
  it('arms a timed set once, without rest controls, and cancels it on an early finish', async () => {
    const s = stores()
    stop = await startWorkoutNotificationSync(s)
    const work = { endsAt: Date.now() + 45000, total: 45, left: 45, label: 'Plank' }
    s.useUI.setState({ work })
    expect(armRestAlert).toHaveBeenCalledExactlyOnceWith(work.endsAt, expect.objectContaining({ controls: false, countdownTitle: 'Plank', totalSec: 45, sound: true }))
    s.useUI.setState({ work: { ...work, left: 44 } })
    expect(armRestAlert).toHaveBeenCalledTimes(1)
    s.useUI.setState({ work: null })
    expect(disarmRestAlert).toHaveBeenCalledTimes(1)
    expect(updateWorkoutNotification).not.toHaveBeenCalledWith(null)
  })
  it('reconciles native Pause/Skip on resume even when workout metadata did not change', async () => {
    const s = stores()
    stop = await startWorkoutNotificationSync(s)
    s.useUI.setState({ timer: { left: 80, total: 90, paused: true } })
    Object.defineProperty(document, 'visibilityState', { configurable: true, value: 'visible' })
    document.dispatchEvent(new Event('visibilitychange'))
    expect(updateWorkoutNotification).toHaveBeenLastCalledWith(expect.objectContaining({ reconcile: true, hasRest: true }))
    stop(); stop = null
    const count = updateWorkoutNotification.mock.calls.length
    s.useStore.setState({ S: state(null) })
    expect(updateWorkoutNotification).toHaveBeenCalledTimes(count)
  })
  it.each(['ios', null])('does nothing on %s', async platform => {
    h.platform = platform
    stop = await startWorkoutNotificationSync(stores())
    expect(updateWorkoutNotification).not.toHaveBeenCalled()
    expect(armRestAlert).not.toHaveBeenCalled()
  })
})
