import '../styles/progress-refinement.css'
import { useDeferredValue, useMemo, useState } from 'react'
import { useUI } from '../store/useUI.js'
import { useNavigate } from 'react-router-dom'
import { useStore } from '../store/useStore.js'
import { EXDB, BODYPARTS, allExercises, isCustomEx, equipmentOf, byCategory, searchExercises, similarExercises } from '../lib/exercises.js'
import { MUSCLE_NAME } from '../lib/muscles.js'
import { activeProfile, exAvailable } from '../lib/equipment.js'
import { bestWeightFor } from '../lib/history.js'
import { fmtNum, exCount } from '../lib/format.js'
import { t, tn, exerciseNameFor, exerciseNameClass } from '../lib/i18n.js'
import { exerciseNameParts } from '../components/ExerciseName.jsx'
import { Thumb } from '../components/Media.jsx'
import { exerciseDetailSheet, customExSheet } from '../sheets.jsx'
import Icon from '../components/Icon.jsx'
import ExerciseViewToggle from '../components/ExerciseViewToggle.jsx'
import { Button, Segmented } from '../components/ui.jsx'
import { tappable } from '../lib/use-sheet-keyboard.js'
import { useAutoMore } from '../lib/use-auto-more.js'
import { isFav, sortFavouritesFirst, sortYoursFirst, usageOf } from '../lib/favourites.js'

