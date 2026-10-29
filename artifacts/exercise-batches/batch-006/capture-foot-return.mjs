import {homedir} from 'node:os';
import {readFile, writeFile, mkdir} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {chromium} from '../../first-exercise-3d/runtime/node_modules/playwright-core/index.mjs';

const label = process.argv[2];
if (!['before', 'after'].includes(label)) throw Error('Pass before or after');
const id = process.argv[3] ?? '1512';
if (!['1512', '3479', '3531'].includes(id)) throw Error('Pass exercise1512,3479 or3531');
const times = id === '1512' ? [3.7, 4.1, 4.4, 4.7, 4.95]
 : id === '3479' ? (label === 'before' ? [0, .3, .6, .9] : [0, .9, 1.7, 1.95, 2.55])
 : [0, 8 / 30, 33 / 30, .8];
const root = new URL('./', import.meta.url), directory = new URL('foot-return-review/', root);
await mkdir(directory, {recursive: true});
const browser = await chromium.launch({headless: true,
 executablePath: homedir() + '/Library/Caches/ms-playwright/chromium_headless_shell-1248/chrome-headless-shell-mac-arm64/chrome-headless-shell',
 args: ['--use-angle=metal']});
try {
 const page = await browser.newPage({viewport: {width: 1600, height: 1100}, deviceScaleFactor: 1});
 await page.goto(new URL('viewer.html', root).href);
 await page.waitForFunction(() => window.heatReady || window.heatError, undefined, {timeout: 60000});
 const error = await page.evaluate(() => window.heatError);
 if (error) throw Error(error);
 await page.evaluate(id => window.heatSelect(id), id);
 await page.locator('#view').selectOption('dual');
 await page.locator('#zones').uncheck();
 const files = [];
 for (const time of times) {
  await page.evaluate(time => window.heatFrame(time), time);
  const file = `${id === '1512' ? label : label + '-' + id}-${time.toFixed(2)}.png`;
  await page.locator('canvas').screenshot({path: new URL(file, directory).pathname});
  files.push({time, file});
 }
 await writeFile(new URL(label + (id === '1512' ? '' : '-' + id) + '.json', directory), JSON.stringify({
  scope: 'Selected actual GPU feedback poses in the same recommended views; no video or frame cache.',
  viewer_sha256: createHash('sha256').update(await readFile(new URL('viewer.html', root))).digest('hex'),
  model: Object.values(JSON.parse(await readFile(new URL('build-manifest.json', root))).models)
   .find(model => model.animations.includes('Exercise_' + id)), files,
 }, null, 2) + '\n');
 console.log(JSON.stringify({label, files}));
} finally {await browser.close();}
