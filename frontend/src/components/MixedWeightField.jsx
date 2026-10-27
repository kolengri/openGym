import { useEffect, useState } from 'react'
import { useStore } from '../store/useStore.js'
import { useUI } from '../store/useUI.js'
import { Button, NumberField, Segmented } from './ui.jsx'
import { baseWeightFor } from '../lib/plates.js'
import { fmtPlate } from '../lib/format.js'
import { t } from '../lib/i18n.js'

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
  let valid = true
  const same = state => (state.user?.id ?? null) === owner && state.S.unit === unit &&
    state.S.active?.id === wid && JSON.stringify(state.S.active?.entries) === entries
  let stop = null
  const listen = () => { stop ||= store.subscribe(state => { if (!same(state)) valid = false }) }
  const dispose = () => { stop?.(); stop = null }
  listen()
  return { listen, dispose, matches: s => valid && same(store.getState()) && s?.unit === unit &&
    s?.active?.id === wid && JSON.stringify(s?.active?.entries) === entries }
}

function Calculator({ value, unit, barWeight, onApply, close, guard }) {
  useEffect(() => { guard.listen(); return guard.dispose }, [guard])
  const [stale, setStale] = useState(false)
  const [bar, setBar] = useState(barWeight)
  const [barUnit, setBarUnit] = useState(unit)
  const [plateUnit, setPlateUnit] = useState(unit === 'kg' ? 'lb' : 'kg')
  const [plates, setPlates] = useState(0)
  const [totalOnly, setTotalOnly] = useState(true)
  const [total, setTotal] = useState(value || 0)
  const [totalUnit, setTotalUnit] = useState(unit)
  const options = [{ value: 'kg', label: 'kg' }, { value: 'lb', label: 'lb' }]
  const result = totalOnly
    ? Number.isFinite(total) && total >= 0 ? Math.round(exactWeightIn(total, totalUnit, unit) * 10000) / 10000 : null
    : mixedBarWeight({ bar, barUnit, plates, plateUnit, unit })
  return <>
    <h3>{t('Weight calculator')}</h3>
    <Segmented value={totalOnly ? 'total' : 'bar'} onChange={v => setTotalOnly(v === 'total')} options={[{ value: 'total', label: t('Total weight') }, { value: 'bar', label: t('Bar and plates') }]} />
    {totalOnly ? <label className="measure-date">
      <span>{t('Total weight')}</span>
      <NumberField value={total} onChange={setTotal} aria-label={t('Total weight')} />
      <Segmented value={totalUnit} onChange={v => { setTotal(exactWeightIn(total, totalUnit, v)); setTotalUnit(v) }} options={options} />
    </label> : <>
      <label className="measure-date"><span>{t('Bar weight')}</span><NumberField value={bar} onChange={setBar} aria-label={t('Bar weight')} /></label>
      <Segmented value={barUnit} onChange={v => { setBar(exactWeightIn(bar, barUnit, v)); setBarUnit(v) }} options={options} />
      <label className="measure-date"><span>{t('Plates on one side')}</span><NumberField value={plates} onChange={setPlates} aria-label={t('Plates on one side')} /></label>
      <Segmented value={plateUnit} onChange={v => { setPlates(exactWeightIn(plates, plateUnit, v)); setPlateUnit(v) }} options={options} />
      <p className="small muted">{t('Enter the combined plate weight on one side. Both sides are counted.')}</p>
    </>}
    <p><b>{t('Total weight')}: {result == null ? '–' : fmtPlate(result)} {unit}</b></p>
    {stale && <p role="alert">{t('Workout changed. Reopen the weight calculator.')}</p>}
    <Button variant="primary" disabled={stale || result == null || result > 10000} onClick={() => {
      if (!guard.matches(useStore.getState().S)) { setStale(true); return }
      onApply(result, guard.matches); guard.dispose(); close()
    }}>{t('Apply')}</Button>
  </>
}

/** The logged number stays in the profile's unit; conversion is an explicit per-row action. */
export default function MixedWeightField({ value, onChange, unit, exerciseId, ...rest }) {
  const open = () => {
    const initial = useStore.getState()
    if (initial.S.unit !== unit) return
    const base = exerciseId ? baseWeightFor(initial.S, exerciseId) : 0
    const guard = weightTargetGuard(useStore)
    useUI.getState().openSheet(close => <Calculator value={value} unit={unit} barWeight={base} guard={guard}
      close={close} onApply={onChange} />)
  }
  const displayed = typeof value === 'number' ? Math.round(value * 100) / 100 : value
  return <span style={{ display: 'flex', flexDirection: 'column', width: '100%', minWidth: 0 }}>
    <NumberField value={displayed} onChange={onChange} {...rest} />
    <button type="button" aria-label={t('Weight calculator')} title={t('Weight calculator')} onClick={open}
      style={{ fontSize: 10, width: '100%', minWidth: 0, minHeight: 44, padding: '0 3px', flexShrink: 0 }}>kg/lb</button>
  </span>
}