export default function Library() {
  const nav = useNavigate()
  const S = useStore(s => s.S)
  const [browse, setBrowse] = useState('all')
  const [q, setQ] = useState('')
  const [bp, setBp] = useState('')
  const [eq, setEq] = useState('')
  const [cat, setCat] = useState('')
  const [showAll, setShowAll] = useState(false)   // ignore the active equipment profile for this session
  const [shown, setShown] = useState(40)
  const moreRef = useAutoMore(() => setShown(s => s + 40))
  const profile = activeProfile(S)
  // Your own exercises, counted the way the list below shows them (allExercises puts every
  // custom entry in front of the catalogue; deleting one removes it from customEx outright).
  const ownCount = (S.customEx || []).filter(c => c && c.id).length
  const catalogue = allExercises(S)
  const browsePool = catalogue.filter(e => browse === 'favourites' ? isFav(S, e.id)
    : browse === 'own' ? isCustomEx(e) || (S.customEx || []).includes(e) : true)
  const inPart = searchExercises(browsePool.filter(e => !bp || e.bp === bp), q)
  // Kind of exercise (strength, stretching, cardio...), the same fallback as equipment below: a
  // choice the search or body part has narrowed away is ignored for now, never a dead end.
  const { opts: catOpts, on: catOn, list: base } = byCategory(inPart, cat)
  const eqFiltered = (profile && !showAll) ? base.filter(e => exAvailable(S, e)) : base
  const eqOpts = equipmentOf(eqFiltered)
  // Drop the equipment filter if the search narrowed it away, so you never hit a dead end.
  const eqOn = eqOpts.includes(eq) ? eq : ''
  // Favourites float to the top of whatever the filters left (issue #6), the rest keeps its order;
  // while searching, the exercises you have logged or planned follow right after them.
  const narrowedList = eqOn ? eqFiltered.filter(e => e.eq === eqOn) : eqFiltered
  const usage = useMemo(() => (q.trim() ? usageOf(S) : null), [q, S.routines, S.workouts])
  const f = usage ? sortYoursFirst(narrowedList, S, usage) : sortFavouritesFirst(narrowedList, S)
  // Type and equipment live in the Filters sheet (P7). It works out its own options from the same
  // search and body part, so a choice it offers is never a dead end either.
  const sheetOn = (bp ? 1 : 0) + (catOn ? 1 : 0) + (eqOn ? 1 : 0)
  const filtersFor = (c, e, part = bp) => {
    const by = byCategory(searchExercises(browsePool.filter(ex => !part || ex.bp === part), q), c)
    const pool = (profile && !showAll) ? by.list.filter(x => exAvailable(S, x)) : by.list
    const opts = equipmentOf(pool)
    return { catOpts: by.opts, catOn: by.on, eqOpts: opts, eqOn: opts.includes(e) ? e : '' }
  }
  const openFilters = () => useUI.getState().openSheet(close => <LibraryFilters close={close} onMuscles={() => { close(); nav('/muscles') }} cat={catOn} eq={eqOn} bp={bp} filtersFor={filtersFor}
    onChange={(c, e, part) => { setCat(c); setEq(e); setBp(part); setShown(40) }} />)
  // A live count at the end of the search field while a search or filter narrows the list
  // (idea and first version: GitLab !31) — how many are left, before scrolling to find out.
  const narrowed = !!(browse !== 'all' || q.trim() || bp || eqOn || catOn)
  // Close but not exact (a typo too many, most of the words, a similar name), under the results
  // once they are all on screen, so a search almost never ends on "No match".
  // Worked out a beat behind the typing (useDeferredValue): the list itself never waits for it.
  const qLate = useDeferredValue(q)
  const similar = q.trim() && qLate === q && f.length <= shown
    ? similarExercises(browsePool.filter(e => (!bp || e.bp === bp) && (!profile || showAll || exAvailable(S, e))), q, f, f.length ? 12 : 30)
    : []
  const row = e => {
    const best = bestWeightFor(S, e.id)
    const name = exerciseNameParts(e)
    // The row is not a button: its name is, stretched over the row (.tap-main), with Add to my plan
    // a sibling above it (card dismiss pass), so neither tap can land on the other.
    return <div key={e.id} className="item tap-host">
      <Thumb ex={e} />
      <button type="button" className="grow item-open tap-main" aria-haspopup="dialog" onClick={() => exerciseDetailSheet(e)}><span className={`tt ${exerciseNameClass(e)}`}>{isFav(S, e.id) && <Icon name="starFill" className="fav-star" />}{name.primary}</span>{name.secondary && <span className="ss lib-english" lang="en" dir="ltr">{name.secondary}</span>}<span className="ss capitalize">{t(MUSCLE_NAME[e.tg] || e.tg || e.bp)} · {t(e.eq)}</span></button>
      {best > 0 && <span className="tag acc">{fmtNum(best)}</span>}
      <Icon name="chevronRight" className="chev" />
    </div>
  }

  return <div className="progress-refinement progress-library">
    <div className="hdr lib-hdr"><div><h1>{t('Exercises')}</h1></div>
      <div className="row progress-header-actions">
        <button type="button" className="iconbtn" data-tour="lib-new" aria-label={t('Create your own exercise')} title={t('Create your own exercise')} onClick={() => customExSheet(null, ex => exerciseDetailSheet(ex), q.trim())}><Icon name="plus" /></button>
      </div>
      <div className="sub lib-count">{ownCount
        ? tn('{1} animated exercises + 1 of your own', '{1} animated exercises + {0} of your own', ownCount, EXDB.length)
        : t('{0} exercises with animations', EXDB.length)}</div>
    </div>
    <div className="search-row lib-search-tools" data-tour="lib-search"><div className={'search' + (narrowed ? ' has-count' : '') + (q ? ' has-clear' : '')}><svg viewBox="0 0 24 24"><circle cx="11" cy="11" r="7" /><path d="m21 21-4.3-4.3" /></svg>
      <input className="input" aria-label={t('Search…')} placeholder={t('Search…')} value={q} onChange={e => { setQ(e.target.value); setShown(40) }} />
      {narrowed && <span className="search-count" role="status" aria-label={exCount(f.length)}>{fmtNum(f.length)}</span>}
      {q && <button className="clear" onClick={() => { setQ(''); setShown(40) }} aria-label={t('Clear')}><Icon name="xmark" /></button>}</div>
      <button type="button" data-tour="lib-filters" className={'iconbtn lib-search-filter' + (sheetOn ? ' on' : '')} aria-label={t('Filters') + (sheetOn ? ': ' + sheetOn : '')} aria-haspopup="dialog" onClick={openFilters}>
        <Icon name="slider" />{sheetOn ? <span className="lib-fn">{sheetOn}</span> : null}
      </button>
      <ExerciseViewToggle /></div>
    <Segmented className="lib-browse" value={browse} onChange={value => { setBrowse(value); setShown(40) }}
      options={[{ value: 'all', label: t('All') }, { value: 'favourites', label: t('Favourites') }, { value: 'own', label: t('My own') }]} />
    {profile && <div className="small dim row" style={{ margin: '-4px 2px 10px', gap: 6, alignItems: 'center' }}>
      <Icon name="kettlebell" style={{ fontSize: 'var(--fs-footnote)' }} />
      {showAll ? t('Showing all equipment') : t('Showing what you have in "{0}"', profile.name)}
      <button className="chip nocap" style={{ marginInlineStart: 'auto', padding: '3px 10px', fontSize: 'var(--fs-caption)' }} onClick={() => setShowAll(v => !v)}>
        {showAll ? t('Filter by "{0}"', profile.name) : t('Show all equipment')}
      </button>
    </div>}
    {(bp || catOn || eqOn) && <div className="chips lib-filters">
      {bp && <button type="button" className="chip on ichip" aria-label={t('Clear') + ': ' + t(bp)} onClick={() => { setBp(''); setShown(40) }}>{t(bp)}<Icon name="xmark" /></button>}
      {catOn && <button type="button" className="chip on ichip" aria-label={t('Clear') + ': ' + t(catOn)} onClick={() => { setCat(''); setShown(40) }}>{t(catOn)}<Icon name="xmark" /></button>}
      {eqOn && <button type="button" className="chip on ichip" aria-label={t('Clear') + ': ' + t(eqOn)} onClick={() => { setEq(''); setShown(40) }}>{t(eqOn)}<Icon name="xmark" /></button>}
    </div>}
    <div className={'list lib-results' + (S.exerciseView === 'cards' ? ' ex-grid' : '')}>
      {q.trim() && f.length === 0 && <div className="item ex-new" {...tappable(() => customExSheet(null, ex => exerciseDetailSheet(ex), q.trim()))}>
        <div className="thumb thumb-x"><Icon name="plusCircle" /></div>
        <div className="grow"><div className="tt">{t('Create your own exercise')}</div><div className="ss">{q.trim()}</div></div><Icon name="plus" className="chev" />
      </div>}
      {f.slice(0, shown).map(row)}
      {f.length === 0 && !similar.length && <div className="empty"><div className="ico"><Icon name="magnifier" /></div>{t('No match')}</div>}
      {similar.length > 0 && <h4 className="sec similar-label">{f.length ? t('Similar exercises') : t('No exact match. These come close:')}</h4>}
      {similar.map(row)}
    </div>
    {f.length > shown && <><div style={{ height: 10 }} /><Button ref={moreRef} onClick={() => setShown(s => s + 40)}>{t('Show more')}</Button></>}
  </div>
}


