// @vitest-environment happy-dom
import React, { act } from 'react'
import { createRoot } from 'react-dom/client'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { useStore, DEF } from '../store/useStore.js'
import { _setGarminCloudPluginForTest } from '../lib/garmin-cloud.js'
import { garminHealthArchive } from '../lib/garmin-health.js'
import { todayISO } from '../lib/format.js'
import GarminHealthSettings from './GarminHealthSettings.jsx'
import { shareExport } from '../lib/mobile.js'
vi.mock('../lib/mobile.js', async original => ({ ...await original(), shareExport: vi.fn(async () => true) }))
let root, host, bridge, rows
beforeEach(() => {
  shareExport.mockClear()
  globalThis.IS_REACT_ACT_ENVIRONMENT = true
  const S = structuredClone(DEF); S.garminCloudSessionId = 'synthetic-session'
  useStore.setState({ S, user: null })
  rows = new Map()
  vi.spyOn(garminHealthArchive, 'read').mockImplementation(async (_, d, m) => rows.get(d + m))
  vi.spyOn(garminHealthArchive, 'write').mockImplementation(async (_, r) => rows.set(r.date + r.metric, r))
  bridge = {
    healthMetrics: vi.fn(async () => ({ metrics: [{ id: 'body_composition', label: 'Body composition' }] })),
    readHealthMetric: vi.fn(async o => ({ ...o, status: 'available', data: { dateWeightList: [{ date: Date.now(), weight: 78257 }] } })),
  }
  _setGarminCloudPluginForTest(bridge)
  host = document.createElement('div'); document.body.appendChild(host); root = createRoot(host)
})
afterEach(() => { act(() => root.unmount()); host.remove(); vi.restoreAllMocks() })
const button = text => [...host.querySelectorAll('button')].find(b => b.textContent.trim() === text)
it('reads explicit health data, reports progress and shows archived metrics', async () => {
  await act(async () => root.render(<GarminHealthSettings connected />))
  expect(host.querySelector('input[aria-label="From"]').value).toBe(todayISO())
  const period = host.querySelector('.garmin-health-period')
  expect(period.open).toBe(false)
  expect(host.querySelector('input[aria-label="From"]').closest('details')).toBe(period)
  expect(button('Read Garmin health data').closest('details')).toBeNull()
  expect(button('Read Garmin health data').compareDocumentPosition(host.querySelector('.garmin-health-summary')) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
  expect(host.querySelector('.garmin-health-summary').compareDocumentPosition(period) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
  await act(async () => button('Read Garmin health data').click())
  expect(bridge.readHealthMetric).toHaveBeenCalledOnce()
  expect(useStore.getState().S.bodyweight[0].w).toBe(78.3)
  expect(host.textContent).toContain('Available: 1. No data: 0. Errors: 0. Weigh-ins added: 1.')
  expect(host.querySelector('[role="status"]').closest('details')).toBeNull()
  expect(host.querySelector('.garmin-health-archive > summary').textContent).toBe('Saved readings')
  expect(host.querySelector('.garmin-health-archive').open).toBe(false)
  expect(host.querySelector('.garmin-health-archive details > summary').textContent).toBe('Body composition')
  expect(button('Export Garmin health data')).toBeTruthy()
})
it('keeps reading disabled before an explicit Garmin connection', async () => {
  await act(async () => root.render(<GarminHealthSettings connected={false} />))
  expect(button('Read Garmin health data').disabled).toBe(true)
  expect(host.querySelector('.garmin-health-reason').textContent).toBe('Garmin Connect must be ready before reading health data.')
  expect(host.querySelector('.garmin-health-reason').closest('details')).toBeNull()
  expect(bridge.readHealthMetric).not.toHaveBeenCalled()
})

it.each(['unmount', 'session', 'profile'])('does not refresh connection status after the initiating %s changes', async change => {
  let finish
  bridge.readHealthMetric.mockImplementation(options => new Promise(resolve => { finish = () => resolve({ ...options, status: 'error', error: 'auth_required' }) }))
  const changed = vi.fn()
  await act(async () => root.render(<GarminHealthSettings connected onStatusChange={changed} />))
  await act(async () => { button('Read Garmin health data').click() })
  expect(finish).toBeTypeOf('function')
  await act(async () => {
    if (change === 'unmount') root.render(null)
    else if (change === 'session') useStore.getState().update(s => { s.garminCloudSessionId = 'another-session' })
    else useStore.setState({ user: { id: 'another-profile' } })
    finish()
  })
  expect(changed).not.toHaveBeenCalled()
})
it.each([
  ['auth_exchange_failed', 'Garmin could not authorize this phone. Try signing in again later.'],
  ['auth_expired', 'Your Garmin Connect session has expired.'],
  ['network_error', 'Check your connection and retry.'],
  ['profile_unavailable', 'Could not verify the Garmin account.'],
])('shows the native renewal failure and stops the health batch: %s', async (error, message) => {
  bridge.healthMetrics.mockResolvedValue({ metrics: [{ id: 'body_composition', label: 'Body composition' }, { id: 'sleep', label: 'Sleep' }] })
  bridge.readHealthMetric.mockImplementation(async o => ({ date: o.date, metric: o.metric, status: 'error', error }))
  await act(async () => root.render(<GarminHealthSettings connected />))
  await act(async () => button('Read Garmin health data').click())
  expect(bridge.readHealthMetric).toHaveBeenCalledOnce()
  expect(host.querySelector('[role="alert"]').textContent).toContain(message)
  expect(host.querySelector('[role="alert"]').closest('details')).toBeNull()
})
it('shows archived health cards while disconnected without starting health requests', async () => {
  rows.set(todayISO() + 'body_composition', { date: todayISO(), metric: 'body_composition', status: 'available', data: { dateWeightList: [{ date: '2026-10-19T12:00:00', weight: 78257 }] } })
  await act(async () => root.render(<GarminHealthSettings connected={false} />))
  expect(host.querySelector('.garmin-health-summary').textContent).toContain('78.3 kg')
  expect(host.querySelector('time').dateTime).toBe('2026-10-19')
  expect(host.querySelector('.garmin-health-archive').textContent).toContain('date Weight List')
  expect(bridge.readHealthMetric).not.toHaveBeenCalled()
  await act(async () => useStore.setState({ S: { ...useStore.getState().S, unit: 'lb' } }))
  expect(host.querySelector('.garmin-health-summary').textContent).toContain('172.5 lb')
})
it('clears another profile’s cards while its archive read is pending and ignores a late previous result', async () => {
  const hold = deferred()
  garminHealthArchive.read.mockImplementation(owner => owner === null ? hold.promise : Promise.resolve(undefined))
  await act(async () => root.render(<GarminHealthSettings connected={false} />))
  await act(async () => useStore.setState({ user: { id: 'other' } }))
  await act(async () => hold.resolve({ date: todayISO(), metric: 'body_composition', status: 'available', data: { dateWeightList: [{ date: Date.now(), weight: 78257 }] } }))
  expect(host.querySelector('.garmin-health-summary').textContent).not.toContain('78.3')
  expect(host.querySelector('.garmin-health-summary').textContent.match(/No saved reading/g)).toHaveLength(4)
  expect(bridge.readHealthMetric).not.toHaveBeenCalled()
})
const deferred = () => { let resolve; const promise = new Promise(r => { resolve = r }); return { promise, resolve } }
it('exports earlier saved days even when the final day has no readings', async () => {
  const end = todayISO(), day = new Date(Date.parse(end) - 86400000).toISOString().slice(0, 10)
  rows.set(day + 'body_composition', { date: day, metric: 'body_composition', status: 'available', data: { original: [1, 2] } })
  await act(async () => root.render(<GarminHealthSettings connected={false} />))
  const input = host.querySelector('input[aria-label="From"]')
  await act(async () => {
    Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(input, day)
    input.dispatchEvent(new Event('change', { bubbles: true }))
    input.dispatchEvent(new Event('input', { bubbles: true }))
  })
  expect(host.querySelector('.garmin-health-archive details')).toBeNull()
  host.querySelector('.garmin-health-archive').open = true
  await act(async () => button('Export Garmin health data').click())
  expect(shareExport).toHaveBeenCalledOnce()
  expect(JSON.parse(shareExport.mock.calls[0][0]).readings).toEqual([rows.get(day + 'body_composition')])
})
it('explains an empty period without exporting an empty archive', async () => {
  await act(async () => root.render(<GarminHealthSettings connected />))
  await act(async () => button('Export Garmin health data').click())
  expect(shareExport).not.toHaveBeenCalled()
  expect(host.textContent).toContain('No saved health readings in this period.')
})
for (const cancel of ['button', 'owner ABA', 'session ABA', 'unmount']) it(`does not share after ${cancel} during an archive read`, async () => {
  await act(async () => root.render(<GarminHealthSettings connected />))
  const hold = deferred()
  garminHealthArchive.read.mockImplementation(() => hold.promise)
  act(() => button('Export Garmin health data').click())
  if (cancel === 'unmount') act(() => root.render(null))
  await act(async () => {
    if (cancel === 'button') {
      expect(button('Cancel').closest('details')).toBeNull()
      button('Cancel').click()
    }
    if (cancel === 'owner ABA') { useStore.setState({ user: { id: 'other' } }); useStore.setState({ user: null }) }
    if (cancel === 'session ABA') {
      useStore.getState().update(s => { s.garminCloudSessionId = 'other' })
      useStore.getState().update(s => { s.garminCloudSessionId = 'synthetic-session' })
    }
    hold.resolve({ date: todayISO(), metric: 'body_composition', status: 'available', data: {} })
  })
  expect(shareExport).not.toHaveBeenCalled()
})
