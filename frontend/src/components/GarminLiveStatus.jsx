import { useEffect, useState } from 'react'
import { garminConnection, garminStatus, onGarminChange } from '../lib/garmin-sync.js'
import { t } from '../lib/i18n.js'
import { fmtAgo } from '../lib/format.js'
import Icon from './Icon.jsx'
import { useStore } from '../store/useStore.js'
import { useUI } from '../store/useUI.js'
import './GarminLiveStatus.css'

export function GarminConnectionDetails({ connection }) {
  if (!connection?.enabled) return null
  const label = !connection.connected ? 'Watch disconnected. Actions will sync after reconnection.'
    : !connection.installed ? 'Install the openGym companion on your watch, then connect below.'
      : !connection.replying ? connection.lastMessageAt ? 'Watch app is not responding' : 'Waiting for openGym on the watch'
        : !connection.hasWorkout ? 'Watch app connected'
          : connection.confirmed ? 'Workout confirmed on the watch' : 'Waiting for workout confirmation'
  return <div className="garmin-connection-details">
    <strong>{t(label)}</strong>
    <span>{connection.lastMessageAt ? t('Last watch reply: {0}', fmtAgo(connection.lastMessageAt)) : t('No watch reply yet')}</span>
    {connection.lastConfirmedAt > 0 && <span>{t('Last workout confirmation: {0}', fmtAgo(connection.lastConfirmedAt))}</span>}
    {connection.watchPending > 0 && <span>{t('{0} commands waiting on the watch', connection.watchPending)}</span>}
    {connection.phonePending > 0 && <span>{t('{0} commands waiting on the phone', connection.phonePending)}</span>}
    {connection.error && <span>{t('Garmin link error')}</span>}
  </div>
}

export default function GarminLiveStatus({ wid, paused }) {
  const [, tick] = useState(0)
  useEffect(() => {
    let gone = false, reading = false
    const read = async () => {
      if (reading) return
      reading = true
      try { await garminStatus() } catch { /* Last known status remains visible. */ }
      finally { reading = false; if (!gone) tick(n => n + 1) }
    }
    read()
    const off = onGarminChange(() => { if (!gone) tick(n => n + 1) })
    const refresh = setInterval(read, 4000)
    const clock = setInterval(() => tick(n => n + 1), 1000)
    return () => { gone = true; off(); clearInterval(refresh); clearInterval(clock) }
  }, [wid])
  const connection = garminConnection(wid)
  const sample = connection.sample
  if (!connection.enabled && !sample && !paused) return null
  return <div className="garmin-live" role="status" aria-label={t('Garmin connection')}>
    <GarminConnectionDetails connection={connection} />
    <span><Icon name="heart" /> {sample ? t('{0} bpm', sample.bpm)
      : t(connection.hadSample ? 'Heart rate data is stale' : 'Heart rate unavailable')}</span>
    {!sample && connection.replying && <small>{t('Open openGym on the watch and wear it snugly to receive heart rate.')}</small>}
    {paused && <><span>{t('Paused on Garmin')}</span><button className="btn ghost" aria-label={t('Resume Garmin workout')} onClick={() => {
      useStore.getState().update(s => { if (s.active?.id === wid) s.active.watchPaused = false })
      useUI.getState().resumeRest()
    }}>{t('Resume')}</button></>}
  </div>
}
