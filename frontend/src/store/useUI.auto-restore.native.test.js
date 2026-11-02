// @vitest-environment happy-dom
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
vi.mock('../lib/mobile.js', async original => ({ ...(await original()), MOBILE: true, nativePlatform: async () => 'android' }))
vi.mock('../lib/rest-alert.js', async original => ({ ...(await original()),
  armRestAlert: vi.fn(async () => true), disarmRestAlert: vi.fn(), updateWorkoutNotification: vi.fn(async () => true),
}))
import { armRestAlert, disarmRestAlert } from '../lib/rest-alert.js'
import { useUI, restoreWork, WORK_KEY } from './useUI.js'
import { useStore } from './useStore.js'
import { startWorkoutNotificationSync } from '../lib/workout-notification.js'
let original, stop
beforeEach(() => {
  vi.useFakeTimers(); original = useStore.getState()
  useStore.setState({ ready: true, tourSandbox: null, S: { ...original.S, autoHolds: true, restSec: 10,
    active: { id: 'w', entries: [{ id: 'plank', target: { mode: 'time' }, sets: [{ sec: 15 }, { sec: 20 }] }] } } })
  useUI.setState({ work: null, timer: null, countIn: null }); localStorage.clear(); vi.clearAllMocks()
})
afterEach(() => { stop?.(); stop = null; useUI.getState().stopWork(); useUI.getState().stopRest(); useStore.setState(original); vi.useRealTimers() })
const restore = () => {
  localStorage.setItem(WORK_KEY, JSON.stringify({ total: 15, endsAt: Date.now() + 12000, label: 'Plank', auto: true, owner: { idx: 0, i: 0, id: 'plank' } }))
  expect(restoreWork()).toBe(true)
}
it('restores the native forecast before screen hooks bind and never replaces it with a generic work alarm', async () => {
  restore()
  expect(armRestAlert).toHaveBeenCalledOnce()
  expect(armRestAlert.mock.calls[0][1]).toMatchObject({ countdown: false, controls: false, cues: expect.any(Array) })
  expect(armRestAlert.mock.calls[0][1].cues.length).toBeGreaterThan(0)
  stop = await startWorkoutNotificationSync({ useStore, useUI })
  expect(armRestAlert).toHaveBeenCalledOnce()
})
it('cancels the forecast before booking the remaining manual hold when auto is stopped', async () => {
  restore(); stop = await startWorkoutNotificationSync({ useStore, useUI })
  useUI.getState().stopAuto()
  expect(armRestAlert).toHaveBeenCalledTimes(2)
  expect(armRestAlert.mock.calls[1][1]).not.toHaveProperty('cues')
  expect(disarmRestAlert.mock.invocationCallOrder.at(-1)).toBeLessThan(armRestAlert.mock.invocationCallOrder.at(-1))
})
