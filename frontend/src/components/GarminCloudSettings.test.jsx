// @vitest-environment happy-dom
import React, { act } from 'react'
import { createRoot } from 'react-dom/client'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { DEF, useStore } from '../store/useStore.js'
import GarminCloudSettings from './GarminCloudSettings.jsx'
import GarminCloudUploadButton from './GarminCloudUploadButton.jsx'
import { _setGarminCloudPluginForTest } from '../lib/garmin-cloud.js'
import { setLang } from '../lib/i18n.js'

let root, host, bridge
beforeEach(() => {
  globalThis.IS_REACT_ACT_ENVIRONMENT = true
  useStore.setState({ S: structuredClone(DEF), user: null, ready: true })
  bridge = {
    status: vi.fn(async () => ({ available: true, connected: false })),
    connect: vi.fn(async () => ({ available: true, connected: true, sessionId: 'synthetic-session' })),
    disconnect: vi.fn(async () => {}),
    upload: vi.fn(async () => ({ status: 'uploaded' })),
  }
  _setGarminCloudPluginForTest(bridge)
  host = document.createElement('div'); document.body.appendChild(host); root = createRoot(host)
})
afterEach(async () => { act(() => root.unmount()); host.remove(); await setLang('en') })
const render = async element => { await act(async () => { root.render(element) }) }
const button = text => [...host.querySelectorAll('button')].find(b => b.textContent.trim() === text)

it('shows expired authentication separately from connected credentials and storage errors', async () => {
  bridge.status.mockResolvedValue({ available: true, connected: true, sessionId: 'synthetic-session', authState: 'expired' })
  useStore.getState().update(s => { s.garminCloudSessionId = 'synthetic-session'; s.garminCloudAuto = true })
  await render(<GarminCloudSettings />)
  expect(host.textContent).toContain('Your Garmin Connect session has expired.')
  expect(host.textContent).not.toContain('Connected to Garmin Connect')
  expect(host.textContent).not.toContain('upload journal needs attention')
  expect(button('Sign in to Garmin Connect').disabled).toBe(false)
  expect(host.querySelector('[role="switch"]').disabled).toBe(true)
  expect(useStore.getState().S.garminCloudSessionId).toBe('synthetic-session')
  expect(useStore.getState().S.garminCloudAuto).toBe(true)
})

it('reports an unparseable expiry without changing the saved connection or pretending expiry was verified', async () => {
  bridge.status.mockResolvedValue({ available: true, connected: true, sessionId: 'synthetic-session', authState: 'unknown' })
  useStore.getState().update(s => { s.garminCloudSessionId = 'synthetic-session' })
  await render(<GarminCloudSettings />)
  expect(host.textContent).toContain('Garmin session expiration could not be checked.')
  expect(host.textContent).not.toContain('Connected to Garmin Connect')
  expect(button('Disconnect Garmin Connect')).toBeDefined()
  expect(useStore.getState().S.garminCloudSessionId).toBe('synthetic-session')
})

it('reports a cancelled sign-in without suggesting reconnecting or changing the local binding', async () => {
  bridge.connect.mockRejectedValue(Object.assign(new Error('synthetic cancellation'), { code: 'cancelled' }))
  await render(<GarminCloudSettings />)
  await act(async () => { button('Sign in to Garmin Connect').click() })
  expect(host.querySelector('[role="alert"]').textContent).toContain('The Garmin action was cancelled.')
  expect(host.textContent).not.toContain('Reconnect or retry')
  expect(useStore.getState().S.garminCloudSessionId).toBeUndefined()
})

it.each([
  ['auth_expired', 'Your Garmin Connect session has expired.'],
  ['auth_required', 'Your saved session was not accepted.'],
  ['network_error', 'Check your connection and retry.'],
  ['invalid_fit', 'valid FIT file'],
  ['upload_failed', 'Check your access in Garmin Connect'],
  ['storage_error', 'Check local storage and retry.'],
  ['cancelled', 'The Garmin action was cancelled.'],
  ['unknown_result', 'Check Connect before retrying.'],
  ['session_changed', 'automatic replay is blocked.'],
  ['content_changed', 'automatic replay is blocked.'],
])('shows an actionable %s upload result without generic reconnect advice', async (code, expected) => {
  const w = { id: 'synthetic-error', start: 1800000000000, end: 1800000060000, entries: [{ id: '0025', sets: [{ done: true, r: 8, w: 40 }] }] }
  bridge.status.mockResolvedValue({ available: true, connected: true, sessionId: 'synthetic-session' })
  bridge.upload.mockRejectedValue(Object.assign(new Error('synthetic failure'), { code }))
  useStore.getState().update(s => { s.garminCloudSessionId = 'synthetic-session'; s.workouts.push(w) })
  await render(<GarminCloudUploadButton workout={w} />)
  await act(async () => { button('Upload to Garmin Connect').click() })
  expect(host.querySelector('[role="alert"]').textContent).toContain(expected)
  expect(host.textContent).not.toContain('Reconnect or retry')
})

