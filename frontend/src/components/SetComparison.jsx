import { fmtNum } from '../lib/format.js'
import { t } from '../lib/i18n.js'
import { isAssisted } from '../lib/exercises.js'
import { effortColor, rirOf, toScale } from '../lib/effort.js'

export function SetComparison({ current, previous, field, exerciseId, view = v => v, deltaOnly = false }) {
  if (previous?.[field] == null || current?.[field] == null) return null
  const before = view(previous[field]), now = view(current[field])
  if (!Number.isFinite(before) || !Number.isFinite(now)) return null
  const delta = Math.round((now - before) * 100) / 100
  if (deltaOnly && delta === 0) return null
  const up = field === 'w' && isAssisted(exerciseId) ? delta < 0 : delta > 0
  return <span className={'set-comparison' + (deltaOnly ? ' delta-only' : '')} dir="ltr" title={t('Last time') + ': ' + fmtNum(before)}>
    {!deltaOnly && <span className="set-previous">{fmtNum(before)}</span>}
    {delta !== 0 && <b className={up ? 'set-delta up' : 'set-delta down'}>{delta > 0 ? '+' : '−'}{fmtNum(Math.abs(delta))}</b>}
  </span>
}

// Separate stripes retain both readings: rating the new set never erases last time's effort.
export function SetEffortMarker({ current, previous, kind = 'rir' }) {
  const now = rirOf(current), before = rirOf(previous)
  if (now == null && before == null) return null
  const reading = value => `${kind.toUpperCase()} ${fmtNum(toScale(kind, value))}`
  const label = [now != null && reading(now), before != null && `${t('Last time')}: ${reading(before)}`].filter(Boolean).join(' · ')
  return <span className="set-effort-marker" role="img" aria-label={label} title={label}>
    <i className="current" style={{ background: effortColor(now) || 'var(--sep)' }} />
    {before != null && <i className="previous" style={{ background: effortColor(before) }} />}
  </span>
}
