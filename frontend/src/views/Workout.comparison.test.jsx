// @vitest-environment happy-dom
import React, { act } from 'react'
import { createRoot } from 'react-dom/client'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import Workout from './Workout.jsx'
import { DEF, useStore } from '../store/useStore.js'
import { useUI } from '../store/useUI.js'
import { exerciseHistorySheet } from '../sheets.jsx'
import { buildSessionEntries } from '../lib/session-start.js'
import { withExUnit } from '../lib/ex-unit.js'

vi.mock('../lib/sound.js', () => ({ beep: vi.fn(), vibrate: vi.fn(), alertBuzz: vi.fn(), unlock: vi.fn(), restOver: vi.fn() }))
vi.mock('../lib/api.js', () => ({ api: vi.fn(() => Promise.resolve({})) }))
vi.mock('../sheets.jsx', async original => ({ ...await original(), exerciseHistorySheet: vi.fn() }))

globalThis.IS_REACT_ACT_ENVIRONMENT = true
const BENCH = '0025'
const row = (w = 30, r = 10, extra = {}) => ({ w, r, done: true, ...extra })
const entry = (sets, extra = {}) => ({ id: BENCH, target: { mode: 'reps', reps: 10, sets: sets.length, weight: 30, prog: 'off' }, sets, ...extra })
const logged = (n, sets = [row()], id = BENCH) => ({ id: `past-${n}`, d: `2026-10-${String(n).padStart(2, '0')}`, entries: [{ ...entry(sets), id }] })
let host, root
beforeEach(() => {
  vi.clearAllMocks()
  useUI.setState({ sheets: [], timer: null, work: null })
})
afterEach(() => {
  if (root) act(() => root.unmount())
  host?.remove()
  host = root = null
})
function mount(sets, patch = {}, extra = {}) {
  const S = { ...structuredClone(DEF), gifSize: 'off', effort: 'rir', workouts: [logged(22)], ...patch }
  S.active = { id: 'live', d: '2026-11-02', start: Date.now(), cur: 0, entries: [entry(sets, extra)] }
  useStore.setState({ S, user: null })
  host = document.createElement('div')
  document.body.appendChild(host)
  root = createRoot(host)
  act(() => root.render(<MemoryRouter><Workout /></MemoryRouter>))
}

describe('workout comparisons', () => {
  it('opens planned work at the last completed weight and reps by default, still unticked', () => {
    const S = { ...structuredClone(DEF), workouts: [logged(22, [row(35, 9), row(32.5, 8)])] }
    const routine = { id: 'r', prog: 'off', ex: [{ ...entry([]).target, id: BENCH, sets: 2 }] }
    expect(buildSessionEntries(S, routine)[0].sets).toMatchObject([
      { w: 35, r: 9, done: false }, { w: 32.5, r: 8, done: false },
    ])
    delete S.startFrom
    expect(buildSessionEntries(S, routine)[0].sets[0]).toMatchObject({ w: 35, r: 9, done: false })
  })

  it('shows signed differences and updates them as the user edits, including a return to baseline', () => {
    mount([row(35, 9, { done: false })])
    expect(host.querySelector('.set-delta')).toBeNull()
    act(() => host.querySelector('.set-table-row .chk').click())
    expect(host.querySelector('.set-delta.up')?.textContent).toBe('+5')
    expect(host.querySelector('.set-delta.down')?.textContent).toBe('−1')
    act(() => useStore.getState().update(s => { s.active.entries[0].sets[0].w = 30 }))
    expect(host.querySelectorAll('.set-delta')).toHaveLength(1)
    expect(host.querySelector('.set-previous')).toBeNull()
  })

  it('also renders numeric and effort comparisons in Focus', () => {
    mount([row(35, 9, { done: false, rir: 2 })], { workoutView: 'focus', workouts: [logged(22, [row(30, 10, { rir: 4 })])] })
    const comparison = host.querySelector('.focus-comparison')
    expect(comparison.querySelector('.set-delta.up').textContent).toBe('+5')
    expect(comparison.querySelector('.set-delta.down').textContent).toBe('−1')
    expect(comparison.querySelector('.set-effort-marker').getAttribute('aria-label')).toBe('RIR 2 · Last time: RIR 4')
  })

  it('leaves warm-ups and extra sets without a reference and matches the work-set order', () => {
    mount([row(15, 5, { phase: 'warmup' }), row(35, 9), row(35, 9)])
    const rows = host.querySelectorAll('.setrow')
    expect(rows[0].querySelector('.set-comparison')).toBeNull()
    expect(rows[1].querySelector('.set-delta.up')?.textContent).toBe('+5')
    expect(rows[2].querySelector('.set-comparison')).toBeNull()
  })

  it('renders current and historical effort as separate colored stripes', () => {
    mount([row(35, 9, { rir: 2 })], { workouts: [logged(22, [row(30, 10, { rpe: 6 })])] })
    const marker = host.querySelector('.set-effort-marker')
    expect(marker.getAttribute('aria-label')).toBe('RIR 2 · Last time: RIR 4')
    expect(marker.querySelectorAll('i')).toHaveLength(2)
    expect(marker.querySelectorAll('i')[0].style.background).not.toBe(marker.querySelectorAll('i')[1].style.background)
  })

  it.each(['cards', 'list', 'compact', 'focus'])('hides effort comparison when ratings are disabled in %s', workoutView => {
    mount([row(35, 9, { rir: 2 })], { workoutView, effort: 'none', workouts: [logged(22, [row(30, 10, { rir: 4 })])] })
    expect(host.querySelector('.set-effort-marker')).toBeNull()
    expect(host.textContent).not.toContain('NONE')
  })
})

