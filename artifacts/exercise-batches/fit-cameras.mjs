import {readFile, writeFile} from 'node:fs/promises';
import {homedir} from 'node:os';
import {chromium} from '../first-exercise-3d/runtime/node_modules/playwright-core/index.mjs';

const batch = process.argv[2];
if (!['002', '003', '004'].includes(batch)) throw Error('Pass batch 002, 003 or 004');
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
  const sampled = await page.evaluate(async id => {
   await window.heatSelect(id); const result = [], frames = [];
   for (let frame = 0; frame <= Math.round(window.heatProbe().duration * 30); frame += 5) frames.push(frame);
   for (const mode of ['front', 'back']) {
    const select = document.querySelector('#view'); select.value = mode; select.dispatchEvent(new Event('change'));
    let maximum = 0;
    for (const frame of frames) {
     window.heatFrame(frame / 30);
     const [{min, max}] = window.heatFrustum();
     maximum = Math.max(maximum, ...[...min, ...max].map(Math.abs));
    }
    result.push(maximum);
   }
   return {bounds: result, frames};
  }, exercise.id);
  // Uniform camera-width expansion preserves the authored angle and target.
  // All inactive body surfaces also remain inside a10percent framing margin.
  const factors = sampled.bounds.map(value => Math.max(1, value / .9));
  const source = batch !== '002' ? new URL(`assets/${exercise.id}/cameras.json`, root)
   : new URL(`../bodyweight-next-five/${['10565', '6560'].includes(exercise.id) ? 'ninety-' : ''}camera-presets.json`, import.meta.url);
  const document = JSON.parse(await readFile(source));
  const cameras = batch !== '002' ? document : document[exercise.id];
  for (const [index, factor] of factors.entries()) cameras[index].scale = Math.ceil(cameras[index].scale * factor * 100) / 100;
  await writeFile(source, JSON.stringify(document, null, 2) + '\n');
  evidence.push({id: exercise.id, sampledRuntimeFrames: sampled.frames,
   originalMaxAbsNDC: sampled.bounds, widthFactors: factors, finalHorizontalWidths: cameras.map(camera => camera.scale)});
 }
 await writeFile(new URL('camera-fit.json', root), JSON.stringify({margin: .1, evidence, note: 'Angles and targets unchanged; actual exported surfaces sampled in the live renderer.'}, null, 2) + '\n');
 console.log(JSON.stringify(evidence.map(({id, finalHorizontalWidths}) => ({id, widths: finalHorizontalWidths}))));
} finally {await browser.close();}
