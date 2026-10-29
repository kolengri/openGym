import { useEffect, useState } from 'react'
import { Button, Row, Section, Switch } from './ui.jsx'
import { useStore } from '../store/useStore.js'
import { t } from '../lib/i18n.js'
import { connectGarminCloud, disconnectGarminCloud, garminCloudStatus } from '../lib/garmin-cloud.js'
import GarminHealthSettings from './GarminHealthSettings.jsx'

export default function GarminCloudSettings() {
  const state = useStore(s => s.S)
  const [status, setStatus] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(false)
  const [statusAttempt, setStatusAttempt] = useState(0)
  useEffect(() => { let stopped = false; garminCloudStatus().then(s => { if (!stopped) setStatus(s) }); return () => { stopped = true } }, [statusAttempt])
  if (!status?.available) return null
  const connected = status.connected && status.sessionId === state.garminCloudSessionId
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
      if (!result.connected || !result.sessionId) throw new Error('Sign-in was not completed.')
      useStore.getState().update(s => { s.garminCloudSessionId = result.sessionId; s.garminCloudAuto = false })
      await useStore.getState().saveNow()
      if ((useStore.getState().user?.id ?? null) === owner && useStore.getState().S.garminCloudSessionId === result.sessionId) setStatus({ ...result, available: true })
    } catch { setError(true) }
    finally { stopGuard(); setBusy(false) }
  }
  const disconnect = async () => {
    setBusy(true); setError(false)
    try {
      await disconnectGarminCloud()
      useStore.getState().update(s => { s.garminCloudAuto = false; delete s.garminCloudSessionId })
      await useStore.getState().saveNow()
      setStatus({ available: true, connected: false })
    } catch { setError(true) }
    finally { setBusy(false) }
  }
  return <Section className="garmin-cloud-settings" title={t('Garmin Connect uploads')} footer={t('Sign in on Garmin’s own page. openGym keeps the resulting session only on this phone.')}>
    <Row icon="watch" title="Garmin Connect" subtitle={status.error
      ? t('The local Garmin upload journal needs attention. Reconnecting cannot reset its duplicate protection.')
      : t(connected ? 'Connected to Garmin Connect' : 'Garmin Connect is not connected')} />
    <div className="garmin-actions">
    {status.error && <Button onClick={() => setStatusAttempt(value => value + 1)}>{t('Retry')}</Button>}
    {!connected && !status.error && <Button disabled={busy || !!state.active} onClick={connect}>{t('Sign in to Garmin Connect')}</Button>}
    {connected && <Button disabled={busy || !!state.active} onClick={disconnect}>{t('Disconnect Garmin Connect')}</Button>}
    </div>
    <Row title={t('Upload new workouts automatically')} subtitle={t('Automatic upload is available after signing in. Change this setting between workouts.')}>
      <Switch aria-label={t('Upload new workouts automatically')} checked={state.garminCloudAuto === true} disabled={!connected || !!state.active || busy}
        onChange={value => useStore.getState().update(s => { s.garminCloudAuto = value })} />
    </Row>
    <div className="garmin-help">
    <p className="small muted">{t('When enabled, openGym uploads completed workouts to Garmin Connect and stops separate FIT recording on the watch to avoid duplicate activities. Garmin may forward uploads to linked services such as Strava.')}</p>
    <p className="small muted">{t('Garmin Connect uploads use your Strava weight-sharing preference. Sensor recordings from other apps are unchanged.')}</p>
    <p className="small muted">{t('Heart-rate samples received from the watch are included. Bluetooth or sleeping-phone gaps are not reconstructed.')}</p>
    {error && <p className="small muted" role="alert">{t('Garmin upload failed. Reconnect or retry.')}</p>}
    </div>
    <GarminHealthSettings connected={connected} />
  </Section>
}
