// @vitest-environment happy-dom
import React, { act } from 'react'
import { createRoot } from 'react-dom/client'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import MixedWeightField, { mixedBarWeight, weightTargetGuard } from './MixedWeightField.jsx'
import { DEF, useStore } from '../store/useStore.js'
import { useUI } from '../store/useUI.js'

let root, host, modalRoot, modalHost, change
beforeEach(() => {
  globalThis.IS_REACT_ACT_ENVIRONMENT = true
  const S = structuredClone(DEF); S.active = { id: 'synthetic-session' }
  useStore.setState({ S, user: null }); useUI.setState({ sheets: [] })
  host = document.createElement('div'); document.body.appendChild(host); root = createRoot(host)
  change = vi.fn()
})
afterEach(() => { act(() => { root.unmount(); modalRoot?.unmount() }); host.remove(); modalHost?.remove(); modalRoot = null })
const click = text => act(() => [...modalHost.querySelectorAll('button')].find(b => b.textContent.trim() === text).click())
const enter = (name, value) => act(() => {
  const input = modalHost.querySelector(`input[aria-label="${name}"]`)
  Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(input, value)
  input.dispatchEvent(new Event('input', { bubbles: true }))
})
function open(unit = 'kg') {
  useStore.getState().update(s => { s.unit = unit })
  act(() => root.render(<MixedWeightField value={60} unit={unit} onChange={change} />))
  act(() => host.querySelector('button').click())
  const sheet = useUI.getState().sheets.at(-1)
  modalHost = document.createElement('div'); document.body.appendChild(modalHost); modalRoot = createRoot(modalHost)
  act(() => modalRoot.render(<React.StrictMode>{sheet.render(() => useUI.getState().closeSheet(sheet.id))}</React.StrictMode>))
}

it('counts a kg bar plus two lb plate loads in either profile unit', () => {
  expect(mixedBarWeight({ bar: 20, barUnit: 'kg', plates: 45, plateUnit: 'lb', unit: 'kg' })).toBeCloseTo(60.8233, 4)
  expect(mixedBarWeight({ bar: 20, barUnit: 'kg', plates: 45, plateUnit: 'lb', unit: 'lb' })).toBeCloseTo(134.0925, 4)
  expect(mixedBarWeight({ bar: 20, barUnit: 'kg', plates: -1, plateUnit: 'lb', unit: 'kg' })).toBeNull()
})
it('applies total pounds to only this field in a kg profile', () => {
  open(); click('lb'); enter('Total weight', '100')
  expect(change).not.toHaveBeenCalled()
  click('Apply')
  expect(change).toHaveBeenCalledWith(45.3592, expect.any(Function))
  expect(useStore.getState().S.unit).toBe('kg')
})
it('applies a kg bar and the combined lb plates on one side without counting the bar twice', () => {
  open(); click('Bar and plates'); enter('Bar weight', '20'); enter('Plates on one side', '45'); click('Apply')
  expect(change).toHaveBeenCalledWith(60.8233, expect.any(Function))
})
it('does not apply a calculator left open across a workout switch', () => {
  open(); useStore.getState().update(s => { s.active = { id: 'different-session' } }); click('Apply')
  expect(change).not.toHaveBeenCalled()
})

for (const changeTarget of [
  s => s.active.entries.reverse(),
  s => { s.active.entries[0] = { ...s.active.entries[0], id: 'replacement' } },
  s => s.active.entries[0].sets.splice(0, 1),
  s => s.active.entries[0].sets[0].drops.splice(0, 1),
  s => { s.active.entries[0].sets[0].sides.L.w = 99 },
]) it('rejects a changed indexed target before applying', () => {
  useStore.getState().update(s => { s.active.entries = [
    { id: 'one', sets: [{ w: 60, drops: [{ w: 40 }], sides: { L: { w: 60 }, R: { w: 60 } } }, { w: 60 }] },
    { id: 'two', sets: [{ w: 40 }] },
  ] })
  open(); act(() => useStore.getState().update(changeTarget)); click('Apply')
  expect(change).not.toHaveBeenCalled()
  expect(modalHost.textContent).toContain('Workout changed.')
})
it('rejects owner and unit A-B-A changes and checks the actual mutation candidate', () => {
  for (const change of [
    () => { useStore.setState({ user: { id: 'other' } }); useStore.setState({ user: null }) },
    () => { useStore.getState().update(s => { s.unit = 'lb' }); useStore.getState().update(s => { s.unit = 'kg' }) },
  ]) {
    const guard = weightTargetGuard(useStore)
    change()
    expect(guard.matches(useStore.getState().S)).toBe(false)
    guard.dispose()
  }
  const guard = weightTargetGuard(useStore)
  expect(guard.matches(useStore.getState().S)).toBe(true)
  expect(guard.matches({ ...useStore.getState().S, active: { id: 'replacement' } })).toBe(false)
  guard.dispose()
})
