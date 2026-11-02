// @vitest-environment happy-dom
import React, { act } from 'react'
import { createRoot } from 'react-dom/client'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import GarminLiveStatus, { GarminConnectionDetails } from './GarminLiveStatus.jsx'
import { _resetGarminForTest, _setGarminPluginForTest, receiveGarminStatus, receiveGarminHeartRate, garminConnection, configureGarmin, garminStatus, GARMIN_HR_MAX_AGE, GARMIN_REPLY_MAX_AGE } from '../lib/garmin-sync.js'

globalThis.IS_REACT_ACT_ENVIRONMENT = true
let root, host, state
const at = 1800000000000
const diagnostics = () => ({ workoutId: 'workout-a', lastMessageAt: at, lastConfirmedAt: at, snapshotConfirmed: true, watchPending: 0, phonePending: 0 })
beforeEach(() => {
  vi.useFakeTimers(); vi.setSystemTime(at); _resetGarminForTest()
  state = { available: true, enabled: true, connected: true, installed: true, paired: true, linkEpoch: 1, diagnostics: diagnostics() }
  _setGarminPluginForTest({ status: async () => state })
  host = document.createElement('div'); document.body.append(host); root = createRoot(host)
})
afterEach(() => { act(() => root.unmount()); host.remove(); _resetGarminForTest(); vi.useRealTimers() })
const render = async wid => { await act(async () => root.render(<GarminLiveStatus wid={wid} />)) }
const renderDetails = async wid => {
  receiveGarminStatus(state)
  await act(async () => root.render(<GarminConnectionDetails connection={garminConnection(wid)} />))
}

it('shows only the heart icon and fresh heart rate for the active workout', async () => {
  state.diagnostics = { ...diagnostics(), watchPending: 2, phonePending: 1 }
  await render('workout-a')
  expect(host.childElementCount).toBe(0)
  await act(async () => receiveGarminHeartRate({ wid: 'workout-a', at, bpm: 74 }, 'workout-a'))
  expect(host.textContent.trim()).toBe('74 bpm')
  expect(host.querySelector('[role="status"]').getAttribute('aria-label')).toBe('Heart rate')
  expect(host.querySelector('svg')).not.toBeNull()
  expect(host.querySelector('button, small, .garmin-connection-details')).toBeNull()
  await render('workout-b')
  expect(host.childElementCount).toBe(0)
})

it.each([
  ['disconnected', { connected: false }],
  ['disabled', { enabled: false }],
])('hides the entire heart-rate block when the watch is %s despite a fresh sample', async (_, status) => {
  await render('workout-a')
  await act(async () => receiveGarminHeartRate({ wid: 'workout-a', at, bpm: 82 }, 'workout-a'))
  expect(host.textContent.trim()).toBe('82 bpm')
  await act(async () => receiveGarminStatus({ ...state, ...status }))
  expect(host.childElementCount).toBe(0)
  await act(async () => receiveGarminStatus(state))
  expect(host.textContent.trim()).toBe('82 bpm')
})

it('hides missing and expired samples without a placeholder', async () => {
  await render('workout-a')
  expect(host.childElementCount).toBe(0)
  await act(async () => receiveGarminHeartRate({ wid: 'workout-a', at, bpm: 74 }, 'workout-a'))
  await act(async () => vi.advanceTimersByTimeAsync(GARMIN_HR_MAX_AGE))
  expect(host.textContent.trim()).toBe('74 bpm')
  await act(async () => vi.advanceTimersByTimeAsync(1000))
  expect(host.childElementCount).toBe(0)
})

it.each([
  { wid: 'workout-b', at, bpm: 82 },
  { wid: 'workout-a', at, bpm: 0 },
  { wid: 'workout-a', at, bpm: 251 },
  { wid: 'workout-a', at, bpm: NaN },
  { wid: 'workout-a', at: at - GARMIN_HR_MAX_AGE - 1, bpm: 82 },
  { wid: 'workout-a', at: at + 5001, bpm: 82 },
])('does not show rejected heart-rate data: %j', async sample => {
  await render('workout-a')
  await act(async () => expect(receiveGarminHeartRate(sample, 'workout-a')).toBe(false))
  expect(host.childElementCount).toBe(0)
})

it('preserves separate queue diagnostics for settings without attributing another workout confirmation', async () => {
  state.diagnostics = { ...diagnostics(), watchPending: 2, phonePending: 1, snapshotConfirmed: false }
  await renderDetails('workout-a')
  expect(host.textContent).toContain('2 commands waiting on the watch')
  expect(host.textContent).toContain('1 commands waiting on the phone')
  await renderDetails('workout-b')
  expect(host.textContent).toContain('Waiting for workout confirmation')
  expect(host.textContent).not.toContain('commands waiting')
  expect(host.textContent).not.toContain('Last workout confirmation')
})

it('preserves confirmed and expired watch reply diagnostics in settings', async () => {
  await renderDetails('workout-a')
  expect(host.textContent).toContain('Workout confirmed on the watch')
  await act(async () => vi.advanceTimersByTimeAsync(GARMIN_REPLY_MAX_AGE + 1))
  await renderDetails('workout-a')
  expect(host.textContent).toContain('Watch app is not responding')
  expect(host.textContent).not.toContain('Workout confirmed on the watch')
})

it('does not treat Bluetooth or legacy status as a watch application confirmation in settings', async () => {
  delete state.diagnostics
  await renderDetails('workout-a')
  expect(host.textContent).toContain('Waiting for openGym on the watch')
  expect(host.textContent).not.toContain('Workout confirmed')
})

it('ignores late native generations and in-flight status after reconfiguration', async () => {
  receiveGarminStatus(state)
  receiveGarminStatus({ ...state, linkEpoch: 0, diagnostics: { ...diagnostics(), watchPending: 9 } })
  expect(garminConnection('workout-a').watchPending).toBe(0)
  let releaseStatus
  _setGarminPluginForTest({ status: () => new Promise(resolve => { releaseStatus = resolve }), configure: async () => ({ ...state, enabled: false, linkEpoch: 2 }) })
  const pending = garminStatus()
  await Promise.resolve(); await Promise.resolve()
  await configureGarmin({ enabled: false })
  releaseStatus(state); await pending
  expect(garminConnection('workout-a').enabled).toBe(false)
  expect(garminConnection('workout-a').sample).toBeNull()
})
