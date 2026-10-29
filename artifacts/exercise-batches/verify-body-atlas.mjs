import assert from 'node:assert/strict';
import {readFile, writeFile, mkdir} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {homedir} from 'node:os';
import {chromium} from '../first-exercise-3d/runtime/node_modules/playwright-core/index.mjs';
import {buildReview} from './build-review.mjs';

const here = new URL('./', import.meta.url), root = new URL('batch-004/draft-review/mixed-topology/', here);
const read = async path => JSON.parse(await readFile(new URL(path, here)));
await mkdir(root, {recursive: true});
await writeFile(new URL('template.html', root), await readFile(new URL('batch-004/template.html', here)));
await writeFile(new URL('viewer.js', root), "import '../../../batch-002/viewer.js';\n");
await writeFile(new URL('build.mjs', root), '// Generated fixture. Rebuild with artifacts/exercise-batches/verify-body-atlas.mjs.\n');
const oldClip = await read('batch-004/assets/1980/clip.json');
const bikeClip = await read('batch-004/assets/0003/clip.json');
const newClip = (await read('../bodyweight-next-five/ninety-clips.json')).find(clip => clip.id === '10565');
const oldPresentation = await read('batch-004/presentation.json'), newPresentation = await read('batch-002/presentation.json');
const presentation = {'1980': oldPresentation['1980'], '0003': oldPresentation['0003'], '10565': newPresentation['10565']};
await writeFile(new URL('presentation.json', root), JSON.stringify(presentation));
const params = {root, batch: 'mixed-body-qa', ids: ['1980', '0003', '10565'], initialExerciseId: '1980', presentation,
 clips: [{...oldClip, asset: '1980'}, {...bikeClip, asset: '0003'}, {...newClip, asset: '10565', skinning: 'linear'}],
 cameras: {'1980': await read('batch-004/assets/1980/cameras.json'), '0003': await read('batch-004/assets/0003/cameras.json'), '10565': await read('../ninety-mpfb-review/camera-presets.json')},
 assetFiles: {'1980': new URL('batch-004/assets/1980/motion.glb', here), '0003': new URL('batch-004/assets/0003/motion.glb', here), '10565': new URL('../ninety-mpfb-review/ninety.glb', here)}};
await assert.rejects(buildReview(params), /Muscle atlas does not match body topology/);
const override = await read('../ninety-mpfb-review/heat-regions.json');
await buildReview({...params, atlasOverrides: {'10565': override}});
const browser = await chromium.launch({headless: true,
 executablePath: homedir() + '/Library/Caches/ms-playwright/chromium_headless_shell-1248/chrome-headless-shell-mac-arm64/chrome-headless-shell', args: ['--use-angle=metal']});
try {
 const page = await browser.newPage({viewport: {width: 728, height: 950}}), errors = [], states = [];
 page.on('pageerror', error => errors.push(String(error)));
 page.on('console', message => {if (message.type() === 'error') errors.push(message.text());});
 await page.goto(new URL('viewer.html', root).href);
 await page.waitForFunction(() => window.heatReady || window.heatError);
 assert.equal(await page.evaluate(() => window.heatError), undefined);
 for (const [id, count, bones] of [['1980', 10582, 51], ['0003', 10582, 51], ['10565', 13408, 116], ['0003', 10582, 51], ['1980', 10582, 51]]) {
  await page.locator(`button[data-id="${id}"]`).click();
  await page.waitForFunction(id => window.heatProbe().exerciseId === id && document.querySelector('#loading').hidden, id);
  const state = await page.evaluate(() => {
   window.heatFrame(2);
   const value = window.heatProbe();
   const gl = document.querySelector('canvas').getContext('webgl2'), pixels = new Uint8Array(gl.drawingBufferWidth * gl.drawingBufferHeight * 4);
   gl.readPixels(0, 0, gl.drawingBufferWidth, gl.drawingBufferHeight, gl.RGBA, gl.UNSIGNED_BYTE, pixels);
   let warm = 0, cyan = 0;
   for (let i = 0; i < pixels.length; i += 4) if (pixels[i + 3] > 250) {
    if (pixels[i] > pixels[i + 1] * 1.25 && pixels[i] > pixels[i + 2] * 1.4) warm++;
    if (pixels[i + 2] > pixels[i] * 1.25 && pixels[i + 1] > pixels[i] * 1.15) cyan++;
   }
   return {id: value.exerciseId, count: value.sourceVertices, primaryLength: value.primary.length,
    secondaryLength: value.secondary.length, primaryMaximum: Math.max(...value.primary),
    bones: value.bones, sourceCount: Object.keys(window.heatSurface()).length,
    morphWeights: value.morphWeights, alpha: value.cornerAlpha, shadows: value.shadows, ao: value.ao,
    skinning: value.skinning, displayMode: value.displayMode, warmPixels: warm, cyanPixels: cyan};
  });
  assert.equal(state.id, id); assert.equal(state.count, count); assert.equal(state.sourceCount, count);
  assert.equal(state.primaryLength, count); assert.equal(state.secondaryLength, count);
  assert.equal(state.primaryMaximum, 1); assert.equal(state.bones, bones);
  assert.equal(state.alpha, 0); assert.equal(state.shadows, false); assert.equal(state.ao, false);
  assert.equal(state.skinning, id === '0003' ? 'dualQuaternion' : 'linear');
  assert.equal(state.displayMode, id === '0003' ? 'load' : 'stretch');
  assert.ok(id === '0003' ? state.warmPixels > 100 && state.cyanPixels < 50 : state.cyanPixels > 100 && state.warmPixels === 0);
  if (id === '10565') assert.deepEqual(state.morphWeights, [[0, 1]]);
  states.push(state);
 }
 assert.deepEqual(errors, []);
 const files = ['build-review.mjs', 'batch-002/viewer.js', '../chaturanga-heatmap/heat-field.js'];
 const report = {status: 'passed', missingBodyAtlasRejected: true, states, errors,
  inputs: Object.fromEntries(await Promise.all(files.map(async path => [path, createHash('sha256').update(await readFile(new URL(path, here))).digest('hex')])))};
 await writeFile(new URL('verification.json', root), JSON.stringify(report, null, 2) + '\n');
 console.log(JSON.stringify(report));
} finally {await browser.close();}
