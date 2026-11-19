import { useEffect, useId, useRef, useState } from 'react'
import { useStore } from '../store/useStore.js'
import { useUI } from '../store/useUI.js'
import { Button, NumberField, Segmented } from './ui.jsx'
import { baseWeightFor } from '../lib/plates.js'
import { cleanNum, fmtPlate } from '../lib/format.js'
import { exUnitOf, exView } from '../lib/ex-unit.js'
import { sessionGymView } from '../lib/gym-inventory.js'
import { calculatorSetupFor } from '../lib/exercise-merge.js'
import { t } from '../lib/i18n.js'
import { useSheetKeyboard } from '../lib/use-sheet-keyboard.js'

export const LB_PER_KG = 2.2046226218
export const exactWeightIn = (value, from, to) => from === to ? value : to === 'lb' ? value * LB_PER_KG : value / LB_PER_KG
export function mixedBarWeight({ bar, barUnit, plates, plateUnit, unit }) {
  if (![bar, plates].every(v => typeof v === 'number' && Number.isFinite(v) && v >= 0)) return null
  const total = exactWeightIn(bar, barUnit, unit) + 2 * exactWeightIn(plates, plateUnit, unit)
  return total <= 10000 ? Math.round(total * 10000) / 10000 : null
}

// Any intervening edit invalidates this deferred index-based operation, including A–B–A
// profile/unit changes and equal-length replacements. Check again inside the store mutation.
export function weightTargetGuard(store) {
  const initial = store.getState()
  const owner = initial.user?.id ?? null, unit = initial.S.unit, wid = initial.S.active?.id
  const entries = JSON.stringify(initial.S.active?.entries)
  const pins = JSON.stringify(initial.S.exUnit)
  let valid = true
  const same = state => (state.user?.id ?? null) === owner && state.S.unit === unit &&
    state.S.active?.id === wid && JSON.stringify(state.S.exUnit) === pins && JSON.stringify(state.S.active?.entries) === entries
  let stop = null
  const listen = () => { stop ||= store.subscribe(state => { if (!same(state)) valid = false }) }
  const dispose = () => { stop?.(); stop = null }
  listen()
  return { listen, dispose, matches: s => valid && same(store.getState()) && s?.unit === unit &&
    s?.active?.id === wid && JSON.stringify(s?.exUnit) === pins && JSON.stringify(s?.active?.entries) === entries }
}

// Keep the exact profile-unit value separate from the rounded conversion preview. A unit
// toggle is presentation-only; only typing a new amount changes the calculated load.
function useWeightAmount(initial, unit, saved, savedUnit) {
  const [value, setValue] = useState(() => saved ? exactWeightIn(saved.value, savedUnit, unit) : initial)
  const [input, setInput] = useState(saved?.input ?? initial)
  const [inputUnit, setInputUnit] = useState(saved?.unit ?? unit)
  return { value, input, unit: inputUnit,
    onChange: amount => { setInput(amount); setValue(exactWeightIn(amount, inputUnit, unit)) },
    onUnitChange: next => {
      setInput(next === unit ? Math.round(value * 100) / 100 : Math.round(exactWeightIn(value, unit, next)))
      setInputUnit(next)
    },
  }
}

const inputNumber = new Intl.NumberFormat('en-US', { useGrouping: false, maximumSignificantDigits: 21 })

function WeightInput({ label, amount, exact = false }) {
  const id = useId()
  return <div className="weight-calc-field">
    <label htmlFor={id}>{label}</label>
    <div className="weight-calc-input">
      <NumberField id={id} className="field" value={amount.input} formatValue={exact ? inputNumber.format : undefined}
        onChange={amount.onChange} aria-label={label} />
      <button type="button" className="weight-unit" aria-label={t('Weight unit') + ': ' + amount.unit}
        onClick={() => amount.onUnitChange(amount.unit === 'kg' ? 'lb' : 'kg')}>{amount.unit}</button>
    </div>
  </div>
}

