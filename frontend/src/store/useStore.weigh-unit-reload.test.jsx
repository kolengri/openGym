// @vitest-environment happy-dom
import { afterEach, expect, it, vi } from 'vitest'
vi.mock('../lib/api.js', () => ({ api: vi.fn(async () => ({})), setRemoteAuth: vi.fn() }))
afterEach(() => localStorage.clear())
it('normalizes explicitly tagged readings when an older local-only client changed the profile unit', async () => {
  localStorage.clear(); vi.resetModules()
  localStorage.setItem('gym_state_v1', JSON.stringify({ unit: 'lb', bwDaily: 'avg', bodyweight: [{
    d: '2026-10-28', w: 178.2, t: 200, insUnit: 'kg',
    ins: [80.2, 80.9, 81.4].map((w, i) => ({ id: String(i), at: `${8 + i}:00`, w, t: i + 10 })),
  }] }))
  const { useStore } = await import('./useStore.js')
  const day = useStore.getState().S.bodyweight[0]
  expect(day.insUnit).toBe('lb')
  expect(day.ins.map(r => r.w)).toEqual([176.8, 178.4, 179.5])
  expect(day.w).toBe(178.23)
})
