import { useEffect, useRef, useState } from 'react'
import { useStore } from '../store/useStore.js'
import { Button } from './ui.jsx'
import { t } from '../lib/i18n.js'
import { todayISO } from '../lib/format.js'
import { shareExport } from '../lib/mobile.js'
import { garminHealthMetrics } from '../lib/garmin-cloud.js'
import { garminHealthArchive, healthDays, healthDisplayRows, syncGarminHealth } from '../lib/garmin-health.js'
import GarminHealthSummary from './GarminHealthSummary.jsx'

export default function GarminHealthSettings({ connected }) {
  const owner = useStore(s => s.user?.id ?? null)
  const unit = useStore(s => s.S.unit)
  const [start, setStart] = useState(todayISO)
  const [end, setEnd] = useState(todayISO)
  const [catalog, setCatalog] = useState([])
  const [busy, setBusy] = useState(false)
  const [progress, setProgress] = useState(null)
  const [error, setError] = useState(null)
  const [saved, setSaved] = useState(null)
  const records = saved?.owner === owner && saved.date === end ? saved.records : []
  const loading = !saved || saved.owner !== owner || saved.date !== end
  const controller = useRef(null)
  const mounted = useRef(true)
  useEffect(() => {
    mounted.current = true
    garminHealthMetrics().then(c => { if (mounted.current) setCatalog(c?.metrics || []) }).catch(() => {})
    return () => { mounted.current = false; controller.current?.abort() }
  }, [])
  useEffect(() => { controller.current?.abort(); setSaved(null); setProgress(null) }, [owner])
  useEffect(() => {
    let stopped = false
    setSaved(null)
    Promise.all(catalog.map(async m => ({ label: m.label, ...(await garminHealthArchive.read(owner, end, m.id)) })))
      .then(rows => { if (!stopped) setSaved({ owner, date: end, records: rows.filter(r => r.status === 'available') }) })
      .catch(() => { if (!stopped) { setSaved({ owner, date: end, records: [] }); setError('storage_error') } })
    return () => { stopped = true }
  }, [owner, end, catalog, busy])
  const read = async () => {
    const abort = new AbortController(); controller.current = abort
    setBusy(true); setError(null); setProgress(null)
    try { await syncGarminHealth(useStore, { start, end, signal: abort.signal, progress: p => { if (mounted.current && !abort.signal.aborted) setProgress(p) } }) }
    catch (e) { if (mounted.current && !abort.signal.aborted) setError(e.message) }
    finally { if (mounted.current) setBusy(false) }
  }
  const exportReadings = async () => {
    const abort = new AbortController(); controller.current = abort
    const initial = useStore.getState(), session = initial.S.garminCloudSessionId
    let valid = true
    const stop = useStore.subscribe((state, previous) => {
      if ((state.user?.id ?? null) !== (previous.user?.id ?? null) || state.S.garminCloudSessionId !== previous.S.garminCloudSessionId) {
        valid = false; abort.abort()
      }
    })
    const belongs = () => valid && mounted.current && !abort.signal.aborted &&
      owner === (useStore.getState().user?.id ?? null) && useStore.getState().S.garminCloudSessionId === session
    const check = () => { if (!belongs()) throw new Error('cancelled') }
    setBusy(true); setError(null)
    try {
      const readings = []
      for (const date of healthDays(start, end)) for (const m of catalog) {
        check()
        const row = await garminHealthArchive.read(owner, date, m.id)
        check()
        if (row) readings.push(row)
      }
      check()
      if (!readings.length) { setError('no_saved_readings'); return }
      await shareExport(JSON.stringify({ source: 'Garmin Connect', version: 1, readings }), `garmin-health-${start}-${end}.json`, { shouldShare: belongs })
    } catch (e) { if (belongs()) setError(e.message === 'invalid_date' ? 'invalid_date' : 'storage_error') }
    finally { stop(); if (controller.current === abort) controller.current = null; if (mounted.current) setBusy(false) }
  }
  const message = error === 'auth_required' || error === 'session_changed' ? 'Connect Garmin in Settings before uploading.'
    : error === 'rate_limited' ? 'Garmin is limiting requests. Try again later.'
      : error === 'invalid_date' ? 'Choose a date range of up to 7 days.'
        : error === 'no_saved_readings' ? 'No saved health readings in this period.' : 'Could not read Garmin health data. Try again.'
  return <div style={{ marginTop: 20 }}>
    <h4>{t('Garmin health data')}</h4>
    <p className="small muted">{t('Read all supported health metrics available to your Garmin account. Missing data stays missing. Weight readings are added without replacing manually logged weights.')}</p>
    <label className="measure-date"><span>{t('From')}</span><input aria-label={t('From')} type="date" className="field" value={start} max={end} min="2000-01-01" disabled={busy} onChange={e => setStart(e.target.value)} /></label>
    <label className="measure-date"><span>{t('To')}</span><input aria-label={t('To')} type="date" className="field" value={end} min={start} max={todayISO()} disabled={busy} onChange={e => setEnd(e.target.value)} /></label>
    <Button disabled={!connected || busy} onClick={read}>{t('Read Garmin health data')}</Button>
    {busy && controller.current && <Button onClick={() => controller.current.abort()}>{t('Cancel')}</Button>}
    {progress && <p className="small" role="status">{progress.date} · {t(progress.label)} · {progress.completed}/{progress.total}<br />{t('Available: {0}. No data: {1}. Errors: {2}. Weigh-ins added: {3}.', progress.available, progress.unavailable, progress.error, progress.weighIns)}</p>}
    {error && <p className="small muted" role="alert">{t(message)}</p>}
    <GarminHealthSummary records={records} unit={unit} date={end} loading={loading} />
    {records.length > 0 && <>
      <h4>{t('Saved readings')} · {end}</h4>
      {records.map(record => <details key={record.metric} style={{ marginBottom: 10 }}>
        <summary>{t(record.label)}</summary>
        <dl style={{ fontSize: 12, overflowWrap: 'anywhere' }}>{healthDisplayRows(record.data).map(([key, value], i) => <div key={i} style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}><dt>{key}</dt><dd style={{ margin: 0 }}>{value}</dd></div>)}</dl>
      </details>)}
    </>}
    {catalog.length > 0 && <Button onClick={exportReadings} disabled={busy}>{t('Export Garmin health data')}</Button>}
    <p className="small muted">{t('Detailed readings stay in a separate private archive on this phone. Use Export Garmin health data to back them up. Values retain Garmin’s original fields and units; unavailable units are not guessed.')}</p>
  </div>
}
