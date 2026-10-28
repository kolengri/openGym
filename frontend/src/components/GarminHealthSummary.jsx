import { useId } from 'react'
import { dateLocale, t, useLang } from '../lib/i18n.js'
import { fmtBodyWeight, fmtDate, fmtDur } from '../lib/format.js'
import { garminHealthSummary } from '../lib/garmin-health-summary.js'
import './GarminHealthSummary.css'

export default function GarminHealthSummary({ records, unit, date, loading = false }) {
  useLang()
  const id = useId()
  const number = value => new Intl.NumberFormat(dateLocale(), { maximumFractionDigits: 2 }).format(value)
  const valueText = card => card.kind === 'weight' ? `${fmtBodyWeight(card.value)} ${card.unit}`
    : card.kind === 'duration' ? fmtDur(card.value * 1000)
      : card.kind === 'heartRate' ? t('{0} bpm', number(card.value)) : number(card.value)
  return <section className="garmin-health-summary" aria-labelledby={id} aria-busy={loading}>
    <h4 id={id}>{t('Health overview')}</h4>
    <p className="small muted">{date ? t('Saved on this phone for {0}.', fmtDate(date, false, true)) : t('Choose a date to view saved readings.')}</p>
    <dl className="garmin-health-summary-grid">
      {garminHealthSummary(records, unit).map(card => <div className="garmin-health-summary-card" key={card.id}>
        <dt>{t(card.label)}</dt>
        <dd className="garmin-health-summary-value">{loading ? t('Loading…') : card.value == null ? t('No saved reading') : valueText(card)}</dd>
        {!loading && card.value != null && <dd className="garmin-health-summary-meta">
          <time dateTime={card.date}>{fmtDate(card.date, false, true)}</time>
          {card.note && <span>{t(card.note)}</span>}
          {card.unitUnknown && <span>{t('Unit not verified; original Garmin value.')}</span>}
        </dd>}
      </div>)}
    </dl>
  </section>
}
