// @vitest-environment happy-dom
import React, { act } from 'react'
import { createRoot } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import GarminSettingsPage from './GarminSettings.jsx'

const h = vi.hoisted(() => ({ status: { available: true, enabled: false }, devices: [{ id: 'synthetic', name: 'tactix test' }], configure: vi.fn(), open: vi.fn(), store: vi.fn() }))
vi.mock('../lib/garmin-sync.js', () => ({
  garminStatus: async () => h.status, garminDevices: async () => h.devices,
  configureGarmin: (...args) => h.configure(...args), onGarminChange: () => () => {},
  garminPlugin: async () => ({ bridge: { openOnWatch: h.open, openStore: h.store } }),
}))
globalThis.IS_REACT_ACT_ENVIRONMENT = true
let host, root
beforeEach(() => {
  h.status = { available: true, enabled: false }; h.devices = [{ id: 'synthetic', name: 'tactix test' }]
  h.configure.mockReset(); h.open.mockReset(); h.store.mockReset()
  h.configure.mockImplementation(async ({ enabled }) => { h.status = { ...h.status, enabled, installed: true, connected: enabled } })
  host = document.createElement('div'); document.body.append(host); root = createRoot(host)
})
afterEach(() => { act(() => root.unmount()); host.remove() })
const render = async () => { await act(async () => { root.render(<GarminSettingsPage />) }) }
const button = name => [...host.querySelectorAll('button')].find(el => el.textContent.trim() === name)

describe('Garmin connection settings', () => {
  it('shows the bridge failure instead of hiding it behind a generic connection message', async () => {
    h.status = { available: true, enabled: true, installed: true, connected: true,
      error: 'Garmin send failed (FAILURE_DEVICE_NOT_CONNECTED). Open Garmin Connect and reconnect the watch.' }
    await render()
    expect(host.querySelector('[role="alert"]').textContent).toBe(h.status.error)
    expect(host.textContent).not.toContain('GitHub')
  })
  it('requires an explicit connect action, then offers disconnect and opening the watch app', async () => {
    await render()
    expect(h.configure).not.toHaveBeenCalled()
    expect(button('Connect').disabled).toBe(false)
    await act(async () => button('Install on the watch').click())
    expect(h.store).toHaveBeenCalledOnce()
    await act(async () => button('Connect').click())
    expect(h.configure).toHaveBeenCalledExactlyOnceWith({ enabled: true, deviceId: 'synthetic' })
    expect(button('Disconnect')).toBeTruthy()
    await act(async () => button('Open on the watch').click())
    expect(h.open).toHaveBeenCalledTimes(1)
    await act(async () => button('Disconnect').click())
    expect(h.configure).toHaveBeenLastCalledWith({ enabled: false })
  })
  it('does not connect when no paired watch exists', async () => {
    h.devices = []
    await render()
    expect(button('Connect').disabled).toBe(true)
    expect(host.textContent).toContain('No Garmin watches found')
  })
  it('keeps connection errors visible and allows retry', async () => {
    h.configure.mockRejectedValueOnce(new Error('Test connection refused'))
    await render()
    await act(async () => button('Connect').click())
    expect(host.querySelector('[role="alert"]').textContent).toBe('Test connection refused')
    expect(button('Connect').disabled).toBe(false)
    await act(async () => button('Install on the watch').click())
    expect(h.store).toHaveBeenCalledOnce()
    await act(async () => button('Connect').click())
    expect(host.querySelector('[role="alert"]')).toBeNull()
  })
})
