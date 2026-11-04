// @vitest-environment happy-dom
import React, { act } from 'react'
import { createRoot } from 'react-dom/client'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { DEF, useStore } from '../store/useStore.js'
import { useUI } from '../store/useUI.js'
import { openTour, closeTour } from '../lib/tour.js'
import Tour, { _setAnchorWait } from './Tour.jsx'
import Plan from '../views/Plan.jsx'
import Stats from '../views/Stats.jsx'
import { exerciseDetailSheet, workoutDetailSheet } from '../sheets.jsx'
import { EXIDX } from '../lib/exercises.js'

globalThis.IS_REACT_ACT_ENVIRONMENT = true
let root, host
function Sheets() {
  const sheets = useUI(s => s.sheets)
  return sheets.map(sheet => <div key={sheet.id}>{sheet.render(() => useUI.getState().closeSheet(sheet.id))}</div>)
}
beforeEach(() => {
  localStorage.clear()
  _setAnchorWait(300)
  const S = structuredClone(DEF)
  S.workouts = [{ id: 'tour-reveal', d: '2026-11-01', name: 'Saved', start: 1, end: 60001,
    entries: [{ id: '0025', target: { mode: 'reps', sets: 1, reps: 5 }, sets: [{ w: 40, r: 5, done: true }] }] }]
  S.routines = []
  S.gifSize = 'off'
  useStore.setState({ S, user: null, ready: true, tourSandbox: null })
  useUI.getState().closeAll()
  window.history.replaceState(null, '', '#/stats')
  host = document.createElement('div')
  document.body.appendChild(host)
  root = createRoot(host)
})
afterEach(async () => {
  await act(async () => { closeTour(); root.unmount() })
  host.remove()
  useStore.getState().leaveTourSandbox()
  useUI.getState().closeAll()
  vi.restoreAllMocks()
})
async function run(element, at, path, flow = 'tour') {
  act(() => root.render(<MemoryRouter initialEntries={[path]}>{element}<Sheets /><Tour /></MemoryRouter>))
  await act(async () => { openTour({ kind: 'run', at, flow }) })
  await vi.waitFor(async () => {
    await act(async () => { await new Promise(resolve => setTimeout(resolve, 30)) })
    expect(host.querySelector('.tour')?.getAttribute('data-step')).toBe(at)
    expect(host.querySelector('.tour-card')).not.toBeNull()
  })
}
it('reveals the actual collapsed plan-mode controls before spotlighting them', async () => {
  await run(<Plan />, 'plan-mode', '/plan')
  expect(host.querySelector('[data-tour="plan-mode"]').closest('details').open).toBe(true)
})
it.each([
  ['stats-body', 'tour', 'lifts', 'stats-body'],
  ['e-measure', 'edit', 'body', 'stats-measure'],
])('selects the real Stats panel for %s', async (at, flow, panel, anchor) => {
  await run(<Stats />, at, '/stats', flow)
  await vi.waitFor(() => expect(host.querySelector(`[data-tour="${anchor}"]`).closest('[hidden]')).toBeNull())
  expect(host.querySelector(`[data-tour="stats-panel-${panel}"]`).getAttribute('aria-pressed')).toBe('true')
  expect(window.location.hash).toContain('section=' + panel)
})
it('opens the real exercise equipment disclosure for the unit tutorial', async () => {
  act(() => exerciseDetailSheet(EXIDX['0025']))
  await run(null, 'c-unit', '/library', 'custom')
  expect(host.querySelector('[data-tour="ex-unit"]').closest('details').open).toBe(true)
})
it('opens an empty saved-note disclosure for the edit tutorial', async () => {
  act(() => workoutDetailSheet(useStore.getState().S.workouts[0]))
  await run(null, 'e-note', '/history', 'edit')
  expect(host.querySelector('[data-tour="wd-note"]').closest('details').open).toBe(true)
})
