import assert from 'node:assert/strict';
import {homedir} from 'node:os';
import {readFile, writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {chromium} from '../../first-exercise-3d/runtime/node_modules/playwright-core/index.mjs';

// Selected diagnostic stills, not an animation frame sequence or runtime cache.
const root = new URL('./', import.meta.url);
const read = async name => JSON.parse(await readFile(new URL(name, root)));
const poses = await read('review-poses.json'), manifest = await read('build-manifest.json');
assert.deepEqual(Object.keys(poses).sort(), [...manifest.exercise_ids].sort());
const hash = value => createHash('sha256').update(value).digest('hex');
const browser = await chromium.launch({headless: true,
 executablePath: homedir() + '/Library/Caches/ms-playwright/chromium_headless_shell-1248/chrome-headless-shell-mac-arm64/chrome-headless-shell',
 args: ['--use-angle=metal']});
try {
 const page = await browser.newPage({viewport: {width: 1200, height: 1100}, deviceScaleFactor: 1});
 const errors = [], evidence = [];
 page.on('pageerror', error => errors.push(error.message));
 await page.goto(new URL('viewer.html', root).href);
 await page.waitForFunction(() => window.heatReady || window.heatError, undefined, {timeout: 60000});
 assert.equal(await page.evaluate(() => window.heatError), undefined);
 for (const [id, samples] of Object.entries(poses)) {
  await page.evaluate(id => window.heatSelect(id), id);
  const duration = await page.evaluate(() => window.heatProbe().duration);
  assert.ok(samples.length >= 3 && samples.every(([, time]) => Number.isFinite(time) && time >= 0 && time <= duration));
  await page.locator('#view').selectOption('dual');
  for (const [label, time] of samples) {
   assert.match(label, /^[a-z0-9-]+$/);
   await page.evaluate(time => window.heatFrame(time), time);
   for (const zones of [false, true]) {
    await page.locator('#zones').setChecked(zones);
    const state = await page.evaluate(() => window.heatProbe());
    assert.equal(state.exerciseId, id); assert.ok(Math.abs(state.time - time) < 1e-5);
    assert.ok(state.drawCalls > 0 && state.triangles > 0, 'No character draw');
    const occupied = await page.locator('canvas').evaluate(canvas => {
     const copy = document.createElement('canvas'); copy.width = canvas.width; copy.height = canvas.height;
     const context = copy.getContext('2d'); context.drawImage(canvas, 0, 0);
     const pixels = context.getImageData(0, 0, copy.width, copy.height).data;
     let count = 0; for (let i = 3; i < pixels.length; i += 4) if (pixels[i]) count++;
     return count;
    });
    assert.ok(occupied > 100, 'Empty character canvas');
    const file = `${zones ? 'zones' : 'neutral'}-${id}-${label}.png`;
    await page.locator('canvas').screenshot({path: new URL(file, root).pathname});
    evidence.push({id, label, time, zones, file, png_sha256: hash(await readFile(new URL(file, root))),
     model: manifest.models[state.asset], skinning: state.skinning, morph_weights: state.morphWeights,
     draw_calls: state.drawCalls, triangles: state.triangles, occupied_pixels: occupied});
   }
  }
 }
 assert.deepEqual(errors, []);
 await writeFile(new URL('capture-peaks.json', root), JSON.stringify({
  scope: 'Selected actual GPU poses in two recommended views, neutral and with soft muscle fields. Natural drawing-buffer aspect; no CSS stretch.',
  viewer_sha256: hash(await readFile(new URL('viewer.html', root))),
  build_manifest_sha256: hash(await readFile(new URL('build-manifest.json', root))),
  pose_plan_sha256: hash(await readFile(new URL('review-poses.json', root))), evidence, errors,
 }, null, 2) + '\n');
 console.log(JSON.stringify({poses: evidence.length / 2, screenshots: evidence.length, errors}));
} finally {await browser.close();}
