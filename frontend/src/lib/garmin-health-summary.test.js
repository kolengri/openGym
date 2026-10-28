import { describe, expect, it } from 'vitest'
import { garminHealthSummary } from './garmin-health-summary.js'

const record = (metric, data, date = '2026-10-20') => ({ metric, data, date, status: 'available' })
const byId = records => Object.fromEntries(garminHealthSummary(records).map(card => [card.id, card]))

describe('Garmin archived health summaries', () => {
  it('converts only the verified dateRange weight schema and uses the latest measurement date', () => {
    const data = [record('body_composition', { dateWeightList: [
      { date: '2026-10-18T12:00:00', weight: 78000 },
      { date: '2026-10-19T12:00:00', weight: 78257 },
      { date: 'broken', weight: 90000 },
      { date: '2026-10-20T12:00:00', weight: null },
    ] })]
    expect(garminHealthSummary(data)[0]).toMatchObject({ value: 78.257, unit: 'kg', date: '2026-10-19' })
    expect(garminHealthSummary(data, 'lb')[0]).toMatchObject({ value: 172.5, unit: 'lb', date: '2026-10-19' })
    expect(byId([record('weight', { weight: 78257 })]).weight.value).toBeUndefined()
  })
  it('reads documented sleep seconds without mixing naps or inventing timestamp units', () => {
    expect(byId([record('sleep', { dailySleepDTO: { sleepTimeSeconds: 27000, napTimeSeconds: 1800, calendarDate: '2026-10-19' } })]).sleep)
      .toMatchObject({ value: 27000, date: '2026-10-19' })
    expect(byId([record('sleep', { dailySleepDTO: { sleepTimeSeconds: 0 } })]).sleep.value).toBe(0)
    expect(byId([record('sleep', { sleepTimeSeconds: 27000 })]).sleep.value).toBeUndefined()
  })
  it('reads only dated points from the dedicated resting-heart-rate series or exact heart_rate field', () => {
    const resting = record('resting_heart_rate', { allMetrics: { metricsMap: { WELLNESS_RESTING_HEART_RATE: [
      { calendarDate: '2026-10-19', value: 99 }, { calendarDate: '2026-10-20', value: 53 },
    ] } } })
    expect(byId([resting]).resting_heart_rate).toMatchObject({ value: 53, date: '2026-10-20' })
    expect(byId([record('heart_rate', { restingHeartRate: 55 })]).resting_heart_rate.value).toBe(55)
    expect(byId([record('resting_heart_rate', { value: 53 })]).resting_heart_rate.value).toBeUndefined()
  })
  it('keeps the exact nightly HRV number without assigning unproven units or substituting a weekly average', () => {
    const hrv = record('hrv', { hrvSummary: { lastNightAvg: 47.25, weeklyAvg: 70, calendarDate: '2026-10-19' } })
    expect(byId([hrv]).hrv).toMatchObject({ value: 47.25, date: '2026-10-19', unitUnknown: true })
    expect(byId([hrv]).hrv.unit).toBeUndefined()
    expect(byId([record('hrv', { hrvSummary: { weeklyAvg: 70 } })]).hrv.value).toBeUndefined()
  })
  it('leaves missing, unavailable, malformed, and undocumented fields missing', () => {
    for (const data of [null, [], [record('sleep', {})], [{ ...record('sleep', { dailySleepDTO: { sleepTimeSeconds: 200 } }), status: 'unavailable' }],
      [record('sleep', { dailySleepDTO: { sleepTimeSeconds: '27000' } })],
      [record('sleep', { dailySleepDTO: { sleepTimeSeconds: Infinity } })],
      [record('sleep', { dailySleepDTO: { sleepTimeSeconds: -1 } })],
      [record('sleep', { dailySleepDTO: { sleepTimeSeconds: 200, calendarDate: '2026-02-30' } })],
      [record('sleep', { dailySleepDTO: { sleepTimeSeconds: 200 } }, '2026-02-30')]]) {
      expect(garminHealthSummary(data).every(card => card.value == null)).toBe(true)
    }
  })
  it('does not mutate archived data', () => {
    const records = [record('hrv', { hrvSummary: { lastNightAvg: 40 } })]
    const before = structuredClone(records)
    garminHealthSummary(records, 'lb')
    expect(records).toEqual(before)
  })
})
