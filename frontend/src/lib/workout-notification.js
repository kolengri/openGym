// Android uses the rest timer's foreground service for the whole workout. Metadata changes
// update its existing card; the native alarm and Chronometer keep timers independent of JS.
import { MOBILE, nativePlatform } from './mobile.js'
import { buildLiveActivity } from './live-activity.js'
import { accentValue } from './accent.js'
import { accentColors, armRestAlert, disarmRestAlert, updateWorkoutNotification } from './rest-alert.js'
import { restSoundOf } from './rest-sounds.js'
import { t } from './i18n.js'

export function buildWorkoutNotification(S) {
  const A = S?.active
  if (!A || A.editingWorkoutId) return null
  // Reuse the workout's superset order, localized exercise names and target/set formatting.
  const live = buildLiveActivity(S)
  const state = live?.state
  return {
    wid: String(A.id || ''),
    title: A.name || t('Workout'),
    exercise: state?.cur?.exName || '',
    detail: [state?.cur?.setLine, state?.cur?.target].filter(Boolean).join(' · '),
    done: state?.done || 0,
    total: state?.total || 0,
    ...accentColors(accentValue(S)),
  }
}

export async function startWorkoutNotificationSync({ useStore, useUI }) {
  if (!MOBILE || await nativePlatform() !== 'android') return () => {}
  let last = null, workEnd = null
  const send = (reconcile = false) => {
    const { S, ready } = useStore.getState()
    // Boot restores the private phone copy asynchronously; an empty copy must not end it.
    if (!ready) return
    const snapshot = buildWorkoutNotification(S)
    const json = JSON.stringify(snapshot)
    if (json === last && !reconcile) return
    last = json
    const timer = useUI.getState().timer
    updateWorkoutNotification(snapshot ? { ...snapshot, reconcile, hasRest: !!timer && !timer.ready } : null)
      .then(ok => { if (!ok && last === json) last = null })
  }
  const syncWork = () => {
    if (!useStore.getState().ready) return
    const { S } = useStore.getState()
    const work = S.active && !S.active.editingWorkoutId ? useUI.getState().work : null
    const end = work?.endsAt || null
    if (end === workEnd) return
    const previous = workEnd
    workEnd = end
    if (end > Date.now()) {
      armRestAlert(end, {
        title: work.label || t('Workout'), countdownTitle: work.label || t('Workout'),
        totalSec: work.total, controls: false, accent: accentValue(S),
        sound: !!S.sound, tone: restSoundOf(S), vibrate: S.vibrate !== false,
        alarmBuzz: S.vibrate !== false && !!S.vibrateOnSilent,
      })
    } else if (previous) disarmRestAlert()
  }
  const offStore = useStore.subscribe(() => { send(); syncWork() })
  const offUI = useUI.subscribe((s, prev) => { if (s.work !== prev.work) syncWork() })
  const onVisible = () => { if (document.visibilityState === 'visible') send(true) }
  document.addEventListener('visibilitychange', onVisible)
  send(true); syncWork()
  return () => { offStore(); offUI(); document.removeEventListener('visibilitychange', onVisible) }
}
