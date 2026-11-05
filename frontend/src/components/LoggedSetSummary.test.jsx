import React from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { parseHTML } from 'linkedom'
import { expect, it } from 'vitest'
import LoggedSetSummary from './LoggedSetSummary.jsx'
import { setLabel } from '../lib/history.js'

const render = (set, props = {}) => parseHTML(renderToStaticMarkup(<LoggedSetSummary exerciseId="0025" set={set}
  target={{ mode: 'reps' }} effortKind="rpe" {...props} />)).document

it('separates recorded zero-RIR, valid heart rate and load without changing the stored row or legacy label', () => {
  const set = { w: 40, r: 8, rir: 0, done: true, hr: { avg: 120, max: 145 } }
  const snapshot = structuredClone(set)
  const dom = render(set)
  expect(dom.querySelector('.logged-set-load').textContent).toBe('40×8')
  expect(dom.querySelector('.logged-set-effort').textContent).toBe('RPE 10')
  expect(dom.querySelector('.logged-set-heart').textContent).toBe('120/145')
  expect(setLabel('0025', set, { mode: 'reps' })).toContain('(RIR 0)')
  expect(set).toEqual(snapshot)
})

it('keeps drop and rest-pause work in the load column without inventing effort or heart rate', () => {
  const dom = render({ w: 60, r: 14, done: true, type: 'restpause', clusters: [{ r: 4 }], hr: { avg: 0, max: 0 } })
  expect(dom.querySelector('.logged-set-load').textContent).toBe('60×10+4')
  const drop = render({ w: 60, r: 14, done: true, type: 'dropset', drops: [{ w: 40, r: 5 }] })
  expect(drop.querySelector('.logged-set-load').textContent).toBe('60×14 ↘ 40×5')
  expect(dom.querySelector('.logged-set-effort').textContent).toBe('')
  expect(dom.querySelector('.logged-set-heart').textContent).toBe('')
})

it('retains an incomplete side and only shows the completed side rating', () => {
  const dom = render({ w: 20, r: 10, done: false, sides: {
    L: { w: 20, r: 6, rir: 2, done: true }, R: { w: 20, r: 4, rir: 1, done: false },
  } })
  expect(dom.querySelector('.logged-set-load').textContent).toBe('L 20×6 · R –')
  expect(dom.querySelector('.logged-set-effort').textContent).toBe('L RPE 8')
})
