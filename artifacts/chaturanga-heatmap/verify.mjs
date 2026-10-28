import assert from 'node:assert/strict';
import {readFile, writeFile} from 'node:fs/promises';
import {homedir} from 'node:os';
import {chromium} from '../first-exercise-3d/runtime/node_modules/playwright-core/index.mjs';

const root = new URL('./', import.meta.url);
const poses = JSON.parse(await readFile(new URL('../bodyweight-five/pose-samples.json', root))).filter(row => row.id === '5915');
const atlas = JSON.parse(await readFile(new URL('../bodyweight-five/runtime-muscles.json', root)));
const browser = await chromium.launch({headless: true,
 executablePath: homedir() + '/Library/Caches/ms-playwright/chromium_headless_shell-1248/chrome-headless-shell-mac-arm64/chrome-headless-shell', args: ['--use-angle=metal']});
const errors = [], mediaRequests = [];
async function ready(page, filename) {
 page.on('pageerror', error => errors.push(error.message));
 page.on('console', message => {if (message.type() === 'error') errors.push(message.text());});
 page.on('request', request => {if (request.resourceType() === 'media') mediaRequests.push(request.url());});
 await page.goto(new URL(filename, root).href);
 await page.waitForFunction(() => window.heatReady || window.heatError, undefined, {timeout: 60000});
 assert.equal(await page.evaluate(() => window.heatError), undefined);
}
const probe = page => page.evaluate(() => window.heatProbe());
function assertState(value) {
 assert.equal(value.action, 'Exercise_5915'); assert.equal(value.meshes, 1); assert.equal(value.bones, 51);
 assert.equal(value.colorTextures, 0); assert.equal(value.ao, false); assert.equal(value.shadows, false);
 assert.equal(value.transparentCanvas, true); assert.equal(value.cornerAlpha, 0); assert.equal(value.panEnabled, false);
}
function average(field, region) {
 const indices = atlas.regions[region].indices;
 return indices.reduce((sum, id) => sum + field[id], 0) / indices.length;
}
const warmPixels = page => page.evaluate(() => {
 const data = document.querySelector('canvas').toDataURL('image/png');
 // Read the WebGL canvas rather than the CSS backdrop.
 const canvas = document.querySelector('canvas'), gl = canvas.getContext('webgl2');
 const pixels = new Uint8Array(canvas.width * canvas.height * 4); gl.readPixels(0, 0, canvas.width, canvas.height, gl.RGBA, gl.UNSIGNED_BYTE, pixels);
 let warm = 0;
 for (let i = 0; i < pixels.length; i += 4) if (pixels[i + 3] > 250 && pixels[i] > pixels[i + 1] * 1.25 && pixels[i] > pixels[i + 2] * 1.4) warm++;
 return {warm, data};
});
try {
 const page = await browser.newPage({viewport: {width: 728, height: 900}, deviceScaleFactor: 1});
 await ready(page, 'viewer.html'); assertState(await probe(page));
 assert.equal(await page.locator('video').count(), 0);
 let maximumJointError = 0;
 for (const sample of poses) {
  await page.evaluate(time => window.heatFrame(time), sample.frame / 30);
  const state = await probe(page); assertState(state);
  for (const [name, [x, y, z]] of Object.entries(sample.joints)) {
   const expected = [x, z, -y];
   maximumJointError = Math.max(maximumJointError, Math.hypot(...state.joints[name].map((value, axis) => value - expected[axis])));
  }
 }
 assert.ok(maximumJointError < .0001, 'Chaturanga movement changed');
 await page.evaluate(() => window.heatFrame(2));
 const field = await probe(page), lit = await warmPixels(page);
 assert.ok(lit.warm > 1000, 'Missing visible warm area or shader compile failure');
 const leftGlute = average(field.secondary, 'gluteus_maximus.L');
 const rightGlute = average(field.secondary, 'gluteus_maximus.R');
 assert.ok(leftGlute > .25 && rightGlute < .10, 'Unilateral glute heat leaked to the free side');
 assert.ok(average(field.primary, 'triceps_long.L') > .35);
 assert.ok(field.primary.filter(value => value > .04 && value < .7).length > 400, 'Missing gradual heat falloff');
 await writeFile(new URL('poster.png', root), Buffer.from(lit.data.split(',')[1], 'base64'));
 await page.locator('#zones').uncheck();
 const off = await warmPixels(page); assert.equal(off.warm, 0);
 await page.locator('#zones').check();
 for (const background of ['white', 'dark', 'checker']) {
  await page.locator('#background').selectOption(background); assertState(await probe(page));
 }
 await page.locator('#background').selectOption('dark');
 await page.screenshot({path: new URL('desktop.png', root).pathname});
 await page.locator('#view').selectOption('front'); assert.equal((await probe(page)).viewportCount, 1);
 await page.locator('#view').selectOption('back'); assert.equal((await probe(page)).viewportCount, 1);
 await page.locator('#view').selectOption('dual');
 await page.locator('#timeline').fill('4'); await page.locator('#timeline').dispatchEvent('input');
 await page.locator('#play').click();
 await page.waitForFunction(() => window.heatProbe().time > .15 && window.heatProbe().time < 3.8);
 const resumed = await probe(page); assert.equal(resumed.playing, true);
 assert.notDeepEqual(resumed.joints.LeftForeArm, field.joints.LeftForeArm);
 await page.waitForFunction(time => window.heatProbe().time > time + .2, resumed.time);
 assert.notDeepEqual((await probe(page)).joints.LeftForeArm, resumed.joints.LeftForeArm, 'The pose froze after seeking to the endpoint');
 const mobile = await browser.newPage({viewport: {width: 390, height: 900}, deviceScaleFactor: 1, isMobile: true, hasTouch: true});
 await ready(mobile, 'viewer.html'); const before = await probe(mobile); assertState(before);
 assert.equal(before.viewportCount, 2);
 assert.equal(await mobile.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
 const bounds = await mobile.locator('canvas').boundingBox(); assert.ok(bounds.height > bounds.width, 'Expected stacked mobile views');
 const cdp = await mobile.context().newCDPSession(mobile);
 const touch = (type, points) => cdp.send('Input.dispatchTouchEvent', {type, touchPoints: points.map(([x, y], id) => ({x, y, id}))});
 const x = bounds.x + bounds.width * .45, y = bounds.y + bounds.height * .25;
 await touch('touchStart', [[x, y]]);
 for (let i = 1; i <= 5; i++) await touch('touchMove', [[x + i * 8, y + i * 3]]);
 await touch('touchEnd', []);
 const rotated = await probe(mobile);
 for (let i = 0; i < 2; i++) assert.ok(Math.hypot(...rotated.cameras[i].position.map((v, axis) => v - before.cameras[i].position[axis])) > .02);
 assert.equal(rotated.playing, true);
 await mobile.waitForFunction(time => window.heatProbe().time !== time, rotated.time);
 await touch('touchStart', [[x - 30, y], [x + 30, y]]);
 for (let i = 1; i <= 4; i++) await touch('touchMove', [[x - 30 - i * 5, y], [x + 30 + i * 5, y]]);
 await touch('touchEnd', []);
 const zoomed = await probe(mobile); assert.ok(zoomed.cameras[0].zoom > rotated.cameras[0].zoom);
 assert.equal(zoomed.cameras[0].zoom, zoomed.cameras[1].zoom);
 await mobile.locator('#reset').tap();
 const reset = await probe(mobile);
 assert.deepEqual(reset.cameras, before.cameras);
 await mobile.evaluate(() => window.heatFrame(2));
 await mobile.screenshot({path: new URL('mobile.png', root).pathname});
 const report = {ok: true, scope: 'Actual Three.js / Chromium / Metal, desktop and mobile touch emulation; physical devices and application integration await approval.',
  action: field.action, maxJointErrorMeters: maximumJointError, videoElements: 0, mediaRequests,
  transparentCanvas: true, colorTextures: 0, shadows: false, ao: false,
  warmPixelsEnabled: lit.warm, warmPixelsDisabled: off.warm, unilateralGluteField: {left: leftGlute, right: rightGlute},
  softIntermediateSourceVertices: field.primary.filter(value => value > .04 && value < .7).length,
  linkedTouchOrbit: true, linkedPinch: true, reset: true, seekEndResume: true, mobileStackedViews: true, mobileOverflow: false, errors};
 assert.deepEqual(errors, []); assert.deepEqual(mediaRequests, []);
 await writeFile(new URL('verification.json', root), JSON.stringify(report, null, 2) + '\n');
 console.log(JSON.stringify(report));
} finally {await browser.close();}
