// @vitest-environment happy-dom
import React, { act } from 'react'
import { createRoot } from 'react-dom/client'
import { afterEach, describe, expect, it, vi } from 'vitest'
import Stats from './Stats.jsx'

const mocks = vi.hoisted(() => ({ S: null, charts: [], history: vi.fn(), nav: vi.fn() }))
vi.mock('../store/useStore.js', () => ({ useStore: selector => selector({ S: mocks.S }) }))
vi.mock('react-router-dom', () => ({ useNavigate: () => mocks.nav }))
vi.mock('../sheets.jsx', () => ({
  bwSheet: () => {}, goalSheet: () => {}, calendarSheet: () => {}, workoutDetailSheet: () => {},
  exerciseHistorySheet: (...args) => mocks.history(...args), WorkoutRow: () => null, bwDeltaColor: () => 'inherit',
}))
vi.mock('../components/LineChart.jsx', () => ({ default: props => { mocks.charts.push(props); return null } }))
vi.mock('../components/Heatmap.jsx', () => ({ default: () => null }))
vi.mock('../components/BodyMap.jsx', () => ({ default: () => null, BodyMapLegend: () => null }))

globalThis.IS_REACT_ACT_ENVIRONMENT = true
const NOW = new Date('2026-11-05T12:00:00').getTime()
const session = (ago, w, extra = []) => {
  const start = NOW - ago * 86400000
  return { id: 'w' + ago, d: new Date(start).toISOString().slice(0, 10), start, end: start + 3600000, name: 'Push',
    entries: [{ id: '0025', target: { sets: 1, reps: 5 }, sets: [{ w, r: 5, done: true }, ...extra] }] }
}
let root, host
function mount({ workouts = [], ...settings } = {}) {
  vi.spyOn(Date, 'now').mockReturnValue(NOW)
  mocks.charts = []
  mocks.S = { body: 'male', effort: 'none', unit: 'kg', targetW: null, bodyweight: [], routines: [], exWeights: {}, workouts, ...settings }
  host = document.createElement('div'); document.body.appendChild(host)
  root = createRoot(host)
  act(() => root.render(<Stats />))
}
afterEach(() => { act(() => root.unmount()); host.remove(); vi.restoreAllMocks(); mocks.history.mockClear(); window.history.replaceState(null, '', '#/') })
const overview = () => host.querySelector('#stats-overview')
const values = () => [...overview().querySelectorAll('.overview-summary b')].map(el => el.textContent)
const chart = () => mocks.charts.filter(c => c.h === 128).at(-1)
const click = el => act(() => el.click())
const pressRange = label => click([...overview().querySelectorAll('.overview-range button')].find(b => b.textContent === label))
const history = () => [session(400, 60), session(60, 40), session(10, 100, [{ w: 40, r: 10, done: true, phase: 'warmup', warmup: true }]), session(3, 120, [{ w: 500, r: 5, done: false }])]

describe('Stats approved Overview', () => {
  it('starts with a month of actual sessions, matching summary and chronological volume points', () => {
    mount({ workouts: history() })
    expect(values()).toEqual(['2', '3', '1,100 kg'])
    expect(chart().points.map(p => p.y)).toEqual([500, 600])
    expect(chart().unit).toBe('kg')
    expect(overview().querySelector('[data-tour="stats-records"]')).toBeNull()
    expect(host.querySelector('#stats-lifts [data-tour="stats-records"]')).toBeTruthy()
    expect(overview().querySelector('.progress-activity').open).toBe(false)
  })
  it('uses the selected period for all three summary figures and the chart', () => {
    mount({ workouts: history() })
    pressRange('3M')
    expect(values()).toEqual(['3', '4', '1,300 kg'])
    expect(chart().points.map(p => p.y)).toEqual([200, 500, 600])
    pressRange('All')
    expect(values()).toEqual(['4', '5', '1,600 kg'])
    expect(chart().points.map(p => p.y)).toEqual([300, 200, 500, 600])
  })
  it('honors warm-up volume and profile units without counting unfinished work', () => {
    mount({ workouts: history(), volumeWarmups: true, unit: 'lb' })
    expect(values()).toEqual(['2', '3', '1,500 lb'])
    expect(chart().points.map(p => p.y)).toEqual([900, 600])
    expect(chart().unit).toBe('lb')
  })
  it('keeps the period while opening Exercises, and exercise rows open the existing history', () => {
    mount({ workouts: history() })
    pressRange('3M')
    click(overview().querySelector('.overview-exercises button'))
    expect(mocks.history).toHaveBeenCalledWith('0025')
    click([...host.querySelectorAll('.stats-index button')].find(b => b.textContent === 'Exercises'))
    expect(window.location.hash).toContain('section=lifts')
    click([...host.querySelectorAll('.stats-index button')].find(b => b.textContent === 'Overview'))
    expect(values()).toEqual(['3', '4', '1,300 kg'])
    expect(overview().querySelector('.overview-range button.on').textContent).toBe('3M')
  })
  it('shows empty totals and no fabricated chart points for a fresh profile', () => {
    mount()
    expect(values()).toEqual(['0', '0', '0 kg'])
    expect(chart().points).toEqual([])
    expect(overview().querySelector('.overview-exercises')).toBeNull()
  })
})
