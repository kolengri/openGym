import { setLabel } from '../lib/history.js'
import { isSideSet } from '../lib/workout-model.js'
import { effortColor, rirOf, toScale } from '../lib/effort.js'
import { sanitizeHr } from '../lib/heart-rate.js'
import { fmtNum } from '../lib/format.js'
import { t } from '../lib/i18n.js'
import Icon from './Icon.jsx'

export default function LoggedSetSummary({ exerciseId, set, target, speedUnit, effortKind, children }) {
  const readings = isSideSet(set) ? ['L', 'R'].map(side => ({ side, set: set.sides[side] })) : [{ set }]
  const hr = sanitizeHr(set.hr)
  return <span className="logged-set-row">
    <span className="logged-set-load">{setLabel(exerciseId, set, target, speedUnit, { includeEffort: false })}{children}</span>
    <span className="logged-set-effort">{readings.map(({ side, set: reading }) => {
      const rir = rirOf(reading)
      if (rir == null || (side && !reading.done)) return null
      const kind = effortKind === 'rpe' || effortKind === 'rir' ? effortKind : reading.rpe != null ? 'rpe' : 'rir'
      return <span key={side || 'set'} style={{ color: effortColor(rir) }}>{side && t(side) + ' '}{kind.toUpperCase()} {fmtNum(toScale(kind, rir))}</span>
    })}</span>
    <span className="logged-set-heart">{hr && <><Icon name="heart" />{hr.avg}/{hr.max}</>}</span>
  </span>
}
