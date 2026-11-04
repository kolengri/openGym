// @vitest-environment happy-dom
// The finish summary's Share (v1.4.5): right next to the way out, which stays right under the
// numbers, and it opens the same picture sheet as History's "Share as image".
import React, { act } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createRoot } from 'react-dom/client'
import { DEF, useStore } from './store/useStore.js'
import { useUI } from './store/useUI.js'
import { finishWorkoutNow } from './sheets.jsx'
import { _setGarminCloudPluginForTest } from './lib/garmin-cloud.js'

const clone = v => JSON.parse(JSON.stringify(v))
const mounted = []
let host
function renderTopSheet() {
  const sheet = useUI.getState().sheets.at(-1)
  host = document.createElement('div')
  document.body.appendChild(host)
  const root = createRoot(host)
  mounted.push(root)
  act(() => root.render(sheet.render(() => useUI.getState().closeSheet(sheet.id))))
}
const settle = () => act(async () => {})

beforeEach(() => {
  globalThis.IS_REACT_ACT_ENVIRONMENT = true
  localStorage.clear()
  _setGarminCloudPluginForTest(null)
  useUI.setState({ sheets: [], timer: null, work: null })
  const st = clone(DEF)
  st.routines = [{ id: 'r1', name: 'Push A', ex: [{ id: '0025', sets: 1, reps: 5, weight: 60 }] }]
  st.active = { id: 'fin', d: '2026-09-28', start: Date.now() - 20 * 60000, routineIds: ['r1'], routineId: 'r1', name: 'Push A', bw: null, cur: 0,
    entries: [{ id: '0025', rid: 'r1', target: { sets: 1, reps: 5, weight: 60 }, sets: [{ w: 60, r: 5, done: true }] }] }
  useStore.setState({ S: st, user: null })
})
afterEach(() => {
  _setGarminCloudPluginForTest(null)
  mounted.splice(0).forEach(r => act(() => r.unmount()))
  document.body.innerHTML = ''
})

describe('finish summary: Share', () => {
  it('sits beside the way out, which still comes right after the numbers', async () => {
    act(() => finishWorkoutNow())
    renderTopSheet()
    await settle()
    const row = host.querySelector('.fin-actions')
    expect(row).toBeTruthy()
    const [done, share] = row.querySelectorAll('button')
    expect(done.textContent).toBe('Nice!')
    expect(share.textContent).toBe('Share')
    // Nothing but the numbers and the records list between the title and the way out.
    const tiles = host.querySelector('.tiles.fin')
    expect(tiles.compareDocumentPosition(row) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    expect(host.querySelector('.bodymap, [data-keep-in-routine]')?.compareDocumentPosition(row) & Node.DOCUMENT_POSITION_PRECEDING).toBeTruthy()
  })

  it('opens the picture sheet for the saved workout: story or square, dark or light', async () => {
    act(() => finishWorkoutNow())
    renderTopSheet()
    await settle()
    const before = useUI.getState().sheets.length
    act(() => host.querySelector('[data-fin-share]').click())
    expect(useUI.getState().sheets.length).toBe(before + 1)
    renderTopSheet()
    await settle()
    expect(host.querySelector('h3').textContent).toBe('Share workout')
    const labels = [...host.querySelectorAll('.share-opts button')].map(b => b.textContent)
    expect(labels).toEqual(['Story 9:16', 'Square 1:1', 'Dark', 'Light'])
  })

  it('keeps a failed Garmin upload and its retry message outside the Done and Share row', async () => {
    const status = vi.fn(async () => ({ available: true, connected: false }))
    _setGarminCloudPluginForTest({ status })
    act(() => finishWorkoutNow())
    act(() => useStore.getState().update(s => {
      s.workouts[0].garminCloudUpload = { status: 'failed', error: 'auth_required' }
    }))
    renderTopSheet()
    await settle()
    const row = host.querySelector('.fin-actions')
    const [done, share] = row.querySelectorAll('button')
    const upload = host.querySelector('.garmin-cloud-upload')
    expect([...row.children]).toEqual([done, share])
    expect(row.nextElementSibling).toBe(upload)
    expect(upload.parentElement).toBe(row.parentElement)
    expect(upload.querySelector('[role="alert"]').textContent).toContain('Your saved session was not accepted.')
    expect(upload.querySelector('button').textContent).toBe('Retry Garmin upload')
    await act(async () => { upload.querySelector('button').click() })
    expect(status).toHaveBeenCalledTimes(2)
    expect(upload.querySelector('[role="alert"]').textContent).toContain('Your saved session was not accepted.')
    const before = useUI.getState().sheets.length
    act(() => share.click())
    expect(useUI.getState().sheets).toHaveLength(before + 1)
    act(() => useUI.getState().closeSheet(useUI.getState().sheets.at(-1).id))
    act(() => done.click())
    expect(useUI.getState().sheets).toHaveLength(0)
  })
})
