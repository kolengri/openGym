import assert from 'node:assert/strict';
import {homedir} from 'node:os';
import {execFileSync} from 'node:child_process';
import {readFile, writeFile, mkdir, unlink} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {chromium} from '../../../first-exercise-3d/runtime/node_modules/playwright-core/index.mjs';

// Diagnostic stills only. Camera overrides never change the delivered viewer.
const root = new URL('./', import.meta.url), repo = new URL('../../../../', root);
const plan = JSON.parse(await readFile(new URL('capture-plan.json', root)));
const hash = value => createHash('sha256').update(value).digest('hex');
const temporary = new URL('logs/camera-review.html', root), evidence = [], errors = [];
await mkdir(new URL('logs/', root), {recursive: true});
const browser = await chromium.launch({headless: true,
 executablePath: homedir() + '/Library/Caches/ms-playwright/chromium_headless_shell-1248/chrome-headless-shell-mac-arm64/chrome-headless-shell',
 args: ['--use-angle=metal']});
try {
 const page = await browser.newPage({viewport: {width: 1200, height: 1100}, deviceScaleFactor: 1});
 page.on('pageerror', error => errors.push(error.message));
 for (const sample of plan.samples) {
  assert.match(sample.batch, /^00[67]$/); assert.match(sample.id, /^\d+$/);
  assert.match(sample.label, /^[a-z0-9-]+$/); assert.ok(Number.isFinite(sample.time) && sample.time >= 0);
  const batchRoot = new URL(`../../batch-${sample.batch}/`, root);
  const html = await readFile(new URL('viewer.html', batchRoot), 'utf8');
  const manifest = JSON.parse(await readFile(new URL('build-manifest.json', batchRoot)));
  const match = html.match(/<script id="heat-data" type="application\/json">(.*?)<\/script>/s);
  assert.ok(match, 'Missing embedded review configuration');
  const config = JSON.parse(match[1]), exercise = config.exercises.find(item => item.id === sample.id);
  assert.ok(exercise, 'Exercise is absent from the delivered review');
  const model = manifest.models[exercise.asset];
  assert.equal(hash(Buffer.from(config.assets[exercise.asset].model, 'base64')), model.sha256);
  let capturedModel = {path: model.path, sha256: model.sha256};
  if (sample.baseline_revision) {
   assert.match(sample.baseline_revision, /^[a-f0-9]{40}$/);
   const bytes = execFileSync('git', ['show', `${sample.baseline_revision}:${model.path}`], {cwd: repo});
   assert.equal(hash(bytes), sample.baseline_model_sha256);
   config.assets[exercise.asset] = {model: bytes.toString('base64')};
   capturedModel = {...capturedModel, sha256: hash(bytes), revision: sample.baseline_revision};
  }
  if (sample.camera) exercise.cameras = [sample.camera, sample.camera];
  if (sample.camera || sample.baseline_revision) {
   const modified = html.replace(match[0], () => `<script id="heat-data" type="application/json">${JSON.stringify(config)}</script>`);
   await writeFile(temporary, modified); await page.goto(temporary.href + '?capture=' + evidence.length);
  } else await page.goto(new URL('viewer.html', batchRoot).href);
  await page.waitForFunction(() => window.heatReady || window.heatError, undefined, {timeout: 60000});
  const error = await page.evaluate(() => window.heatError); if (error) throw Error(error);
  await page.evaluate(id => window.heatSelect(id), sample.id);
  await page.locator('#view').selectOption(sample.camera ? 'front' : 'dual');
  await page.locator('#zones').setChecked(sample.zones ?? false);
  await page.evaluate(time => window.heatFrame(time), sample.time);
  await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
  const state = await page.evaluate(() => {
   const value = window.heatProbe();
   return {id: value.exerciseId, action: value.action, time: value.time,
    skinning: value.skinning, morph_weights: value.morphWeights, source_vertices: value.sourceVertices,
    draw_calls: value.drawCalls, triangles: value.triangles, frustum_culling: value.frustumCulling};
  });
  assert.equal(state.id, sample.id); assert.ok(Math.abs(state.time - sample.time) < 1e-5);
  assert.ok(state.draw_calls > 0 && state.triangles > 0, 'No character was drawn');
  const occupied = await page.locator('canvas').evaluate(canvas => {
   const copy = document.createElement('canvas'); copy.width = canvas.width; copy.height = canvas.height;
   const context = copy.getContext('2d'); context.drawImage(canvas, 0, 0);
   const pixels = context.getImageData(0, 0, copy.width, copy.height).data;
   let count = 0; for (let index = 3; index < pixels.length; index += 4) if (pixels[index] > 0) count++;
   return count;
  });
  assert.ok(occupied > 100, 'The character canvas is empty');
  const filename = `${sample.batch}-${sample.id}-${sample.label}.png`;
  await page.locator('canvas').screenshot({path: new URL(filename, root).pathname});
  evidence.push({...sample, file: filename, png_sha256: hash(await readFile(new URL(filename, root))),
   source_viewer_sha256: hash(html), source_manifest_sha256: hash(await readFile(new URL('build-manifest.json', batchRoot))),
   model: capturedModel, state, occupied_pixels: occupied});
 }
 assert.deepEqual(errors, []);
 await writeFile(new URL('capture.json', root), JSON.stringify({
  scope: 'Selected actual GPU feedback poses. Hand crops override only diagnostic camera configuration; baseline model bytes come from the declared immutable Git revision.',
  plan_sha256: hash(await readFile(new URL('capture-plan.json', root))), evidence, errors,
 }, null, 2) + '\n');
 console.log(JSON.stringify({screenshots: evidence.length, errors}));
} finally {await browser.close(); await unlink(temporary).catch(error => {if (error.code !== 'ENOENT') throw error;});}
