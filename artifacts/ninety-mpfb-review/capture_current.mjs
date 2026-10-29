import {readFile, writeFile, mkdir} from 'node:fs/promises';
import {homedir} from 'node:os';
import {fileURLToPath, pathToFileURL} from 'node:url';
import {resolve, sep} from 'node:path';
import {createHash} from 'node:crypto';
import {parseArgs} from 'node:util';
import {chromium} from '../first-exercise-3d/runtime/node_modules/playwright-core/index.mjs';

const {values: options} = parseArgs({options: {times: {type: 'string', default: '0'}, 'review-dir': {type: 'string'}, neutral: {type: 'boolean'}}});
const here = options['review-dir'] ? pathToFileURL(resolve(options['review-dir']) + sep) : new URL('./', import.meta.url);
const output = new URL('visuals/', here);
const times = options.times.split(',').map(Number);
if (!times.length || times.some(value => !Number.isFinite(value) || value < 0 || value > 5)) throw Error('Invalid pose times');
await mkdir(output, {recursive: true});
const browser = await chromium.launch({headless: true,
 executablePath: homedir() + '/Library/Caches/ms-playwright/chromium_headless_shell-1248/chrome-headless-shell-mac-arm64/chrome-headless-shell', args: ['--use-angle=metal']});
try {
 const page = await browser.newPage({viewport: {width: 1280, height: 1000}});
 const errors = [];
 page.on('pageerror', error => errors.push(String(error)));
 page.on('console', message => {if (message.type() === 'error') errors.push(message.text());});
 await page.goto(new URL('viewer.html', here).href);
 await page.waitForFunction(() => window.heatReady || window.heatError);
 const error = await page.evaluate(() => window.heatError); if (error) throw Error(error);
 if (options.neutral) await page.locator('#zones').uncheck();
 const poses = [];
 for (const time of times) {
  await page.evaluate(value => window.heatFrame(value), time);
  const file = time === 0 ? 'current-start.png' : `current-${Math.round(time * 1000)}ms.png`;
  await page.locator('#stage').screenshot({path: fileURLToPath(new URL(file, output))});
  poses.push({time, file, framing: await page.evaluate(() => window.heatFrustum()),
   probe: await page.evaluate(() => {
    const {primary, secondary, joints, ...probe} = window.heatProbe();
    return probe;
   })});
 }
 const bytes = await readFile(new URL('viewer.html', here));
 const report = {status: 'provisional_visual_capture_not_geometry_acceptance',
  htmlSha256: createHash('sha256').update(bytes).digest('hex'), viewport: [1280, 1000], errors, poses};
 await writeFile(new URL('current-start.json', output), JSON.stringify(report, null, 2) + '\n');
 console.log(JSON.stringify({status: report.status, htmlSha256: report.htmlSha256, errors,
  poses: poses.map(({time, file, framing, probe}) => ({time, file, framing, morphWeights: probe.morphWeights, cornerAlpha: probe.cornerAlpha}))}));
 if (errors.length) throw Error('Browser/graphics errors: ' + errors.join('\n'));
} finally {await browser.close();}
