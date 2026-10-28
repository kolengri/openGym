import { useCallback, useEffect, useRef, useState } from 'react'
import { t } from '../lib/i18n.js'
import { Button, Row, Section, SelectRow } from '../components/ui.jsx'
import { configureGarmin, garminDevices, garminStatus, garminConnection, onGarminChange } from '../lib/garmin-sync.js'
import GarminCloudSettings from '../components/GarminCloudSettings.jsx'
import { GarminConnectionDetails } from '../components/GarminLiveStatus.jsx'
import { useStore } from '../store/useStore.js'

export default function GarminSettingsPage() {
  const wid = useStore(s => s.S.active?.id)
  const [status, setStatus] = useState(null)
  const [devices, setDevices] = useState([])
  const [selected, setSelected] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const epoch = useRef(0)
  const mounted = useRef(true)

  const refresh = useCallback(async () => {
    const request = ++epoch.current
    const [st, list] = await Promise.all([garminStatus(), garminDevices()])
    if (!mounted.current || request !== epoch.current) return
    setStatus(st)
    setDevices(list)
    setSelected(prev => list.some(d => d.id === prev) ? prev : st.deviceId || list[0]?.id || '')
  }, [])
  useEffect(() => {
    mounted.current = true
    let gone = false
    const ask = async () => { try { if (!gone) await refresh() } catch { if (!gone) setError(t('Garmin connection failed. Try again.')) } }
    ask()
    const off = onGarminChange(kind => { if (kind === 'config' || kind === 'error') ask() })
    const timer = setInterval(ask, 4000)
    return () => { gone = true; mounted.current = false; epoch.current++; clearInterval(timer); off() }
  }, [refresh])
  const connect = async enabled => {
    setBusy(true)
    setError(null)
    try {
      await configureGarmin({ enabled, ...(enabled ? { deviceId: selected } : {}) })
      await refresh()
    } catch (e) { setError(e?.message || t('Garmin connection failed. Try again.')) }
    finally { setBusy(false) }
  }
  const line = !status ? t('Checking…')
    : !status.available ? t('Garmin Connect must be installed and paired with your watch.')
    : !status.enabled ? t('Install the openGym companion on your watch, then connect below.')
    : !status.installed ? t('Install the openGym companion on your watch, then connect below.')
    : status.connected ? t('Watch Bluetooth connected') : t('Watch disconnected. Actions will sync after reconnection.')

  return <>
    <Section className="garmin-settings">
      <Row icon="watch" title={t('Garmin')} subtitle={line} />
      {status?.enabled && <GarminConnectionDetails connection={garminConnection(wid)} />}
      {status?.deviceName && <p className="small muted" style={{ padding: '0 16px', overflowWrap: 'anywhere' }}>{status.deviceName}</p>}
      {!status?.enabled && devices.length > 0 && <SelectRow icon="watch" title={t('Select a watch')} value={selected}
        options={devices.map(d => ({ value: d.id, label: d.name }))} onChange={setSelected} />}
      {!status?.enabled && status?.available && !devices.length && <p className="muted small">{t('No Garmin watches found. Pair your watch in Garmin Connect, then try again.')}</p>}
      <div className="garmin-actions">
        {status?.enabled && <Button variant="primary" disabled={busy} onClick={async () => {
          try {
            const { garminPlugin } = await import('../lib/garmin-sync.js')
            const p = await garminPlugin()
            await p?.bridge.openOnWatch()
          } catch { setError(t('Garmin connection failed. Try again.')) }
        }}>{t('Open on the watch')}</Button>}
        <Button disabled={busy || !status?.available} onClick={async () => {
          try {
            const { garminPlugin } = await import('../lib/garmin-sync.js')
            const p = await garminPlugin()
            await p?.bridge.openStore()
          } catch { setError(t('Garmin connection failed. Try again.')) }
        }}>{t('Install on the watch')}</Button>
        <Button disabled={busy || (!status?.enabled && (!selected || !status?.available))} onClick={() => connect(!status?.enabled)}>
          {status?.enabled ? t('Disconnect') : t('Connect')}
        </Button>
        <Button disabled={busy} onClick={() => refresh().catch(() => setError(t('Garmin connection failed. Try again.')))}>{t('Refresh devices')}</Button>
      </div>
      {(error || status?.error) && <p className="garmin-error small" role="alert">{error || (status.installed === false
        ? t('Install the openGym companion on your watch, then connect below.') : status.error)}</p>}
    </Section>
    <GarminCloudSettings />
    <Section footer={t('Recordings sync from Garmin Connect to Strava when those accounts are linked.')}>
      <Row icon="heart" title={t('Heart rate')} subtitle={t('The watch sends live heart rate and saves an average and maximum for each set.')} />
      <Row icon="phoneScreen" title={t('While the phone is locked')} subtitle={t('The watch keeps your session. Actions sync when openGym resumes.')} />
    </Section>
  </>
}
