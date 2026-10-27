import { useEffect, useState } from 'react'
import { garminHeartRate, GARMIN_HR_MAX_AGE, onGarminChange } from '../lib/garmin-sync.js'
import { t } from '../lib/i18n.js'
import Icon from './Icon.jsx'
import { useStore } from '../store/useStore.js'
import { useUI } from '../store/useUI.js'

export default function GarminLiveStatus({ wid, paused }) {
  const [sample, setSample] = useState(() => garminHeartRate(wid))
  useEffect(() => {
    const refresh = () => setSample(garminHeartRate(wid))
    refresh()
    const off = onGarminChange(refresh)
    return off
  }, [wid])
  useEffect(() => {
    if (!sample) return
    const timer = setTimeout(() => setSample(null), Math.max(1, sample.at + GARMIN_HR_MAX_AGE - Date.now() + 1))
    return () => clearTimeout(timer)
  }, [sample])
  if (!sample && !paused) return null
  return <div className="garmin-live" role="status">
    {sample && <span><Icon name="heart" /> {t('Garmin')} · {t('{0} bpm', sample.bpm)}</span>}
    {paused && <><span>{t('Paused on Garmin')}</span><button className="btn ghost" aria-label={t('Resume Garmin workout')} onClick={() => {
      useStore.getState().update(s => { if (s.active?.id === wid) s.active.watchPaused = false })
      useUI.getState().resumeRest()
    }}>{t('Resume')}</button></>}
  </div>
}
