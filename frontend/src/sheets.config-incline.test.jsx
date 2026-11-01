// @vitest-environment happy-dom
// Discord: "the incline can only be modified while a workout is actively in progress". A
// treadmill's legacy settings remain editable in More while goals use the primary controls.
import React, { act } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createRoot } from 'react-dom/client'
import { EXIDX } from './lib/exercises.js'
import { DEF, useStore } from './store/useStore.js'
import { useUI } from './store/useUI.js'
import { exConfigSheet } from './sheets.jsx'

const TREADMILL = '2259'   // walking on treadmill
const BIKE = '2138'        // stationary bike run v. 3
const mounted = []
function open(ex, existing) {
  useStore.setState({ S: structuredClone(DEF), user: null })
  const onSave = vi.fn()
  exConfigSheet(ex, existing, onSave, null, null)
  const sheet = useUI.getState().sheets.at(-1)
  const host = document.createElement('div')
  document.body.appendChild(host)
  const root = createRoot(host)
  mounted.push(root)
  act(() => root.render(sheet.render(() => useUI.getState().closeSheet(sheet.id))))
  const labels = () => [...host.querySelectorAll('.stp-l')].map(l => l.textContent.trim())
  const field = label => [...host.querySelectorAll('.stp-w')].find(w => w.querySelector('.stp-l')?.textContent === label)?.querySelector('input.num')
  const type = (el, value) => act(() => {
    Object.getOwnPropertyDescriptor(el.constructor.prototype, 'value').set.call(el, value)
    el.dispatchEvent(new Event('input', { bubbles: true }))
  })
  const save = () => act(() => [...host.querySelectorAll('button')].find(b => b.textContent.trim() === 'Save').click())
  const details = () => host.querySelector('details')
  const more = () => act(() => host.querySelector('summary').click())
  const primaryLabels = () => [...host.querySelector('.cfgrow').querySelectorAll('.stp-l')].map(l => l.textContent.trim())
  return { labels, primaryLabels, details, more, field, type, save, onSave }
}

beforeEach(() => {
  globalThis.IS_REACT_ACT_ENVIRONMENT = true
  useUI.setState({ sheets: [] })
  document.body.innerHTML = ''
})
afterEach(() => { act(() => { mounted.splice(0).forEach(root => root.unmount()) }) })

describe('incline in a treadmill\'s settings (Discord)', () => {
  it('offers incline under More for a fresh goals-only treadmill slot', () => {
    const v = open(EXIDX[TREADMILL], { sets: 1, mode: 'cardio', min: 20 })
    expect(v.primaryLabels()).toEqual(['Time goal (min)', 'Distance goal (km)'])
    expect(v.details().open).toBe(false)
    v.more()
    v.type(v.field('Incline (%)'), '6')
    v.save()
    expect(v.onSave.mock.calls[0][0]).toEqual({ sets: 1, mode: 'cardio', min: 20, incline: 6 })
  })
  it('keeps legacy incline editable under More and saves it on the slot', () => {
    const v = open(EXIDX[TREADMILL], { sets: 1, min: 30, speed: 5 })
    expect(v.primaryLabels()).toEqual(['Time goal (min)', 'Distance goal (km)'])
    expect(v.details().open).toBe(false)
    v.more()
    expect(v.details().open).toBe(true)
    expect(v.labels()).toContain('Incline (%)')
    v.type(v.field('Incline (%)'), '7.3')
    v.save()
    expect(v.onSave.mock.calls[0][0]).toMatchObject({ sets: 1, min: 30, speed: 5, incline: 7.5 })
  })

  it('reopens with the saved incline, and a flat one leaves the key out', () => {
    const v = open(EXIDX[TREADMILL], { sets: 1, min: 30, speed: 5, incline: 6 })
    v.more()
    expect(v.field('Incline (%)').value).toBe('6')
    v.type(v.field('Incline (%)'), '0')
    v.save()
    expect(v.onSave.mock.calls[0][0]).not.toHaveProperty('incline')
  })

  it('a bike has no incline to set', () => {
    const v = open(EXIDX[BIKE], { sets: 1, min: 30, speed: 20 })
    expect(v.labels()).not.toContain('Incline (%)')
    v.save()
    expect(v.onSave.mock.calls[0][0]).not.toHaveProperty('incline')
  })
})
