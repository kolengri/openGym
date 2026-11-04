// @vitest-environment happy-dom
import React, { act } from 'react'
import { createRoot } from 'react-dom/client'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { DEF, useStore } from './store/useStore.js'
import { useUI } from './store/useUI.js'
import { finishWorkoutNow } from './sheets.jsx'
import History from './views/History.jsx'
import { _setGarminCloudPluginForTest } from './lib/garmin-cloud.js'

const roots = new Set()
const mount = element => {
  const host = document.createElement('div')
  document.body.appendChild(host)
  const root = createRoot(host)
  roots.add(root)
  act(() => root.render(element))
  return { host, unmount: () => { act(() => root.unmount()); roots.delete(root); host.remove() } }
}
const mountTopSheet = () => {
  const sheet = useUI.getState().sheets.at(-1)
  return mount(sheet.render(() => useUI.getState().closeSheet(sheet.id)))
}
const settle = () => act(async () => {})
const click = element => { expect(element).toBeTruthy(); act(() => element.click()) }

beforeEach(() => {
  globalThis.IS_REACT_ACT_ENVIRONMENT = true
  localStorage.clear()
  useUI.setState({ sheets: [], timer: null, work: null })
  const S = structuredClone(DEF)
  Object.assign(S, { sound: false, garminCloudSessionId: 'synthetic-session', garminCloudAuto: false, workouts: [], routines: [],
    active: { id: 'finished-history-upload', d: '2026-11-04', start: Date.now() - 20 * 60000, name: 'History retry', cur: 0, routineIds: [],
      entries: ['0025', '0031', '1001'].map(id => ({ id, target: { mode: 'reps', sets: 1, reps: 8, weight: 40 }, sets: [{ w: 40, r: 8, done: true }] })) },
  })
  useStore.setState({ S, user: null, ready: true, tourSandbox: null })
  vi.spyOn(useStore.getState(), 'saveNow').mockResolvedValue()
  vi.spyOn(useStore.getState(), 'autoBackupNow').mockResolvedValue()
})

afterEach(() => {
  act(() => { roots.forEach(root => root.unmount()); roots.clear() })
  _setGarminCloudPluginForTest(null)
  vi.restoreAllMocks()
  document.body.innerHTML = ''
})

it.each(['uploaded', 'duplicate'])('retries a saved workout from History after the finish window closes and guards %s results', async status => {
  const bridge = {
    status: vi.fn(async () => ({ available: true, connected: true, sessionId: 'synthetic-session' })),
    upload: vi.fn(async () => ({ status, activityId: 'synthetic-activity' })),
  }
  _setGarminCloudPluginForTest(bridge)
  act(() => finishWorkoutNow())
  const finish = mountTopSheet()
  await settle()
  click([...finish.host.querySelectorAll('button')].find(button => button.textContent === 'Nice!'))
  expect(useUI.getState().sheets).toHaveLength(0)
  finish.unmount()
  act(() => useStore.getState().update(s => {
    s.workouts[0].garminCloudUpload = { status: 'failed', error: 'auth_required', sessionId: 'synthetic-session' }
  }))
  const saved = structuredClone(useStore.getState().S.workouts[0])

  const history = mount(<MemoryRouter><History /></MemoryRouter>)
  click(history.host.querySelector('[data-tour="history-row"]'))
  const detail = mountTopSheet().host
  await settle()
  const upload = detail.querySelector('.garmin-cloud-upload')
  expect(detail.querySelectorAll('.garmin-cloud-upload')).toHaveLength(1)
  expect(upload.previousElementSibling).toBe(detail.querySelector('h3').nextElementSibling)
  expect(upload.compareDocumentPosition(detail.querySelector('.wd-ex')) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
  expect(upload.querySelector('[role="alert"]').textContent).toContain('Your saved session was not accepted.')
  const retry = upload.querySelector('button')
  expect(retry.textContent).toBe('Retry Garmin upload')
  expect(bridge.upload).not.toHaveBeenCalled()
  await act(async () => { retry.click() })
  expect(bridge.upload).toHaveBeenCalledOnce()
  expect(bridge.upload.mock.calls[0][0]).toMatchObject({ workoutId: saved.id, sessionId: 'synthetic-session', retryUnknown: false })
  expect(useStore.getState().S.workouts).toHaveLength(1)
  const { garminCloudUpload, ...after } = useStore.getState().S.workouts[0]
  const { garminCloudUpload: previousUpload, ...before } = saved
  expect(after).toEqual(before)
  expect(garminCloudUpload).toMatchObject({ status, activityId: 'synthetic-activity', error: null })
  expect(retry.textContent).toBe(status === 'duplicate' ? 'Already in Garmin Connect' : 'Uploaded to Garmin Connect')
  expect(retry.disabled).toBe(true)
  click(retry)
  expect(bridge.upload).toHaveBeenCalledOnce()
})
