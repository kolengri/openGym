// @vitest-environment happy-dom
// Settings → Modules on Home: a module switched off takes its cards with it, and brings them
// back when it is on again. Visibility only; what the cards do is their own tests'.
import React, { act } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createRoot } from 'react-dom/client'
import { useStore } from '../store/useStore.js'
import { presetModules } from '../lib/modules.js'
import Home from './Home.jsx'

vi.mock('react-router-dom', () => ({ useNavigate: () => vi.fn() }))
vi.mock('../sheets.jsx', () => ({
  starterPlanSheet: vi.fn(), bwSheet: vi.fn(), goalSheet: vi.fn(), dayOverrideSheet: vi.fn(),
  calendarSheet: vi.fn(), startFlow: vi.fn(), bwDeltaColor: () => '', weighInsSheet: vi.fn(),
}))

let host, root
beforeEach(() => {
  globalThis.IS_REACT_ACT_ENVIRONMENT = true
  host = document.createElement('div')
  document.body.appendChild(host)
  root = createRoot(host)
})
afterEach(() => { act(() => root.unmount()); host.remove() })

const today = new Date().toISOString().slice(0, 10)
const mountWith = (modules, extra = {}) => {
  useStore.setState(s => ({
    S: { ...s.S, routines: [{ id: 'r1', name: 'Push', ex: [] }], workouts: [{ id: 'w1', d: today, start: Date.now() - 4e6, end: Date.now() - 3e6, entries: [] }],
      bodyweight: [{ d: today, w: 80, t: Date.now() }], dayPlan: {}, week: {}, active: null, modules, homeMuscleSets: false, ...extra },
    user: null,
  }))
  act(() => root.render(<Home />))
}
const heads = () => [...host.querySelectorAll('.card-head-title')].map(el => el.textContent)

describe('Home follows the modules', () => {
  it('puts the compact calendar before today and keeps optional activity quiet without changing preferences', () => {
    mountWith(undefined, { challengesFold: true })
    const todayRow = host.querySelector('[data-tour="today"]')
    const week = host.querySelector('.week')
    const motivation = host.querySelector('.home-motivation')
    expect(week.compareDocumentPosition(todayRow) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    expect(week.closest('.planning-today')).toBeNull()
    const weight = host.querySelector('.planning-weight')
    expect(weight.open).toBe(false)
    expect(weight.querySelector('summary').textContent).toContain('80')
    expect(todayRow.compareDocumentPosition(weight) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    act(() => weight.querySelector('summary').click())
    expect(weight.open).toBe(true)
    expect(motivation.open).toBe(false)
    expect(host.querySelector('.bw-head').compareDocumentPosition(motivation) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    act(() => motivation.querySelector('summary').click())
    expect(motivation.open).toBe(true)
    expect(heads().some(h => /week streak/.test(h))).toBe(true)
    expect(useStore.getState().S.challengesFold).toBe(true)
    expect(useStore.getState().S.modules).toBeUndefined()
  })

  it('Everything: the weight card, the check-in and the streak are there', () => {
    mountWith(undefined)
    expect(heads()).toContain('Body weight')
    expect(heads()).toContain('Check in')
    expect(heads().some(h => /week streak/.test(h))).toBe(true)
  })

  it('Just training: none of them, and the week strip and today row stay', () => {
    mountWith(presetModules('training'))
    expect(heads()).not.toContain('Body weight')
    expect(heads()).not.toContain('Check in')
    expect(heads().some(h => /week streak/.test(h))).toBe(false)
    expect(host.querySelector('[data-tour="today"]')).toBeTruthy()
    expect(host.querySelector('.week')).toBeTruthy()
  })

  it('one module at a time, and back on brings it back', () => {
    mountWith({ body: false })
    expect(heads()).not.toContain('Body weight')
    expect(heads()).toContain('Check in')
    mountWith({ body: true, checkin: false })
    expect(heads()).toContain('Body weight')
    expect(heads()).not.toContain('Check in')
  })

  it('the old check-in switch still hides its card until Modules decides', () => {
    mountWith(undefined, { checkIn: false })
    expect(heads()).not.toContain('Check in')
    mountWith({ checkin: true }, { checkIn: false })
    expect(heads()).toContain('Check in')
  })
})
