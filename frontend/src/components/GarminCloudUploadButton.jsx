import { useEffect, useState } from 'react'
import { Button } from './ui.jsx'
import { useStore } from '../store/useStore.js'
import { t } from '../lib/i18n.js'
import { garminCloudStatus, uploadGarminWorkout } from '../lib/garmin-cloud.js'

export default function GarminCloudUploadButton({ workout }) {
  const state = useStore(s => s.S)
  const [available, setAvailable] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(false)
  useEffect(() => {
    let stopped = false
    garminCloudStatus().then(s => { if (!stopped) setAvailable(s.available === true) })
    return () => { stopped = true }
  }, [])
  if (!available || typeof workout.id !== 'string' || !workout.id) return null
  const job = state.workouts.find(w => w.id === workout.id)?.garminCloudUpload
  const done = ['uploaded', 'duplicate'].includes(job?.status)
  const pending = job?.status === 'uploading'
  const upload = async () => {
    setBusy(true); setError(false)
    try { await uploadGarminWorkout(useStore, workout.id, { retry: job?.error === 'unknown_result' }) }
    catch { setError(true) }
    finally { setBusy(false) }
  }
  return <div style={{ marginTop: 10 }}>
    <Button icon="arrowUp" disabled={done || pending || busy} onClick={upload}>
      {done ? t(job.status === 'duplicate' ? 'Already in Garmin Connect' : 'Uploaded to Garmin Connect')
        : busy || pending ? t('Uploading to Garmin Connect…')
          : job?.status === 'failed' ? t('Retry Garmin upload') : t('Upload to Garmin Connect')}
    </Button>
    {!job && <p className="small muted">{t('Use this for workouts that are not already in Garmin Connect.')}</p>}
    {(error || job?.status === 'failed') && <p className="small muted" role="alert">
      {job?.error === 'unknown_result' ? t('Garmin may already have received this workout. Check Connect before retrying.')
        : ['session_changed', 'content_changed'].includes(job?.error) ? t('This workout has a receipt from another connection or different file. Check Garmin Connect; automatic replay is blocked.')
          : ['receipt_limit', 'storage_unavailable'].includes(job?.error) ? t('The local Garmin upload journal needs attention. Reconnecting cannot reset its duplicate protection.')
        : !state.garminCloudSessionId ? t('Connect Garmin in Settings before uploading.') : t('Garmin upload failed. Reconnect or retry.')}
    </p>}
  </div>
}
