import { EFFORT_BANDS, effortColor } from '../lib/effort.js'
import { fmtNum } from '../lib/format.js'
import { t } from '../lib/i18n.js'
import Icon from './Icon.jsx'

export default function SetEffortValue({ kind, value, onClick, cardio = false }) {
  const rir = value == null ? null : kind === 'rpe' ? 10 - value : value
  const band = rir == null ? null : EFFORT_BANDS.find(b => rir <= b.max)
  return <button type="button" className="set-effort-value" aria-label={kind.toUpperCase()} aria-haspopup="dialog" onClick={onClick}>
    <span className="set-effort-badge" style={band ? { background: effortColor(rir) } : undefined}>{value == null ? '–' : fmtNum(value)}</span>
    <span className="set-effort-description">{band ? t(cardio ? band.cardioFeel : band.feel) : t('Not rated yet')}</span>
    <Icon name="chevronDown" />
  </button>
}
