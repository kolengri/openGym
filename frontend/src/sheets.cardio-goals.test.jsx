// @vitest-environment happy-dom
import React, { act } from 'react'
import { createRoot } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { EXIDX } from './lib/exercises.js'
import { DEF, useStore } from './store/useStore.js'
import { useUI } from './store/useUI.js'
import { _setLangState } from './lib/i18n-core.js'
import { exConfigSheet } from './sheets.jsx'

let root, host
function open(target) {
  const onSave = vi.fn()
  exConfigSheet(EXIDX['2138'], target, onSave)
  const sheet = useUI.getState().sheets.at(-1)
  host = document.createElement('div'); document.body.appendChild(host)
  root = createRoot(host)
  act(() => root.render(sheet.render(() => useUI.getState().closeSheet(sheet.id))))
  return onSave
}
const field = label => host.querySelector(`input[aria-label="${label}"]`)
const save = () => [...host.querySelectorAll('button')].find(b => b.textContent.trim() === 'Save')
function type(label, value) {
  act(() => {
    const input = field(label)
    Object.getOwnPropertyDescriptor(input.constructor.prototype, 'value').set.call(input, value)
    input.dispatchEvent(new Event('input', { bubbles: true }))
  })
}
beforeEach(() => {
  globalThis.IS_REACT_ACT_ENVIRONMENT = true
  useStore.setState({ S: structuredClone(DEF), user: null })
  useUI.setState({ sheets: [] })
  _setLangState('en', null, null, null)
})
afterEach(() => { act(() => root?.unmount()); host?.remove() })

describe('cardio goal configuration', () => {
  it('offers just time and kilometers as its main controls and saves both', () => {
    const onSave = open({ sets: 1, mode: 'cardio', min: 20 })
    expect([...host.querySelectorAll('.cfgrow')][0].textContent).toBe('Time goal (min)Distance goal (km)')
    expect(host.textContent).not.toMatch(/Intervals|Speed \(|Incline/)
    type('Distance goal (km)', '5,25')
    act(() => save().click())
    expect(onSave).toHaveBeenCalledWith({ sets: 1, mode: 'cardio', min: 20, km: 5.25 })
  })

  it('supports a distance-only target and rejects an empty target', () => {
    const onSave = open({ sets: 1, mode: 'cardio', min: 20 })
    type('Time goal (min)', '0')
    expect(save().disabled).toBe(true)
    expect(host.querySelector('[role="alert"]')).toBeTruthy()
    type('Distance goal (km)', '5')
    expect(save().disabled).toBe(false)
    act(() => save().click())
    expect(onSave).toHaveBeenCalledWith({ sets: 1, mode: 'cardio', km: 5 })
  })

  it('clears optional distance without restoring it and retains legacy fields', () => {
    const onSave = open({ sets: 2, min: 12.5, km: 3, speed: 0, incline: 4 })
    expect(host.querySelector('details').open).toBe(false)
    type('Distance goal (km)', '0')
    act(() => save().click())
    expect(onSave).toHaveBeenCalledWith({ sets: 2, mode: 'cardio', min: 12.5, speed: 0, incline: 4 })
  })
})
