import {chromium} from '../first-exercise-3d/runtime/node_modules/playwright-core/index.mjs';
import {readFile, writeFile} from 'node:fs/promises';
import {homedir} from 'node:os';

const root = new URL('./', import.meta.url);
const samples = JSON.parse(await readFile(new URL('pose-samples.json', root), 'utf8'));
const cameras = JSON.parse(await readFile(new URL('camera-presets.json', root), 'utf8'));
const ids = ['5965', '5915', '5887', '0001', '9066'];
const model = await readFile(new URL('bodyweight-five.glb', root));
const modelJson = JSON.parse(model.subarray(20, 20 + model.readUInt32LE(12)).toString());
const atlasUvChannel = modelJson.materials[0].pbrMetallicRoughness.baseColorTexture.texCoord ?? 0;
const browser = await chromium.launch({headless: true, executablePath: process.env.EXERCISE_CHROME || homedir() + '/Library/Caches/ms-playwright/chromium_headless_shell-1248/chrome-headless-shell-mac-arm64/chrome-headless-shell', args: ['--use-angle=metal']});
function assertRendering(actual) {
 if (actual.shadowMap || actual.castShadow || actual.receiveShadow || actual.ao) throw Error('Shadows or AO enabled');
 if (!actual.sceneBackgroundNull || !actual.contextAlpha || actual.clearAlpha !== 0 || actual.cornerAlpha.some(alpha => alpha !== 0)) throw Error('Canvas is not transparent: ' + JSON.stringify({background: actual.sceneBackgroundNull, contextAlpha: actual.contextAlpha, clearAlpha: actual.clearAlpha, corners: actual.cornerAlpha}));
 if (actual.canvasCssBackground !== 'rgba(0, 0, 0, 0)') throw Error('Canvas has an opaque CSS background');
 if (actual.modelInstances !== 1 || !actual.mixerRootIsModel) throw Error('Viewport model/mixer is duplicated');
 if (actual.loadedTextureCount > 2 || actual.textureLoading || actual.activeTextureId !== actual.selected) throw Error('Unexpected activation texture cache: ' + JSON.stringify(actual));
 if (actual.textureSize[0] !== 2048 || actual.textureSize[1] !== 1024) throw Error('Expected the 2K runtime texture atlas');
 if (actual.atlasUvChannel !== atlasUvChannel || actual.materialUvChannels.some(channel => channel !== atlasUvChannel)) throw Error('Replacement texture lost the exported atlas UV channel');
}
try {
 const page = await browser.newPage({viewport: {width: 1100, height: 1100}, deviceScaleFactor: 1}), errors = [];
 page.on('pageerror', error => errors.push(error.message));
 await page.goto(new URL('threejs-viewer.html', root).href);
 await page.waitForFunction(() => window.runtimeReady || window.runtimeError, undefined, {timeout: 60000});
 const state = await page.evaluate(() => ({ready: window.runtimeReady, error: window.runtimeError}));
 if (state.error) throw Error(state.error);
 if (state.ready.bones !== 51 || state.ready.skeletons !== 1 || state.ready.clips.length !== 5 || !state.ready.sourceIndexAttribute || ids.some(id => !state.ready.clips.some(clip => clip.name === 'Exercise_' + id))) throw Error('Unexpected exported model structure: ' + JSON.stringify(state));
 if (state.ready.defaultView !== 'dual') throw Error('Complementary views are not the default');
 let maxJointError = 0;
 const clips = [];
 for (const id of ids) {
  await page.evaluate(id => window.setRuntimeClip(id), id);
  const selected = await page.evaluate(() => window.runtimeProbe());
  assertRendering(selected);
  if (selected.viewMode !== 'default' || selected.viewportCount !== 2 || selected.renderCalls !== 2 || selected.orbitEnabled) throw Error('Expected two recommended synchronized viewports for ' + id);
  for (let index = 0; index < 2; index++) {
   const [x, y, z] = cameras[id][index].position;
   const expected = [x, z, -y];
   if (Math.hypot(...selected.viewportCameras[index].position.map((value, axis) => value - expected[axis])) > 1e-8) throw Error('Camera preset conversion mismatch for ' + id);
  }
  let maximum = 0, worst;
  for (const sample of samples.filter(sample => sample.id === id)) {
   const before = await page.evaluate(() => window.runtimeProbe().poseEvaluations);
   await page.evaluate(time => window.renderRuntimeFrame(time), sample.frame / 30);
   const actual = await page.evaluate(() => window.runtimeProbe());
   assertRendering(actual);
   if (actual.poseEvaluations !== before + 1 || actual.viewportCount !== 2 || actual.renderCalls !== 2) throw Error('Pose must update once for both viewports');
   for (const [bone, position] of Object.entries(sample.joints)) {
    const value = actual.joints[bone], expected = [position[0], position[2], -position[1]];
    if (!value) throw Error('Missing bone ' + bone);
    const error = Math.hypot(...value.map((coordinate, index) => coordinate - expected[index]));
    if (error > maximum) {maximum = error; worst = {bone, frame: sample.frame, actual: value, expected};}
   }
  }
  if (maximum > .003) {
   await writeFile(new URL('runtime-verification-failure.json', root), JSON.stringify({id, maximum, worst, ready: state.ready}, null, 2));
   throw Error('Exported pose mismatch ' + id + ': ' + maximum + ' ' + JSON.stringify(worst));
  }
  maxJointError = Math.max(maxJointError, maximum);
  clips.push({id, maxJointErrorMeters: maximum, synchronizedViewports: 2, poseUpdatesPerFrame: 1});
  const half = state.ready.clips.find(clip => clip.name === 'Exercise_' + id).duration / 2;
  await page.evaluate(time => window.renderRuntimeFrame(time), half);
  await page.locator('canvas').screenshot({path: new URL('runtime-' + id + '.png', root).pathname});
 }
 await page.locator('#highlight').uncheck();
 await page.locator('#highlight').check();
 const backgrounds = [];
 for (const background of ['white', 'dark', 'checker']) {
  await page.locator('#background').selectOption(background);
  const actual = await page.evaluate(() => window.runtimeProbe());
  assertRendering(actual);
  if (actual.background !== background) throw Error('Background control did not change CSS backdrop');
  if (background === 'checker' && actual.cssBackgroundImage === 'none') throw Error('Checkerboard CSS background missing');
  if (background === 'white' && actual.cssBackground !== 'rgb(255, 255, 255)') throw Error('White CSS background missing');
  if (background === 'dark' && actual.cssBackground !== 'rgb(32, 39, 48)') throw Error('Dark CSS background missing');
  backgrounds.push({name: background, cornerAlpha: actual.cornerAlpha});
 }
 await page.locator('#view').selectOption('detail');
 const detail = await page.evaluate(() => window.runtimeProbe());
 assertRendering(detail);
 if (detail.viewportCount !== 1 || !detail.orbitEnabled) throw Error('Detail camera is not a rotatable single view');
 await page.locator('#view').selectOption('primary');
 const primary = await page.evaluate(() => window.runtimeProbe());
 const bounds = await page.locator('canvas').boundingBox();
 await page.mouse.move(bounds.x + bounds.width / 2, bounds.y + bounds.height / 2);
 await page.mouse.down();
 await page.mouse.move(bounds.x + bounds.width / 2 + 60, bounds.y + bounds.height / 2 + 25, {steps: 5});
 await page.mouse.up();
 const rotated = await page.evaluate(() => window.runtimeProbe());
 assertRendering(rotated);
 if (Math.hypot(...rotated.viewportCameras[0].position.map((value, index) => value - primary.viewportCameras[0].position[index])) < .01) throw Error('Single-view orbit did not rotate the camera');
 await page.locator('#view').selectOption('back');
 await page.locator('#view').selectOption('default');
 await page.locator('#background').selectOption('white');
 // Rapid selections must not let an older asynchronous image load replace the
 // latest clip's activation. Stale textures are disposed before GPU use.
 await page.evaluate(() => Promise.all([window.setRuntimeClip('5915'), window.setRuntimeClip('5887')]));
 const switched = await page.evaluate(() => window.runtimeProbe());
 assertRendering(switched);
 if (switched.selected !== '5887' || switched.activeTextureId !== '5887') throw Error('Stale activation texture won a clip switch');
 if (errors.length) throw Error(errors.join('\n'));
 await writeFile(new URL('runtime-verification.json', root), JSON.stringify({ok: true, engine: 'Actual Three.js / Chromium / Metal', ...state.ready, maxJointErrorMeters: maxJointError, clips, transparentCanvas: true, clearAlpha: 0, backgrounds, shadows: false, ao: false, modelInstances: 1, mixerInstances: 1, loadedTextureCount: switched.loadedTextureCount, gpuTextureCount: switched.gpuTextureCount, textureSize: switched.textureSize, staleTextureSwitchGuard: true, controls: {clip: true, muscleToggle: true, view: true, orbit: true, background: true}, errors}, null, 2) + '\n');
 console.log('Verified five clips, 51 bones, source-index lookup, transparent dual viewports and a two-color-texture cache; max joint error', maxJointError);
} finally {
 await browser.close();
}
