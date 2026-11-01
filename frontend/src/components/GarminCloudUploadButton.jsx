import { useEffect, useState } from 'react'
import { Button } from './ui.jsx'
import { useStore } from '../store/useStore.js'
import { t } from '../lib/i18n.js'
import { garminCloudErrorMessage, garminCloudStatus, uploadGarminWorkout } from '../lib/garmin-cloud.js'

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
  const failureCode = error || (job?.status === 'failed' ? job.error || 'upload_failed' : null)
  const upload = async () => {
    setBusy(true); setError(false)
    try { await uploadGarminWorkout(useStore, workout.id, { retry: job?.error === 'unknown_result' }) }
    catch (failure) { setError(failure?.code || 'upload_failed') }
    finally { setBusy(false) }
  }
  return <div style={{ marginTop: 10 }}>
    <Button icon="arrowUp" disabled={done || pending || busy} onClick={upload}>
      {done ? t(job.status === 'duplicate' ? 'Already in Garmin Connect' : 'Uploaded to Garmin Connect')
        : busy || pending ? t('Uploading to Garmin Connect…')
          : job?.status === 'failed' ? t('Retry Garmin upload') : t('Upload to Garmin Connect')}
    </Button>
    {!job && <p className="small muted">{t('Use this for workouts that are not already in Garmin Connect.')}</p>}
    {failureCode && <p className="small muted" role="alert">{t(garminCloudErrorMessage(failureCode))}</p>}
    {job?.error === 'unknown_result' && failureCode !== 'unknown_result' && <p className="small muted" role="alert">
      {t(garminCloudErrorMessage('unknown_result'))}
    </p>}
  </div>
}