const isUnit = unit => unit === 'kg' || unit === 'lb'
const isAmount = amount => isUnit(amount?.unit) &&
  Number.isFinite(amount.value) && amount.value >= 0 && Number.isFinite(amount.input) && amount.input >= 0

function Calculator({ value, unit, barWeight, previous, onApply, close, guard }) {
  useEffect(() => { guard.listen(); return guard.dispose }, [guard])
  const ref = useRef(null)
  const onFocus = useSheetKeyboard(ref, true, { reveal: true })
  useEffect(() => {
    // Focus only after the .34s sheet entrance; native autofocus can pan a sheet mid-animation.
    const timer = setTimeout(() => {
      const form = ref.current
      if (!form || form.contains(document.activeElement)) return
      form.querySelector('input')?.focus({ preventScroll: true })
      onFocus()
    }, 400)
    return () => clearTimeout(timer)
  }, [onFocus])
  const [stale, setStale] = useState(false)
  const bar = useWeightAmount(barWeight, unit, previous?.bar, previous?.unit)
  const plates = useWeightAmount(0, unit, previous?.plates, previous?.unit)
  const [totalOnly, setTotalOnly] = useState(!previous)
  const total = useWeightAmount(value || 0, unit)
  const result = totalOnly
    ? Number.isFinite(total.value) && total.value >= 0 ? Math.round(total.value * 10000) / 10000 : null
    : mixedBarWeight({ bar: bar.value, barUnit: unit, plates: plates.value, plateUnit: unit, unit })
  return <div ref={ref} className="weight-calculator kb-lift" onFocusCapture={onFocus}>
    <h3>{t('Weight calculator')}</h3>
    <Segmented value={totalOnly ? 'total' : 'bar'} onChange={v => setTotalOnly(v === 'total')} options={[{ value: 'total', label: t('Total weight') }, { value: 'bar', label: t('Bar and plates') }]} />
    {totalOnly ? <WeightInput label={t('Total weight')} amount={total} /> : <>
      <WeightInput label={t('Bar weight')} amount={bar} exact />
      <WeightInput label={t('Plates on one side')} amount={plates} exact />
      <p className="small muted">{t('Enter the combined plate weight on one side. Both sides are counted.')}</p>
    </>}
    <div className="weight-calc-result"><span>{t('Total weight')}</span><strong>{result == null ? '–' : fmtPlate(result)} <small>{unit}</small></strong></div>
    {stale && <p role="alert">{t('Workout changed. Reopen the weight calculator.')}</p>}
    <Button variant="primary" disabled={stale || result == null || result > 10000} onClick={() => {
      if (!guard.matches(useStore.getState().S)) { setStale(true); return }
      const snapshot = ({ value, input, unit }) => ({ value, input, unit })
      const setup = totalOnly ? null : { unit, bar: snapshot(bar), plates: snapshot(plates) }
      onApply(result, guard.matches, setup); guard.dispose(); close()
    }}>{t('Apply')}</Button>
  </div>
}

/** Edits use the exercise's displayed unit; the caller stores them in the profile's unit. */
export default function MixedWeightField({ value, onChange, unit, exerciseId }) {
  const open = () => {
    const initial = useStore.getState()
    if (exUnitOf(initial.S, exerciseId) !== unit) return
    const base = exerciseId ? baseWeightFor(exView(sessionGymView(initial.S), exerciseId), exerciseId) : 0
    const saved = calculatorSetupFor(initial.S, exerciseId)
    const previous = isUnit(saved?.unit) && isAmount(saved.bar) && isAmount(saved.plates) ? saved : null
    const guard = weightTargetGuard(useStore)
    useUI.getState().openSheet(close => <Calculator value={value} unit={unit} barWeight={base} guard={guard}
      previous={previous} close={close} onApply={onChange} />)
  }
  const displayed = cleanNum(value)
  const readout = displayed === '' || displayed == null ? '–' : displayed
  return <button type="button" className="weight-value" aria-label={`${t('Weight calculator')}: ${readout} ${unit}`} title={t('Weight calculator')} onClick={open}>
    {readout}
  </button>
}
