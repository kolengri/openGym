import { beforeEach, expect, it, vi } from 'vitest'
import { _setGarminCloudPluginForTest } from './garmin-cloud.js'
import { bodyCompositionReadings, healthArchive, healthDays, healthDisplayRows, syncGarminHealth } from './garmin-health.js'
const date = '2026-10-20', at = Date.parse(date + 'T09:00:00Z')
const composition = () => ({ metric: 'body_composition', date, status: 'available', data: { dateWeightList: [{ date: at, weight: 78257, bodyFat: null, bodyWater: 51.2, samplePk: 123 }] } })
function storeOf(bodyweight = []) {
  const listeners = new Set()
  let state = { user: { id: 'synthetic-a' }, S: { unit: 'kg', bodyweight, garminCloudSessionId: 'synthetic-session' } }
  state.update = fn => { const before = state; const S = structuredClone(state.S); fn(S); state = { ...state, S }; listeners.forEach(fn => fn(state, before)) }
  state.saveNow = vi.fn(async () => {})
  return { getState: () => state, subscribe: fn => { listeners.add(fn); return () => listeners.delete(fn) }, switchOwner(id) { const before = state; state = { ...state, user: { id } }; listeners.forEach(fn => fn(state, before)) } }
}
let bridge, archive, rows

it('formats scalar and list readings equally without rounding the archived source', () => {
  const values = [7.5, 7.25, 0.1 + 0.2, 16.5346696635, 10, null, 'available', false]
  const data = { average: 0.1 + 0.2, readings: values }
  const original = structuredClone(data)
  expect(healthDisplayRows(data)).toEqual([
    ['average', '0.3'],
    ['readings', '7.5, 7.25, 0.3, 16.53, 10, available, false'],
  ])
  expect(data).toEqual(original)
  expect(healthDisplayRows({ values: Array.from({ length: 15 }, (_, i) => i) })[0][1].split(', ')).toHaveLength(12)
})

beforeEach(() => {
  rows = new Map()
  archive = { read: vi.fn(async (_, d, m) => rows.get(d + m)), write: vi.fn(async (_, r) => { rows.set(r.date + r.metric, structuredClone(r)) }) }
  bridge = { healthMetrics: vi.fn(async () => ({ metrics: [{ id: 'body_composition', label: 'Body composition' }] })), readHealthMetric: vi.fn(async () => composition()) }
  _setGarminCloudPluginForTest(bridge)
})
it('bounds real ordered date ranges to seven days', () => {
  expect(healthDays('2026-10-20', '2026-10-26')).toHaveLength(7)
  for (const args of [['2026-02-30', date], [date, '2026-10-19'], [date, '2026-10-27']]) expect(() => healthDays(...args)).toThrow('invalid_date')
})
it('archives exact original values and adds a one-decimal weigh-in in the profile unit', async () => {
  const store = storeOf()
  expect(await syncGarminHealth(store, { start: date, end: date, archive })).toMatchObject({ available: 1, weighIns: 1 })
  expect(rows.get(date + 'body_composition').data).toEqual(composition().data)
  expect(store.getState().S.bodyweight[0]).toMatchObject({ w: 78.3, src: 'garmin', t: at })
  store.getState().update(s => { s.unit = 'lb'; s.bodyweight = [] })
  await syncGarminHealth(store, { start: date, end: date, archive })
  expect(store.getState().S.bodyweight[0].w).toBe(172.5)
})
it('preserves manual weights and never invents a measurement timestamp', async () => {
  const store = storeOf([{ d: date, w: 80, t: at }])
  await syncGarminHealth(store, { start: date, end: date, archive })
  expect(store.getState().S.bodyweight[0].w).toBe(80)
  const result = composition(); delete result.data.dateWeightList[0].date
  expect(bodyCompositionReadings(result)).toEqual([])
})
it('retains saved available data after an empty later response', async () => {
  const store = storeOf()
  await syncGarminHealth(store, { start: date, end: date, archive })
  bridge.readHealthMetric.mockResolvedValue({ date, metric: 'body_composition', status: 'unavailable' })
  await syncGarminHealth(store, { start: date, end: date, archive })
  expect(rows.get(date + 'body_composition').status).toBe('available')
  expect(archive.write).toHaveBeenCalledTimes(1)
})
it('rejects an A-B-A profile switch before storing an awaited result', async () => {
  const store = storeOf()
  bridge.readHealthMetric.mockImplementationOnce(async () => { store.switchOwner('synthetic-b'); store.switchOwner('synthetic-a'); return composition() })
  await expect(syncGarminHealth(store, { start: date, end: date, archive })).rejects.toThrow('session_changed')
  expect(archive.write).not.toHaveBeenCalled()
})
it('stops after authentication failure or rate limiting', async () => {
  for (const error of ['auth_required', 'rate_limited']) {
    bridge.readHealthMetric.mockResolvedValue({ date, metric: 'body_composition', status: 'error', error })
    await expect(syncGarminHealth(storeOf(), { start: date, end: date, archive })).rejects.toThrow(error)
  }
  expect(bridge.readHealthMetric).toHaveBeenCalledTimes(2)
  expect(archive.write).not.toHaveBeenCalled()
})
it('cancels between calls and keeps the already saved partial archive', async () => {
  bridge.healthMetrics.mockResolvedValue({ metrics: [{ id: 'body_composition', label: 'Body composition' }, { id: 'sleep', label: 'Sleep' }] })
  const abort = new AbortController()
  await expect(syncGarminHealth(storeOf(), { start: date, end: date, archive, signal: abort.signal, progress: () => abort.abort() })).rejects.toThrow('cancelled')
  expect(bridge.readHealthMetric).toHaveBeenCalledTimes(1)
  expect(rows.size).toBe(1)
})
it('uses the native atomic archive contract, hashed owners and offline reads', async () => {
  const files = new Map()
  const key = o => o.ownerKey + o.date + o.metric
  const client = {
    writeHealthArchive: vi.fn(async o => files.set(key(o), JSON.parse(o.record))),
    readHealthArchive: vi.fn(async o => ({ record: files.get(key(o)) ?? null })),
  }
  const disk = healthArchive({ load: async () => client })
  await disk.write('synthetic-a', composition())
  expect((await disk.read('synthetic-a', date, 'body_composition')).data).toEqual(composition().data)
  expect(await disk.read('synthetic-b', date, 'body_composition')).toBeNull()
  expect(client.writeHealthArchive.mock.calls[0][0].ownerKey).toMatch(/^[a-f0-9]{64}$/)
  expect(JSON.stringify(client.writeHealthArchive.mock.calls[0][0])).not.toContain('synthetic-a')
  client.readHealthArchive.mockRejectedValueOnce(new Error('disk failure'))
  await expect(disk.read('synthetic-a', date, 'body_composition')).rejects.toThrow('storage_error')
})
it('reads and archives digit-containing oxygen metric IDs', async () => {
  bridge.healthMetrics.mockResolvedValue({ metrics: [{ id: 'spo2', label: 'Pulse oxygen' }] })
  bridge.readHealthMetric.mockResolvedValue({ date, metric: 'spo2', status: 'available', data: { value: 98 } })
  await syncGarminHealth(storeOf(), { start: date, end: date, archive })
  expect(rows.get(date + 'spo2').data.value).toBe(98)
})