describe('recent exercise history and swipe navigation', () => {
  it('shows exactly five latest sessions for this exercise, with the full-history action', () => {
    mount([row(30, 10, { done: false })], { workouts: [1, 2, 3, 4, 5, 6, 7].map(n => logged(n)).concat(logged(22, [row()], '0031')) })
    const recent = host.querySelector('.recent-exercise-history')
    expect([...recent.querySelectorAll('time')].map(el => el.dateTime)).toEqual(['2026-10-07', '2026-10-06', '2026-10-05', '2026-10-04', '2026-10-03'])
    expect(recent.querySelector('svg')).toBeTruthy()
    act(() => recent.querySelector('.recent-history-link').click())
    expect(exerciseHistorySheet).toHaveBeenCalledWith(BENCH)
    expect([...host.querySelectorAll('button')].some(b => ['Prev', 'Next'].includes(b.textContent.trim()))).toBe(false)
    expect(host.querySelector('[data-testid="workout-swipe-surface"]')).toBeTruthy()
  })

  it('shows the available history when fewer than five sessions exist and hides an empty history', () => {
    mount([row()], { workouts: [logged(1), logged(2)] })
    expect(host.querySelectorAll('.recent-history-list li')).toHaveLength(2)
    act(() => useStore.getState().update(s => { s.workouts = [] }))
    expect(host.querySelector('.recent-exercise-history')).toBeNull()
  })

  it('labels cardio session totals and the chart in kilometers when the latest session measures distance', () => {
    const id = '2259'
    const target = { mode: 'cardio', min: 20, km: 3 }
    const workouts = [2, 3].map(n => ({ ...logged(n), entries: [{ id, target,
      sets: [{ min: 10, km: n / 2, done: true }, { min: 10, km: n / 2, done: true }] }] }))
    mount([{ min: 20, km: 3, done: false }], { workouts }, { id, target })
    const recent = host.querySelector('.recent-exercise-history')
    expect([...recent.querySelectorAll('li > .row > .dim')].map(el => el.textContent)).toEqual(['3 km', '2 km'])
    expect(recent.querySelector('.recent-history-sets').textContent).toContain('1.5 km')
    act(() => recent.querySelector('.chart-i').dispatchEvent(new MouseEvent('mousemove', { bubbles: true, clientX: 340 })))
    expect(recent.querySelector('.ctip').textContent).toContain('3 km')
  })

  it('shows recent loads, volume and chart values in a pinned exercise unit without changing kg history', () => {
    mount([row(20.4117, 10, { done: false })], {
      unit: 'kg', exUnit: withExUnit({}, BENCH, 'lb', 1),
      workouts: [logged(2, [row(20.4117)]), logged(3, [row(22.6796)])],
    })
    const recent = host.querySelector('.recent-exercise-history')
    expect([...recent.querySelectorAll('li > .row > .dim')].map(el => el.textContent)).toEqual(['500 lb', '450 lb'])
    expect([...recent.querySelectorAll('.recent-history-sets')].map(el => el.textContent)).toEqual(['50×10', '45×10'])
    act(() => recent.querySelector('.chart-i').dispatchEvent(new MouseEvent('mousemove', { bubbles: true, clientX: 340 })))
    expect(recent.querySelector('.ctip').textContent).toContain('50 lb')
    expect(useStore.getState().S.workouts.map(w => w.entries[0].sets[0].w)).toEqual([20.4117, 22.6796])
  })
})
