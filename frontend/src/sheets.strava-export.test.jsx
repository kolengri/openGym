// @vitest-environment happy-dom
import React, { act } from 'react'
import { createRoot } from 'react-dom/client'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { DEF, useStore } from './store/useStore.js'
import { useUI } from './store/useUI.js'
import { workoutDetailSheet } from './sheets.jsx'
import Settings from './views/Settings.jsx'
import { fitFileName, workoutFit } from './lib/fit-export.js'
import { stravaWorkoutFit } from './lib/strava-export.js'

const mounted = []
const button = (host, text) => [...host.querySelectorAll('button')].find(b => b.textContent.trim() === text)
function mount(element) {
  const host = document.createElement('div')
  document.body.appendChild(host)
  const root = createRoot(host)
  mounted.push(root)
  act(() => root.render(element))
  return host
}
function detail(workout) {
  workoutDetailSheet(workout)
  const sheet = useUI.getState().sheets.at(-1)
  return mount(sheet.render(() => useUI.getState().closeSheet(sheet.id)))
}
const saved = {
  id: 'strava-test', d: '2026-09-15', name: 'Strength',
  start: new Date(2026, 8, 15, 17).getTime(), end: new Date(2026, 8, 15, 18).getTime(),
  vol: 300, prs: [], entries: [{ id: '0025', target: { mode: 'reps' }, sets: [{ w: 60, r: 5, done: true }] }],
}
let blobs, downloads
beforeEach(() => {
  globalThis.IS_REACT_ACT_ENVIRONMENT = true
  globalThis.__APP_VERSION__ ??= 'test'
  useUI.setState({ sheets: [], toast: vi.fn() })
  const S = structuredClone(DEF)
  Object.assign(S, { unit: 'kg', workouts: [structuredClone(saved)], routines: [], active: null })
  delete S.stravaShareWeights
  useStore.setState({ S, user: null })
  localStorage.removeItem('gym_state_v1')
  blobs = []
  downloads = []
  vi.stubGlobal('URL', Object.assign(Object.create(URL), {
    createObjectURL: vi.fn(blob => { blobs.push(blob); return 'blob:strava-fit' }), revokeObjectURL: vi.fn(),
  }))
  vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(function () { downloads.push(this.download) })
})
afterEach(() => {
  act(() => mounted.splice(0).forEach(root => root.unmount()))
  document.body.innerHTML = ''
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
})

describe('Strava file export controls', () => {
  it('defaults off for an imported profile without the flag and persists both choices through the real store', async () => {
    const host = mount(<MemoryRouter><Settings page="data" /></MemoryRouter>)
    const toggle = host.querySelector('[role="switch"][aria-label="Include weights in Strava exports"]')
    expect(toggle).not.toBeNull()
    expect(toggle.getAttribute('aria-checked')).toBe('false')
    expect(host.textContent).toContain('Applies to Strava FIT files and openGym uploads to Garmin Connect.')
    const before = structuredClone(useStore.getState().S.workouts)
    await act(async () => { toggle.click() })
    expect(toggle.getAttribute('aria-checked')).toBe('true')
    expect(useStore.getState().S.stravaShareWeights).toBe(true)
    expect(JSON.parse(localStorage.getItem('gym_state_v1')).stravaShareWeights).toBe(true)
    await act(async () => { toggle.click() })
    expect(toggle.getAttribute('aria-checked')).toBe('false')
    expect(JSON.parse(localStorage.getItem('gym_state_v1')).stravaShareWeights).toBe(false)
    expect(useStore.getState().S.workouts).toEqual(before)
  })

  it('returns to private exports when a backup without the preference replaces an opted-in profile', async () => {
    const imported = structuredClone(useStore.getState().S)
    act(() => useStore.getState().update(s => { s.stravaShareWeights = true }))
    const host = mount(<MemoryRouter><Settings page="data" /></MemoryRouter>)
    const toggle = () => host.querySelector('[aria-label="Include weights in Strava exports"]')
    expect(toggle().getAttribute('aria-checked')).toBe('true')
    await act(async () => { useStore.getState().replaceState(imported) })
    expect(toggle().getAttribute('aria-checked')).toBe('false')
    expect(useStore.getState().S.stravaShareWeights).toBeUndefined()
    expect(stravaWorkoutFit(saved, useStore.getState().S)).toEqual(workoutFit(saved, { includeWeights: false }))
  })

  it.each([undefined, true, false])('offers separate Strava and Garmin downloads using the current preference: %s', async preference => {
    if (preference !== undefined) useStore.setState(s => ({ S: { ...s.S, stravaShareWeights: preference } }))
    const host = detail(saved)
    expect(button(host, 'Export for Strava (.fit)')).toBeTruthy()
    expect(button(host, 'Export as .fit file')).toBeTruthy()
    const before = structuredClone(useStore.getState().S.workouts)
    await act(async () => { button(host, 'Export for Strava (.fit)').click() })
    expect(downloads).toEqual([fitFileName(saved).replace(/\.fit$/, '-strava.fit')])
    expect(new Uint8Array(await blobs[0].arrayBuffer())).toEqual(stravaWorkoutFit(saved, useStore.getState().S, { unit: 'kg', version: __APP_VERSION__ }))
    expect(useUI.getState().toast).toHaveBeenLastCalledWith('Saved. Upload this file to Strava.')
    await act(async () => { button(host, 'Export as .fit file').click() })
    expect(downloads[1]).toBe(fitFileName(saved))
    expect(new Uint8Array(await blobs[1].arrayBuffer())).toEqual(workoutFit(saved, { unit: 'kg', version: __APP_VERSION__ }))
    expect(useUI.getState().toast).toHaveBeenLastCalledWith('Saved. Garmin Connect can take it from here.')
    expect(useStore.getState().S.workouts).toEqual(before)
  })

  it('reports invalid workouts without downloading a Strava file', async () => {
    const host = detail({ id: 'missing-date', name: 'Undated', entries: [], prs: [] })
    await act(async () => { button(host, 'Export for Strava (.fit)').click() })
    expect(downloads).toHaveLength(0)
    expect(useUI.getState().toast).toHaveBeenCalledWith('Could not create the file')
  })
})
