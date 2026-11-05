// @vitest-environment happy-dom
import React, { act } from 'react'
import { createRoot } from 'react-dom/client'
import { afterEach, expect, it } from 'vitest'
import RecentExerciseHistory from './RecentExerciseHistory.jsx'

let root, host
globalThis.IS_REACT_ACT_ENVIRONMENT = true
const session = (day, km) => ({ id: 'w' + day, d: `2026-10-${String(day).padStart(2, '0')}`, start: Date.UTC(2026, 9, day), entries: [{ id: '2138', target: { mode: 'cardio' }, sets: [{ min: 15, km, done: true }] }] })
function mount(workouts) {
  host = document.createElement('div'); document.body.append(host); root = createRoot(host)
  act(() => root.render(<RecentExerciseHistory exerciseId="2138" history={{ unit: 'kg', workouts }} />))
}
afterEach(() => { act(() => root?.unmount()); host?.remove() })

it('shows a single dated result with units rather than an invented trend', () => {
  mount([session(1, 1.9)])
  expect(host.querySelector('.recent-history-single').textContent).toContain('1.9 km')
  expect(host.querySelector('.recent-history-single time').dateTime).toBe('2026-10-01')
  expect(host.querySelector('svg')).toBeTruthy() // Navigation glyphs remain.
  expect(host.querySelector('.chart-i')).toBeNull()
  expect(host.querySelectorAll('[data-exercise-history-link]')).toHaveLength(1)
})
it('bounds the recent trend to five sessions and includes its measurement unit', () => {
  mount([1, 2, 3, 4, 5, 6].map(day => session(day, day / 10)))
  expect(host.querySelector('.chart.recent-history-chart svg').getAttribute('viewBox')).toBe('0 0 340 80')
  expect(host.querySelector('.recent-history-unit').textContent).toBe('km')
  expect(host.querySelectorAll('.recent-history-list li')).toHaveLength(5)
  expect(host.querySelector('.recent-history-list').textContent).not.toContain('0.1 km')
})
