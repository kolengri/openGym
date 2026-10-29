import {homedir} from 'node:os';
import {readFile, writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {chromium} from '../../first-exercise-3d/runtime/node_modules/playwright-core/index.mjs';

// A few diagnostic poses per action; no animation frame sequence or runtime cache.
const root = new URL('./', import.meta.url);
const poses = {
 '1512': [['approach', 1], ['grasp', 1.5], ['hold', 2.5], ['release', 3.7], ['late-return', 4.4]],
 '3479': [['deep-squat', .9], ['stand-transfer', 1.85], ['kick', 71 / 30], ['heel-touch', 80 / 30]],
 '0006': [['left', 1.25], ['right', 3.75]],
 '4918': [['left-flight', .675], ['right-flight', 1.925]],
 '4826': [['left', 1.25]],
 '4001': [['left', 1.25]],
 '3590': [['left', 1.25]],
 '4354': [['left', 1.25], ['right', 3.75]],
 '3531': [['right-punch', 8 / 30], ['left-punch', 33 / 30]],
 '3480': [['left', 1.25], ['right', 3.75]],
 '5106': [['left', 1.25]],
};
const browser = await chromium.launch({headless: true,
 executablePath: homedir() + '/Library/Caches/ms-playwright/chromium_headless_shell-1248/chrome-headless-shell-mac-arm64/chrome-headless-shell',
 args: ['--use-angle=metal']});
try {
 const page = await browser.newPage({viewport: {width: 1200, height: 1100}, deviceScaleFactor: 1});
 await page.goto(new URL('viewer.html', root).href);
 await page.waitForFunction(() => window.heatReady || window.heatError, undefined, {timeout: 60000});
 const error = await page.evaluate(() => window.heatError);
 if (error) throw Error(error);
 const evidence = [];
 for (const [id, samples] of Object.entries(poses)) {
  await page.evaluate(id => window.heatSelect(id), id);
  await page.locator('#view').selectOption('dual');
  for (const [label, time] of samples) {
   await page.evaluate(time => window.heatFrame(time), time);
   for (const zones of [false, true]) {
    await page.locator('#zones').setChecked(zones);
    const file = `${zones ? 'zones' : 'neutral'}-${id}-${label}.png`;
    await page.locator('canvas').screenshot({path: new URL(file, root).pathname});
    evidence.push({id, label, time, zones, file});
   }
  }
 }
 const hash = data => createHash('sha256').update(data).digest('hex');
 await writeFile(new URL('capture-peaks.json', root), JSON.stringify({
  scope: 'Selected actual GPU poses in both recommended views, with and without muscle fields.',
  viewer_sha256: hash(await readFile(new URL('viewer.html', root))), evidence,
 }, null, 2) + '\n');
 console.log(JSON.stringify({poses: evidence.length / 2, screenshots: evidence.length}));
} finally {await browser.close();}
