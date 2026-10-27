// Local Android/Connect IQ transport. No HTTP requests, health credentials or account data.
import { MOBILE, nativePlatform } from './mobile.js'
import { setType } from './workout-model.js'
import { ownExerciseRest, ownSetRest, restSecFor, sideRestFor, warmupRestSecFor } from './supersetFlow.js'
import { pyramidRestFor } from './pyramid.js'
import { supersetUnits } from './history.js'

export const GARMIN_APP_ID = '6fcd6528636d4cc39c3ad1e317d7524a'
export const GARMIN_SNAPSHOT_MAX = 12 * 1024
export const GARMIN_HR_MAX_AGE = 15000
const listeners = new Set()
let pluginP = null, heartRate = null, linkError = null
const changed = (kind = 'config') => { for (const fn of listeners) fn(kind) }
export const onGarminChange = fn => { listeners.add(fn); return () => listeners.delete(fn) }

export const garminPlugin = () => pluginP || (pluginP = (async () => {
  if (!MOBILE || await nativePlatform() !== 'android') return null
  const { registerPlugin } = await import('@capacitor/core')
  return { bridge: registerPlugin('GarminBridge') }
})().catch(() => null))

export async function garminStatus() {
  const p = await garminPlugin()
  if (!p) return { available: false, enabled: false, paired: false, installed: false, connected: false }
  const status = await p.bridge.status()
  return { ...status, error: linkError || status?.error || null }
}

export async function garminDevices() {
  const p = await garminPlugin()
  if (!p) return []
  const result = await p.bridge.devices()
  return Array.isArray(result?.devices) ? result.devices : []
}

export async function configureGarmin(config) {
  const p = await garminPlugin()
  if (!p) throw new Error('Garmin is available in the Android app only.')
  const status = await p.bridge.configure(config)
  heartRate = null
  linkError = null
  changed()
  return status
}

export function garminError(error) {
  const next = error ? String(error.message || error).slice(0, 300) : null
  if (next === linkError) return
  linkError = next
  changed('error')
}

// Live samples are deliberately transient. Only watch-computed aggregates go in the workout log.
export function receiveGarminHeartRate(sample, wid, now = Date.now()) {
  const bpm = sample?.bpm, at = sample?.at
  if (!wid || sample?.wid !== wid || !Number.isFinite(bpm) || bpm < 20 || bpm > 250 ||
    !Number.isFinite(at) || at > now + 5000 || now - at > GARMIN_HR_MAX_AGE) return false
  if (heartRate?.wid === wid && heartRate.at >= at) return false
  heartRate = { wid, bpm: Math.round(bpm), at }
  changed('hr')
  return true
}

export const garminHeartRate = (wid, now = Date.now()) => heartRate?.wid === wid && now - heartRate.at <= GARMIN_HR_MAX_AGE ? heartRate : null

