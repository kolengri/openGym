import '../styles/settings-refinement.css'
// First-start permission explanations. iOS Continue always hands off to the OS dialog;
// Android notification setup can be deferred without recording an OS permission answer.
// Already-granted or unsupported steps are skipped by pendingSteps().
import { useEffect, useState } from 'react'
import { useStore } from '../store/useStore.js'
import { t } from '../lib/i18n.js'
import { pendingSteps, markStepSeen } from '../lib/onboarding-perms.js'
import { platformNow } from '../lib/platform-now.js'
import Icon from '../components/Icon.jsx'
import { Button } from '../components/ui.jsx'

// What each step says. Literal t() calls, so check-source-strings sees them; a new step adds its
// own entry here and its check/request in onboarding-perms.js.
const COPY = {
  notifications: () => ({
    icon: 'bell',
    title: t('Never miss the end of a rest'),
    body: t('openGym can tap you on the shoulder when a rest is over, even with the phone locked in your pocket.'),
    lines: [t('Rest timer, right on the lock screen'), t('Training reminders, only if you switch them on')],
  }),
  appleHealth: () => ({
    icon: 'heart',
    title: t('Your workouts in Apple Health'),
    body: t('openGym can save every workout and weigh-in to Apple Health, and your Apple Watch can show your heart rate while you lift.'),
    lines: [t('Workouts and weigh-ins saved to Apple Health'), t('Heart rate per set on your Apple Watch'), t('Switch it off anytime in Settings')],
    foot: t('You can change it anytime in Settings.'),
  }),
}

export default function PermissionSteps() {
  const done = useStore(s => s.finishPermSteps)
  const [steps, setSteps] = useState(null)
  const [i, setI] = useState(0)
  const [busy, setBusy] = useState(false)
  useEffect(() => { pendingSteps().then(setSteps).catch(() => setSteps([])) }, [])
  const step = steps && steps[i]
  useEffect(() => { if (steps && !step) done() }, [steps, step])
  if (!step) return null

  const next = async () => {
    setBusy(true)
    markStepSeen(step.id)
    await Promise.resolve(step.request()).catch(() => false)
    setBusy(false)
    setI(i + 1)
  }
  const canDefer = platformNow() === 'android' && step.id === 'notifications'
  const defer = () => { markStepSeen(step.id); setI(i + 1) }
  const c = (COPY[step.id] || (() => ({ icon: 'info', title: step.id, body: '', lines: [] })))()
  return <div className="narrow guided-refined first-launch-refined">
    <div style={{ fontSize: 54, display: 'flex', justifyContent: 'center', color: 'var(--acc-ink)' }}><Icon name={c.icon} /></div>
    <div className="dim small" style={{ marginTop: 12, textTransform: 'uppercase', letterSpacing: '.06em' }}>{t('One quick thing')}</div>
    <h1 className="t-large" style={{ fontWeight: 700, margin: '6px 0 10px' }}>{c.title}</h1>
    <div className="muted" style={{ lineHeight: 1.5, marginBottom: 18 }}>{c.body}</div>
    <Button variant="primary" disabled={busy} onClick={next}>{t('Continue')}</Button>
    {canDefer && <Button variant="ghost" disabled={busy} onClick={defer}>{t('Not now')}</Button>}
    <details className="settings-disclosure onboarding-details">
      <summary>{t('Details')}</summary>
      <div className="onboarding-benefits">
        {c.lines.map(l => <div key={l} className="row"><Icon name="check" /><span className="small">{l}</span></div>)}
      </div>
    </details>
    <div className="dim small" style={{ marginTop: 18, lineHeight: 1.5 }}>{c.foot || t('You can change it anytime in your phone’s settings.')}</div>
  </div>
}
