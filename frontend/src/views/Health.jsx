import '../styles/progress-refinement.css'
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useStore } from '../store/useStore.js'
import { dateLocale, t } from '../lib/i18n.js'
import { todayISO } from '../lib/format.js'
import { isAndroid } from '../lib/mobile.js'
import { garminHealthArchive } from '../lib/garmin-health.js'
import GarminHealthSummary from '../components/GarminHealthSummary.jsx'
import DateField from '../components/DateField.jsx'
import Icon from '../components/Icon.jsx'
import { Row, Segmented } from '../components/ui.jsx'

const METRICS = ['body_composition', 'sleep', 'resting_heart_rate', 'heart_rate', 'hrv']

// This screen reads only the existing private archive. Fetching and setup stay in Settings.
export default function Health() {
  const nav = useNavigate()
  const owner = useStore(s => s.user?.id ?? null)
  const unit = useStore(s => s.S.unit)
  const [date, setDate] = useState(todayISO)
  const [saved, setSaved] = useState(null)
  const current = saved?.owner === owner && saved.date === date ? saved : null
  const records = current?.records || []
  useEffect(() => {
    let stopped = false
    setSaved(null)
    const read = async () => {
      try {
        if (!await isAndroid()) {
          if (!stopped) setSaved({ owner, date, records: [], status: 'unsupported' })
          return
        }
        if (stopped) return
        const rows = await Promise.all(METRICS.map(async metric => {
          const record = await garminHealthArchive.read(owner, date, metric)
          return record?.date === date && record.metric === metric && record.status === 'available' ? record : null
        }))
        if (!stopped) setSaved({ owner, date, records: rows.filter(Boolean), status: 'ready' })
      } catch {
        if (!stopped) setSaved({ owner, date, records: [], status: 'storage_error' })
      }
    }
    void read()
    return () => { stopped = true }
  }, [owner, date])
  const fetchedAt = Math.max(0, ...records.map(record => Number.isFinite(record.fetchedAt) ? record.fetchedAt : 0))
  const fetched = fetchedAt > 0 ? new Date(fetchedAt).toLocaleString(dateLocale(), { dateStyle: 'medium', timeStyle: 'short' }) : null

  return <div className="progress-refinement progress-health">
    <div className="hdr">
      <button className="iconbtn" data-back="/stats?section=body" aria-label={t('Body')} onClick={() => nav('/stats?section=body')}><Icon name="chevronLeft" /></button>
      <div className="grow"><h1>{t('Health')}</h1><div className="sub">{t('Garmin Connect')}</div></div>
    </div>
    <Segmented className="progress-body-tabs" value="health" onChange={value => { const route = { weight: '/stats?section=body', measurements: '/measurements', photos: '/progress-photos' }[value]; if (route) nav(route) }}
      options={[{ value: 'weight', label: t('Weight') }, { value: 'measurements', label: t('Measurements') }, { value: 'health', label: t('Health') }, { value: 'photos', label: t('Photos') }]} />
    <div className="health-date"><DateField value={date} max={todayISO()} label={t('Date')} onChange={setDate} /></div>
    {current?.status === 'unsupported' && <p className="small dim" role="status">{t('Android app only')}</p>}
    {current?.status === 'storage_error' && <p className="small dim" role="alert">{t('Could not read Garmin health data. Try again.')}</p>}
    <GarminHealthSummary records={records} unit={unit} date={date} loading={!current} />
    {records.length > 0 && <p className="small dim health-provenance">{t('Garmin Connect')} · {t('Saved readings')}{fetched && <><br />{t('Last synced: {0}', fetched)}</>}</p>}
    <div className="sect-b"><Row icon="heart" title={t('Garmin health data')} subtitle={t('Settings')} accessory="chevron" onClick={() => nav('/settings/garmin')} /></div>
  </div>
}
