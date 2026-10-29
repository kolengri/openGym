import assert from 'node:assert/strict';
import {readFile, writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {relative} from 'node:path';
import {fileURLToPath} from 'node:url';

const root = new URL('./', import.meta.url), repo = new URL('../../../', root);
const sourceOnly = process.argv.includes('--source-only');
const read = async file => JSON.parse(await readFile(file));
const selection = await read(new URL('selection.json', root)), files = new Map();
function add(file) {
 const path = relative(fileURLToPath(repo), fileURLToPath(file));
 assert.ok(path.startsWith('artifacts/') && !path.split('/').includes('..'), 'File outside artifact scope: ' + path);
 assert.ok(!/(\/logs\/|\/node_modules\/|\/\.venv\/|__pycache__|\.blend1$)/.test(path), 'Uncurated temporary dependency: ' + path);
 files.set(path, file);
}
async function addDependencies(declaration, base) {
 if (!declaration) return;
 if (typeof declaration === 'string') {
  const file = new URL(declaration, base);
  add(file);
  const packet = await read(file);
  declaration = packet.read_only_workspace_files ?? packet.repository ?? packet.read_only_dependencies;
  if (packet.original_CC0_body) declaration = [packet.original_CC0_body, ...(declaration ?? [])];
 }
 assert.ok(Array.isArray(declaration), 'Missing explicit workspace dependency list');
 for (const entry of declaration) {
  const path = typeof entry === 'string' ? entry : entry.path;
  assert.equal(typeof path, 'string', 'Dependency path must be explicit');
  // Installed libraries and external QA tools remain recorded dependencies, not vendored artifacts.
  if (path.startsWith('/') || path.includes('/node_modules/')) continue;
  assert.ok(path.startsWith('artifacts/') || path.startsWith('catalogue/'), 'Unexpected dependency scope: ' + path);
  if (entry.sha256) assert.equal(createHash('sha256').update(await readFile(new URL(path, repo))).digest('hex'),
   entry.sha256, 'Changed read-only dependency: ' + path);
  if (path.startsWith('artifacts/')) add(new URL(path, repo));
 }
}
for (const name of ['.gitignore', 'README.md', 'selection.json', 'authoring-handoff.md', 'asset-interface.json',
 'intake-contract.json', 'intake-provenance.json', 'build.mjs', 'template.html', 'viewer.js', 'verify.mjs',
 'verify-inline.mjs', 'prepare-muscle-atlas.mjs', 'muscle-atlas.json', 'muscle-atlas-provenance.json',
 'presentation.json', 'phase-labels.json', 'findings.md', 'review-poses.json', 'camera-integration.json', 'capture-peaks.mjs', 'curate.mjs']) add(new URL(name, root));
for (const id of selection.exercise_ids) add(new URL(`contexts/${id}.json`, root));
// The same declared family list drives both source and final packets, including each manifest itself.
for (const directory of [...selection.exercise_ids.map(id => `assets/${id}`), ...selection.authoring_families]) {
 const base = new URL(directory + '/', root), manifest = new URL('curated-files.json', base);
 add(manifest);
 const packet = await read(manifest);
 assert.notEqual(packet.delivery_ready, false, 'Unfinished author packet: ' + directory);
 const entries = packet.files ?? packet.included_files;
 assert.ok(Array.isArray(entries), 'Missing explicit author file list: ' + directory);
 for (const entry of entries) add(new URL(typeof entry === 'string' ? entry : entry.path, base));
 for (const declaration of [packet.external_workspace_dependencies_already_tracked_elsewhere,
  packet.read_only_dependencies, packet.exact_readonly_inputs]) await addDependencies(declaration, base);
 if (entries.some(entry => (typeof entry === 'string' ? entry : entry.path) === 'dependencies.json') &&
  packet.read_only_dependencies !== 'dependencies.json') await addDependencies('dependencies.json', base);
}
for (const name of ['build-review.mjs', 'fit-cameras.mjs', 'verify-review.mjs', 'verify-inline.mjs',
 'dual-quaternion.js', 'batch-002/viewer.js']) add(new URL('../' + name, root));
for (const name of ['heat-field.js', 'heat-material.js']) add(new URL('../../chaturanga-heatmap/' + name, root));
let build;
if (!sourceOnly) {
 build = await read(new URL('build-manifest.json', root));
 assert.deepEqual(build.exercise_ids, selection.exercise_ids);
 for (const name of ['camera-fit.json', 'root-integration.json', 'build-manifest.json', 'verification.json',
  'runtime-contacts.json', 'visual-review.json', 'operator-checks.json', 'capture-peaks.json', 'poster.png', 'mobile.png']) add(new URL(name, root));
 for (const id of selection.exercise_ids) add(new URL(`review-${id}.png`, root));
 for (const path of Object.keys(build.input_files_sha256)) add(new URL(path, repo));
 for (const sample of (await read(new URL('capture-peaks.json', root))).evidence) add(new URL(sample.file, root));
 for (const name of ['source-revision.json', 'inline.html', 'inline-verification.json', 'inline-settled.png',
  'inline-delivery.json', 'publication-report.json']) {
  const file = new URL(name, root);
  try {await readFile(file); add(file);} catch (error) {if (error.code !== 'ENOENT') throw error;}
 }
}
const entries = [];
for (const [path, file] of [...files].sort(([a], [b]) => a.localeCompare(b))) {
 const data = await readFile(file);
 entries.push({path, bytes: data.length, sha256: createHash('sha256').update(data).digest('hex')});
}
const destination = sourceOnly ? 'source-delivery.json' : 'curated-delivery.json';
await writeFile(new URL(destination, root), JSON.stringify({batch: '008', exercise_ids: selection.exercise_ids,
 packet: sourceOnly ? 'accepted_sources_and_reproduction_dependencies' : 'accepted_sources_and_verified_review',
 model_revision: build?.model_revision ?? null,
 policy: 'Explicit source/asset/family manifests and selected final evidence only. No logs, trials, caches, environments, backups or runtime frame streams.',
 manifest_self_hash_policy: 'The generated packet manifest is staged separately and does not hash itself.',
 files: entries, total_bytes: entries.reduce((sum, entry) => sum + entry.bytes, 0)}, null, 2) + '\n');
console.log(JSON.stringify({packet: destination, files: entries.length, bytes: entries.reduce((sum, entry) => sum + entry.bytes, 0)}));
