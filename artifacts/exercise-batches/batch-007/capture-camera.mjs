import {homedir} from 'node:os';
import {chromium} from '../../first-exercise-3d/runtime/node_modules/playwright-core/index.mjs';

const root = new URL('./', import.meta.url), id = process.argv[2], time = Number(process.argv[3]);
if (!/^\d+$/.test(id ?? '') || !Number.isFinite(time) || time < 0) throw Error('Pass exercise ID and time in seconds');
const browser = await chromium.launch({headless: true,
 executablePath: homedir() + '/Library/Caches/ms-playwright/chromium_headless_shell-1248/chrome-headless-shell-mac-arm64/chrome-headless-shell',
 args: ['--use-angle=metal']});
try {
 const page = await browser.newPage({viewport: {width: 1200, height: 1100}, deviceScaleFactor: 1});
 await page.goto(new URL('viewer.html', root).href);
 await page.waitForFunction(() => window.heatReady || window.heatError, undefined, {timeout: 60000});
 const error = await page.evaluate(() => window.heatError); if (error) throw Error(error);
 await page.evaluate(id => window.heatSelect(id), id);
 await page.locator('#view').selectOption('dual');
 await page.evaluate(time => window.heatFrame(time), time);
 await page.locator('#zones').check();
 await page.locator('canvas').screenshot({path: new URL(`camera-muscle-${id}.png`, root).pathname});
 console.log(JSON.stringify({id, time, screenshot: `camera-muscle-${id}.png`}));
} finally {await browser.close();}
