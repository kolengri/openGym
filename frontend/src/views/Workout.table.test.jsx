// @vitest-environment happy-dom
import React, { act } from 'react'
import { createRoot } from 'react-dom/client'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import Workout from './Workout.jsx'
import Modals from '../components/Modals.jsx'
import { DEF, useStore } from '../store/useStore.js'
import { useUI } from '../store/useUI.js'
import { makeSideSet } from '../lib/workout-model.js'
import { buildSessionEntries } from '../lib/session-start.js'
import { withExUnit } from '../lib/ex-unit.js'

vi.mock('../lib/sound.js', () => ({ beep: vi.fn(), vibrate: vi.fn(), alertBuzz: vi.fn(), unlock: vi.fn(), restOver: vi.fn() }))
vi.mock('../lib/api.js', () => ({ api: vi.fn(() => Promise.resolve({})) }))
vi.mock('../components/GarminLiveStatus.jsx', () => ({ default: () => null }))
globalThis.IS_REACT_ACT_ENVIRONMENT = true
const BENCH = '0025'
const row = (extra = {}) => ({ w: 30, r: 10, done: false, ...extra })
const entry = (sets = [row(), row(), row()], extra = {}) => ({ id: BENCH,
  target: { mode: 'reps', sets: 3, reps: 10, weight: 32.5, prog: 'off' },
  planned: { sets: 3, reps: 10, weight: 32.5 }, sets, ...extra })
const past = { id: 'past', d: '2026-10-22', entries: [entry([row({ done: true })])] }
let host, root
beforeEach(() => {
  useUI.getState().stopRest()
  useUI.getState().stopWork()
  useUI.setState({ sheets: [], timer: null, work: null })
})
afterEach(() => {
  if (root) act(() => root.unmount())
  useUI.getState().stopRest()
  useUI.getState().stopWork()
  host?.remove()
  host = root = null
})
function mount(ex = entry(), patch = {}) {
  const S = { ...structuredClone(DEF), gifSize: 'off', sound: false, effort: 'rpe', workouts: [past], ...patch }
  S.active = { id: 'table-test', d: '2026-11-02', start: Date.now(), name: 'Workout', cur: 0, entries: [ex], workoutView: 'cards' }
  useStore.setState({ S, user: null })
  host = document.createElement('div'); document.body.appendChild(host)
  root = createRoot(host)
  act(() => root.render(<MemoryRouter><Workout /><Modals /></MemoryRouter>))
}
const click = el => { expect(el).toBeTruthy(); act(() => el.click()) }
const live = () => useStore.getState().S.active.entries[0]
const editor = () => host.querySelector('.workout-set-editor')
const open = (index = 0) => click(host.querySelectorAll('.set-table-edit')[index])
const type = (input, value) => act(() => {
  expect(input).toBeTruthy()
  Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(input, value)
  input.dispatchEvent(new Event('input', { bubbles: true }))
})
const chooseEffort = value => {
  click(editor().querySelector('.set-effort-value'))
  const preset = [...host.querySelectorAll('.effpick .menu-item')].find(el => el.querySelector('.effpick-n')?.textContent === value)
  click(preset)
}

