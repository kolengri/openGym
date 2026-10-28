import assert from 'node:assert/strict';
import {readFile, writeFile} from 'node:fs/promises';
import {homedir} from 'node:os';
import {createHash} from 'node:crypto';
import {chromium} from '../../first-exercise-3d/runtime/node_modules/playwright-core/index.mjs';

const root = new URL('./', import.meta.url);
const manifest = JSON.parse(await readFile(new URL('build-manifest.json', root)));
const browser = await chromium.launch({headless: true,
 executablePath: homedir() + '/Library/Caches/ms-playwright/chromium_headless_shell-1248/chrome-headless-shell-mac-arm64/chrome-headless-shell', args: ['--use-angle=metal']});
try {
 const page = await browser.newPage({viewport: {width: 728, height: 950}, deviceScaleFactor: 1});
 const errors = [], media = [], urls = [];
 page.on('pageerror', error => errors.push(error.message));
 page.on('console', message => {if (message.type() === 'error') errors.push(message.text());});
 page.on('request', request => {
  if (request.resourceType() === 'media') media.push(request.url());
  if (request.url().startsWith('http')) urls.push(request.url());
 });
 const modelResponse = page.waitForResponse(response => response.url().endsWith('/bodyweight-next-five/next-five.glb'));
 await page.goto(new URL('inline.html', root).href);
 await page.waitForFunction(() => window.heatReady || window.heatError, undefined, {timeout: 60000});
 assert.equal(await page.evaluate(() => window.heatError), undefined);
 const response = await modelResponse; assert.equal(response.status(), 200);
 assert.ok(response.url().includes('/' + manifest.model_revision + '/'));
 assert.equal(createHash('sha256').update(await response.body()).digest('hex'), manifest.model_sha256);
 assert.equal(await page.locator('#poster').count(), 0, 'The actual3D scene did not replace the loading poster');
 assert.equal(await page.locator('#loading').isVisible(), false);
 const actions = [];
 for (const id of manifest.exercise_ids) {
  await page.locator(`#exercises button[data-id="${id}"]`).click();
  const state = await page.evaluate(() => window.heatProbe());
  assert.equal(state.action, 'Exercise_' + id); assert.equal(state.cornerAlpha, 0); assert.equal(state.colorTextures, 0);
  actions.push(state.action);
 }
 await page.locator('#exercises button').first().click();
 const before = await page.evaluate(() => ({time: window.heatProbe().time, joints: window.heatProbe().joints}));
 await page.waitForFunction(time => window.heatProbe().time > time + .2, before.time);
 assert.notDeepEqual(await page.evaluate(() => window.heatProbe().joints), before.joints);
 await page.evaluate(() => window.heatFrame(2));
 await page.screenshot({path: new URL('inline-settled.png', root).pathname});
 assert.equal(await page.locator('video').count(), 0); assert.deepEqual(media, []); assert.deepEqual(errors, []);
 const report = {ok: true, scope: 'Actual URL-mode Three.js preview; pinned public model bytes verified and all five live actions selected.',
  model_revision: manifest.model_revision, model_sha256: manifest.model_sha256, actions,
  input_bytes: (await readFile(new URL('inline.html', root))).byteLength, mediaRequests: media,
  liveCanvasReplacesPoster: true, livePoseChanges: true, externalResources: [...new Set(urls)], errors};
 await writeFile(new URL('inline-verification.json', root), JSON.stringify(report, null, 2) + '\n');
 console.log(JSON.stringify({ok: true, actions, liveCanvasReplacesPoster: true, externalResources: report.externalResources.length}));
} finally {await browser.close();}
