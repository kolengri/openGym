// @vitest-environment happy-dom
import React, { act } from 'react'
import { createRoot } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { DEF, useStore } from '../store/useStore.js'
import Health from './Health.jsx'

const mocks = vi.hoisted(() => ({ read: vi.fn(), supported: vi.fn(), nav: vi.fn() }))
vi.mock('../lib/garmin-health.js', async load => ({ ...await load(), garminHealthArchive: { read: (...args) => mocks.read(...args) } }))
vi.mock('../lib/mobile.js', async load => ({ ...await load(), isAndroid: () => mocks.supported() }))
vi.mock('react-router-dom', () => ({ useNavigate: () => mocks.nav }))
vi.mock('../components/DateField.jsx', () => ({ default: ({ value, onChange }) => <input aria-label="Date" value={value} onChange={event => onChange(event.target.value)} /> }))

globalThis.IS_REACT_ACT_ENVIRONMENT = true
let root, host
const flush = () => act(async () => { await Promise.resolve(); await Promise.resolve() })
const sleep = (date, seconds = 28800) => ({ date, metric: 'sleep', status: 'available', fetchedAt: Date.now(), data: { dailySleepDTO: { calendarDate: date, sleepTimeSeconds: seconds } } })
const pending = () => { let resolve; const promise = new Promise(yes => { resolve = yes }); return { promise, resolve } }
const datePick = value => act(() => {
  const input = host.querySelector('input[aria-label="Date"]')
  Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(input, value)
  input.dispatchEvent(new Event('input', { bubbles: true }))
})
beforeEach(() => {
  mocks.read.mockReset(); mocks.supported.mockReset(); mocks.nav.mockReset()
  mocks.supported.mockResolvedValue(true)
  useStore.setState({ S: structuredClone(DEF), user: { id: 'owner-a' } })
  host = document.createElement('div'); document.body.appendChild(host); root = createRoot(host)
})
afterEach(() => { act(() => root.unmount()); host.remove() })
const mount = async () => { await act(async () => root.render(<Health />)); await flush() }

describe('read-only saved health screen', () => {
  it('reads only five known metrics and shows source/date/fetched time without guessing missing values', async () => {
    mocks.read.mockImplementation(async (owner, date, metric) => metric === 'sleep' ? sleep(date) : null)
    await mount()
    expect(mocks.read.mock.calls.map(args => args[2])).toEqual(['body_composition', 'sleep', 'resting_heart_rate', 'heart_rate', 'hrv'])
    expect(mocks.read.mock.calls.every(args => args[0] === 'owner-a')).toBe(true)
    expect(host.textContent).toContain('8h 0m')
    expect(host.textContent).toContain('Garmin Connect · Saved readings')
    expect(host.textContent).toContain('Last synced:')
    expect(host.textContent.match(/No saved reading/g)).toHaveLength(3)
    expect(host.querySelectorAll('.progress-body-tabs button')).toHaveLength(4)
  })
  it('keeps Health selected and routes each other body section explicitly', async () => {
    mocks.read.mockResolvedValue(null)
    await mount()
    const tabs = [...host.querySelectorAll('.progress-body-tabs button')]
    act(() => tabs[2].click())
    expect(mocks.nav).not.toHaveBeenCalled()
    for (const [index, route] of [[0, '/stats?section=body'], [1, '/measurements'], [3, '/progress-photos']]) {
      act(() => tabs[index].click())
      expect(mocks.nav).toHaveBeenLastCalledWith(route)
    }
  })
  it('hides old-owner data immediately and ignores a late result after owner change', async () => {
    const old = pending(), newer = pending()
    mocks.read.mockImplementation((owner, date, metric) => metric !== 'sleep' ? Promise.resolve(null) : (owner === 'owner-a' ? old : newer).promise.then(() => sleep(date, owner === 'owner-a' ? 28800 : 25200)))
    await mount()
    act(() => useStore.setState({ user: { id: 'owner-b' } }))
    expect(host.textContent).not.toContain('8h 0m')
    await flush()
    await act(async () => newer.resolve())
    expect(host.textContent).toContain('7h 0m')
    await act(async () => old.resolve())
    expect(host.textContent).toContain('7h 0m')
    expect(host.textContent).not.toContain('8h 0m')
  })
  it('removes an already displayed owner reading before the replacement owner finishes loading', async () => {
    const next = pending()
    mocks.read.mockImplementation(async (owner, date, metric) => metric !== 'sleep' ? null : owner === 'owner-a' ? sleep(date) : next.promise)
    await mount()
    expect(host.textContent).toContain('8h 0m')
    act(() => useStore.setState({ user: { id: 'owner-b' } }))
    expect(host.textContent).not.toContain('8h 0m')
    expect(host.querySelector('.garmin-health-summary').getAttribute('aria-busy')).toBe('true')
    await flush()
    await act(async () => next.resolve(null))
    expect(host.textContent.match(/No saved reading/g)).toHaveLength(4)
  })
  it('hides old-date data while the selected day loads and rejects mismatched archive dates', async () => {
    const newer = pending()
    mocks.read.mockImplementation(async (owner, date, metric) => metric !== 'sleep' ? null : date === '2026-01-01' ? newer.promise : sleep(date))
    await mount()
    expect(host.textContent).toContain('8h 0m')
    datePick('2026-01-01')
    expect(host.textContent).not.toContain('8h 0m')
    await flush()
    await act(async () => newer.resolve(sleep('2026-01-02')))
    expect(host.textContent).not.toContain('8h 0m')
    expect(host.textContent.match(/No saved reading/g)).toHaveLength(4)
  })
  it('shows unsupported and storage failures explicitly, without network actions', async () => {
    mocks.supported.mockResolvedValue(false)
    await mount()
    expect(host.textContent).toContain('Android app only')
    expect(mocks.read).not.toHaveBeenCalled()
    act(() => root.unmount()); root = createRoot(host)
    mocks.supported.mockResolvedValue(true)
    mocks.read.mockRejectedValue(new Error('storage_error'))
    await mount()
    expect(host.querySelector('[role="alert"]').textContent).toBe('Could not read Garmin health data. Try again.')
    expect(host.textContent.match(/No saved reading/g)).toHaveLength(4)
  })
})
