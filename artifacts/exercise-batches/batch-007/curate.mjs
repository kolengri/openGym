import {readFile, writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {relative} from 'node:path';
import {fileURLToPath} from 'node:url';

const root = new URL('./', import.meta.url), repo = new URL('../../../', root);
const read = async file => JSON.parse(await readFile(file));
const build = await read(new URL('build-manifest.json', root));
const files = new Set();
const add = file => files.add(fileURLToPath(file));
for (const name of ['.gitignore', 'README.md', 'selection.json', 'authoring-handoff.md',
 'asset-interface.json', 'build.mjs', 'template.html', 'viewer.js', 'verify.mjs',
 'verify-inline.mjs', 'prepare-muscle-atlas.mjs', 'muscle-atlas.json', 'muscle-atlas-provenance.json',
 'presentation.json', 'phase-labels.json', 'findings.md', 'capture-peaks.mjs', 'review-poses.json',
 'capture-peaks.json', 'curate.mjs', 'camera-fit.json', 'root-integration.json', 'reference-normalization.json',
 'capture-camera.mjs', 'camera-muscle-3294.json', 'camera-muscle-3294.png',
 'eight-diagnostic-checks.json', 'visual-eight-diagnostic.json',
 'build-manifest.json', 'verification.json', 'runtime-contacts.json', 'visual-review.json',
 'operator-checks.json', 'poster.png', 'mobile.png']) add(new URL(name, root));
for (const id of build.exercise_ids) {
 add(new URL(`contexts/${id}.json`, root));
 add(new URL(`review-${id}.png`, root));
}
for (const directory of [...build.exercise_ids.map(id => `assets/${id}/`),
 'upright-family/', 'kneeling-family/', 'prone-family/', 'ankle-family/', 'arm-circle-family/',
 'resting-repair/', 'feedback-resting-fists/']) {
 const base = new URL(directory, root), manifest = new URL('curated-files.json', base);
 add(manifest);
 const packet = await read(manifest);
 if (packet.delivery_ready === false) throw Error('Rejected or incomplete asset packet: ' + directory);
 const entries = packet.files ?? packet.included_files;
 if (!Array.isArray(entries)) throw Error('Missing explicit packet file list: ' + directory);
 for (const item of entries) add(new URL(typeof item === 'string' ? item : item.path, base));
 for (const item of [...(packet.external_workspace_dependencies_already_tracked_elsewhere ?? []),
  ...(packet.read_only_dependencies ?? []), ...(packet.exact_readonly_inputs ?? [])]) add(new URL(item.path, repo));
}
for (const path of Object.keys(build.input_files_sha256)) add(new URL(path, repo));
for (const name of ['rollback-mask.json', 'rollback-domain-inspection.json', 'frame-binding-evidence.json',
 'inspect_frames.py', 'derive_rollback_domains.py']) add(new URL('joint-diagnosis/' + name, root));
for (const name of ['diagnosis.md', 'hinge-plane-evidence.json', 'hip-original-binding-contract.json',
 'shoulder-volume-target-contract.json']) add(new URL('fold-skin-diagnosis/' + name, root));
for (const sample of (await read(new URL('capture-peaks.json', root))).evidence) add(new URL(sample.file, root));
for (const name of ['build-review.mjs', 'fit-cameras.mjs', 'verify-review.mjs', 'verify-inline.mjs']) add(new URL('../' + name, root));
for (const name of ['source-revision.json', 'inline.html', 'inline-verification.json',
 'inline-settled.png', 'inline-delivery.json', 'publication-report.json']) {
 const file = new URL(name, root);
 try {await readFile(file); add(file);} catch (error) {if (error.code !== 'ENOENT') throw error;}
}
const entries = [];
for (const file of [...files].sort()) {
 const data = await readFile(file);
 entries.push({path: relative(fileURLToPath(repo), file), bytes: data.length,
  sha256: createHash('sha256').update(data).digest('hex')});
}
await writeFile(new URL('curated-delivery.json', root), JSON.stringify({batch: '007',
 exercise_ids: build.exercise_ids, model_revision: build.model_revision,
 policy: 'Explicit final packets and accepted evidence only; no logs, trials, caches, backups, environments or temporary full-cycle streams.',
 manifest_self_hash_policy: 'This manifest is staged separately and does not hash itself.',
 files: entries, total_bytes: entries.reduce((sum, entry) => sum + entry.bytes, 0)}, null, 2) + '\n');
console.log(JSON.stringify({files: entries.length, bytes: entries.reduce((sum, entry) => sum + entry.bytes, 0)}));
