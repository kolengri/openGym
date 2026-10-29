import {homedir} from 'node:os';
import {chromium} from '../../first-exercise-3d/runtime/node_modules/playwright-core/index.mjs';

// Selected diagnostic poses, not an animation frame sequence or runtime cache.
const root = new URL('./', import.meta.url);
const browser = await chromium.launch({headless: true,
 executablePath: homedir() + '/Library/Caches/ms-playwright/chromium_headless_shell-1248/chrome-headless-shell-mac-arm64/chrome-headless-shell',
 args: ['--use-angle=metal']});
try {
 const page = await browser.newPage({viewport: {width: 1200, height: 1100}, deviceScaleFactor: 1});
 await page.goto(new URL('viewer.html', root).href);
 await page.waitForFunction(() => window.heatReady || window.heatError, undefined, {timeout: 60000});
 const error = await page.evaluate(() => window.heatError);
 if (error) throw Error(error);
 for (const id of ['2395', '5266']) {
  await page.evaluate(id => window.heatSelect(id), id);
  await page.locator('#view').selectOption('dual');
  for (const [side, time] of [['right', 1.25], ['left', 3.75]]) {
   await page.evaluate(time => window.heatFrame(time), time);
   for (const zones of [false, true]) {
    await page.locator('#zones').setChecked(zones);
    await page.locator('canvas').screenshot({path: new URL(`${zones ? 'zones' : 'neutral'}-${id}-${side}-peak.png`, root).pathname});
   }
  }
 }
 console.log(JSON.stringify({exerciseIds: ['2395', '5266'], times: [1.25, 3.75],
  scope: 'Two distinct extreme poses with and without zones; no video or runtime frame cache.'}));
} finally {await browser.close();}
