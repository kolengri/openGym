// @vitest-environment happy-dom
// Cardio speed in mph (Discord "miles per hour"): the set row shows, steps and takes typing in
// the profile's speed unit, and what it stores is always km/h.
import React, { act } from 'react'
import { createRoot } from 'react-dom/client'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import Workout from './Workout.jsx'
import { DEF, useStore } from '../store/useStore.js'

vi.mock('../lib/sound.js', () => ({ beep: vi.fn(), vibrate: vi.fn(), alertBuzz: vi.fn(), unlock: vi.fn() }))
vi.mock('../lib/api.js', () => ({ api: vi.fn(() => Promise.resolve({})) }))

globalThis.IS_REACT_ACT_ENVIRONMENT = true
const BIKE = '2138'   // stationary bike, cardio
let root, container

function mount(settings = {}) {
  if (root) unmount()
  const S = { ...JSON.parse(JSON.stringify(DEF)), ...settings }
  S.active = {
    id: 'speed-test', d: '2026-09-23', start: Date.now(), routineId: null, name: 'Cardio', bw: null, cur: 0,
    entries: [{ id: BIKE, target: { sets: 1, min: 20, speed: 8 }, sets: [{ min: 20, speed: 8, done: false }] }],
  }
  useStore.setState({ S, user: null })
  container = document.createElement('div')
  document.body.appendChild(container)
  root = createRoot(container)
  act(() => root.render(<MemoryRouter><Workout /></MemoryRouter>))
}
function unmount() {
  act(() => root.unmount())
  container.remove()
  root = null
}
afterEach(() => { if (root) unmount() })

// The speed column is the second stepper of the set row, after the minutes.
const speedCell = () => container.querySelector('input[aria-label="speed"]').closest('.stp')
const shown = () => speedCell().querySelector('input').value
const header = () => speedCell().closest('.stp-w').querySelector('.stp-l').textContent
const stored = () => useStore.getState().S.active.entries[0].sets[0].speed
const tap = label => act(() => speedCell().querySelector(`button[aria-label="${label} speed"]`).click())
function type(value) {
  const input = speedCell().querySelector('input')
  act(() => {
    Object.getOwnPropertyDescriptor(input.constructor.prototype, 'value').set.call(input, value)
    input.dispatchEvent(new Event('input', { bubbles: true }))
  })
}

