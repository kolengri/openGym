import '../styles/settings-refinement.css'
import { useEffect, useState } from 'react'
import { Button, Row, Section, Switch } from './ui.jsx'
import { useStore } from '../store/useStore.js'
import { t } from '../lib/i18n.js'
import { connectGarminCloud, disconnectGarminCloud, garminCloudErrorMessage, garminCloudStatus } from '../lib/garmin-cloud.js'
import GarminHealthSettings from './GarminHealthSettings.jsx'
import { isOn } from '../lib/modules.js'

export default function GarminCloudSettings() {
  const state = useStore(s => s.S)
  const [status, setStatus] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(false)
  const [statusAttempt, setStatusAttempt] = useState(0)
  useEffect(() => { let stopped = false; garminCloudStatus().then(s => { if (!stopped) setStatus(s) }); return () => { stopped = true } }, [statusAttempt])
  if (!status?.available) return null
  const linked = status.connected && status.sessionId === state.garminCloudSessionId
  const expired = linked && status.authState === 'expired' && status.renewalAvailable !== true
  const connected = linked && !expired
  const saveSettings = async () => {
    try { await useStore.getState().saveNow() }
    catch { throw Object.assign(new Error('Garmin settings could not be saved.'), { code: 'storage_error' }) }
  }
  const connect = async () => {
    const owner = useStore.getState().user?.id ?? null
    const session = useStore.getState().S.garminCloudSessionId
    let valid = true
    const stopGuard = useStore.subscribe((current, previous) => {
      if ((current.user?.id ?? null) !== (previous.user?.id ?? null) || current.S.garminCloudSessionId !== previous.S.garminCloudSessionId) valid = false
    })
    const belongs = () => valid && (useStore.getState().user?.id ?? null) === owner && useStore.getState().S.garminCloudSessionId === session
    setBusy(true); setError(false)
    try {
      const result = await connectGarminCloud()
      if (!belongs()) { await disconnectGarminCloud(); return }
      if (!result.connected || !result.sessionId) throw Object.assign(new Error('Sign-in was not completed.'), { code: 'auth_incomplete' })
      useStore.getState().update(s => { s.garminCloudSessionId = result.sessionId; s.garminCloudAuto = false })
      await saveSettings()
      if ((useStore.getState().user?.id ?? null) === owner && useStore.getState().S.garminCloudSessionId === result.sessionId) setStatus({ ...result, available: true })
    } catch (failure) { setError(failure?.code || 'upload_failed') }
    finally { stopGuard(); setBusy(false) }
  }
  const disconnect = async () => {
    setBusy(true); setError(false)
    try {
      await disconnectGarminCloud()
      useStore.getState().update(s => { s.garminCloudAuto = false; delete s.garminCloudSessionId })
      await saveSettings()
      setStatus({ available: true, connected: false })
    } catch (failure) { setError(failure?.code || 'upload_failed') }
    finally { setBusy(false) }
  }
  return <>
  <Section className="garmin-cloud-settings" title={t('Garmin Connect uploads')}>
    <Row icon="cloud" title="Garmin Connect" subtitle={status.error
      ? t('The local Garmin upload journal needs attention. Reconnecting cannot reset its duplicate protection.')
      : expired ? t(garminCloudErrorMessage('auth_expired'))
        : linked && status.authState === 'unknown' ? t('Garmin session expiration could not be checked.')
          : t(connected ? 'Connected to Garmin Connect' : 'Garmin Connect is not connected')} />
    {(status.error || !connected) && <div className="garmin-actions">
    {status.error && <Button onClick={() => setStatusAttempt(value => value + 1)}>{t('Retry')}</Button>}
    {!connected && !status.error && <Button variant="primary" disabled={busy || !!state.active} onClick={connect}>{t('Sign in to Garmin Connect')}</Button>}
    </div>}
    {error && <p className="small muted" role="alert">{t(garminCloudErrorMessage(error))}</p>}
    <Row title={t('Upload new workouts automatically')} subtitle={(!connected || !!state.active || busy) ? t('Automatic upload is available after signing in. Change this setting between workouts.') : undefined}>
      <Switch aria-label={t('Upload new workouts automatically')} checked={state.garminCloudAuto === true} disabled={!connected || !!state.active || busy}
        onChange={value => useStore.getState().update(s => { s.garminCloudAuto = value })} />
    </Row>
    <div className="garmin-help">
    <p className="small muted">{t('When enabled, openGym uploads completed workouts to Garmin Connect and stops separate FIT recording on the watch to avoid duplicate activities. Garmin may forward uploads to linked services such as Strava.')}</p>
    <details className="settings-disclosure">
      <summary>{t('Advanced')}</summary>
    {linked && <div className="garmin-account-actions">
      <Button disabled={busy || !!state.active} onClick={disconnect}>{t('Disconnect Garmin Connect')}</Button>
    </div>}
    <p className="small muted">{t('Sign in on Garmin’s own page. openGym keeps the resulting session only on this phone.')}</p>
    <p className="small muted">{t('Garmin Connect uploads use your Strava weight-sharing preference. Sensor recordings from other apps are unchanged.')}</p>
    <p className="small muted">{t('Heart-rate samples received from the watch are included. Bluetooth or sleeping-phone gaps are not reconstructed.')}</p>
    </details>
    </div>
  </Section>
    {isOn(state, 'health') ? <GarminHealthSettings connected={connected} onStatusChange={() => setStatusAttempt(value => value + 1)} />
      : <p className="small muted">{t('{0} stops syncing while Health is off. Nothing is disconnected, and it catches up once Health is back.', 'Garmin Connect')}</p>}
  </>
}
