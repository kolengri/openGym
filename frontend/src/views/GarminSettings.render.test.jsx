// @vitest-environment happy-dom
import React, { act } from 'react'
import { createRoot } from 'react-dom/client'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { DEF, useStore } from '../store/useStore.js'
import { _resetGarminForTest, _setGarminPluginForTest } from '../lib/garmin-sync.js'
import { _setGarminCloudPluginForTest } from '../lib/garmin-cloud.js'
import ErrorBoundary from '../components/ErrorBoundary.jsx'
import GarminSettingsPage from './GarminSettings.jsx'

let host, root, errors
beforeEach(() => {
  globalThis.IS_REACT_ACT_ENVIRONMENT = true
  _resetGarminForTest()
  const S = structuredClone(DEF)
  S.active = null
  useStore.setState({ S, user: null })
  _setGarminPluginForTest({
    status: async () => ({ available: true, enabled: true, connected: true, installed: true, deviceId: 'synthetic' }),
    devices: async () => ({ devices: [{ id: 'synthetic', name: 'Synthetic watch' }] }),
  })
  _setGarminCloudPluginForTest(null)
  errors = vi.spyOn(console, 'error').mockImplementation(() => {})
  host = document.createElement('div')
  document.body.append(host)
  root = createRoot(host)
})
afterEach(() => {
  act(() => root.unmount())
  host.remove()
  _resetGarminForTest()
  _setGarminCloudPluginForTest(null)
  errors.mockRestore()
})

it('opens Garmin settings with an enabled watch and no active workout or heart-rate sample', async () => {
  await act(async () => root.render(<ErrorBoundary><GarminSettingsPage /></ErrorBoundary>))
  expect(host.textContent).toContain('Watch Bluetooth connected')
  expect(host.textContent).toContain('Open on the watch')
  expect(host.textContent).not.toContain('This screen could not be drawn.')
  expect(errors).not.toHaveBeenCalled()
})
