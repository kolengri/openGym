// Check the exported GLB's actual skinned surface, separately from native modifiers.
import assert from 'node:assert/strict';
import {readFile, writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {homedir} from 'node:os';
import {Triangle, Vector3} from '../first-exercise-3d/runtime/node_modules/three/build/three.module.js';
import {chromium} from '../first-exercise-3d/runtime/node_modules/playwright-core/index.mjs';

const root = new URL('./', import.meta.url);
const landmarksData = await readFile(new URL('situp-repair/landmarks.json', root));
const landmarks = JSON.parse(landmarksData);
const native = JSON.parse(await readFile(new URL('situp-repair/contact-report.json', root)));
const model = await readFile(new URL('bodyweight-five.glb', root));
const hash = data => createHash('sha256').update(data).digest('hex');
const indices = [...new Set(Object.values(landmarks.patches).flatMap(patch => patch.vertex_ids))];
const tolerance = landmarks.tolerances;
const browser = await chromium.launch({headless: true,
 executablePath: process.env.EXERCISE_CHROME || homedir() + '/Library/Caches/ms-playwright/chromium_headless_shell-1248/chrome-headless-shell-mac-arm64/chrome-headless-shell',
 args: ['--use-angle=metal']});
const samples = [];
try {
 const page = await browser.newPage({viewport: {width: 1100, height: 1000}});
 await page.goto(new URL('threejs-viewer.html', root).href);
 await page.waitForFunction(() => window.runtimeReady || window.runtimeError, undefined, {timeout: 60000});
 assert.equal(await page.evaluate(() => window.runtimeError), undefined);
 await page.evaluate(() => window.setRuntimeClip('0001'));
 for (const frame of landmarks.sample_frames) {
  await page.evaluate(time => window.renderRuntimeFrame(time), frame / 30);
  const surface = await page.evaluate(({indices, head}) => window.runtimeSurfaceProbe(indices, head),
   {indices, head: landmarks.patches.head_surface.vertex_ids});
  assert.ok(surface.maximumSeamSpread < 1e-5, 'UV seam skin diverged');
  assert.ok(surface.minimumFloorHeight >= -tolerance.maximum_skin_floor_penetration_m, `Floor penetration at ${frame}`);
  const vertices = Object.fromEntries(Object.entries(surface.vertices).map(([id, value]) => [id, new Vector3(...value)]));
  const contacts = {};
  const reference = native.samples.find(sample => sample.path === 'linear_cage' && sample.frame === frame);
  assert.ok(reference, `Missing linear reference at ${frame}`);
  for (const [name, patch] of Object.entries(landmarks.patches)) {
   if (patch.kind !== 'supported' && name !== 'lumbar_clearance') continue;
   const heights = patch.vertex_ids.map(id => vertices[id].y);
   const minimum = Math.min(...heights);
   const fraction = heights.filter(value => Math.abs(value) <= tolerance.support_near_distance_m).length / heights.length;
   assert.ok(Math.abs(minimum - reference.contacts[name].minimum_m) < 1e-4, `GLB / linear skin mismatch: ${frame} ${name}`);
   if (name === 'lumbar_clearance') assert.ok(minimum >= tolerance.minimum_lumbar_clearance_m, `Lumbar clearance at ${frame}`);
   else {
    assert.ok(minimum <= tolerance.support_maximum_closest_gap_m, `Floating ${name} at ${frame}`);
    assert.ok(fraction >= tolerance.support_minimum_near_fraction, `Insufficient support ${name} at ${frame}`);
   }
   contacts[name] = {minimum_m: minimum, fraction_within_contact_band: fraction};
  }
  const triangles = surface.triangles.map(ids => {
   const triangle = new Triangle(...ids.map(id => vertices[id]));
   return {triangle, normal: triangle.getNormal(new Vector3())};
  });
  assert.ok(triangles.length > 1000, 'Missing actual GLB head triangles');
  const headClearances = {}, closest = new Vector3(), delta = new Vector3();
  for (const name of ['hand_L', 'hand_R', 'fingertips_L', 'fingertips_R']) {
   let minimum = Infinity;
   for (const id of landmarks.patches[name].vertex_ids) {
    const point = vertices[id];
    let squaredDistance = Infinity, signed = Infinity;
    for (const {triangle, normal} of triangles) {
     triangle.closestPointToPoint(point, closest);
     const distance = point.distanceToSquared(closest);
     if (distance < squaredDistance) {
      squaredDistance = distance;
      signed = Math.sqrt(distance) * (delta.subVectors(point, closest).dot(normal) >= 0 ? 1 : -1);
     }
    }
    minimum = Math.min(minimum, signed);
   }
   assert.ok(minimum >= -tolerance.maximum_hand_scalp_penetration_m, `Scalp penetration ${frame} ${name}: ${minimum}`);
   if (name.startsWith('fingertips')) assert.ok(minimum <= tolerance.maximum_fingertip_light_touch_gap_m, `Fingertip gap ${frame} ${name}`);
   headClearances[name] = {minimum_signed_distance_m: minimum, deepest_penetration_m: Math.max(0, -minimum)};
  }
  samples.push({frame, minimum_floor_height_m: surface.minimumFloorHeight,
   maximum_uv_seam_spread_m: surface.maximumSeamSpread, head_triangles: triangles.length, contacts, head_clearances: headClearances});
 }
} finally { await browser.close(); }
const report = {ok: true, exercise_id: '0001', model_sha256: hash(model), landmarks_sha256: hash(landmarksData),
 scope: 'Actual loaded GLB, Three.js CPU skinning with exported four-bone weights and _SOURCE_INDEX. Native linear-cage contact comparison; nearest signed distances to actual exported head triangles. Nine authored phase samples, not continuous collision or biomechanics certification.',
 samples, contract_issues_closed: false};
await writeFile(new URL('situp-repair/runtime-contact-report.json', root), JSON.stringify(report, null, 2) + '\n');
console.log(JSON.stringify({ok: true, exercise_id: '0001', phases: samples.length, model_sha256: report.model_sha256}));
