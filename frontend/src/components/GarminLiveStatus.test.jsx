// @vitest-environment happy-dom
import React, { act } from 'react'
import { createRoot } from 'react-dom/client'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import GarminLiveStatus from './GarminLiveStatus.jsx'
import { _resetGarminForTest, _setGarminPluginForTest, receiveGarminStatus, receiveGarminHeartRate, garminConnection, configureGarmin, garminStatus } from '../lib/garmin-sync.js'

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
const render = async wid => { await act(async () => root.render(<GarminLiveStatus wid={wid} paused={false} />)) }

it('keeps missing and stale heart rate visible and expires watch confirmation', async () => {
  await render('workout-a')
  expect(host.textContent).toContain('Workout confirmed on the watch')
  expect(host.textContent).toContain('Heart rate unavailable')
  await act(async () => receiveGarminHeartRate({ wid: 'workout-a', at, bpm: 74 }, 'workout-a'))
  expect(host.textContent).toContain('74 bpm')
  await act(async () => vi.advanceTimersByTimeAsync(16000))
  expect(host.textContent).toContain('Heart rate data is stale')
  await act(async () => vi.advanceTimersByTimeAsync(30000))
  expect(host.textContent).toContain('Watch app is not responding')
})

it('does not attribute another workout confirmation and displays queues separately', async () => {
  state.diagnostics = { ...diagnostics(), watchPending: 2, phonePending: 1, snapshotConfirmed: false }
  await render('workout-a')
  expect(host.textContent).toContain('2 commands waiting on the watch')
  expect(host.textContent).toContain('1 commands waiting on the phone')
  await render('workout-b')
  expect(host.textContent).toContain('Waiting for workout confirmation')
  expect(host.textContent).not.toContain('commands waiting')
  expect(host.textContent).not.toContain('Last workout confirmation')
})

it('does not treat Bluetooth or legacy status as a watch application confirmation', async () => {
  delete state.diagnostics
  await render('workout-a')
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
