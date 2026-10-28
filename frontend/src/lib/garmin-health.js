import { garminHealthMetrics, readGarminHealthMetric, readGarminHealthArchive, writeGarminHealthArchive } from './garmin-cloud.js'
import { sha256Hex } from './sha256.js'
import { mergeWeighIns } from './health-read.js'

const DAY_MS = 86400000
const ownerOf = store => store.getState().user?.id ?? null
export function healthDays(start, end) {
  const day = x => typeof x === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(x) && Number.isFinite(Date.parse(x)) && new Date(x).toISOString().slice(0, 10) === x
  if (!day(start) || !day(end)) throw new Error('invalid_date')
  const n = (Date.parse(end) - Date.parse(start)) / DAY_MS
  if (n < 0 || n > 6) throw new Error('invalid_date')
  return Array.from({ length: n + 1 }, (_, i) => new Date(Date.parse(start) + i * DAY_MS).toISOString().slice(0, 10))
}

/** One atomic private file per metric/day, keeping dense sensor arrays out of localStorage. */
export function healthArchive({ load = async () => ({ readHealthArchive: readGarminHealthArchive, writeHealthArchive: writeGarminHealthArchive }) } = {}) {
  let loaded
  const ready = () => loaded ||= load()
  const key = async (owner, date, metric) => {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(date) || !/^[a-z][a-z0-9_]{0,79}$/.test(metric)) throw new Error('invalid_metric')
    const hash = await sha256Hex(new TextEncoder().encode(owner == null ? 'guest' : 'user:' + owner))
    return { ownerKey: hash, date, metric }
  }
  return {
    async read(owner, date, metric) {
      const client = await ready()
      try { return (await client.readHealthArchive(await key(owner, date, metric))).record }
      catch { throw new Error('storage_error') }
    },
    async write(owner, result) {
      const client = await ready()
      // AtomicFile replacement/recovery belongs to Android, not Capacitor's destructive rename.
      await client.writeHealthArchive({ ...await key(owner, result.date, result.metric), record: JSON.stringify(result) })
    },
  }
}
export const garminHealthArchive = healthArchive()

/** Exact dateRange weight schema: weights are grams, body fat percent. Other fields stay raw. */
export function bodyCompositionReadings(result) {
  if (result?.metric !== 'body_composition' || result.status !== 'available') return []
  const rows = result.data?.dateWeightList
  if (!Array.isArray(rows)) return []
  return rows.flatMap(row => {
    if (typeof row?.weight !== 'number' || !Number.isFinite(row.weight)) return []
    const date = row.date
    const at = typeof date === 'number' ? date : typeof date === 'string' ? Date.parse(date) : NaN
    if (!Number.isFinite(at) || at <= 0) return []
    return [{ t: at, kg: row.weight / 1000, id: row.samplePk == null ? null : String(row.samplePk), origin: 'com.garmin.android.apps.connectmobile' }]
  })
}

/** Serial bounded reads, cancellable between calls, strictly bound to the initiating profile. */
export async function syncGarminHealth(store, { start, end, archive = garminHealthArchive, signal, progress = () => {}, metrics: selected } = {}) {
  const days = healthDays(start, end)
  const owner = ownerOf(store), sessionId = store.getState().S.garminCloudSessionId
  if (!sessionId) throw new Error('auth_required')
  let valid = true
  const stopGuard = store.subscribe((state, previous) => {
    if ((state.user?.id ?? null) !== (previous.user?.id ?? null) || state.S.garminCloudSessionId !== previous.S.garminCloudSessionId) valid = false
  })
  const belongs = () => valid && ownerOf(store) === owner && store.getState().S.garminCloudSessionId === sessionId
  const check = () => { if (signal?.aborted) throw new Error('cancelled'); if (!belongs()) throw new Error('session_changed') }
  const counts = { available: 0, unavailable: 0, error: 0, completed: 0, total: 0, weighIns: 0 }
  try {
    const catalog = await garminHealthMetrics()
    check()
    const metrics = (catalog?.metrics || []).filter(m => /^[a-z][a-z0-9_]{0,79}$/.test(m.id) && (!selected || selected.includes(m.id)))
    if (!metrics.length) throw new Error('invalid_metric')
    counts.total = metrics.length * days.length
    for (const date of days.slice().reverse()) for (const metric of metrics) {
      check()
      const result = await readGarminHealthMetric({ sessionId, date, metric: metric.id })
      check()
      if (result?.date !== date || result.metric !== metric.id || !['available', 'unavailable', 'error'].includes(result.status)) throw new Error('invalid_response')
      if (result.status === 'error' && ['auth_required', 'rate_limited', 'storage_unavailable'].includes(result.error)) throw new Error(result.error)
      const previous = await archive.read(owner, date, metric.id)
      check()
      // A failed/empty late response never replaces an earlier successful observation.
      if (result.status === 'available' || previous?.status !== 'available') await archive.write(owner, { ...result, fetchedAt: Date.now(), sessionId })
      check()
      const readings = bodyCompositionReadings(result)
      if (readings.length) {
        store.getState().update(s => { counts.weighIns += mergeWeighIns(s, readings, { src: 'garmin' }).length })
        await store.getState().saveNow()
        check()
      }
      counts[result.status]++; counts.completed++
      progress({ ...counts, date, label: metric.label })
    }
    return counts
  } finally { stopGuard() }
}

const healthDisplayValue = value => typeof value === 'number' ? String(Math.round(value * 100) / 100) : String(value)

export function healthDisplayRows(data, prefix = '', out = [], depth = 0) {
  if (depth > 6 || out.length >= 100) return out
  if (Array.isArray(data)) {
    if (data.length && data.every(x => x == null || typeof x !== 'object')) out.push([prefix, data.filter(x => x != null).slice(0, 12).map(healthDisplayValue).join(', ')])
    else if (data.length) out.push([prefix, String(data.length)])
  } else if (data && typeof data === 'object') {
    for (const [key, value] of Object.entries(data)) {
      if (/^(id|.*(?:pk|uuid|profile|token|credential))$/i.test(key)) continue
      const label = key.replace(/([a-z])([A-Z])/g, '$1 $2').replace(/_/g, ' ')
      healthDisplayRows(value, prefix ? prefix + ' · ' + label : label, out, depth + 1)
    }
  } else if (data !== null && data !== undefined && out.length < 100) out.push([prefix, healthDisplayValue(data)])
  return out
}
