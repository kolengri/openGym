import { useMemo, useState } from 'react'
import { exerciseHistory } from '../lib/exercise-history.js'
import { fmtDate, fmtNum, fmtVol } from '../lib/format.js'
import { setLabel } from '../lib/history.js'
import { speedUnitOf } from '../lib/speed.js'
import { t } from '../lib/i18n.js'
import { exView } from '../lib/ex-unit.js'
import { exerciseHistorySheet } from '../sheets.jsx'
import LineChart from './LineChart.jsx'
import Icon from './Icon.jsx'

export default function RecentExerciseHistory({ history, exerciseId, initialOpen = false }) {
  const [open, setOpen] = useState(initialOpen)
  const view = exView(history, exerciseId)
  const h = useMemo(() => exerciseHistory(view, exerciseId, { limit: 5 }), [view.workouts, view.dbLoad, view.volumeWarmups, exerciseId])
  const points = useMemo(() => h.sessions.slice().reverse()
    .filter(s => s.value != null).map(s => ({ t: s.t, d: s.d, y: s.value })), [h])
  if (!h.total) return null
  const unit = h.metric === 'weight' ? view.unit : h.metric === 'reps' ? t('reps') : h.metric === 'sec' ? 's' : h.metric === 'km' ? 'km' : t('min')
  return <section className="card recent-exercise-history" aria-label={t('Exercise history')}>
    <div className="row between recent-history-heading">
      <h3>{t('Last {0} sessions', Math.min(5, h.total))}</h3>
      <button type="button" className="recent-history-link" data-exercise-history-link onClick={() => exerciseHistorySheet(exerciseId)}>
        {t('History')}<Icon name="chevronRight" />
      </button>
    </div>
    {points.length > 0 && <LineChart points={points} h={100} unit={unit} />}
    <details open={open} onToggle={event => setOpen(event.currentTarget.open)}>
    <summary>{t('Details')}<Icon name="chevronDown" /></summary>
    <ol className="recent-history-list">
      {h.sessions.map(s => <li key={s.id}>
        <div className="row between small">
          <time dateTime={s.d}>{fmtDate(s.d, true)}</time>
          <span className="dim">{s.volume > 0 ? fmtVol(s.volume, view.unit) : s.value != null ? `${fmtNum(s.value)} ${unit}` : ''}</span>
        </div>
        <div className="small dim recent-history-sets">{s.sets.map(row => setLabel(exerciseId, row, s.target, speedUnitOf(history))).join(' · ')}</div>
      </li>)}
    </ol>
    </details>
  </section>
}
