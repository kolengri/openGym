import assert from 'node:assert/strict';
import {readFile, writeFile} from 'node:fs/promises';
import {homedir} from 'node:os';
import {chromium} from '../first-exercise-3d/runtime/node_modules/playwright-core/index.mjs';

const root = new URL('./', import.meta.url);
const browser = await chromium.launch({headless: true,
 executablePath: homedir() + '/Library/Caches/ms-playwright/chromium_headless_shell-1248/chrome-headless-shell-mac-arm64/chrome-headless-shell', args: ['--use-angle=metal']});
try {
 const page = await browser.newPage({viewport: {width: 728, height: 850}, deviceScaleFactor: 1});
 const errors = [], media = [], urls = [];
 page.on('pageerror', error => errors.push(error.message));
 page.on('request', request => {
  if (request.resourceType() === 'media') media.push(request.url());
  if (request.url().startsWith('http')) urls.push(request.url());
 });
 await page.goto(new URL('inline.html', root).href);
 await page.waitForFunction(() => window.heatReady || window.heatError, undefined, {timeout: 60000});
 assert.equal(await page.evaluate(() => window.heatError), undefined);
 await page.evaluate(() => window.heatFrame(2));
 const state = await page.evaluate(() => {
  const state = window.heatProbe(); delete state.primary; delete state.secondary; delete state.joints;
  return state;
 });
 assert.equal(state.action, 'Exercise_5915'); assert.equal(state.cornerAlpha, 0); assert.equal(state.colorTextures, 0);
 assert.equal(await page.locator('#poster').count(), 0, 'The real 3D view did not replace the loading poster');
 assert.equal(await page.locator('#loading').isVisible(), false);
 assert.equal(await page.locator('video').count(), 0); assert.deepEqual(media, []); assert.deepEqual(errors, []);
 assert.ok(urls.some(url => url.includes('raw.githubusercontent.com/kolengri/openGym/62298177')));
 await page.screenshot({path: new URL('inline-settled.png', root).pathname});
 const report = {ok: true, scope: 'Actual URL-mode Three.js preview, pinned public model and Three.js version; live canvas replaces startup poster.',
  input_bytes: (await readFile(new URL('inline.html', root))).byteLength, mediaRequests: media, externalResources: [...new Set(urls)], state, errors};
 await writeFile(new URL('inline-verification.json', root), JSON.stringify(report, null, 2) + '\n');
 console.log(JSON.stringify({ok: true, liveCanvasReplacesPoster: true, videoRequests: media.length, externalResources: report.externalResources.length}));
} finally {await browser.close();}