it('keeps automatic uploads and health reads available when an expired session can renew', async () => {
  bridge.status.mockResolvedValue({ available: true, connected: true, sessionId: 'synthetic-session', authState: 'expired', renewalAvailable: true })
  useStore.getState().update(s => { s.garminCloudSessionId = 'synthetic-session'; s.garminCloudAuto = true })
  await render(<GarminCloudSettings />)
  expect(host.textContent).toContain('Connected to Garmin Connect')
  expect(button('Sign in to Garmin Connect')).toBeUndefined()
  expect(host.querySelector('[aria-label="Upload new workouts automatically"]').disabled).toBe(false)
  expect(host.querySelector('[aria-label="Upload new workouts automatically"]').getAttribute('aria-checked')).toBe('true')
  expect(button('Read Garmin health data').disabled).toBe(false)
})

it('shows sign-in immediately when a health read confirms that silent renewal was rejected', async () => {
  const renewable = { available: true, connected: true, sessionId: 'synthetic-session', authState: 'expired', renewalAvailable: true }
  bridge.status.mockResolvedValue(renewable)
  bridge.healthMetrics = vi.fn(async () => ({ metrics: [{ id: 'weight', label: 'Weight' }] }))
  bridge.readHealthArchive = vi.fn(async () => ({ record: null }))
  bridge.readHealthMetric = vi.fn(async options => {
    bridge.status.mockResolvedValue({ ...renewable, renewalAvailable: false })
    return { date: options.date, metric: options.metric, status: 'error', error: 'auth_required' }
  })
  useStore.getState().update(s => { s.garminCloudSessionId = 'synthetic-session'; s.garminCloudAuto = true })
  await render(<GarminCloudSettings />)
  expect(button('Sign in to Garmin Connect')).toBeUndefined()
  await act(async () => button('Read Garmin health data').click())
  expect(bridge.status).toHaveBeenCalledTimes(2)
  expect(button('Sign in to Garmin Connect').disabled).toBe(false)
  expect(button('Read Garmin health data').disabled).toBe(true)
  expect(host.querySelector('[aria-label="Upload new workouts automatically"]').disabled).toBe(true)
  expect(host.textContent).not.toContain('Connected to Garmin Connect')
  expect(useStore.getState().S.garminCloudSessionId).toBe('synthetic-session')
  expect(useStore.getState().S.garminCloudAuto).toBe(true)
})

it('localizes the expired-session reason in Russian', async () => {
  await setLang('ru')
  bridge.status.mockResolvedValue({ available: true, connected: true, sessionId: 'synthetic-session', authState: 'expired' })
  useStore.getState().update(s => { s.garminCloudSessionId = 'synthetic-session' })
  await render(<GarminCloudSettings />)
  expect(host.textContent).toContain('Сессия Garmin Connect истекла. Войдите заново в настройках.')
})

it('requires sign-in before automatic upload and allows disconnect without changing private workouts', async () => {
  await render(<GarminCloudSettings />)
  const toggle = () => host.querySelector('[role="switch"]')
  expect(toggle().disabled).toBe(true)
  await act(async () => { button('Sign in to Garmin Connect').click() })
  expect(useStore.getState().S.garminCloudSessionId).toBe('synthetic-session')
  expect(toggle().getAttribute('aria-checked')).toBe('false')
  await act(async () => { toggle().click() })
  expect(useStore.getState().S.garminCloudAuto).toBe(true)
  await act(async () => { button('Disconnect Garmin Connect').click() })
  expect(bridge.disconnect).toHaveBeenCalledOnce()
  expect(useStore.getState().S.garminCloudSessionId).toBeUndefined()
  expect(useStore.getState().S.garminCloudAuto).toBe(false)
})

it('keeps account and recording-mode changes disabled during an active workout', async () => {
  useStore.getState().update(s => { s.active = { id: 'synthetic-active' } })
  await render(<GarminCloudSettings />)
  expect(button('Sign in to Garmin Connect').disabled).toBe(true)
  expect(host.querySelector('[role="switch"]').disabled).toBe(true)
})

