import {readFile, writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {build} from '../first-exercise-3d/runtime/node_modules/esbuild/lib/main.js';

const root = new URL('./', import.meta.url), source = new URL('../bodyweight-five/', root);
const model = await readFile(new URL('bodyweight-five.glb', source));
const atlas = JSON.parse(await readFile(new URL('runtime-muscles.json', source)));
const clip = JSON.parse(await readFile(new URL('clips.json', source))).find(clip => clip.id === '5915');
function regions(names) {
 return [...new Set(names.flatMap(name => atlas.mappings[name].regions.filter(region =>
  !clip.highlight_sides[name] || clip.highlight_sides[name].includes(region.split('.').at(-1)))))];
}
const primary = regions(clip.primary), secondary = regions(clip.secondary);
const config = {sourceVertices: atlas.source_vertices, primary, secondary,
 regions: Object.fromEntries([...primary, ...secondary].map(name => [name, atlas.regions[name]])),
 cameras: JSON.parse(await readFile(new URL('camera-presets.json', source)))['5915']};
const template = await readFile(new URL('template.html', root), 'utf8');
const nodePaths = [fileURLToPath(new URL('../first-exercise-3d/runtime/node_modules', root))];
const entryPoints = [fileURLToPath(new URL('viewer.js', root))];
const offline = await build({entryPoints, nodePaths, bundle: true, write: false, minify: true, format: 'iife'});
const module = await build({entryPoints, nodePaths, bundle: true, write: false, minify: false,
 format: 'esm', external: ['three', 'three/*']});
function data(value) {return '<script id="heat-data" type="application/json">' + JSON.stringify(value) + '</script>';}
const html = template.replace('__POSTER__', '').replace('__SCRIPTS__', () =>
 data({...config, model: model.toString('base64')}) + '<script>' + offline.outputFiles[0].text + '</script>');
await writeFile(new URL('viewer.html', root), html);
const revision = '62298177a63b9ddde7dc81c089cccef1ccdf19a8';
const modelUrl = `https://raw.githubusercontent.com/kolengri/openGym/${revision}/artifacts/bodyweight-five/bodyweight-five.glb`;
const imports = {three: 'https://cdn.jsdelivr.net/npm/three@0.186.1/build/three.module.js',
 'three/addons/': 'https://cdn.jsdelivr.net/npm/three@0.186.1/examples/jsm/'};
let poster = '';
try {poster = '<img id="poster" alt="" src="data:image/png;base64,' + (await readFile(new URL('poster.png', root))).toString('base64') + '">';}
catch (error) {if (error.code !== 'ENOENT') throw error;}
const inline = template.replace('__POSTER__', () => poster).replace('__SCRIPTS__', () =>
 '<script type="importmap">' + JSON.stringify({imports}) + '</script>' + data({...config, modelUrl})
 + '<script type="module">' + module.outputFiles[0].text + '</script>');
if (Buffer.byteLength(inline) >= 512000) throw Error('Inline preview exceeds the host limit');
await writeFile(new URL('inline.html', root), inline);
const hash = value => createHash('sha256').update(value).digest('hex');
const inputFiles = {};
for (const name of ['build.mjs', 'template.html', 'viewer.js', 'heat-field.js', 'heat-material.js'])
 inputFiles[name] = hash(await readFile(new URL(name, root)));
await writeFile(new URL('build-manifest.json', root), JSON.stringify({exercise_id: '5915',
 model_sha256: createHash('sha256').update(model).digest('hex'), model_revision: revision,
 primary_regions: primary, secondary_regions: secondary, video_outputs: [],
 runtime: 'Three.js0.186.1 / WebGLRenderer', display_role_note: 'Authored surface heat cue; relative colors and phase emphasis are not measured physiological activation.',
 offline_html_bytes: Buffer.byteLength(html), inline_html_bytes: Buffer.byteLength(inline),
 offline_html_sha256: hash(html), inline_html_sha256: hash(inline), input_files_sha256: inputFiles}, null, 2) + '\n');
console.log(JSON.stringify({offline_bytes: Buffer.byteLength(html), inline_bytes: Buffer.byteLength(inline), video_outputs: []}));