// The Library's Filters sheet (P7): the kind of exercise and the equipment, as wrapping chips. Every
// tap filters the list behind it at once; Done only closes.
function LibraryFilters({ close, onMuscles, cat, eq, bp, filtersFor, onChange }) {
  const [c, setC] = useState(cat)
  const [e, setE] = useState(eq)
  const [part, setPart] = useState(bp)
  const { catOpts, catOn, eqOpts, eqOn } = filtersFor(c, e, part)
  const set = (nc, ne, nb = part) => { setC(nc); setE(ne); setPart(nb); onChange(nc, ne, nb) }
  return <div className="lib-fsheet">
    <h3>{t('Filters')}</h3>
    <Button variant="ghost" icon="figureStrength" trailingIcon="chevronRight" onClick={onMuscles}>{t('By muscle')}</Button>
    <h4 className="sec">{t('Body')}</h4>
    <div className="chips wrap lib-body-parts">
      <button type="button" className={'chip' + (!part ? ' on' : '')} aria-pressed={!part} onClick={() => set(c, e, '')}>{t('All')}</button>
      {BODYPARTS.map(value => <button type="button" key={value} className={'chip' + (part === value ? ' on' : '')} aria-pressed={part === value} onClick={() => set(c, e, value)}>{t(value)}</button>)}
    </div>
    {catOpts.length > 1 && <>
      <h4 className="sec">{t('Exercise type')}</h4>
      <div className="chips wrap">
        <button type="button" className={'chip nocap' + (!catOn ? ' on' : '')} aria-pressed={!catOn} onClick={() => set('', e)}>{t('Any type')}</button>
        {catOpts.map(x => <button type="button" key={x} className={'chip' + (catOn === x ? ' on' : '')} aria-pressed={catOn === x} onClick={() => set(x, e)}>{t(x)}</button>)}
      </div>
    </>}
    {eqOpts.length > 1 && <>
      <h4 className="sec">{t('Equipment')}</h4>
      <div className="chips wrap">
        <button type="button" className={'chip nocap' + (!eqOn ? ' on' : '')} aria-pressed={!eqOn} onClick={() => set(c, '')}>{t('Any equipment')}</button>
        {eqOpts.map(x => <button type="button" key={x} className={'chip' + (eqOn === x ? ' on' : '')} aria-pressed={eqOn === x} onClick={() => set(c, x)}>{t(x)}</button>)}
      </div>
    </>}
    <div style={{ height: 16 }} />
    <Button variant="primary" onClick={close}>{t('Done')}</Button>
    {(part || catOn || eqOn) && <Button variant="ghost" className="dim" style={{ marginTop: 6 }} onClick={() => set('', '', '')}>{t('Clear filters')}</Button>}
  </div>
}
