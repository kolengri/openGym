import { describe, expect, it } from 'vitest'
import { previousWorkSets, previousSetAt } from './workout-comparison.js'
import { makeSideSet } from './workout-model.js'

const BENCH = '0025'
const row = (w = 30, r = 10, extra = {}) => ({ w, r, done: true, ...extra })
const entry = (sets, extra = {}) => ({ id: BENCH, target: { mode: 'reps' }, sets, ...extra })

describe('previous workout references', () => {
  it('compares dumbbells in the active entry’s load meaning and refuses different modes', () => {
    const id = '0289' // dumbbell bench press
    const active = { ...entry([row(22, 10)]), id, target: { mode: 'reps', dbLoad: 'each' } }
    const H = { workouts: [{ d: '2026-10-22', entries: [{ ...active, target: { mode: 'reps', dbLoad: 'total' }, sets: [row(40, 10)] }] }] }
    expect(previousWorkSets(H, active)[0].w).toBe(20)
    active.target.mode = 'time'
    expect(previousWorkSets(H, active)).toEqual([])
  })

  it('compares each side independently and refuses a combined-to-side comparison', () => {
    const previous = makeSideSet(row(30, 20))
    const active = entry([makeSideSet(row(35, 18))])
    expect(previousSetAt(active, 0, [previous], 'L')).toMatchObject({ w: 30, r: 10 })
    expect(previousSetAt(active, 0, [row()])).toBeNull()
  })

  it('infers legacy timed rows without mistaking their load for a rep-set reference', () => {
    const H = { workouts: [{ d: '2026-10-22', entries: [{ id: BENCH, sets: [{ sec: 45, w: 10, done: true }] }] }] }
    expect(previousWorkSets(H, entry([row()]))).toEqual([])
    expect(previousWorkSets(H, entry([], { target: { mode: 'time' } }))).toMatchObject([{ sec: 45, w: 10 }])
  })

  it('honors explicit row modes and suppresses mixed-mode references', () => {
    const historical = entry([{ mode: 'time', sec: 45, w: 10, done: true }])
    const H = { workouts: [{ d: '2026-10-22', entries: [historical] }] }
    expect(previousWorkSets(H, entry([row()]))).toEqual([])
    expect(previousWorkSets(H, entry([], { target: { mode: 'time' } }))).toHaveLength(1)
    historical.sets.push(row())
    expect(previousWorkSets(H, entry([row()]))).toEqual([])
  })
})
