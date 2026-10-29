import {readFile, writeFile} from 'node:fs/promises';
import {homedir} from 'node:os';
import {chromium} from '../first-exercise-3d/runtime/node_modules/playwright-core/index.mjs';

const batch = process.argv[2];
if (!['002', '003', '004', '005', '006'].includes(batch)) throw Error('Pass batch 002, 003, 004, 005 or 006');
const root = new URL(`./batch-${batch}/`, import.meta.url);
const config = JSON.parse((await readFile(new URL('viewer.html', root), 'utf8')).match(/<script id="heat-data" type="application\/json">(.*?)<\/script>/s)[1]);
const browser = await chromium.launch({headless: true,
 executablePath: homedir() + '/Library/Caches/ms-playwright/chromium_headless_shell-1248/chrome-headless-shell-mac-arm64/chrome-headless-shell', args: ['--use-angle=metal']});
try {
 const page = await browser.newPage({viewport: {width: 728, height: 950}, deviceScaleFactor: 1});
 await page.goto(new URL('viewer.html', root).href);
 await page.waitForFunction(() => window.heatReady || window.heatError, undefined, {timeout: 60000});
 const error = await page.evaluate(() => window.heatError); if (error) throw Error(error);
 const evidence = [];
 for (const exercise of config.exercises) {
  const sourceVertices = exercise.sourceVertices ?? config.sourceVertices;
  if (!exercise.cameras.some(camera => !camera.frameSourceIds)) throw Error(`${exercise.id}: retain a whole-body view`);
  for (const camera of exercise.cameras) if (camera.frameSourceIds && (!camera.frameSourceIds.length ||
   new Set(camera.frameSourceIds).size !== camera.frameSourceIds.length ||
   camera.frameSourceIds.some(id => !Number.isInteger(id) || id < 0 || id >= sourceVertices))) throw Error(`${exercise.id}: invalid detail framing IDs`);
  const sampled = await page.evaluate(async exercise => {
   await window.heatSelect(exercise.id); const result = [], frames = [];
   for (let frame = 0; frame <= Math.round(window.heatProbe().duration * 30); frame += 5) frames.push(frame);
   for (const [index, mode] of ['front', 'back'].entries()) {
    const select = document.querySelector('#view'); select.value = mode; select.dispatchEvent(new Event('change'));
    let maximum = 0;
    for (const frame of frames) {
     window.heatFrame(frame / 30);
     const ids = exercise.cameras[index].frameSourceIds;
     const [{min, max, sourceVertices}] = window.heatFrustum(ids);
     if (sourceVertices !== (ids?.length ?? exercise.sourceVertices)) throw Error('Missing framing source vertices');
     maximum = Math.max(maximum, ...[...min, ...max].map(Math.abs));
    }
    result.push(maximum);
   }
   return {bounds: result, frames};
  }, {...exercise, sourceVertices});
  // Uniform camera-width expansion preserves the authored angle and target.
  // Detail views explicitly frame their source IDs; a whole-body companion is required.
  const factors = sampled.bounds.map(value => Math.max(1, value / .9));
  const source = batch !== '002' ? new URL(`assets/${exercise.id}/cameras.json`, root)
   : new URL(`../bodyweight-next-five/${['10565', '6560'].includes(exercise.id) ? 'ninety-' : ''}camera-presets.json`, import.meta.url);
  const document = JSON.parse(await readFile(source));
  const cameras = batch !== '002' ? document : document[exercise.id];
  for (const [index, factor] of factors.entries()) if (factor > 1)
   cameras[index].scale = Math.ceil(cameras[index].scale * factor * 100) / 100;
  await writeFile(source, JSON.stringify(document, null, 2) + '\n');
  evidence.push({id: exercise.id, sampledRuntimeFrames: sampled.frames,
   framingSourceVertices: cameras.map(camera => camera.frameSourceIds?.length ?? sourceVertices),
   originalMaxAbsNDC: sampled.bounds, widthFactors: factors, finalHorizontalWidths: cameras.map(camera => camera.scale)});
 }
 await writeFile(new URL('camera-fit.json', root), JSON.stringify({margin: .1, evidence, note: 'Angles and targets unchanged; actual exported surfaces sampled in the live renderer.'}, null, 2) + '\n');
 console.log(JSON.stringify(evidence.map(({id, finalHorizontalWidths}) => ({id, widths: finalHorizontalWidths}))));
} finally {await browser.close();}
