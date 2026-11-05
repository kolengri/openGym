import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useStore } from '../store/useStore.js'
import { effectiveRoutines, effectiveRoutineIds, nextTrainingDay, lastBW, setsDoneActive, setsDone, sessionVolume, workoutDuration } from '../lib/history.js'
import { streakInfo } from '../lib/streak.js'
import { StreakFlame, StreakMeta, StreakParty } from '../components/Streak.jsx'
import { fmtNum, fmtBodyWeight, fmtDate, todayISO, isoOf, weekStartOf, weekDayOffset, DAYS, DAYN, durPart, fmtVol, exCount } from '../lib/format.js'
import { t, tn, dateLocale } from '../lib/i18n.js'
import { bwSheet, goalSheet, dayOverrideSheet, calendarSheet, startFlow, starterPlanSheet, bwDeltaColor, weighInsSheet, workoutDetailSheet, menuSheet } from '../sheets.jsx'
import LineChart from '../components/LineChart.jsx'
import Icon from '../components/Icon.jsx'
import CardHead from '../components/CardHead.jsx'
import QueueRow from '../components/QueueRow.jsx'
import MiniBodyMap from '../components/MiniBodyMap.jsx'
import { queueOf, queueView, weekTally, pinState } from '../lib/queue.js'
import { workoutsLeft } from '../lib/week-left.js'
import { WeeklySetsHomeLine } from '../components/WeeklySets.jsx'
import { RecapHomeCard } from '../components/Recap.jsx'
import { scheduleModeOf } from '../lib/rotation.js'
import { useConnectionTrouble } from '../components/SyncBanner.jsx'
import { Button } from '../components/ui.jsx'
import { tappable } from '../lib/use-sheet-keyboard.js'
import { dayNoteOf } from '../lib/day-notes.js'
import { weighInAt } from '../lib/bodyweight.js'
import WeightRate from '../components/WeightRate.jsx'
import { programmeChip } from '../lib/programmes.js'
import { SeasonDeco } from '../components/Seasonal.jsx'
import { WrappedHomeCard } from '../components/WrappedEntry.jsx'
import RecoveryHint from '../components/RecoveryHint.jsx'
import { ChallengesCard } from '../components/Challenges.jsx'
import { isOn } from '../lib/modules.js'
import '../styles/planning-refinement.css'

