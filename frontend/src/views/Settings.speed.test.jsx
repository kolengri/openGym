// @vitest-environment happy-dom
// Settings → General → Speed unit (Discord "miles per hour"): follows the weight unit until
// chosen, and choosing converts nothing — speeds stay stored in km/h.
import React, { act } from 'react'
import { createRoot } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import Settings from './Settings.jsx'
import { createPickerHarness } from './test-picker.js'

globalThis.IS_REACT_ACT_ENVIRONMENT = true

const mocks = vi.hoisted(() => {
  const state = { S: null }
  state.snapshot = () => ({
    S: state.S,
    user: null,
    update: mut => {
      const next = structuredClone(state.S)
      mut(next)
      state.S = next
    },
    replaceState: vi.fn(), setUser: vi.fn(), pullState: vi.fn(), pushState: vi.fn(),
    signOut: vi.fn(), signOutAll: vi.fn(), resetDemo: vi.fn(), disconnectServer: vi.fn(),
  })
  return state
})
vi.mock('../store/useStore.js', () => {
  const useStore = selector => selector ? selector(mocks.snapshot()) : mocks.snapshot()
  useStore.getState = mocks.snapshot
  return { useStore, DEF: { reminder: { time: '17:30' } }, hasData: () => false }
})
vi.mock('../store/useUI.js', () => {
  const snap = () => ({ toast: vi.fn(), openSheet: vi.fn() })
  const useUI = selector => selector ? selector(snap()) : snap()
  useUI.getState = snap
  return { useUI }
})
vi.mock('react-router-dom', () => ({ useNavigate: () => () => {} }))
vi.mock('../lib/api.js', () => ({
  api: vi.fn(), webauthnOK: () => false, passkeyLogin: vi.fn(), passkeyRegister: vi.fn(), IS_ANDROID: false,
}))
vi.mock('../lib/push.js', () => ({ pushSupported: () => false, enablePush: vi.fn(), disablePush: vi.fn(), sendTestPush: vi.fn() }))
vi.mock('../lib/wakelock.js', () => ({ wakeLockSupported: () => false }))
vi.mock('../lib/mobile.js', () => ({ MOBILE: false, isAndroid: () => Promise.resolve(false), shareExport: vi.fn(), syncReminder: vi.fn() }))
vi.mock('./MobileOnboarding.jsx', () => ({ ConnectSheet: () => null }))
vi.mock('../sheets.jsx', () => ({
  loadStarterPlan: vi.fn(), starterPlanSheet: vi.fn(), confirmSheet: vi.fn(), importFromApp: vi.fn(),
  importFromHevy: vi.fn(), equipmentProfileSheet: vi.fn(),
}))

// The Settings view reads the build-time version constant at render time.
globalThis.__APP_VERSION__ ??= 'test'

let host, root, picker
beforeEach(() => {
  picker = createPickerHarness()
  mocks.S = {
    unit: 'kg', restSec: 90, restPauseSec: 15, sound: false, effort: 'none',
    gifSize: 'full', workouts: [], routines: [], exWeights: {},
  }
  host = document.createElement('div')
  document.body.appendChild(host)
  root = createRoot(host)
})
afterEach(() => {
  picker.destroy()
  act(() => root.unmount())
  host.remove()
})

const mount = () => act(() => root.render(<Settings page="units" />))
const rowTitled = title => [...host.querySelectorAll('.lrow')].find(r => r.querySelector('.lrow-t')?.textContent === title)
const current = title => rowTitled(title).querySelector('.lrow-v').textContent

describe('Settings — speed unit', () => {
  it('shows km/h for a kg profile and mph for a pound profile until one is chosen', () => {
    mount()
    expect(current('Speed unit')).toBe('km/h')
    act(() => root.unmount())
    root = createRoot(host)
    mocks.S.unit = 'lb'
    mount()
    expect(current('Speed unit')).toBe('mph')
  })

  it('stores the choice and nothing else', () => {
    mocks.S.routines = [{ id: 'c', name: 'Cardio', ex: [{ id: '2138', sets: 1, min: 20, speed: 8 }] }]
    const before = structuredClone(mocks.S)
    mount()
    picker.open(rowTitled('Speed unit')).choose('mph')
    expect(mocks.S.speedUnit).toBe('mph')
    expect({ ...mocks.S, speedUnit: undefined }).toEqual({ ...before, speedUnit: undefined })
    mount()
    expect(current('Speed unit')).toBe('mph')
    picker.open(rowTitled('Speed unit')).choose('km/h')
    expect(mocks.S.speedUnit).toBe('kmh')
  })
})
