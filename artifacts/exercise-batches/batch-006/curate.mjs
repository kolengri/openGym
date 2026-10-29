import {readFile, writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {relative} from 'node:path';
import {fileURLToPath} from 'node:url';

const root = new URL('./', import.meta.url), repo = new URL('../../../', root);
const read = async file => JSON.parse(await readFile(file));
const build = await read(new URL('build-manifest.json', root)), ids = build.exercise_ids;
const files = new Set();
function add(file) { files.add(fileURLToPath(file)); }
for (const file of ['.gitignore', 'README.md', 'selection.json', 'user-feedback.json',
 'authoring-handoff.md', 'asset-interface.json', 'build.mjs', 'template.html', 'viewer.js',
 'verify.mjs', 'verify-inline.mjs', 'prepare-muscle-atlas.mjs', 'muscle-atlas.json',
 'muscle-atlas-provenance.json', 'presentation.json', 'phase-labels.json', 'findings.md',
 'capture-peaks.mjs', 'capture-peaks.json', 'curate.mjs', 'camera-fit.json',
 'root-integration.json', 'reference-normalization.json', 'build-manifest.json', 'verification.json', 'runtime-contacts.json',
 'visual-review.json', 'visual-grasp-review.json', 'operator-checks.json', 'poster.png', 'mobile.png']) add(new URL(file, root));
for (const id of ids) {
 add(new URL(`contexts/${id}.json`, root));
 add(new URL(`review-${id}.png`, root));
}
for (const directory of [...ids.map(id => `assets/${id}/`), 'floor-crunch-family/',
 'leg-raise-family/', 'standing-leg-family/', 'upright-cardio-family/']) {
 const base = new URL(directory, root), manifest = new URL('curated-files.json', base);
 add(manifest);
 const packet = await read(manifest);
 for (const item of packet.files) add(new URL(typeof item === 'string' ? item : item.path, base));
 for (const item of [...(packet.external_workspace_dependencies_already_tracked_elsewhere ?? []),
  ...(packet.read_only_dependencies ?? [])]) add(new URL(item.path, repo));
}
for (const path of Object.keys(build.input_files_sha256)) add(new URL(path, repo));
for (const sample of (await read(new URL('capture-peaks.json', root))).evidence) add(new URL(sample.file, root));
for (const file of ['build-review.mjs', 'fit-cameras.mjs', 'verify-review.mjs', 'verify-inline.mjs']) add(new URL('../' + file, root));
for (const file of ['source-revision.json', 'inline.html', 'inline-verification.json', 'inline-settled.png', 'publication-report.json']) {
 const url = new URL(file, root);
 try { await readFile(url); add(url); } catch (error) { if (error.code !== 'ENOENT') throw error; }
}
const entries = [];
for (const file of [...files].sort()) {
 const data = await readFile(file);
 entries.push({path: relative(fileURLToPath(repo), file), bytes: data.length,
  sha256: createHash('sha256').update(data).digest('hex')});
}
const manifest = {batch: '006', exercise_ids: ids, model_revision: build.model_revision,
 policy: 'Explicit final packets and accepted review evidence only; no logs, trials, backups, environments or temporary full-cycle audit streams.',
 manifest_self_hash_policy: 'This manifest is staged separately and does not hash itself.',
 files: entries, total_bytes: entries.reduce((sum, entry) => sum + entry.bytes, 0)};
await writeFile(new URL('curated-delivery.json', root), JSON.stringify(manifest, null, 2) + '\n');
console.log(JSON.stringify({files: entries.length, bytes: manifest.total_bytes}));