it('uploads a manually selected finished workout and shows the confirmed result', async () => {
  const w = { id: 'synthetic-finished', start: 1800000000000, end: 1800000060000, entries: [{ id: '0025', target: { mode: 'reps' }, sets: [{ done: true, r: 8, w: 40 }] }] }
  bridge.status.mockResolvedValue({ available: true, connected: true, sessionId: 'synthetic-session' })
  useStore.getState().update(s => { s.garminCloudSessionId = 'synthetic-session'; s.workouts.push(w) })
  await render(<GarminCloudUploadButton workout={w} />)
  await act(async () => { button('Upload to Garmin Connect').click() })
  expect(bridge.upload).toHaveBeenCalledOnce()
  expect(button('Uploaded to Garmin Connect').disabled).toBe(true)
  expect(useStore.getState().S.workouts[0].entries[0].sets[0].w).toBe(40)
})

it('does not bind a deferred login to another profile, including an A-B-A switch', async () => {
  useStore.setState({ user: { id: 'synthetic-a' } })
  let finishLogin
  bridge.connect.mockImplementation(() => new Promise(resolve => { finishLogin = resolve }))
  await render(<GarminCloudSettings />)
  await act(async () => { button('Sign in to Garmin Connect').click() })
  act(() => { useStore.setState({ user: { id: 'synthetic-b' } }); useStore.setState({ user: { id: 'synthetic-a' } }) })
  await act(async () => { finishLogin({ connected: true, sessionId: 'synthetic-session' }) })
  expect(bridge.disconnect).toHaveBeenCalledOnce()
  expect(useStore.getState().S.garminCloudSessionId).toBeUndefined()
})

it('disables disconnect during a connected active workout', async () => {
  bridge.status.mockResolvedValue({ available: true, connected: true, sessionId: 'synthetic-session' })
  useStore.getState().update(s => { s.garminCloudSessionId = 'synthetic-session'; s.garminCloudAuto = true; s.active = { id: 'synthetic-active' } })
  await render(<GarminCloudSettings />)
  expect(button('Disconnect Garmin Connect').disabled).toBe(true)
})

it('keeps the local binding and auto-upload choice when status storage fails, and allows a status retry', async () => {
  useStore.getState().update(s => { s.garminCloudSessionId = 'synthetic-session'; s.garminCloudAuto = true })
  bridge.status.mockRejectedValueOnce(Object.assign(new Error('synthetic unreadable store'), { code: 'storage_unavailable' }))
  await render(<GarminCloudSettings />)
  expect(host.textContent).toContain('The local Garmin upload journal needs attention.')
  expect(host.textContent).not.toContain('Garmin Connect is not connected')
  expect(button('Sign in to Garmin Connect')).toBeUndefined()
  expect(useStore.getState().S.garminCloudSessionId).toBe('synthetic-session')
  expect(useStore.getState().S.garminCloudAuto).toBe(true)
  expect(bridge.connect).not.toHaveBeenCalled()
  expect(bridge.disconnect).not.toHaveBeenCalled()
  bridge.status.mockResolvedValue({ available: true, connected: true, sessionId: 'synthetic-session' })
  await act(async () => { button('Retry').click() })
  expect(host.textContent).toContain('Connected to Garmin Connect')
  expect(host.querySelector('[aria-label="Upload new workouts automatically"]').getAttribute('aria-checked')).toBe('true')
})

it.each([undefined, 'network_error'])('reports storage failure for a manual upload without asking the user to reconnect: %s', async previousError => {
  const w = { id: 'synthetic-finished', start: 1800000000000, end: 1800000060000, entries: [{ id: '0025', sets: [{ done: true, r: 8, w: 40 }] }] }
  if (previousError) w.garminCloudUpload = { status: 'failed', error: previousError, sessionId: 'synthetic-session' }
  useStore.getState().update(s => { s.garminCloudSessionId = 'synthetic-session'; s.workouts.push(w) })
  bridge.status.mockRejectedValue(Object.assign(new Error('synthetic storage failure'), { code: 'storage_unavailable' }))
  await render(<GarminCloudUploadButton workout={w} />)
  await act(async () => { button(previousError ? 'Retry Garmin upload' : 'Upload to Garmin Connect').click() })
  expect(host.querySelector('[role="alert"]').textContent).toContain('The local Garmin upload journal needs attention.')
  expect(host.querySelector('[role="alert"]').textContent).not.toContain('Garmin upload failed. Reconnect or retry.')
  expect(bridge.upload).not.toHaveBeenCalled()
  expect(useStore.getState().S.workouts[0].garminCloudUpload).toEqual(w.garminCloudUpload)
  expect(useStore.getState().S.garminCloudSessionId).toBe('synthetic-session')
})
