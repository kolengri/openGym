import assert from 'node:assert/strict';
import {readFile, writeFile} from 'node:fs/promises';
import {homedir} from 'node:os';
import {createHash} from 'node:crypto';
import {chromium} from '../../first-exercise-3d/runtime/node_modules/playwright-core/index.mjs';

const root = new URL('./', import.meta.url), source = new URL('../../bodyweight-next-five/', root);
const samples = JSON.parse(await readFile(new URL('pose-samples.json', source)));
const surfaces = JSON.parse(await readFile(new URL('runtime-surface-reference.json', source)));
const ids = ['5265', '4007', '6428', '10565', '6560'];
const configFrom = html => JSON.parse(html.match(/<script id="heat-data" type="application\/json">(.*?)<\/script>/s)[1]);
const config = configFrom(await readFile(new URL('viewer.html', root), 'utf8'));
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
 assert.equal(value.action, 'Exercise_' + id); assert.equal(value.meshes, 1); assert.equal(value.bones, 51);
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
 const result = [], contacts = [], mechanics = []; let maximumJointError = 0, maximumSurfaceError = 0;
 for (const id of ids) {
  await page.locator(`#exercises button[data-id="${id}"]`).click();
  assert.equal(await page.locator(`#exercises button[data-id="${id}"]`).getAttribute('aria-pressed'), 'true');
  const sourceSamples = samples.filter(row => row.id === id); assert.ok(sourceSamples.length >= 3);
  let jointError = 0;
  const jointSamples = [];
  for (const sample of sourceSamples) {
   await page.evaluate(time => window.heatFrame(time), sample.frame / 30);
   const state = await probe(page); assertState(state, id);
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
  if (id === '5265') {
   for (const [time, kneeSide, oppositeSide] of [[2, 'Left', 'Right'], [6, 'Right', 'Left']]) {
    await page.evaluate(time => window.heatFrame(time), time);
    const joints = (await probe(page)).joints;
    const distance = (a, b) => Math.hypot(...joints[a].map((value, axis) => value - joints[b][axis]));
    const crossed = distance(kneeSide + 'Leg', oppositeSide + 'ForeArm');
    const sameSide = distance(kneeSide + 'Leg', kneeSide + 'ForeArm');
    assert.ok(crossed < sameSide, `Bicycle twists toward the same-side elbow at ${time}s`);
    // Blender front is -Y, converted to +Three.jsZ.
    assert.ok(joints[oppositeSide + 'Arm'][2] > joints[kneeSide + 'Arm'][2], 'The opposite shoulder turns away from the raised knee');
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
   maximumSurfaceError = Math.max(maximumSurfaceError, Math.abs(floor - row.global_floor_z));
   const patches = {};
   for (const [name, patch] of Object.entries(row.patches)) {
    const values = patch.indices.map(id => actual[id][1]);
    const min = Math.min(...values), max = Math.max(...values);
    maximumSurfaceError = Math.max(maximumSurfaceError, Math.abs(min - patch.min_z), Math.abs(max - patch.max_z));
    patches[name] = {min_z: min, max_z: max};
   }
   contacts.push({id, frame: row.frame, global_floor_z: floor, patches});
  }
  const exercise = config.exercises.find(item => item.id === id), hold = exercise.phases.find(phase => phase.label === 'Удержание');
  if (exercise.displayMode === 'stretch') assert.ok(hold && hold.end - hold.start >= 20 && hold.end - hold.start <= 30);
  const reviewTime = hold ? (hold.start + hold.end) / 2 : (await probe(page)).duration / 4;
  await page.evaluate(time => window.heatFrame(time), reviewTime);
  const lit = await pixels(page), state = await probe(page); assertState(state, id);
  assert.ok(state.primary.filter(value => value > .04 && value < .7).length > 100, `${id}: no soft gradient`);
  assert.ok(exercise.displayMode === 'stretch' ? lit.cyan > 100 && lit.warm === 0 : lit.warm > 100 && lit.cyan < 50,
   `${id}: missing or wrong muscle palette: ${JSON.stringify({warm: lit.warm, cyan: lit.cyan})}`);
  await page.locator('#zones').uncheck(); const off = await pixels(page);
  assert.equal(off.warm, 0); assert.equal(off.cyan, 0); await page.locator('#zones').check();
  if (id === ids[0]) await writeFile(new URL('poster.png', root), Buffer.from(lit.data.split(',')[1], 'base64'));
  await page.screenshot({path: new URL(`review-${id}.png`, root).pathname});
  result.push({id, duration: state.duration, maxJointErrorMeters: jointError, reviewTime, warmPixels: lit.warm, cyanPixels: lit.cyan,
   sourceSurfacePhases: rows.length, displayMode: state.displayMode, holdSeconds: hold ? hold.end - hold.start : null});
 }
 assert.ok(maximumSurfaceError < .0001, `Exported support surfaces differ by ${maximumSurfaceError}m`);
 await page.locator('#exercises button').first().click();
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
 await mobile.locator('#exercises button[data-id="6560"]').tap(); assertState(await probe(mobile), '6560');
 await mobile.evaluate(() => window.heatFrame(5)); await mobile.screenshot({path: new URL('mobile.png', root).pathname});
 assert.equal(await page.locator('video').count(), 0); assert.deepEqual(errors, []); assert.deepEqual(mediaRequests, []);
 const report = {ok: true, scope: 'Actual Three.js/Chromium/Metal and mobile touch emulation; no physical device or production application integration claim.',
  model_sha256: createHash('sha256').update(await readFile(new URL('next-five.glb', source))).digest('hex'),
  exercises: result, mechanics, maxJointErrorMeters: maximumJointError, maxSurfaceParityErrorMeters: maximumSurfaceError,
  transparentCanvas: true, colorTextures: 0, shadows: false, ao: false, noVideo: true, mediaRequests,
  switchingFiveActions: true, touchOrbit: true, pinch: true, reset: true, seekEndResume: true,
  backgrounds: ['white', 'dark', 'checker'], noOverflowWidths: [320, 768, 1024, 1440], errors};
 await writeFile(new URL('runtime-contacts.json', root), JSON.stringify(contacts, null, 2) + '\n');
 await writeFile(new URL('verification.json', root), JSON.stringify(report, null, 2) + '\n');
 console.log(JSON.stringify(report));
} finally {await browser.close();}
