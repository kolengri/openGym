// @vitest-environment happy-dom
import React, { act } from 'react'
import { createRoot } from 'react-dom/client'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import Workout from './Workout.jsx'
import { DEF, useStore } from '../store/useStore.js'
import { useUI } from '../store/useUI.js'

vi.mock('../lib/sound.js', () => ({ beep: vi.fn(), vibrate: vi.fn(), alertBuzz: vi.fn(), unlock: vi.fn(), restOver: vi.fn() }))
vi.mock('../lib/api.js', () => ({ api: vi.fn(() => Promise.resolve({})) }))
let root, host, sheetRoot, sheetHost
beforeEach(() => {
  globalThis.IS_REACT_ACT_ENVIRONMENT = true
  useUI.setState({ sheets: [], timer: null, work: null })
  host = document.createElement('div'); document.body.appendChild(host); root = createRoot(host)
})
afterEach(() => { act(() => { root.unmount(); sheetRoot?.unmount() }); host.remove(); sheetHost?.remove(); sheetRoot = null })
const row = () => ({ w: 60, r: 8, done: false })
function mount(sets, target = {}) {
  const S = structuredClone(DEF); S.workoutView = 'list'
  S.active = { id: 'synthetic-calculator', name: 'Synthetic', start: Date.now(), cur: 0,
    entries: [{ id: '0043', target: { reps: 8, ...target }, sets }] }
  useStore.setState({ S, user: null })
  act(() => root.render(<MemoryRouter><Workout /></MemoryRouter>))
}
function open(button = host.querySelector('button[aria-label="Weight calculator"]')) {
  expect(button).toBeTruthy()
  act(() => button.click())
  const sheet = useUI.getState().sheets.at(-1)
  sheetHost = document.createElement('div'); document.body.appendChild(sheetHost); sheetRoot = createRoot(sheetHost)
  act(() => sheetRoot.render(sheet.render(() => useUI.getState().closeSheet(sheet.id))))
  act(() => {
    const input = sheetHost.querySelector('input[aria-label="Total weight"]')
    Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(input, '100')
    input.dispatchEvent(new Event('input', { bubbles: true }))
  })
}
const apply = () => act(() => [...sheetHost.querySelectorAll('button')].find(b => b.textContent === 'Apply').click())
it('uses the real normal-set setter and preserves inherited-load cascading', () => {
  mount([row(), row()]); open(); apply()
  expect(useStore.getState().S.active.entries[0].sets.map(s => s.w)).toEqual([100, 100])
  expect(useStore.getState().S.active.entries[0].sets[0].weightOrigin).toBe('manual')
})
it('uses the real side setter without changing the other side', () => {
  const side = () => ({ ...row(), sides: { L: row(), R: row() } })
  mount([side(), side()], { side: true })
  open(host.querySelector('.setrow-side button[aria-label="Weight calculator"]')); apply()
  const sets = useStore.getState().S.active.entries[0].sets
  expect(sets[0].sides.L.w).toBe(100); expect(sets[0].sides.R.w).toBe(60)
})
it('uses the real drop setter and refuses a removed drop without touching the next row', () => {
  mount([{ ...row(), type: 'dropset', drops: [{ w: 40, r: 6 }, { w: 30, r: 6 }] }])
  open(host.querySelector('.subrow button[aria-label="Weight calculator"]'))
  act(() => useStore.getState().update(s => { s.active.entries[0].sets[0].drops.shift() }))
  apply()
  expect(useStore.getState().S.active.entries[0].sets[0].drops).toEqual([{ w: 30, r: 6 }])
})
it('applies through the actual drop setter when the target remains current', () => {
  mount([{ ...row(), type: 'dropset', drops: [{ w: 40, r: 6 }] }])
  open(host.querySelector('.subrow button[aria-label="Weight calculator"]')); apply()
  expect(useStore.getState().S.active.entries[0].sets[0].drops[0].w).toBe(100)
})
it('does not apply to an equal-length replacement exercise', () => {
  mount([row()]); open()
  act(() => useStore.getState().update(s => { s.active.entries[0] = { id: '0289', target: {}, sets: [{ ...row(), w: 20 }] } }))
  apply()
  expect(useStore.getState().S.active.entries[0].sets[0].w).toBe(20)
})
