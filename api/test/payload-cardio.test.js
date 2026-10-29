import test from 'node:test';
import assert from 'node:assert/strict';
import { build } from '../coach/core/payload.js';

const now = Date.now();
const workout = (i, sets = [{ km: 4.8, done: true }], target = { mode: 'cardio', sets: 1, km: 5 }) => {
  const start = now - (5 - i) * 86400000;
  return { id: 'cardio-' + i, d: new Date(start).toISOString().slice(0, 10), start, end: start + 1200000,
    entries: [{ id: '2138', target, sets }] };
};
const state = workouts => ({ unit: 'kg', routines: [{ id: 'cardio', name: 'Cardio',
  ex: [{ id: '2138', mode: 'cardio', sets: 1, km: 5 }] }], workouts, week: {} });
const options = kind => ({ handle: 'synthetic-handle', kind, workoutId: 'cardio-0' });

for (const kind of ['debrief', 'review', 'ask']) {
  test(`${kind} payload retains distance goals and results without inventing duration or speed`, () => {
    const S = state([workout(0)]);
    const p = build(S, { ...options(kind), ...(kind === 'ask' ? { today: workout(0) } : {}) });
    assert.equal(p.plan.routines[0].ex[0].km, 5);
    const w = kind === 'debrief' ? p.session : p.window.workouts[0];
    assert.equal(w.entries[0].target.km, 5);
    assert.deepEqual(w.entries[0].sets[0], { done: true, km: 4.8 });
    assert.equal(w.entries[0].target.min, undefined);
    assert.equal(w.entries[0].target.speed, undefined);
    if (kind === 'ask') assert.deepEqual(p.today.entries[0].sets[0], { done: true, km: 4.8 });
  });
}

for (const kind of ['review', 'ask']) {
  test(`${kind} compact cardio retains distance and picks a top set using one measure`, () => {
    const S = state([workout(0, [{ min: 60, done: true }, { km: 2, done: true }, { km: 4.8, rpe: 7, done: true },
      { km: 99, done: false }, { km: 99, done: true, phase: 'warmup' }]), workout(1), workout(2), workout(3)]);
    const p = build(S, options(kind));
    const old = p.window.workouts[0];
    assert.equal(old.compact, true);
    assert.equal(old.entries[0].target, '5km');
    assert.equal(old.entries[0].top, '4.8km@RPE7');
  });
}

test('compact cardio keeps combined measurements and the legacy speed notation', () => {
  for (const [target, set, expectedTarget, expectedTop] of [
    [{ mode: 'cardio', sets: 1, min: 20, km: 5 }, { min: 18, km: 4.8, done: true }, '20min+5km', '18min+4.8km'],
    [{ mode: 'cardio', sets: 1, min: 20, speed: 8 }, { min: 18, speed: 9, done: true }, '20min/8', '18min/9'],
  ]) {
    const p = build(state([workout(0, [set], target), workout(1), workout(2), workout(3)]), options('review'));
    assert.equal(p.window.workouts[0].entries[0].target, expectedTarget);
    assert.equal(p.window.workouts[0].entries[0].top, expectedTop);
  }
});

test('distance fields use the existing numeric allowlist and never carry arbitrary text', () => {
  for (const km of ['private-injected-text', {}, Infinity, NaN]) {
    const S = state([workout(0, [{ km, done: true }], { mode: 'cardio', sets: 1, km })]);
    S.routines[0].ex[0].km = km;
    const p = build(S, options('debrief'));
    assert.equal(p.plan.routines[0].ex[0].km, undefined);
    assert.equal(p.session.entries[0].target.km, undefined);
    assert.deepEqual(p.session.entries[0].sets[0], { done: true });
    assert.ok(!JSON.stringify(p).includes('private-injected-text'));
  }
});
