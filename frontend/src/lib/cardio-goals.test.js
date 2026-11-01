import { describe, expect, it } from 'vitest'
import { buildSets, defaultConfig, exLine, modeOf, setLabel, setsRepsOf } from './history.js'
import { modeForSet } from './workout-model.js'
import { buildPlanBundle, parsePlan } from './plan-share.js'
import { workoutsCSV } from './export-csv.js'
import { parseWorkoutCSV } from './import-csv.js'
import { workoutFitMessages, MSG, SPORT, SUB_SPORT } from './fit-export.js'

const id = '2138'
const empty = { exWeights: {}, workouts: [] }

describe('cardio time and distance goals', () => {
  it('starts time-only without an invented speed or measured distance', () => {
    const cfg = { id, ...defaultConfig(id) }
    expect(cfg).toEqual({ id, sets: 1, mode: 'cardio', min: 20 })
    expect(buildSets(empty, { ...cfg, km: 5 })).toEqual([{ min: 20, done: false }])
    expect(buildSets(empty, { id, sets: 1, mode: 'cardio', km: 5 })).toEqual([{ done: false }])
  })

  it('recognizes distance-only data and prints only goals or results actually present', () => {
    expect(modeOf({ km: 5 })).toBe('cardio')
    expect(modeForSet({ km: 4.8, done: true })).toBe('cardio')
    expect(setLabel(id, { min: 19.5, km: 4.8 }, { mode: 'cardio', min: 20, km: 5 })).toBe('19.5 min · 4.8 km')
    expect(setLabel(id, { min: 19.5 }, { mode: 'cardio', min: 20, km: 5 })).toBe('19.5 min')
    expect(setLabel('custom-run', { km: 4.8 })).toBe('4.8 km')
    expect(exLine({ id, mode: 'cardio', km: 5 }, 'lb', 'mph')).toBe('1 × 5 km')
    expect(setsRepsOf({ id, mode: 'cardio', min: 20, km: 5 })).toBe('20 min · 5 km')
    expect(setsRepsOf({ id, mode: 'cardio', sets: 2, min: 10 })).toBe('2 × 10 min')
  })

  it('round trips time-only, distance-only and combined goals through shared plans', () => {
    for (const goals of [{ min: 20 }, { km: 5 }, { min: 20, km: 5 }]) {
      const target = { id, sets: 1, mode: 'cardio', ...goals }
      const bundle = buildPlanBundle({ unit: 'kg', customEx: [], routines: [{ id: 'r', name: 'Cardio', ex: [target] }] }, 'Cardio')
      expect(parsePlan(JSON.stringify(bundle), 'lb').routines[0].ex[0]).toEqual(target)
    }
  })

  it('keeps a distance result through CSV export/import and prefers it over legacy speed', () => {
    const S = { unit: 'kg', workouts: [{ id: 'w', d: '2026-10-28', start: 1, end: 1200001, entries: [{ id, target: { mode: 'cardio', min: 20, km: 5 }, sets: [{ min: 20, km: 4.8, speed: 8, done: true }] }] }] }
    const parsed = parseWorkoutCSV(workoutsCSV(S), { unit: 'kg' })
    expect(parsed.workouts[0].entries[0].sets[0]).toMatchObject({ min: 20, km: 4.8, done: true })
    const messages = workoutFitMessages(S.workouts[0])
    const session = messages.find(m => m.global === MSG.session)
    expect(session.fields.find(([field]) => field === 9)[2]).toBe(480000)
  })

  it('exports distance-only results without inventing an interval duration or speed', () => {
    for (const end of [1200001, undefined]) {
      const messages = workoutFitMessages({ id: 'distance-only', start: 1, end, entries: [
        { id, target: { mode: 'cardio', km: 5 }, sets: [{ km: 4.8, done: true }] },
      ] })
      const session = messages.find(m => m.global === MSG.session)
      const field = (m, n) => m.fields.find(([f]) => f === n)?.[2]
      expect(field(session, 9)).toBe(480000)
      expect(field(session, 5)).toBe(SPORT.cycling)
      expect(field(session, 6)).toBe(SUB_SPORT.indoorCycling)
      expect(field(session, 7)).toBe(end ? 1200000 : 0)
      expect(field(session, 14)).toBeUndefined()
      const lap = messages.find(m => m.global === MSG.lap)
      expect(field(lap, 9)).toBe(480000)
      expect(field(lap, 13)).toBeUndefined()
      expect(messages.some(m => m.global === MSG.set)).toBe(false)
    }
  })
})
