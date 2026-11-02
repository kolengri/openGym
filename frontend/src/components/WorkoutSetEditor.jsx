import { useEffect } from 'react'
import { useStore } from '../store/useStore.js'
import { effortPickerSheet } from '../sheets.jsx'
import { rirOf, toScale } from '../lib/effort.js'
import { exerciseNameText } from '../lib/format.js'
import { t } from '../lib/i18n.js'
import { exOr } from '../lib/exercises.js'
import { exUnitOf, viewEntry, viewTarget } from '../lib/ex-unit.js'
import MixedWeightField from './MixedWeightField.jsx'
import SetEffortValue from './SetEffortValue.jsx'
import { SetComparison } from './SetComparison.jsx'
import { Button, NumberField } from './ui.jsx'
import Icon from './Icon.jsx'

// The editor uses the workout's existing field and completion handlers. A checkbox and a
// rating still conclude a set through the same rest/advance flow as the other layouts.
export default function WorkoutSetEditor({ entryIdx, index, owner, columns, effort, side, cardio,
  previous, stepLoad, steppers, onField, onToggle, onOptions, close }) {
  const S = useStore(s => s.S)
  const unit = exUnitOf(S, owner.exercise)
  const matchingEntry = state => {
    const entry = state.active?.entries[entryIdx]
    return state.active?.id === owner.session && exUnitOf(state, owner.exercise) === owner.unit
      && entry?.id === owner.exercise && entry?.rid === owner.routine
      && entry?.sets.length === owner.rows && JSON.stringify(viewTarget(state, owner.exercise, entry.target)) === owner.target
      ? viewEntry(state, entry) : null
  }
  const entry = matchingEntry(S)
  const row = entry?.sets[index]
  const set = side ? row?.sides?.[side] : row
  useEffect(() => { if (!set) close() }, [!!set, close])
  if (!set) return null
  const displaySide = side || row.side
  const current = () => {
    const entry = matchingEntry(useStore.getState().S)
    return side ? entry?.sets[index]?.sides?.[side] : entry?.sets[index]
  }
  const field = (key, value, guard) => {
    if (current()) onField(key, value, st => {
      return !!matchingEntry(st) && (!guard || guard(st))
    })
  }
  const done = () => { const fresh = current(); close(); if (fresh && !fresh.done) onToggle() }
  const rate = () => effortPickerSheet(effort, toScale(effort, rirOf(set)), value => {
    if (!current()) return
    field(effort === 'rir' ? 'rpe' : 'rir', null)
    field(effort, value)
    if (value != null) done()
  }, { cardio })
  return <div className="workout-set-editor">
    <div className="row between">
      <h3>{t('Set {0}', owner.number)}{displaySide ? ' · ' + t(displaySide === 'L' ? 'Left' : 'Right') : ''}</h3>
      <button type="button" className="iconbtn" aria-label={t('More')} onClick={() => { close(); onOptions() }}><Icon name="more" /></button>
    </div>
    <div className="small dim">{exerciseNameText(exOr(entry.id))}</div>
    {columns.filter(Boolean).map(col => {
      const view = value => col.view && value != null ? col.view(value) : value
      const change = value => field(col.f, col.store ? col.store(value) : value)
      const bump = dir => {
        const fresh = current()
        if (!fresh) return
        if (col.f === 'w') return field('w', stepLoad(fresh.w, col.step, dir))
        change(Math.min(col.max ?? Infinity, Math.max(0, Math.round(((view(fresh[col.f]) || 0) + dir * (side && col.f === 'r' ? 1 : col.step)) * 100) / 100)))
      }
      return <section className="workout-set-field" key={col.f}>
        {col.f === 'w' ? <div className="small dim">{col.hd}</div> : <label htmlFor={'set-editor-' + col.f}>{col.hd}</label>}
        <div className={'stp' + (steppers ? '' : ' plain')}>
          {steppers && <button type="button" aria-label={t('Decrease')} onClick={() => bump(-1)}><Icon name="minus" /></button>}
          <span className="val">{col.f === 'w'
            ? <MixedWeightField value={set.w ?? ''} unit={unit} exerciseId={entry.id} onChange={(value, guard) => field('w', value, guard)} />
            : <NumberField id={'set-editor-' + col.f} decimal={col.dec} nullable={col.opt} value={view(set[col.f]) ?? (col.opt ? null : '')} onChange={change} />}</span>
          {steppers && <button type="button" aria-label={t('Increase')} onClick={() => bump(1)}><Icon name="plus" /></button>}
        </div>
        <SetComparison current={set} previous={previous} field={col.f} exerciseId={entry.id} view={col.view} deltaOnly />
      </section>
    })}
    {effort && <section className="workout-set-field"><div className="small dim">{effort.toUpperCase()}</div>
      <SetEffortValue kind={effort} value={toScale(effort, rirOf(set))} onClick={rate} cardio={cardio} />
    </section>}
    <Button variant="primary" onClick={done}>{t('Done')}</Button>
  </div>
}