// Home = what to do now + a quick glance. Deep charts & history live in Stats.
export default function Home() {
  const nav = useNavigate()
  const S = useStore(s => s.S)
  const user = useStore(s => s.user)
  // The banner switched off and the sync stuck: a dot on the gear (Settings → Show connection status).
  const trouble = useConnectionTrouble()
  const [weekOffset, setWeekOffset] = useState(0)
  const [motivationOpen, setMotivationOpen] = useState(() => {
    try { return localStorage.getItem('gym_home_motivation_open') === 'true' } catch { return false }
  })

  const today = new Date()
  // A weekday can hold several routines. `todayRoutines` is the whole day; `routine` is the
  // first, kept for the one-routine glyph. The derived session name joins them (§9).
  const todayRoutines = effectiveRoutines(S, todayISO())
  const routine = todayRoutines[0] || null
  const todayName = todayRoutines.map(r => r.name).join(' + ')
  // A fulfilled pin (a coach session pinned to today and since done) reads as no override.
  const todayOvr = S.dayPlan[todayISO()] !== undefined && pinState(S, S.dayPlan[todayISO()]) !== 'done'
  // An open editor on a saved workout (lib/session-edit.js) holds S.active too, but it is not a
  // session in progress: the row takes you back to it as an edit, the way the tab bar does.
  const editingSaved = !!S.active?.editingWorkoutId
  const bw = lastBW(S)
  const prevBW = S.bodyweight.length > 1 ? S.bodyweight[S.bodyweight.length - 2] : null
  const delta = bw && prevBW ? bw.w - prevBW.w : null

  const ws = weekStartOf(S)
  // The first day of the shown week. Named for the role, not for Monday — which day that is
  // is the setting.
  const wkStart = new Date(today)
  wkStart.setDate(today.getDate() - weekDayOffset(today.getDay(), ws) + weekOffset * 7)
  const doneDays = new Set(S.workouts.map(w => w.d))
  // The last session logged for today, if any — what the row below reports instead of asking
  // you to start the one you already did. Last wins, so a second session names itself. Only once
  // today's plan is covered, though: a freestyle session on a planned day, or the rotation's
  // first session done when its next one is today's too, leaves the row offering what is still
  // to do, as Start and the progress row already do. A queue session is never "covered" by an
  // earlier workout: the queue only names one it does not count as done yet.
  const loggedToday = S.workouts.filter(w => w.d === todayISO())
  const queueIds = queueOf(S)?.ids || []
  const coveredToday = id => !queueIds.includes(id) && loggedToday.some(w => (Array.isArray(w.routineIds) ? w.routineIds : [w.routineId]).includes(id))
  const doneToday = (todayRoutines.every(r => coveredToday(r.id)) && loggedToday.at(-1)) || null
  const strip = []
  for (let i = 0; i < 7; i++) {
    const d = new Date(wkStart); d.setDate(wkStart.getDate() + i)
    const iso = isoOf(d)
    const eff = effectiveRoutineIds(S, iso).length > 0, ovr = S.dayPlan[iso] !== undefined, done = doneDays.has(iso)
    // A day off with a note (#261) reads as excused, not as a plan that went by.
    const dot = done ? ' done' : dayNoteOf(S, iso) ? ' noted' : ovr && eff ? ' ovr' : eff ? ' plan' : ''
    strip.push(<div key={i} className={'wday' + (iso === todayISO() ? ' today' : '')} aria-label={fmtDate(iso) + ' · ' + (done ? t('Workout done') : eff ? t('Planned') : t('Rest day'))} aria-current={iso === todayISO() ? 'date' : undefined} {...tappable(() => dayOverrideSheet(iso))}>
      <div className="lbl">{t(DAYS[d.getDay()])}</div><div className="num">{d.getDate()}</div><div className={'dot' + dot} /></div>)
  }
  const wkEnd = new Date(wkStart); wkEnd.setDate(wkStart.getDate() + 6)
  const wkLabel = weekOffset === 0 ? t('This week') : `${wkStart.getDate()} ${wkStart.toLocaleDateString(dateLocale(), { month: 'short' })} – ${wkEnd.getDate()} ${wkEnd.toLocaleDateString(dateLocale(), { month: 'short' })}`

  // A coach week (S.queue) read through the same tolerant reader QueueRow uses, so a malformed
  // queue from another client shows the weekday dots, never an empty card.
  const queue = queueView(S, todayISO())
  // This card shows one thing or the other — QueueRow for a live queue, or Rotation chosen with
  // nothing built yet (S.scheduleMode), in which case there is no queue for QueueRow to render and
  // an empty-state card takes its place. Plan does the same in rotation mode: no weekday grid, only
  // the days that add a routine the loop does not have (Plan.jsx, "Also on fixed days").
  const rotating = scheduleModeOf(S) === 'rotation'
  // A planner-written queue (no rotationId) still names its weekday when it hasn't started yet —
  // that copy predates rotation and stays as it is. Our own rotation has no weekday of its own
  // (lib/rotation.js): naming one here — including on the pass's own one-day empty gap (THE
  // ONE-DAY BOUNDARY, rotation.js) or before a first routine is even added — would be the
  // fixed-week model leaking into a schedule that was never weekday-based.
  const liveQ = queueOf(S)
  const plannerQueue = !!queue && !liveQ?.rotationId
  // Ownership, not mere presence of a rotationId: a stale id left over from a rebuilt rotation
  // would otherwise still read as "this app manages it" (lib/rotation.js).
  const managedQueue = !!liveQ && !!S.rotation && liveQ.rotationId === S.rotation.id
  // Keep the next fixed session in view, including after today has been completed.
  const next = !S.active && !(rotating && !plannerQueue) ? nextTrainingDay(S, todayISO()) : null
  // The streak card's fraction: this calendar week's workouts over the weekdays with a plan, or,
  // in a coach week, the queue's sessions and your own days together (lib/queue.js weekTally).
  const tally = weekTally(S, todayISO())
  const { done: doneThisWeek, planned: plannedPerWeek } = tally
  const left = workoutsLeft(S, todayISO())
  // The streak with its best run and freezes (lib/streak.js), read back from the workouts.
  const todayKey = todayISO()
  const streak = useMemo(() => streakInfo(S, todayKey), [S.workouts, S.weekStart, todayKey]) // eslint-disable-line react-hooks/exhaustive-deps
  // Settings → Modules (lib/modules.js): what a module switched off hides here.
  const on = id => isOn(S, id)
  const bwPoints = S.bodyweight.slice(-30).map(b => ({ t: weighInAt(b), y: b.w, d: b.d }))

  // today's session shown right under the week strip
  const onToday = () => { if (S.active) nav('/workout'); else if (doneToday) workoutDetailSheet(doneToday); else if (todayRoutines.length) startFlow(effectiveRoutineIds(S, todayISO())); else nav('/workout') }
  // A chip on the coach week's progress row starts that one routine, in any order. A session
  // already in progress wins, as on the today row — starting another would overwrite it.
  const progChip = programmeChip(S)
  const onQueueStart = id => { if (S.active) nav('/workout'); else startFlow([id]) }

  return <div className="narrow planning-home">
    <div className="hdr">
      <SeasonDeco spot="header-bats" />
      <div><h1>{user ? t('Hi {0}', user.name) : 'openGym'}</h1><div className="sub">{weekOffset ? wkLabel : today.toLocaleDateString(dateLocale(), { weekday: 'long', day: 'numeric', month: 'long' })}</div></div>
      <div className="row planning-home-header-actions">
        {!rotating && <button type="button" className="iconbtn" aria-label={wkLabel} aria-haspopup="dialog" onClick={() => menuSheet({ title: wkLabel, items: [
          { icon: 'chevronLeft', label: t('Previous week'), onClick: () => setWeekOffset(w => w - 1) },
          { icon: 'chevronRight', label: t('Next week'), onClick: () => setWeekOffset(w => w + 1) },
        ] })}><Icon name="calendar" /></button>}
      <button className="iconbtn" data-tour="settings-gear" onClick={() => nav('/settings')} aria-label={trouble ? t('Settings') + ', ' + t('Connection problem') : t('Settings')}><Icon name="gear" />{trouble && <span className="tab-dot" aria-hidden="true" />}</button>
      </div>
    </div>

    <div className="planning-calendar">
      {/* A coach week runs by order, not by weekday, so its progress row stands in for the
          seven dots (components/QueueRow.jsx). The today row below stays as it is: the queue's
          next session reaches it through effectiveRoutineIds like any planned routine. */}
      {rotating ? (queue ? <QueueRow S={S} today={todayISO()} onStart={onQueueStart} managed={managedQueue} /> : <div className="empty">
        {t('No rotation yet. Add routines to it in Plan.')}
        <div style={{ marginTop: 10 }}><Button size="sm" variant="tinted" onClick={() => nav('/plan')}>{t('Set up in Plan')}</Button></div>
      </div>) : <>
        <div className="week">{strip}</div>
      </>}
      {/* The week's plan as a countdown (#753, lib/week-left.js): "2 of 4 left this week". */}
      {left && <div className={'small dim wkleft' + (left.left > 0 ? '' : ' done')}>
        {left.left > 0 ? tn('{0} of {1} left this week', '{0} of {1} left this week', left.left, left.of) : t('All done this week. Nice.')}
      </div>}
    </div>

    <section className="planning-today">
      <div className="row between planning-today-heading">
        <h4 className="sec">{t('Today')}</h4>
        {!S.active && <button type="button" className="iconbtn" onClick={() => nav('/workout')} aria-label={t('Choose a different workout')} title={t('Choose a different workout')}>
          <Icon name="swap" /><span className="sr-only">{t('Choose a different workout')}</span>
        </button>}
      </div>
      {progChip && <button type="button" className="chip ichip prog-chip" onClick={() => nav('/plan/programmes')}><Icon name="calendar" /><span>{progChip}</span></button>}
      <button type="button" className="today-row" data-tour="today" onClick={onToday}>
        <span className={'planning-today-status' + (doneToday && !S.active ? ' is-done' : '')}>
          <Icon name={S.active ? (editingSaved ? 'pencil' : 'play') : doneToday ? 'checkCircle' : routine ? 'calendar' : 'moon'} />
          <span className="tag">{S.active ? (editingSaved ? t('Edit') : t('Resume')) : doneToday ? t('Done') : routine ? t('Start') : t('Rest day')}</span>
          {!S.active && !doneToday && routine && <MiniBodyMap routines={todayRoutines} body={S.body} />}
        </span>
        <span className="ttl">{S.active ? S.active.name : doneToday ? doneToday.name || t('Workout done') : routine ? todayName : t('Rest day')}</span>
        <span className="planning-today-meta">{S.active
          ? tn('{0} set', '{0} sets', setsDoneActive(S.active))
          : doneToday ? [durPart(workoutDuration(doneToday)).join(''), tn('{0} set', '{0} sets', setsDone(doneToday)), fmtVol(sessionVolume(doneToday, S), S.unit)].filter(Boolean).join(' · ')
          : routine ? exCount(todayRoutines.reduce((n, r) => n + r.ex.length, 0)) + (todayOvr ? ' · ' + t('rescheduled') : '') : t('Choose a different workout')}</span>
        <span className="planning-today-action">{S.active ? (editingSaved ? t('Edit') : t('Resume')) : doneToday ? t('Open workout') : routine ? t('Start') : t('Choose a different workout')}</span>
      </button>
      <SeasonDeco spot="home-hero" />
    </section>

    {next && <button type="button" className="item planning-next" onClick={() => dayOverrideSheet(next.iso)}>
      <span className="lrow-i"><Icon name="calendar" /></span>
      <span className="grow"><span className="tt">{t('Next session: {0}, {1}', t(DAYN[next.weekday]), next.routines.map(r => r.name).join(' + '))}</span><span className="ss">{exCount(next.routines.reduce((n, r) => n + r.ex.length, 0))}</span></span>
      <Icon name="chevronRight" className="chev" />
    </button>}

    <button type="button" className="item planning-history" onClick={() => nav('/history')}>
      <span className="lrow-i"><Icon name="history" /></span>
      <span className="grow"><span className="tt">{t('History')}</span><span className="ss">{tn('{0} workout total', '{0} workouts total', S.workouts.length)}</span></span>
      <Icon name="chevronRight" className="chev" />
    </button>

    {!S.routines.length && !S.active && (
      <div className="card">
        <CardHead icon="calendar" title={t('Welcome!')} sub={t('Set up your weekly routine to get going, or grab a ready-made starter plan.')} />
        <Button variant="primary" icon="clipboard" onClick={starterPlanSheet}>{t('Load starter plan')}</Button>
        <div style={{ height: 8 }} /><Button onClick={() => nav('/plan')}>{t('Build my own plan')}</Button>
      </div>
    )}

    {on('body') && S.showWeightCard !== false && <div className="planning-weight-row">
      <details className="planning-weight">
        <summary className="bw-head">
          <span className="lrow-i"><Icon name="scale" /></span>
          <span className="grow"><span className="card-head-title">{t('Body weight')}</span>
            {bw && <span className="ss">{fmtBodyWeight(bw.w)} {S.unit}{delta ? ' · ' + (delta > 0 ? '+' : '−') + fmtBodyWeight(Math.abs(delta)) : ''}</span>}
          </span>
          <Icon name="chevronDown" className="planning-fold-chevron" />
        </summary>
        <div className="planning-weight-detail">
      {bw ? <>
        <div className="row" style={{ gap: 8, alignItems: 'baseline' }}>
          <div className="big">{fmtBodyWeight(bw.w)} <span className="muted" style={{ fontSize: 'var(--fs-callout)' }}>{S.unit}</span></div>
          {/* only when it actually moved — an unchanged weight used to read as "− 0" */}
          {!!delta && (
            <span className="small row" style={{ gap: 2, fontWeight: 500, color: bwDeltaColor(delta, bw.w) }}>
              <Icon name={delta > 0 ? 'arrowUp' : 'arrowDown'} style={{ fontSize: 'var(--fs-caption)' }} />
              {fmtBodyWeight(Math.abs(delta))}
            </span>
          )}
          <span className="dim small" style={{ marginInlineStart: 'auto' }}>{fmtDate(bw.d, true)}</span>
        </div>
        {S.targetW && (
          <div className="small row" style={{ color: 'var(--gold-ink)', marginTop: 4, gap: 5 }}>
            <Icon name="target" style={{ fontSize: 'var(--fs-footnote)' }} />
            <span>{t('Goal')} {fmtBodyWeight(S.targetW)} {S.unit} · {Math.abs(S.targetW - bw.w) < 0.05 ? t('reached!') : t(S.targetW > bw.w ? '{0} to gain' : '{0} to lose', fmtBodyWeight(Math.abs(S.targetW - bw.w)) + ' ' + S.unit)}</span>
          </div>
        )}
        <div className="chart" style={{ marginTop: 8 }}><LineChart formatValue={fmtBodyWeight} points={bwPoints} h={130} unit={S.unit} goal={S.targetW} /></div>
        {/* the weekly rate and, with one set, how it sits in its corridor (#759) */}
        <WeightRate S={S} />
        {/* every weigh-in, week by week with its average (Discord 'Weight') */}
        <div className="row between" style={{ marginTop: 4 }}>
          <Button size="sm" variant="ghost" icon="target" className="bw-goal" style={S.targetW ? { color: 'var(--gold-ink)' } : undefined} onClick={goalSheet}>{S.targetW ? fmtNum(S.targetW) : t('Goal')}</Button>
          <Button size="sm" variant="ghost" trailingIcon="chevronRight" data-tour="home-weighins" onClick={weighInsSheet}>{t('All weigh-ins')}</Button>
        </div>
      </> : <>
        <div className="muted small">{S.weighIn === false
          ? t('No weigh-ins yet. Log your weight to start the curve.')
          : t("No weigh-ins yet. Log your weight to start the curve (we also ask before every workout).")}</div>
        <Button size="sm" variant="ghost" icon="target" className="bw-goal" style={{ marginTop: 6, ...(S.targetW ? { color: 'var(--gold-ink)' } : {}) }} onClick={goalSheet}>{S.targetW ? fmtNum(S.targetW) : t('Goal')}</Button>
      </>}
        </div>
      </details>
      <Button size="sm" variant="ghost" icon="plus" className="planning-weight-log" onClick={() => bwSheet()}>{t('Log')}</Button>
    </div>}

    {/* Jump to the gym check-in cards (QR membership codes). Shown here as a quick tap on
        arrival at the gym; folds away per user via the "Gym check-in" switch in Settings. */}
    {on('checkin') && (
      <div className="card tap-host checkin-card">
        <CardHead icon="qr" eyebrow={t('At the gym')} title={t('Check in')} open={{ onClick: () => nav('/checkin') }}
          action={<Icon name="chevronRight" className="chev" />} />
      </div>
    )}

    {/* Recovery shares the quieter activity area beneath the training plan. */}
    {on('health') && <RecoveryHint S={S} />}

    <SeasonDeco spot="home-advent" />

    {/* The streak opens its calendar from its text (CardHead open); the weekly-sets line and the
        party banner are buttons of their own beside it, not inside a card that is a button. */}
    {on('motivation') ? <details className="planning-fold home-motivation" open={motivationOpen} onToggle={event => {
      const open = event.currentTarget.open
      setMotivationOpen(open)
      try { localStorage.setItem('gym_home_motivation_open', String(open)) } catch { /* private mode: disclosure still works */ }
    }}>
      <summary><Icon name="flame" /><span className="grow">{t('Motivation')}<span className="ss">{t('{0} week streak', streak.current)}</span></span><Icon name="chevronDown" className="planning-fold-chevron" /></summary>
      <div className="planning-fold-content">
        <RecapHomeCard S={S} />
        <WrappedHomeCard S={S} />
        <ChallengesCard S={S} />
        <div className="card tap-host streak-card">
          <SeasonDeco spot="home-streak" />
          {/* in season, a Santa hat on the flame (components/Seasonal.jsx) */}
          <CardHead className="streak-head" glyph={<span className="streak-flame-wrap"><StreakFlame lit={streak.current > 0} /><SeasonDeco spot="streak-flame" /></span>}
            title={t('{0} week streak', streak.current)} open={{ onClick: () => calendarSheet(), haspopup: 'dialog' }}
            sub={<>{doneThisWeek}{plannedPerWeek ? ' / ' + plannedPerWeek : ''} {t('this week')} · {tn('{0} workout total', '{0} workouts total', S.workouts.length)}</>}
            action={<Icon name="calendar" className="chev" style={{ fontSize: 'var(--fs-title3)' }} />} />
          {(streak.best > 0 || streak.freezes > 0) && <div className="muted small card-head-indent streak-meta-line"><StreakMeta info={streak} /></div>}
          <StreakParty S={S} info={streak} tally={tally} />
          {/* Settings → Look & Home → Weekly sets on Home (lib/muscle-targets.js): the muscle with
              the most room this week, one tap from the Stats card. */}
          {/* Straight to Stats → Lifts, where the card is, not to the top of Overview (P5 deep link). */}
          {S.homeMuscleSets === true && <WeeklySetsHomeLine S={S} onOpen={() => nav('/stats?section=lifts')} />}
        </div>
      </div>
    </details>
      // Motivation off: no streak card, but the weekly sets line it carried keeps a card of its own.
      : S.homeMuscleSets === true && <div className="card wsets-solo"><WeeklySetsHomeLine S={S} onOpen={() => nav('/stats?section=lifts')} /></div>}
  </div>
}
