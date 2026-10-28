// @vitest-environment happy-dom
import React, { act } from 'react'
import { createRoot } from 'react-dom/client'
import { afterEach, beforeEach, expect, it } from 'vitest'
import { setLang } from '../lib/i18n.js'
import GarminHealthSummary from './GarminHealthSummary.jsx'

let root, host
const records = [
  { date: '2026-10-20', metric: 'body_composition', status: 'available', data: { dateWeightList: [{ date: '2026-10-19T12:00:00', weight: 78257 }] } },
  { date: '2026-10-20', metric: 'sleep', status: 'available', data: { dailySleepDTO: { sleepTimeSeconds: 27000 } } },
  { date: '2026-10-20', metric: 'heart_rate', status: 'available', data: { restingHeartRate: 53 } },
  { date: '2026-10-20', metric: 'hrv', status: 'available', data: { hrvSummary: { lastNightAvg: 47.25 } } },
]
beforeEach(async () => {
  globalThis.IS_REACT_ACT_ENVIRONMENT = true
  await setLang('en')
  host = document.createElement('div'); document.body.appendChild(host); root = createRoot(host)
})
afterEach(async () => { act(() => root.unmount()); host.remove(); await setLang('en') })
it('shows accessible cards with established units and actual measurement dates', () => {
  act(() => root.render(<GarminHealthSummary records={records} unit="kg" date="2026-10-20" />))
  expect(host.querySelector('section').getAttribute('aria-labelledby')).toBe(host.querySelector('h4').id)
  expect(host.querySelectorAll('dt')).toHaveLength(4)
  expect(host.textContent).toContain('78.3 kg')
  expect(host.textContent).toContain('7h 30m')
  expect(host.textContent).toContain('53 bpm')
  expect(host.textContent).toContain('47.25')
  expect(host.textContent).toContain('Unit not verified; original Garmin value.')
  expect(host.querySelector('time').dateTime).toBe('2026-10-19')
  expect(host.textContent).not.toContain(' ms')
})
it('uses the selected profile unit and Russian locale, and responds to language changes', async () => {
  act(() => root.render(<GarminHealthSummary records={records} unit="lb" date="2026-10-20" />))
  await act(async () => setLang('ru'))
  expect(host.textContent).toContain('Обзор здоровья')
  expect(host.textContent).toContain('172,5 lb')
  expect(host.textContent).toContain('53 уд/мин')
  expect(host.textContent).toContain('47,25')
  expect(host.textContent).toContain('Единица не подтверждена')
})
it('shows missing and loading states without inventing readings or dates', () => {
  act(() => root.render(<GarminHealthSummary records={[]} date="2026-10-20" />))
  expect(host.querySelectorAll('.garmin-health-summary-value')).toHaveLength(4)
  expect(host.textContent.match(/No saved reading/g)).toHaveLength(4)
  expect(host.querySelector('time')).toBeNull()
  expect(host.textContent).not.toContain('0 bpm')
  act(() => root.render(<GarminHealthSummary records={records} date="" loading />))
  expect(host.querySelector('section').getAttribute('aria-busy')).toBe('true')
  expect(host.textContent).toContain('Choose a date to view saved readings.')
  expect(host.textContent).not.toContain('78.3')
  expect(host.textContent).not.toContain('Invalid Date')
})
