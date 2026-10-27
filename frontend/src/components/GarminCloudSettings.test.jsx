// @vitest-environment happy-dom
import React, { act } from 'react'
import { createRoot } from 'react-dom/client'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { DEF, useStore } from '../store/useStore.js'
import GarminCloudSettings from './GarminCloudSettings.jsx'
import GarminCloudUploadButton from './GarminCloudUploadButton.jsx'
import { _setGarminCloudPluginForTest } from '../lib/garmin-cloud.js'

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
afterEach(() => { act(() => root.unmount()); host.remove() })
const render = async element => { await act(async () => { root.render(element) }) }
const button = text => [...host.querySelectorAll('button')].find(b => b.textContent.trim() === text)

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