describe('cardio speed in the set row', () => {
  describe.each(['cards', 'list', 'compact'])('%s measurement drafts', workoutView => {
    it.each([['min', 'Duration (min)'], ['km', 'Distance (km)']])('preserves decimal drafts and clearing for %s', (field, label) => {
      mount({ workoutView })
      act(() => useStore.getState().update(s => {
        s.active.entries[0] = { id: BIKE, target: { mode: 'cardio', sets: 1 }, sets: [{ done: false }] }
      }))
      const input = () => container.querySelector(`input[aria-label="${label}"]`)
      const type = value => act(() => {
        Object.getOwnPropertyDescriptor(input().constructor.prototype, 'value').set.call(input(), value)
        input().dispatchEvent(new Event('input', { bubbles: true }))
      })
      for (const prefix of ['', '0']) for (const separator of ['.', ',']) {
        type(prefix + separator)
        expect(input().value).toBe(prefix + '.')
        type(input().value + '5')
        expect(useStore.getState().S.active.entries[0].sets[0][field]).toBe(0.5)
        type('')
        expect(input().value).toBe('')
        expect(useStore.getState().S.active.entries[0].sets[0]).not.toHaveProperty(field)
      }
    })
  })

  it('logs nullable kilometers independently from the target and never copies a goal into a result', () => {
    mount({ unit: 'lb', speedUnit: 'mph' })
    act(() => useStore.getState().update(s => {
      s.active.entries[0] = { id: BIKE, target: { sets: 1, mode: 'cardio', min: 20, km: 5 }, sets: [{ min: 20, done: false }] }
    }))
    const row = container.querySelector('.setrow')
    expect([...container.querySelectorAll('.sethead span')].map(e => e.textContent).filter(Boolean)).toEqual(['Duration (min)', 'Distance (km)'])
    expect(container.querySelector('.planline').textContent).toContain('20 min · 5 km')
    const input = row.querySelector('input[aria-label="Distance (km)"]')
    expect(input.value).toBe('')
    act(() => {
      Object.getOwnPropertyDescriptor(input.constructor.prototype, 'value').set.call(input, '4,8')
      input.dispatchEvent(new Event('input', { bubbles: true }))
    })
    act(() => row.querySelector('[role="checkbox"]').click())
    const entry = useStore.getState().S.active.entries[0]
    expect(entry.target.km).toBe(5)
    expect(entry.sets[0]).toMatchObject({ min: 20, km: 4.8, done: true })
    expect(entry.sets[0].speed).toBeUndefined()
    const add = [...container.querySelectorAll('button')].find(b => /Add set/.test(b.textContent))
    act(() => add.click())
    expect(useStore.getState().S.active.entries[0].sets[1]).toEqual({ min: 20, done: false })
  })

  it('keeps the focus distance field empty until a result is entered', () => {
    mount()
    act(() => useStore.getState().update(s => {
      s.active.workoutView = 'focus'
      s.active.entries[0] = { id: BIKE, target: { sets: 1, mode: 'cardio', km: 5 }, sets: [{ done: false }] }
    }))
    expect(container.querySelector('input[aria-label="distance"]').value).toBe('')
    expect(container.querySelector('input[aria-label="duration"]').value).toBe('')
    expect(container.querySelector('.focus-prescription').textContent).toContain('5 km')
    expect(useStore.getState().S.active.entries[0].sets[0]).toEqual({ done: false })
  })

  it('reads, steps and takes typing in mph for a profile in pounds, and stores km/h', () => {
    mount({ unit: 'lb' })
    expect(header()).toBe('Speed (mph)')
    expect(shown()).toBe('4.97')   // 8 km/h
    // A tap is half a mile an hour, not half a kilometre.
    tap('Increase')
    expect(stored()).toBe(8.8)
    expect(shown()).toBe('5.47')
    type('6')
    expect(stored()).toBe(9.66)
    type('6.5')
    expect(stored()).toBe(10.46)
    expect(shown()).toBe('6.5')
  })

  it('follows a chosen speed unit over the weight unit', () => {
    mount({ unit: 'kg', speedUnit: 'mph' })
    expect(header()).toBe('Speed (mph)')
    mount({ unit: 'lb', speedUnit: 'kmh' })
    expect(header()).toBe('Speed (km/h)')
    expect(shown()).toBe('8')
  })

  it('leaves a km/h profile exactly as it was', () => {
    mount()
    expect(header()).toBe('Speed (km/h)')
    expect(shown()).toBe('8')
    tap('Increase')
    expect(stored()).toBe(8.5)
    type('10.25')
    expect(stored()).toBe(10.25)
  })
})

// The line under the exercise reads the past in the same unit as the row it sits over, whether
// it holds the last time or the best set (#173).
describe('the reference line in mph', () => {
  const past = { id: 'w0', d: '2026-09-20', start: Date.now() - 3 * 86400000, end: Date.now() - 3 * 86400000 + 1800000, name: 'Cardio',
    entries: [{ id: BIKE, target: { mode: 'cardio', sets: 1, min: 20, speed: 16.09344 }, sets: [{ min: 20, speed: 16.09344, done: true }] }] }
  const refText = () => container.querySelector('.refline')?.textContent || ''

  it('shows last time and the best set in mph for a profile in pounds', () => {
    mount({ unit: 'lb', workouts: [past] })
    expect(refText()).toContain('20 min @ 10 mph')
    mount({ unit: 'lb', workouts: [past], logRef: 'best' })
    expect(refText()).toContain('20 min @ 10 mph')
  })
})
