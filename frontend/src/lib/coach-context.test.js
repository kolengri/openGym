import { describe, expect, it } from 'vitest'
import { todayForCoach } from './coach-context.js'
import { build } from '../../../api/coach/core/payload.js'

const set = (w, r, done = true) => ({ w, r, done })
const active = {
  id: 'w1', d: '2026-10-13', start: 1, name: 'Tuesday', cur: 0,
  entries: [{ id: 'legext', rid: 'tue', extra: true, target: { sets: 3, reps: 10 }, note: 'secret', media: [{ hash: 'x' }],
    sets: [{ ...set(45, 12), phase: 'warmup' }, set(45, 12)] }],
}

describe('the running session the Coach is given', () => {
  it.each([undefined, 'cardio'])('retains cardio distance through the actual context-to-payload path: %s', mode => {
    const S = { active: { ...active, entries: [{ id: 'custom-run',
      target: { sets: 1, km: 5, ...(mode ? { mode } : {}), privateField: 'private-context-text' },
      sets: [{ km: 4.8, done: true, privateField: 'private-context-text' }] }] } }
    const today = todayForCoach(S)
    expect(today.entries[0].target).toMatchObject({ mode: 'cardio', km: 5 })
    const payload = build(S, { handle: 'synthetic-handle', kind: 'ask', today })
    expect(payload.today.entries[0].target.km).toBe(5)
    expect(payload.today.entries[0].sets).toEqual([{ done: true, km: 4.8 }])
    expect(JSON.stringify(payload.today)).not.toContain('private-context-text')
  })

  it('carries the numbers and the extra mark, nothing else', () => {
    const today = todayForCoach({ active }, 1 + 25 * 60000)
    expect(today.minutes).toBe(25)
    expect(today.entries[0]).toEqual({ id: 'legext', extra: true, target: { sets: 3, reps: 10, sec: undefined, weight: undefined }, sets: [{ done: true, warmup: true, w: 45, r: 12 }, { done: true, w: 45, r: 12 }] })
    expect(JSON.stringify(today)).not.toContain('secret')
  })
  it('nothing when there is no session, or it is an edit of a past one', () => {
    expect(todayForCoach({})).toBeNull()
    expect(todayForCoach({ active: { ...active, editingWorkoutId: 'w0' } })).toBeNull()
  })
})
