import {readFile} from 'node:fs/promises';
import {homedir} from 'node:os';
import {chromium} from '../first-exercise-3d/runtime/node_modules/playwright-core/index.mjs';

const root = new URL(`./batch-${process.argv[2]}/`, import.meta.url);
const manifest = JSON.parse(await readFile(new URL('build-manifest.json', root)));
const ids = process.argv.slice(3).length ? process.argv.slice(3) : manifest.exercise_ids;
const browser = await chromium.launch({headless: true,
 executablePath: homedir() + '/Library/Caches/ms-playwright/chromium_headless_shell-1248/chrome-headless-shell-mac-arm64/chrome-headless-shell', args: ['--use-angle=metal']});
try {
 const page = await browser.newPage({viewport: {width: 1200, height: 1100}, deviceScaleFactor: 1});
 await page.goto(new URL('viewer.html', root).href);
 await page.waitForFunction(() => window.heatReady || window.heatError, undefined, {timeout: 60000});
 const error = await page.evaluate(() => window.heatError); if (error) throw Error(error);
 for (const id of ids) {
  await page.evaluate(id => window.heatSelect(id), id);
  await page.locator('#view').selectOption('dual');
  await page.evaluate(() => window.heatFrame(window.heatProbe().duration / 2));
  await page.locator('#zones').uncheck();
  await page.locator('canvas').screenshot({path: new URL(`neutral-${id}.png`, root).pathname});
  await page.locator('#zones').check();
  await page.locator('canvas').screenshot({path: new URL(`zones-${id}.png`, root).pathname});
 }
 console.log(JSON.stringify({curatedReviewStills: ids, scope: 'One representative pose per exercise, two views with and without zones; not an animation frame sequence.'}));
} finally {await browser.close();}
