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
function open(button = host.querySelector('button[aria-label^="Weight calculator:"]')) {
  act(() => sheetRoot?.unmount())
  sheetHost?.remove()
  expect(button).toBeTruthy()
  act(() => button.click())
  const sheet = useUI.getState().sheets.at(-1)
  sheetHost = document.createElement('div'); document.body.appendChild(sheetHost); sheetRoot = createRoot(sheetHost)
  act(() => sheetRoot.render(sheet.render(() => useUI.getState().closeSheet(sheet.id))))
}
const click = text => act(() => [...sheetHost.querySelectorAll('button')].find(b => b.textContent.trim() === text).click())
const input = label => sheetHost.querySelector(`input[aria-label="${label}"]`)
const enter = (label, value) => act(() => {
  const field = input(label)
  Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(field, value)
  field.dispatchEvent(new Event('input', { bubbles: true }))
})
const toggleUnit = label => act(() => input(label).closest('.weight-calc-input').querySelector('button').click())
const apply = () => click('Apply')
const applyTotal = () => { enter('Total weight', '100'); apply() }
it('uses the real normal-set setter and preserves inherited-load cascading', () => {
  mount([row(), row()]); open(); applyTotal()
  expect(useStore.getState().S.active.entries[0].sets.map(s => s.w)).toEqual([100, 100])
  expect(useStore.getState().S.active.entries[0].sets[0].weightOrigin).toBe('manual')
})
it('does not report missing kg plates after entering 35 lb per side without a configured inventory', () => {
  mount([row(), row(), row()]); open()
  click('Bar and plates')
  toggleUnit('Plates on one side')
  enter('Plates on one side', '35')
  apply()
  expect(useStore.getState().S.active.entries[0].sets.map(s => s.w)).toEqual([51.7515, 51.7515, 51.7515])
  expect(host.querySelector('.plateline').textContent).toContain('15.88 kg per side')
  expect(host.querySelector('.plateline .short')).toBeNull()
})
it('restores the last applied setup across sessions for this exercise and keeps exact mixed-unit math', () => {
  mount([row()]); open()
  click('Bar and plates')
  enter('Bar weight', '20')
  toggleUnit('Bar weight') // Shows a rounded lb preview but should still calculate with 20 kg.
  toggleUnit('Plates on one side')
  enter('Plates on one side', '45.5')
  apply()
  const weight = useStore.getState().S.active.entries[0].sets[0].w
  expect(weight).toBe(61.2769)

  act(() => useStore.getState().update(s => { s.active = { ...s.active, id: 'next-workout', entries: [
    { id: '0043', target: { reps: 8 }, sets: [row()] },
    { id: '0289', target: { reps: 8 }, sets: [row()] },
  ] } }))
  // The restored values are only a preview until Apply.
  open()
  expect(input('Total weight')).toBeNull()
  expect(input('Bar weight').value).toBe('44')
  expect(input('Plates on one side').value).toBe('45.5')
  expect([...sheetHost.querySelectorAll('.weight-unit')].map(button => button.textContent)).toEqual(['lb', 'lb'])
  expect(useStore.getState().S.active.entries[0].sets[0].w).toBe(60)
  apply()
  expect(useStore.getState().S.active.entries[0].sets[0].w).toBe(weight)

  open([...host.querySelectorAll('button[aria-label^="Weight calculator:"]')].at(-1))
  expect(input('Total weight').value).toBe('60')
  act(() => useUI.getState().closeSheet(useUI.getState().sheets.at(-1).id))

  open()
  enter('Plates on one side', '90')
  act(() => useUI.getState().closeSheet(useUI.getState().sheets.at(-1).id))
  open()
  expect(input('Plates on one side').value).toBe('45.5')
  click('Total weight')
  applyTotal()
  act(() => useStore.getState().update(s => { s.active.entries[0].sets[0].w = 75 }))
  open()
  expect(input('Total weight').value).toBe('75')
})
it('uses the real side setter without changing the other side', () => {
  const side = () => ({ ...row(), sides: { L: row(), R: row() } })
  mount([side(), side()], { side: true })
  open(host.querySelector('.setrow-side button[aria-label^="Weight calculator:"]')); applyTotal()
  const sets = useStore.getState().S.active.entries[0].sets
  expect(sets[0].sides.L.w).toBe(100); expect(sets[0].sides.R.w).toBe(60)
  expect(useStore.getState().S.weightCalculatorHistory['0043'].setup).toBeNull()
})
it('uses the real drop setter and refuses a removed drop without touching the next row', () => {
  mount([{ ...row(), type: 'dropset', drops: [{ w: 40, r: 6 }, { w: 30, r: 6 }] }])
  open(host.querySelector('.subrow button[aria-label^="Weight calculator:"]'))
  act(() => useStore.getState().update(s => { s.active.entries[0].sets[0].drops.shift() }))
  apply()
  expect(useStore.getState().S.active.entries[0].sets[0].drops).toEqual([{ w: 30, r: 6 }])
  expect(useStore.getState().S.weightCalculatorHistory).toEqual({})
})
it('applies through the actual drop setter when the target remains current', () => {
  mount([{ ...row(), type: 'dropset', drops: [{ w: 40, r: 6 }] }])
  open(host.querySelector('.subrow button[aria-label^="Weight calculator:"]')); applyTotal()
  expect(useStore.getState().S.active.entries[0].sets[0].drops[0].w).toBe(100)
  expect(useStore.getState().S.weightCalculatorHistory['0043'].setup).toBeNull()
})
it('does not apply to an equal-length replacement exercise', () => {
  mount([row()]); open()
  act(() => useStore.getState().update(s => { s.active.entries[0] = { id: '0289', target: {}, sets: [{ ...row(), w: 20 }] } }))
  apply()
  expect(useStore.getState().S.active.entries[0].sets[0].w).toBe(20)
  expect(useStore.getState().S.weightCalculatorHistory).toEqual({})
})
