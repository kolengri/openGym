// Reproducible partial review on copied metadata; author camera files stay untouched.
// node artifacts/exercise-batches/batch-009/review-subset.mjs --tag=early-elbow-v1 --ids=1986 --capture
// Add --hands to keep one whole-body view and inspect the held hands.
// --hand-camera=0 uses the anterior camera direction for an otherwise occluded front clasp.
// --hand-frame=37.5 focuses a dynamic first-repetition peak instead of the default frame75.
import assert from 'node:assert/strict';
import {readFile, writeFile, mkdir} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {buildReview} from '../build-review.mjs';

const root = new URL('./', import.meta.url);
const read = async file => JSON.parse(await readFile(file));
const value = name => process.argv.find(arg => arg.startsWith(`--${name}=`))?.slice(name.length + 3);
const tag = value('tag'), requested = value('ids')?.split(',');
assert.match(tag ?? '', /^[a-z0-9-]+$/);
assert.ok(requested?.length && requested.every(id => /^\d+$/.test(id)));
const selection = await read(new URL('selection.json', root));
assert.ok(requested.every(id => selection.exercise_ids.includes(id)));
const ids = selection.exercise_ids.filter(id => requested.includes(id));
const out = new URL(`logs/${tag}/`, root);
const labels = await read(new URL('phase-labels.json', root));
const roles = await read(new URL('display-roles.json', root));
const presentation = await read(new URL('presentation.json', root));
await mkdir(new URL('logs/', root), {recursive: true});
try {await mkdir(out);}
catch (error) {
 if (error.code === 'EEXIST') throw Error('Diagnostic tag already exists; use a fresh tag so cached images cannot masquerade as the new model.');
 throw error;
}
await writeFile(new URL('template.html', out), await readFile(new URL('template.html', root)));
await writeFile(new URL('viewer.js', out), "import '../../viewer.js';\n");
await writeFile(new URL('build.mjs', out), "// Built by batch009/review-subset.mjs.\n");
await writeFile(new URL('presentation.json', out), JSON.stringify(presentation));
const clips = [], cameras = {}, assetFiles = {}, inputFiles = [new URL(import.meta.url)], hashes = new Map(), snapshots = [];
for (const id of ids) {
 const source = new URL(`assets/${id}/`, root), destination = new URL(`assets/${id}/`, out);
 await mkdir(destination, {recursive: true});
 const model = new URL('motion.glb', source), metadata = await read(new URL('clip.json', source));
 const bytes = await readFile(model), hash = createHash('sha256').update(bytes).digest('hex');
 const snapshot = new URL('motion.glb', destination);
 await writeFile(snapshot, bytes);
 const asset = hashes.get(hash) ?? id; hashes.set(hash, asset); assetFiles[asset] ??= snapshot;
 snapshots.push({id, original_model: fileURLToPath(model), sha256: hash, bytes: bytes.length});
 const clip = {...metadata, asset,
  primary: metadata.display_primary ?? roles[id]?.primary ?? metadata.primary,
  secondary: metadata.display_secondary ?? roles[id]?.secondary ?? metadata.secondary,
  phases: metadata.phases.map(phase => ({...phase, label: labels[phase.label] ?? phase.label}))};
 clips.push(clip);
 const cameraBytes = await readFile(new URL('cameras.json', source));
 await writeFile(new URL('cameras.json', destination), cameraBytes);
 await writeFile(new URL('clip.json', destination), JSON.stringify(metadata));
 cameras[id] = JSON.parse(cameraBytes);
 inputFiles.push(new URL('clip.json', source), new URL('cameras.json', source), new URL('cameras.json', destination));
}
await writeFile(new URL('source-snapshot.json', out), JSON.stringify({scope: 'Diagnostic model bytes copied once before fitting/capture; no author asset mutations.', models: snapshots}, null, 2));
const build = () => buildReview({root: out, batch: `009-${tag}`, ids, clips, cameras, assetFiles,
 inputFiles, presentation, initialExerciseId: ids[0], atlasFile: new URL('muscle-atlas.json', root)});
await build();
const fitter = spawnSync(process.execPath,
 [fileURLToPath(new URL('../fit-cameras.mjs', root)), '009', `logs/${tag}`], {stdio: 'inherit'});
assert.equal(fitter.status, 0, 'Subset camera fit failed');
for (const id of ids) {
 const file = new URL(`assets/${id}/cameras.json`, out);
 cameras[id] = await read(file);
 if (process.argv.includes('--hands')) {
  const posesFile = new URL(`assets/${id}/pose-samples.json`, root);
  const poses = await read(posesFile);
  const handFrame = Number(value('hand-frame') ?? 75);
  assert.ok(Number.isFinite(handFrame) && handFrame >= 0 && handFrame <= 150, 'Invalid hand review frame');
  const held = poses.reduce((best, sample) => Math.abs(sample.frame - handFrame) < Math.abs(best.frame - handFrame) ? sample : best);
  const left = held.joints.LeftHand, right = held.joints.RightHand;
  assert.ok(left?.length === 3 && right?.length === 3, `Missing hand joints for ${id}`);
  const target = left.map((value, axis) => (value + right[axis]) / 2);
  const handCamera = Number(value('hand-camera') ?? 1);
  assert.ok(handCamera === 0 || handCamera === 1, 'Hand camera must be0or1');
  const old = cameras[id][handCamera];
  cameras[id][1] = {...old, label: 'diagnostic_hands', target,
   position: target.map((value, axis) => value + old.position[axis] - old.target[axis]), scale: 0.65};
  inputFiles.push(posesFile);
  await writeFile(file, JSON.stringify(cameras[id], null, 2) + '\n');
 }
}
await build();
const allPoses = await read(new URL('review-poses.json', root));
await writeFile(new URL('review-poses.json', out), JSON.stringify(Object.fromEntries(ids.map(id => [id, allPoses[id]])), null, 2));
const captureSource = await readFile(new URL('capture-peaks.mjs', root), 'utf8');
await writeFile(new URL('capture-peaks.mjs', out), captureSource.replace('../../first-exercise-3d/', '../../../../first-exercise-3d/'));
if (process.argv.includes('--capture')) {
 const capture = spawnSync(process.execPath, [fileURLToPath(new URL('capture-peaks.mjs', out))], {stdio: 'inherit'});
 assert.equal(capture.status, 0, 'Subset capture failed');
}
