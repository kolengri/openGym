import {mkdir, readFile, writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {fileURLToPath, pathToFileURL} from 'node:url';
import {resolve, sep} from 'node:path';
import {parseArgs} from 'node:util';
import {build} from '../first-exercise-3d/runtime/node_modules/esbuild/lib/main.js';

const root = new URL('./', import.meta.url);
const {values: options} = parseArgs({options: {'asset-dir': {type: 'string'}, 'output-dir': {type: 'string'}, cameras: {type: 'string'}}});
const directory = path => path ? pathToFileURL(resolve(path) + sep) : root;
const assetRoot = directory(options['asset-dir']), outputRoot = directory(options['output-dir']);
await mkdir(outputRoot, {recursive: true});
const read = async path => JSON.parse(await readFile(new URL(path, root)));
const digest = bytes => createHash('sha256').update(bytes).digest('hex');
const bytes = await readFile(new URL('ninety.glb', assetRoot));
const asset = JSON.parse(await readFile(new URL('asset-build.json', assetRoot)));
if (digest(bytes) !== asset.sha256) throw Error('Asset receipt no longer matches GLB');
const heat = await read('heat-regions.json'), presentation = (await read('../exercise-batches/batch-002/presentation.json'))['10565'];
const cameras = options.cameras ? JSON.parse(await readFile(resolve(options.cameras))) : await read('camera-presets.json');
const exercise = {id: '10565', ...presentation, shortTitle: '90/90', asset: 'default', skinning: 'linear',
 expectedBones: asset.bones, displayMode: 'stretch', primary: heat.primary, secondary: heat.secondary,
 cameras, phases: [{start: 0, end: 2, label: 'Наклон вперёд'}, {start: 2, end: 3, label: 'Удержание'},
  {start: 3, end: 5, label: 'Возврат в исходную'}]};
const config = {sourceVertices: heat.sourceVertices, regions: heat.regions, initialExerciseId: '10565', exercises: [exercise]};
const template = (await readFile(new URL('../exercise-batches/batch-002/template.html', root), 'utf8'))
 .replace('<title>Пять упражнений · мягкие зоны</title>', '<title>90/90 · мягкие зоны растяжения</title>')
 .replace('</style>', 'nav{display:none}</style>');
const nodePaths = [fileURLToPath(new URL('../first-exercise-3d/runtime/node_modules', root))];
const entryPoints = [fileURLToPath(new URL('viewer.js', root))];
const local = await build({entryPoints, nodePaths, bundle: true, minify: true, write: false, format: 'iife'});
const module = await build({entryPoints, nodePaths, bundle: true, minify: false, write: false, format: 'esm', external: ['three', 'three/*']});
const data = object => '<script id="heat-data" type="application/json">' + JSON.stringify(object).replaceAll('<', '\\u003c') + '</script>';
const html = template.replace('__POSTER__', '').replace('__SCRIPTS__', () => data({...config, assets: {default: {model: bytes.toString('base64')}}}) + '<script>' + local.outputFiles[0].text + '</script>');
await writeFile(new URL('viewer.html', outputRoot), html);
let revision, inline;
try {if (assetRoot.href === root.href) revision = (await read('source-revision.json')).revision;}
catch (error) {if (error.code !== 'ENOENT') throw error;}
if (revision) {
 if (!/^[a-f0-9]{40}$/.test(revision)) throw Error('Expected an immutable source revision');
 const imports = {three: 'https://cdn.jsdelivr.net/npm/three@0.186.1/build/three.module.js', 'three/addons/': 'https://cdn.jsdelivr.net/npm/three@0.186.1/examples/jsm/'};
 inline = template.replace('__POSTER__', '').replace('__SCRIPTS__', () => '<script type="importmap">' + JSON.stringify({imports}) + '</script>'
  + data({...config, assets: {default: {modelUrl: `https://raw.githubusercontent.com/kolengri/openGym/${revision}/artifacts/ninety-mpfb-review/ninety.glb`}}})
  + '<script type="module">' + module.outputFiles[0].text + '</script>');
 if (Buffer.byteLength(inline) >= 512000) throw Error('Inline preview exceeds host limit');
 await writeFile(new URL('inline.html', outputRoot), inline);
}
const report = {status: 'built_pending_actual_browser_and_shape_review', exerciseId: '10565',
 modelSha256: digest(bytes), modelBytes: bytes.length, sourceRevision: revision ?? null,
 offlineBytes: Buffer.byteLength(html), offlineSha256: digest(html),
 inlineBytes: inline ? Buffer.byteLength(inline) : null, inlineSha256: inline ? digest(inline) : null,
 sourceVertices: heat.sourceVertices, bones: asset.bones, skinning: 'standardLinear',
 transparentCanvas: true, videoOutputs: [], frameCacheInDelivery: false, promotion_map: {}};
await writeFile(new URL('build-manifest.json', outputRoot), JSON.stringify(report, null, 2) + '\n');
console.log(JSON.stringify(report));