// Allowlist the existing snapshot. Even an accidentally added credential/history field must not
// cross this boundary. Never trim running sets to fit; an incomplete plan could log the wrong set.
const pick = (v, keys) => Object.fromEntries(keys.filter(k => v?.[k] !== undefined).map(k => [k, v[k]]))
export function garminSnapshot(snapshot, { timer = null, paused = false, sourceActive = null, warmupRestSec = null, recording = true } = {}) {
  const out = pick(snapshot, ['v', 'unit', 'restSec', 'discarded'])
  out.settings = { recording: recording !== false, restHaptics: snapshot.settings?.restHaptics !== false }
  const active = snapshot.active
  out.active = active ? pick(active, ['id', 'name', 'start', 'unit', 'cur', 'restSec', 'healthType']) : null
  if (out.active) {
    out.active.watchPaused = !!paused
    out.active.rest = timer && !timer.ready ? pick(timer, ['endsAt', 'paused', 'left', 'total', 'forIdx', 'forSet', 'kind']) : null
    const sources = sourceActive?.entries || []
    const units = supersetUnits(sources)
    out.active.entries = (active.entries || []).map((entry, entryIdx) => {
      const source = sources[entryIdx]
      const target = source?.target || {}
      const rows = source?.sets || []
      const unit = units.find(u => u.includes(entryIdx)) || [entryIdx]
      return {
        ...pick(entry, ['id', 'name', 'mode', 'restSec', 'bodyweight', 'perSide', 'group', 'assisted', 'step']),
        ...(source ? { restSec: ownExerciseRest(target) ?? snapshot.restSec, sideRestSec: sideRestFor(target, { timed: false }) || 0 } : {}),
        sets: (entry.sets || []).map((set, setIdx) => ({
          ...pick(set, ['w', 'r', 'sec', 'done', 'warmup', 'at']),
          ...(source ? { restSec: ownSetRest(rows[setIdx]) ?? warmupRestSecFor(source, setIdx,
            restSecFor(sources, unit, snapshot.restSec, { idx: entryIdx, sec: pyramidRestFor(target, rows, setIdx) }), warmupRestSec) } : {}),
          ...(unsupportedSet(rows[setIdx]) ? { unsupported: true } : {}),
          ...(set.sides ? { sides: { L: pick(set.sides.L, ['w', 'r', 'done']), R: pick(set.sides.R, ['w', 'r', 'done']) } } : {}),
        })),
      }
    })
  }
  if (new TextEncoder().encode(JSON.stringify(out)).length > GARMIN_SNAPSHOT_MAX) throw new Error('This workout is too large to send to Garmin. Split it into smaller sessions.')
  return out
}

const unsupportedSet = set => setType(set) !== 'straight' ||
  (set?.sides && ['L', 'R'].some(side => setType(set.sides[side]) !== 'straight'))

// The Android bridge validates the wire format as well. The web boundary deliberately refuses
// Apple-only commands and missing workout IDs so another session can never receive a stray tick.
export function isGarminEvent(ev) {
  if (!ev || typeof ev.id !== 'string' || !ev.id || ev.id.length > 128 || typeof ev.wid !== 'string' || !ev.wid ||
    !Number.isFinite(ev.at) || ev.at <= 0) return false
  if (['finish', 'discard', 'skipRest'].includes(ev.type)) return true
  if (ev.type === 'pause') {
    if (typeof ev.paused !== 'boolean' || !Object.hasOwn(ev, 'rest')) return false
    const r = ev.rest
    return r === null || (r && typeof r === 'object' && !Array.isArray(r) &&
      Number.isSafeInteger(r.endsAt) && r.endsAt >= 0 && Number.isInteger(r.left) && r.left >= 0 && r.left <= 86400 &&
      typeof r.paused === 'boolean' && r.paused === ev.paused &&
      (r.kind == null || r.kind === 'switch') &&
      (r.total == null || (Number.isInteger(r.total) && r.total >= 0 && r.total <= 86400)) &&
      ['forIdx', 'forSet'].every(k => r[k] == null || (Number.isInteger(r[k]) && r[k] >= 0 && r[k] < 100)))
  }
  if (!['setDone', 'setHr', 'selectExercise'].includes(ev.type) || typeof ev.exId !== 'string' || !ev.exId ||
    !Number.isInteger(ev.entryIdx) || ev.entryIdx < 0) return false
  if (ev.type === 'selectExercise') return true
  if (!Number.isInteger(ev.setIdx) || ev.setIdx < 0) return false
  if (ev.side != null && ev.side !== 'L' && ev.side !== 'R') return false
  for (const [key, max] of [['w', 10000], ['r', 10000], ['sec', 86400]]) {
    if (ev[key] != null && (!Number.isFinite(ev[key]) || ev[key] < 0 || ev[key] > max)) return false
  }
  return true
}

export function _setGarminPluginForTest(bridge) { pluginP = Promise.resolve(bridge ? { bridge } : null) }
export function _resetGarminForTest() { pluginP = null; heartRate = null; linkError = null; listeners.clear() }
