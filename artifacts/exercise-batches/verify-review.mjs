import assert from 'node:assert/strict';
import {readFile, writeFile} from 'node:fs/promises';
import {homedir} from 'node:os';
import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';
import {chromium} from '../first-exercise-3d/runtime/node_modules/playwright-core/index.mjs';

export async function verifyReview(batch) {
const root = new URL(`./batch-${batch}/`, import.meta.url);
const manifest = JSON.parse(await readFile(new URL('build-manifest.json', root)));
const ids = manifest.exercise_ids, samples = [], surfaceSamples = [];
if (batch === '002') {
 const source = new URL('../bodyweight-next-five/', import.meta.url);
 samples.push(...JSON.parse(await readFile(new URL('pose-samples.json', source))).filter(row => !['10565', '6560'].includes(row.id)));
 samples.push(...JSON.parse(await readFile(new URL('ninety-pose-samples.json', source))));
 const reference = JSON.parse(await readFile(new URL('runtime-surface-reference.json', source)));
 surfaceSamples.push(...(Array.isArray(reference) ? reference : reference.samples).filter(row => !['10565', '6560'].includes(row.id)));
 const ninety = JSON.parse(await readFile(new URL('ninety-runtime-surface-reference.json', source)));
 surfaceSamples.push(...(Array.isArray(ninety) ? ninety : ninety.samples));
} else {
 for (const id of ids) {
  const directory = new URL(`assets/${id}/`, root);
  samples.push(...JSON.parse(await readFile(new URL('pose-samples.json', directory))));
  const reference = JSON.parse(await readFile(new URL('runtime-surface-reference.json', directory)));
  surfaceSamples.push(...(Array.isArray(reference) ? reference : reference.samples));
 }
}
const surfaces = {samples: surfaceSamples};
const configFrom = html => JSON.parse(html.match(/<script id="heat-data" type="application\/json">(.*?)<\/script>/s)[1]);
const config = configFrom(await readFile(new URL('viewer.html', root), 'utf8'));
const dqReferences = [];
for (const exercise of config.exercises.filter(item => item.skinning === 'dualQuaternion')) {
 const directory = batch === '002' ? new URL('../bodyweight-next-five/', import.meta.url) : new URL(`assets/${exercise.id}/`, root);
 const reference = JSON.parse(gunzipSync(await readFile(new URL(batch === '002' ? 'ninety-dq-reference.json.gz' : 'dq-reference.json.gz', directory))));
 const sourceBytes = await readFile(new URL(batch === '002' ? 'ninety-repaired.blend' : 'source.blend', directory));
 if (reference.source_sha256 !== createHash('sha256').update(sourceBytes).digest('hex')) throw Error('Stale native DQ reference: ' + exercise.id);
 dqReferences.push(...reference.samples.filter(row => row.id === exercise.id));
}
const browser = await chromium.launch({headless: true,
 executablePath: homedir() + '/Library/Caches/ms-playwright/chromium_headless_shell-1248/chrome-headless-shell-mac-arm64/chrome-headless-shell', args: ['--use-angle=metal']});
const errors = [], mediaRequests = [];
async function ready(page) {
 page.on('pageerror', error => errors.push(error.message));
 page.on('console', message => {if (message.type() === 'error') errors.push(message.text());});
 page.on('request', request => {if (request.resourceType() === 'media') mediaRequests.push(request.url());});
 await page.goto(new URL('viewer.html', root).href);
 await page.waitForFunction(() => window.heatReady || window.heatError, undefined, {timeout: 60000});
 assert.equal(await page.evaluate(() => window.heatError), undefined);
}
const probe = page => page.evaluate(() => window.heatProbe());
function assertState(value, id) {
 const exercise = config.exercises.find(item => item.id === id);
 assert.equal(value.action, 'Exercise_' + id); assert.equal(value.meshes, 1); assert.equal(value.bones, exercise.expectedBones);
 assert.equal(value.asset, exercise.asset);
 assert.equal(value.skinning, exercise.skinning);
 assert.equal(value.colorTextures, 0); assert.equal(value.ao, false); assert.equal(value.shadows, false);
 assert.equal(value.transparentCanvas, true); assert.equal(value.cornerAlpha, 0); assert.equal(value.panEnabled, false);
}
const pixels = page => page.evaluate(() => {
 const canvas = document.querySelector('canvas'), gl = canvas.getContext('webgl2');
 const data = new Uint8Array(canvas.width * canvas.height * 4);
 gl.readPixels(0, 0, canvas.width, canvas.height, gl.RGBA, gl.UNSIGNED_BYTE, data);
 let warm = 0, cyan = 0;
 for (let i = 0; i < data.length; i += 4) {
  if (data[i + 3] < 250) continue;
  if (data[i] > data[i + 1] * 1.25 && data[i] > data[i + 2] * 1.4) warm++;
  if (data[i + 2] > data[i] * 1.25 && data[i + 1] > data[i] * 1.15) cyan++;
 }
 return {warm, cyan, data: canvas.toDataURL('image/png')};
});
try {
 const page = await browser.newPage({viewport: {width: 728, height: 950}, deviceScaleFactor: 1});
 await ready(page); assert.equal(await page.locator('#exercises button').count(), 5);
 assert.equal(await page.evaluate(async ([first, last]) => {
  await Promise.all([window.heatSelect(first), window.heatSelect(last)]);
  return window.heatProbe().exerciseId;
 }, [ids[0], ids.at(-1)]), ids.at(-1), 'A stale asset load replaced the latest selection');
 const result = [], contacts = [], mechanics = []; let maximumJointError = 0, maximumSurfaceError = 0, maximumDQError = 0;
 for (const id of ids) {
  await page.locator(`#exercises button[data-id="${id}"]`).click();
  await page.waitForFunction(id => window.heatProbe().exerciseId === id && document.querySelector('#loading').hidden, id);
  assert.equal(await page.locator(`#exercises button[data-id="${id}"]`).getAttribute('aria-pressed'), 'true');
  const sourceSamples = samples.filter(row => row.id === id); assert.ok(sourceSamples.length >= 3);
  let jointError = 0;
  const jointSamples = [];
  for (const sample of sourceSamples) {
   await page.evaluate(time => window.heatFrame(time), sample.frame / 30);
   const state = await probe(page); assertState(state, id);
   if (['5265', '4007', '6428'].includes(id)) assert.ok(state.morphWeights.flat().every(value => Math.abs(value) < 1e-6), `${id}: a corrective leaked into an unchanged action`);
   jointSamples.push(state.joints);
   const frusta = await page.evaluate(() => window.heatFrustum());
   assert.ok(frusta.every(({min, max}) => [...min, ...max].every(value => Math.abs(value) < 1)), `${id}: a recommended view crops the posed body at frame${sample.frame}: ${JSON.stringify(frusta)}`);
   for (const [name, [x, y, z]] of Object.entries(sample.joints)) {
    const expected = [x, z, -y];
    jointError = Math.max(jointError, Math.hypot(...state.joints[name].map((v, axis) => v - expected[axis])));
   }
  }
  assert.ok(jointError < .0001, `${id}: exported joints differ from authored action`);
  maximumJointError = Math.max(maximumJointError, jointError);
  if (config.exercises.find(item => item.id === id).skinning === 'dualQuaternion') {
   const witnesses = dqReferences.filter(row => row.id === id); assert.ok(witnesses.length >= 3, 'Missing full native DQ witnesses');
   let error = 0;
   for (const witness of witnesses) {
    await page.evaluate(time => window.heatFrame(time), witness.frame / 30);
    const actual = await page.evaluate(() => window.heatSurface());
    assert.equal(witness.positions.length, 10582);
    for (const [index, [x, y, z]] of witness.positions.entries())
     error = Math.max(error, Math.hypot(actual[index][0] - x, actual[index][1] - z, actual[index][2] + y));
   }
   assert.ok(error < .0001, `${id}: CPU dual-quaternion skin differs from native Blender by${error}m`);
   maximumDQError = Math.max(maximumDQError, error);
   mechanics.push({id, fullNativeDQWitnesses: witnesses.length, maxAllVertexDQErrorMeters: error});
  }
  if (['5265', '0003'].includes(id)) {
   const crossPeaks = id === '0003'
    ? [[1.25, 'Left', 'Right'], [3.75, 'Right', 'Left']]
    : [[2, 'Left', 'Right'], [6, 'Right', 'Left']];
   for (const [time, kneeSide, oppositeSide] of crossPeaks) {
    await page.evaluate(time => window.heatFrame(time), time);
    const joints = (await probe(page)).joints;
    const distance = (a, b) => Math.hypot(...joints[a].map((value, axis) => value - joints[b][axis]));
    const crossed = distance(kneeSide + 'Leg', oppositeSide + 'ForeArm');
    const sameSide = distance(kneeSide + 'Leg', kneeSide + 'ForeArm');
    assert.ok(crossed < sameSide, `Bicycle twists toward the same-side elbow at ${time}s`);
    // Blender front is -Y, converted to +Three.jsZ.
    if (id === '5265') assert.ok(joints[oppositeSide + 'Arm'][2] > joints[kneeSide + 'Arm'][2], 'The opposite shoulder turns away from the raised knee');
    mechanics.push({id, time, kneeSide, oppositeSide, crossedElbowKneeMeters: crossed, sameSideElbowKneeMeters: sameSide});
   }
  } else if (['4007', '6428'].includes(id)) {
   let footDrift = 0;
   for (const joints of jointSamples) for (const name of ['LeftFoot', 'RightFoot'])
    footDrift = Math.max(footDrift, Math.hypot(...joints[name].map((value, axis) => value - jointSamples[0][name][axis])));
   assert.ok(footDrift < .0001, `${id}: feet moved during the heel reach`);
   mechanics.push({id, maxAnkleDriftMeters: footDrift, footMode: id === '4007' ? 'airborne' : 'planted'});
  }
  const rows = (Array.isArray(surfaces) ? surfaces : surfaces.samples).filter(row => row.id === id);
  assert.ok(rows.length >= 3, `${id}: missing actual-surface references`);
  for (const row of rows) {
   await page.evaluate(time => window.heatFrame(time), row.frame / 30);
   const actual = await page.evaluate(() => window.heatSurface());
   assert.equal(Object.keys(actual).length, 10582);
   const floor = Math.min(...Object.values(actual).map(point => point[1]));
   assert.ok(Math.abs(floor - row.global_floor_z) < .0001,
    `${id} frame${row.frame}: actual floor${floor}, native reference${row.global_floor_z}`);
   maximumSurfaceError = Math.max(maximumSurfaceError, Math.abs(floor - row.global_floor_z));
   const patches = {};
   for (const [name, patch] of Object.entries(row.patches)) {
    const values = patch.indices.map(id => actual[id][1]);
    const min = Math.min(...values), max = Math.max(...values);
    assert.ok(Math.max(Math.abs(min - patch.min_z), Math.abs(max - patch.max_z)) < .0001,
     `${id} frame${row.frame} patch${name}: actual[${min},${max}], native[${patch.min_z},${patch.max_z}]`);
    maximumSurfaceError = Math.max(maximumSurfaceError, Math.abs(min - patch.min_z), Math.abs(max - patch.max_z));
    patches[name] = {min_z: min, max_z: max};
   }
   contacts.push({id, frame: row.frame, global_floor_z: floor, patches});
  }
  const exercise = config.exercises.find(item => item.id === id), hold = exercise.phases.find(phase => phase.label === 'Удержание');
  if (exercise.displayMode === 'stretch') {
   assert.equal((await probe(page)).duration, 5, 'The stretch demonstration must last5seconds');
   assert.ok(hold && hold.start === 2 && hold.end === 3, 'The compressed demonstration must hold for exactly1second');
   assert.ok(exercise.note.includes('20–30'), 'Preserve the source workout hold separately from demonstration timing');
   await page.evaluate(() => window.heatFrame(0)); await page.locator('#play').click();
   const playback = await page.evaluate(() => new Promise((resolve, reject) => {
    const targets = [.4, 1.5, 2.1, 2.9, 3.5, 4.7], samples = [];
    const started = performance.now(); let previous = 0;
    function sample() {
     const {time, joints} = window.heatProbe();
     if (samples.length < targets.length && time >= targets[samples.length]) samples.push({time, joints});
     if (previous > 4 && time < .5) return resolve({samples, wrapTime: time, wallSeconds: (performance.now() - started) / 1000});
     if (performance.now() - started > 12000) return reject(Error('The live5second stretch loop did not wrap'));
     previous = time; requestAnimationFrame(sample);
    }
    requestAnimationFrame(sample);
   }));
   assert.equal(playback.samples.length, 6);
   const distance = (a, b) => Math.max(...Object.keys(a).map(name => Math.hypot(...a[name].map((value, axis) => value - b[name][axis]))));
   const poses = playback.samples.map(sample => sample.joints);
   const holdDrift = distance(poses[2], poses[3]);
   assert.ok(holdDrift < .0001, `${id}: actual pose drifts during the1second hold`);
   assert.ok(distance(poses[0], poses[1]) > .01, `${id}: the actual hinge does not move`);
   assert.ok(distance(poses[4], poses[5]) > .01, `${id}: the actual return does not move`);
   mechanics.push({id, livePlayback: {durationSeconds: 5, holdSeconds: 1, sampleTimes: playback.samples.map(sample => sample.time),
    holdDriftMeters: holdDrift, wallSeconds: playback.wallSeconds, wrapObserved: true}});
  }
  const reviewTime = hold ? (hold.start + hold.end) / 2 : (await probe(page)).duration / 4;
  await page.evaluate(time => window.heatFrame(time), reviewTime);
  const lit = await pixels(page), state = await probe(page); assertState(state, id);
  assert.ok(state.primary.filter(value => value > .04 && value < .7).length > 100, `${id}: no soft gradient`);
  assert.ok(exercise.displayMode === 'stretch' ? lit.cyan > 100 && lit.warm === 0 : lit.warm > 100 && lit.cyan < 50,
   `${id}: missing or wrong muscle palette: ${JSON.stringify({warm: lit.warm, cyan: lit.cyan})}`);
  await page.locator('#zones').uncheck(); const off = await pixels(page);
  assert.equal(off.warm, 0); assert.equal(off.cyan, 0); await page.locator('#zones').check();
  if (id === config.initialExerciseId) await writeFile(new URL('poster.png', root), Buffer.from(lit.data.split(',')[1], 'base64'));
  await page.screenshot({path: new URL(`review-${id}.png`, root).pathname});
  result.push({id, duration: state.duration, maxJointErrorMeters: jointError, reviewTime, warmPixels: lit.warm, cyanPixels: lit.cyan,
   sourceSurfacePhases: rows.length, displayMode: state.displayMode, holdSeconds: hold ? hold.end - hold.start : null, asset: state.asset, bones: state.bones});
 }
 assert.ok(maximumSurfaceError < .0001, `Exported support surfaces differ by ${maximumSurfaceError}m`);
 await page.locator('#exercises button').first().click();
 await page.waitForFunction(id => window.heatProbe().exerciseId === id, ids[0]);
 const duration = (await probe(page)).duration;
 await page.locator('#timeline').fill(String(duration)); await page.locator('#timeline').dispatchEvent('input');
 await page.locator('#play').click();
 await page.waitForFunction(() => window.heatProbe().time > .15 && window.heatProbe().time < 1);
 const resumed = await probe(page);
 await page.waitForFunction(time => window.heatProbe().time > time + .2, resumed.time);
 assert.notDeepEqual((await probe(page)).joints, resumed.joints, 'Pose froze after endpoint seeking');
 for (const background of ['white', 'dark', 'checker']) {
  await page.locator('#background').selectOption(background); assertState(await probe(page), ids[0]);
 }
 for (const view of ['front', 'back', 'dual']) {
  await page.locator('#view').selectOption(view);
  assert.equal((await probe(page)).viewportCount, view === 'dual' ? 2 : 1);
 }
 for (const width of [320, 768, 1024, 1440]) {
  await page.setViewportSize({width, height: 950});
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false, `Overflow at ${width}px`);
 }
 const mobile = await browser.newPage({viewport: {width: 390, height: 950}, deviceScaleFactor: 1, isMobile: true, hasTouch: true});
 await ready(mobile); await mobile.locator('#view').selectOption('dual'); const before = await probe(mobile);
 const bounds = await mobile.locator('canvas').boundingBox(); assert.ok(bounds.height > bounds.width);
 const cdp = await mobile.context().newCDPSession(mobile);
 const touch = (type, points) => cdp.send('Input.dispatchTouchEvent', {type, touchPoints: points.map(([x, y], id) => ({x, y, id}))});
 const x = bounds.x + bounds.width * .45, y = bounds.y + bounds.height * .25;
 await touch('touchStart', [[x, y]]);
 for (let i = 1; i <= 5; i++) await touch('touchMove', [[x + i * 8, y + i * 3]]);
 await touch('touchEnd', []); const rotated = await probe(mobile);
 for (let i = 0; i < 2; i++) assert.ok(Math.hypot(...rotated.cameras[i].position.map((v, axis) => v - before.cameras[i].position[axis])) > .02);
 assert.equal(rotated.playing, true);
 await mobile.waitForFunction(time => window.heatProbe().time !== time, rotated.time);
 await touch('touchStart', [[x - 30, y], [x + 30, y]]);
 for (let i = 1; i <= 4; i++) await touch('touchMove', [[x - 30 - i * 5, y], [x + 30 + i * 5, y]]);
 await touch('touchEnd', []); const zoomed = await probe(mobile);
 assert.ok(zoomed.cameras[0].zoom > rotated.cameras[0].zoom); assert.equal(zoomed.cameras[0].zoom, zoomed.cameras[1].zoom);
 await mobile.locator('#reset').tap(); assert.deepEqual((await probe(mobile)).cameras, before.cameras);
 await mobile.locator(`#exercises button[data-id="${ids.at(-1)}"]`).tap();
 await mobile.waitForFunction(id => window.heatProbe().exerciseId === id, ids.at(-1)); assertState(await probe(mobile), ids.at(-1));
 await mobile.evaluate(() => window.heatFrame(2.5)); await mobile.screenshot({path: new URL('mobile.png', root).pathname});
 assert.equal(await page.locator('video').count(), 0); assert.deepEqual(errors, []); assert.deepEqual(mediaRequests, []);
 const report = {ok: true, scope: 'Actual Three.js/Chromium/Metal and mobile touch emulation; no physical device or production application integration claim.',
  models: JSON.parse(await readFile(new URL('build-manifest.json', root))).models,
  exercises: result, mechanics, maxJointErrorMeters: maximumJointError, maxSurfaceParityErrorMeters: maximumSurfaceError, maxAllVertexDQErrorMeters: maximumDQError,
  transparentCanvas: true, colorTextures: 0, shadows: false, ao: false, noVideo: true, mediaRequests,
  switchingFiveActions: true, latestSelectionWins: true, touchOrbit: true, pinch: true, reset: true, seekEndResume: true,
  backgrounds: ['white', 'dark', 'checker'], noOverflowWidths: [320, 768, 1024, 1440], errors};
 await writeFile(new URL('runtime-contacts.json', root), JSON.stringify(contacts, null, 2) + '\n');
 await writeFile(new URL('verification.json', root), JSON.stringify(report, null, 2) + '\n');
 console.log(JSON.stringify(report));
} finally {await browser.close();}

}
