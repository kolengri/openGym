import { bodyCompositionReadings } from './garmin-health.js'
import { isoOf } from './format.js'
import { convertBodyWeight } from './units.js'

const numeric = value => typeof value === 'number' && Number.isFinite(value)
const positive = value => numeric(value) && value > 0
const day = value => {
  if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return null
  const parsed = new Date(value + 'T12:00:00')
  return Number.isFinite(parsed.getTime()) && isoOf(parsed) === value ? value : null
}
const dated = (value, fallback) => value == null ? day(fallback) : day(value)

/** Presentation only. Exact supported response shapes; unknown fields/units stay raw. */
export function garminHealthSummary(records, unit = 'kg') {
  const available = (Array.isArray(records) ? records : []).filter(r => r?.status === 'available' && day(r.date))
  const find = metric => available.find(r => r.metric === metric)
  const cards = [
    { id: 'weight', label: 'Body weight', kind: 'weight' },
    { id: 'sleep', label: 'Sleep', kind: 'duration' },
    { id: 'resting_heart_rate', label: 'Resting heart rate', kind: 'heartRate' },
    { id: 'hrv', label: 'Heart rate variability', kind: 'hrv', note: 'Last night average' },
  ]
  const weights = bodyCompositionReadings(find('body_composition'))
    .filter(row => positive(row.kg) && Number.isFinite(new Date(row.t).getTime()))
    .sort((a, b) => b.t - a.t)
  if (weights.length) {
    const { kg, t } = weights[0]
    Object.assign(cards[0], { value: convertBodyWeight(kg, 'kg', unit === 'lb' ? 'lb' : 'kg'), unit: unit === 'lb' ? 'lb' : 'kg', date: isoOf(new Date(t)) })
  }
  const sleep = find('sleep'), dto = sleep?.data?.dailySleepDTO
  if (numeric(dto?.sleepTimeSeconds) && dto.sleepTimeSeconds >= 0 && dated(dto.calendarDate, sleep.date)) {
    Object.assign(cards[1], { value: dto.sleepTimeSeconds, date: dated(dto.calendarDate, sleep.date) })
  }
  // The dedicated endpoint is a metric series, not a flat daily-summary response.
  const resting = find('resting_heart_rate')
  const series = resting?.data?.allMetrics?.metricsMap?.WELLNESS_RESTING_HEART_RATE
  const point = Array.isArray(series) ? series.find(p => day(p?.calendarDate) === resting.date && positive(p?.value)) : null
  if (point) Object.assign(cards[2], { value: point.value, date: point.calendarDate })
  else {
    const heart = find('heart_rate')
    if (positive(heart?.data?.restingHeartRate) && dated(heart.data.calendarDate, heart.date)) {
      Object.assign(cards[2], { value: heart.data.restingHeartRate, date: dated(heart.data.calendarDate, heart.date) })
    }
  }
  const hrv = find('hrv'), summary = hrv?.data?.hrvSummary
  if (positive(summary?.lastNightAvg) && dated(summary.calendarDate, hrv.date)) {
    // No ms label: the supplied schema establishes this field, but not its unit.
    Object.assign(cards[3], { value: summary.lastNightAvg, date: dated(summary.calendarDate, hrv.date), unitUnknown: true })
  }
  return cards
}