describe('compact workout table', () => {
  it('keeps the program alongside historical starting values without inline fields or counters', () => {
    mount()
    expect(host.querySelector('.planline').textContent).toBe('Plan: 3 × 10 · 32.5 kg')
    expect(host.querySelector('.set-table-edit').textContent).toBe('3010')
    expect(host.querySelector('.set-table-row .stp')).toBeNull()
    expect(host.querySelector('.set-previous')).toBeNull()
    expect(host.querySelector('.refline')).toBeNull()
  })

  it('checks and unchecks the existing values without opening an editor', () => {
    mount()
    const check = host.querySelector('.set-table-row .chk')
    click(check)
    expect(live().sets[0]).toMatchObject({ w: 30, r: 10, done: true })
    expect(editor()).toBeNull()
    expect(useUI.getState().timer).not.toBeNull()
    click(check)
    expect(live().sets[0]).toMatchObject({ w: 30, r: 10, done: false })
  })

  it('uses the existing weight step and preserves completed rows on Done', () => {
    mount(entry([row({ done: true }), row(), row()]))
    open()
    click(editor().querySelector('.workout-set-field button[aria-label="Increase"]'))
    expect(live().sets[0].w).toBe(32.5)
    click(editor().querySelector('.btn.primary'))
    expect(live().sets[0].done).toBe(true)
    expect(editor()).toBeNull()
    expect(useUI.getState().timer).toBeNull()
  })

  it('edits a pinned lb load on a kg profile without closing the editor or converting stored values twice', () => {
    mount(entry([row({ w: 20.41 }), row({ w: 20.41 })]), {
      unit: 'kg', exUnit: withExUnit({}, BENCH, 'lb', 1),
    })
    expect(host.querySelector('.set-table-head').textContent).toContain('Weight (lb)')
    expect(host.querySelector('.set-table-value > span').textContent).toBe('45')
    open()
    expect(editor()).not.toBeNull()
    expect(editor().querySelector('.weight-value').getAttribute('aria-label')).toBe('Weight calculator: 45 lb')
    expect(live().sets[0].w).toBe(20.41)

    click(editor().querySelector('.weight-value'))
    expect(host.querySelector('input[aria-label="Total weight"]').value).toBe('45')
    expect(host.querySelector('.weight-calculator .weight-unit').textContent).toBe('lb')
    type(host.querySelector('input[aria-label="Total weight"]'), '50')
    click(host.querySelector('.weight-calculator .btn.primary'))
    expect(live().sets.map(set => set.w)).toEqual([22.6796, 22.6796])
    expect(editor()).not.toBeNull()
    expect(editor().querySelector('.weight-value').textContent).toBe('50')

    click(editor().querySelector('.workout-set-field [aria-label="Decrease"]'))
    expect(live().sets[0]).toMatchObject({ w: 20.4117, r: 10, done: false })
    expect(editor().querySelector('.weight-value').textContent).toBe('45')
    expect(useStore.getState().S.unit).toBe('kg')
    expect(useUI.getState().timer).toBeNull()
  })

  it('shows the selected rating with its original color and description and uses the original picker', () => {
    mount(entry([row({ rpe: 8 }), row(), row()]))
    open()
    const rating = editor().querySelector('.set-effort-value')
    expect(rating.querySelector('.set-effort-badge').textContent).toBe('8')
    expect(rating.querySelector('.set-effort-badge').style.background).toBe('var(--yellow)')
    expect(rating.textContent).toContain('Two more reps')
    chooseEffort('9.5')
    expect(live().sets[0]).toMatchObject({ rpe: 9.5, done: true })
    expect(editor()).toBeNull()
    expect(useUI.getState().sheets).toHaveLength(0)
    expect(useUI.getState().timer).not.toBeNull()
  })

  it('clears a rating without undoing completion', () => {
    mount(entry([row({ rpe: 8, done: true }), row(), row()]))
    open(); click(editor().querySelector('.set-effort-value'))
    click([...host.querySelectorAll('.sheet button')].find(el => el.textContent.includes('Clear rating')))
    expect(live().sets[0].rpe).toBeUndefined()
    expect(live().sets[0].done).toBe(true)
    expect(editor()).not.toBeNull()
  })

  it('hides effort when disabled and shows RIR when selected', () => {
    mount(entry(), { effort: 'none' }); open()
    expect(editor().querySelector('.set-effort-value')).toBeNull()
    act(() => useStore.getState().update(s => { s.effort = 'rir' }))
    // The choice is read at opening; reopen after a settings change.
    act(() => useUI.getState().closeAll()); open()
    expect(editor().querySelector('.set-effort-value').getAttribute('aria-label')).toBe('RIR')
  })

  it('invalidates a stale editor and picker when its exercise is replaced', () => {
    mount(); open(); click(editor().querySelector('.set-effort-value'))
    act(() => useStore.getState().update(s => { s.active.entries[0] = entry(undefined, { id: '0031' }) }))
    const preset = [...host.querySelectorAll('.effpick .menu-item')].find(el => el.querySelector('.effpick-n')?.textContent === '8')
    click(preset)
    expect(live().sets[0]).toMatchObject({ w: 30, r: 10, done: false })
    expect(live().sets[0].rpe).toBeUndefined()
  })

  it('edits and completes only the chosen unilateral side', () => {
    const target = { mode: 'reps', sets: 2, reps: 10, weight: 30, side: true }
    mount(entry([makeSideSet(row()), makeSideSet(row())], { target }))
    expect([...host.querySelectorAll('.set-table-row .n')].map(el => el.textContent)).toEqual(['1 L', '1 R', '2 L', '2 R'])
    open(1)
    expect(editor().textContent).toContain('Right')
    chooseEffort('8')
    expect(live().sets[0].sides.R).toMatchObject({ done: true, rpe: 8 })
    expect(live().sets[0].sides.L.done).toBe(false)
  })

  it('keeps a cardio goal visible separately from an unmeasured distance', () => {
    mount({ id: '2259', target: { mode: 'cardio', sets: 1, min: 20, km: 5 }, sets: [{ min: 20, done: false }] })
    expect(host.querySelector('.planline').textContent).toBe('Goal: 20 min · 5 km')
    open()
    expect(editor().querySelector('#set-editor-km').value).toBe('')
    expect(live().sets[0].km).toBeUndefined()
  })

  it('shows cardio duration and distance while preserving secondary speed and nullable incline controls', () => {
    const cardio = { id: '2259', target: { mode: 'cardio', min: 15, km: 3 }, sets: [{ min: 15, km: 3, speed: 8, done: false }, { min: 15, km: 3, speed: 8, done: false }] }
    mount(cardio, { speedUnit: 'mph' })
    expect([...host.querySelectorAll('.set-table-head > span')].map(el => el.textContent).filter(Boolean)).toEqual(['Duration (min)', 'Distance (km)'])
    expect([...host.querySelector('.set-table-edit').querySelectorAll('.set-table-value > span')].map(el => el.textContent)).toEqual(['15', '3'])
    open()
    expect([...editor().querySelectorAll('label')].map(el => el.textContent)).toEqual(['Duration (min)', 'Distance (km)', 'Speed (mph)', 'Incline (%)'])
    expect(editor().querySelector('#set-editor-min').value).toBe('15')
    expect(editor().querySelector('#set-editor-km').value).toBe('3')
    expect(editor().querySelector('label[for="set-editor-speed"]').textContent).toBe('Speed (mph)')
    expect(editor().querySelector('#set-editor-speed').value).toBe('4.97')
    click(editor().querySelector('#set-editor-km').closest('.workout-set-field').querySelector('[aria-label="Increase"]'))
    expect(live().sets[0].km).toBe(3.1)
    click(editor().querySelector('#set-editor-speed').closest('.workout-set-field').querySelector('[aria-label="Increase"]'))
    expect(live().sets[0].speed).toBe(8.8)
    expect(editor().querySelector('#set-editor-incline').value).toBe('')
    click(editor().querySelector('#set-editor-incline').closest('.workout-set-field').querySelector('[aria-label="Increase"]'))
    expect(live().sets[0].incline).toBe(.5)
    type(editor().querySelector('#set-editor-incline'), '')
    expect(live().sets[0].incline).toBeUndefined()
    expect(live().sets[0].min).toBe(15)
    click(editor().querySelector('.btn.primary'))
    expect(live().sets[0].done).toBe(true)
  })

  it('keeps timed holds startable and their duration editable', () => {
    mount({ id: '1001', target: { mode: 'time', sec: 30, sets: 2 }, sets: [{ sec: 30, w: 0, done: false }, { sec: 30, w: 0, done: false }] })
    expect(host.querySelector('[aria-label="Start set"]')).not.toBeNull()
    open()
    click(editor().querySelector('[aria-label="Increase"]'))
    expect(live().sets[0].sec).toBe(35)
    expect(editor().querySelector('.set-effort-value')).toBeNull()
    click(editor().querySelector('.btn.primary'))
    expect(live().sets[0].done).toBe(true)
  })

  it('keeps set numbers and sides visible for every timed unilateral hold', () => {
    const sets = ['L', 'R', 'L', 'R'].map(side => ({ sec: 30, w: 0, side, done: false }))
    mount({ id: '1001', target: { mode: 'time', sec: 30, sets: 2, side: true }, sets })
    expect([...host.querySelectorAll('.set-table-row .n')].map(el => el.textContent)).toEqual(['1 L', '1 R', '2 L', '2 R'])
    open(1)
    expect(editor().querySelector('h3').textContent).toBe('Set 1 · Right')
    click(editor().querySelector('.btn.primary'))
    expect(live().sets.map(set => set.done)).toEqual([false, true, false, false])
  })

  it('uses historical loads when a program weight is zero and the program when there is no history', () => {
    const S = { ...structuredClone(DEF), workouts: [past] }
    const routine = { id: 'r', prog: 'off', ex: [{ ...entry().target, id: BENCH, weight: 0 }] }
    expect(buildSessionEntries(S, routine)[0].sets[0]).toMatchObject({ w: 30, r: 10, done: false })
    S.workouts = []; routine.ex[0].weight = 32.5
    expect(buildSessionEntries(S, routine)[0].sets[0]).toMatchObject({ w: 32.5, r: 10, done: false })
  })

  it.each([false, true])('provides clickable navigation with chips disabled (superset: %s)', grouped => {
    mount(entry(), { wc: { exerciseChips: false } })
    act(() => useStore.getState().update(s => {
      if (grouped) {
        s.active.entries[0].sg = 'pair'
        s.active.entries.push(entry(undefined, { id: '0031', sg: 'pair' }))
      }
      s.active.entries.push(entry(undefined, { id: '0047' }))
    }))
    expect(host.querySelector('.wchips')).toBeNull()
    click(host.querySelector('[aria-label="Workout options"]'))
    click([...host.querySelectorAll('.menu-item')].find(el => el.querySelector('.tt')?.textContent === 'Exercises'))
    const choices = host.querySelectorAll('.sheet .menu-item')
    expect(choices).toHaveLength(2)
    click(choices[1])
    expect(useStore.getState().S.active.cur).toBe(grouped ? 2 : 1)
    expect(editor()).toBeNull()
    expect(useStore.getState().S.active.entries.every(e => e.sets.every(s => !s.done))).toBe(true)
    expect([...host.querySelectorAll('button')].some(el => ['Prev', 'Next'].includes(el.textContent.trim()))).toBe(false)
  })

  it('ignores navigation from a menu belonging to a replaced workout', () => {
    mount(entry(), { wc: { exerciseChips: false } })
    act(() => useStore.getState().update(s => { s.active.entries.push(entry(undefined, { id: '0047' })) }))
    click(host.querySelector('[aria-label="Workout options"]'))
    click([...host.querySelectorAll('.menu-item')].find(el => el.querySelector('.tt')?.textContent === 'Exercises'))
    act(() => useStore.getState().update(s => { s.active.id = 'replacement' }))
    click(host.querySelectorAll('.sheet .menu-item')[1])
    expect(useStore.getState().S.active.cur).toBe(0)
  })

  it('navigates back to the former current unit if a rest advanced while the menu was open', () => {
    mount(entry(), { wc: { exerciseChips: false } })
    act(() => useStore.getState().update(s => { s.active.entries.push(entry(undefined, { id: '0047' })) }))
    click(host.querySelector('[aria-label="Workout options"]'))
    click([...host.querySelectorAll('.menu-item')].find(el => el.querySelector('.tt')?.textContent === 'Exercises'))
    act(() => useStore.getState().update(s => { s.active.cur = 1 }))
    click(host.querySelectorAll('.sheet .menu-item')[0])
    expect(useStore.getState().S.active.cur).toBe(0)
  })
})
