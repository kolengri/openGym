import {readFile, writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {build} from '../../first-exercise-3d/runtime/node_modules/esbuild/lib/main.js';

const root = new URL('./', import.meta.url), source = new URL('../../bodyweight-next-five/', root);
const model = await readFile(new URL('next-five.glb', source));
const atlas = JSON.parse(await readFile(new URL('../../bodyweight-five/runtime-muscles.json', root)));
const clips = JSON.parse(await readFile(new URL('clips.json', source)));
const cameras = JSON.parse(await readFile(new URL('camera-presets.json', source)));
const presentation = JSON.parse(await readFile(new URL('presentation.json', root)));
const ids = ['5265', '4007', '6428', '10565', '6560'];
const translatedPhases = {
 'Start': 'Начальная позиция', 'Center': 'По центру', 'Left reach': 'К левой пятке', 'Right reach': 'К правой пятке',
 'Left twist': 'Поворот влево', 'Right twist': 'Поворот вправо', 'Forward hinge': 'Наклон', 'Hold': 'Удержание', 'Return': 'Возврат',
 'Left knee / right elbow': 'Левое колено / правый локоть', 'Right knee / left elbow': 'Правое колено / левый локоть',
 'Return through center': 'Возврат через центр', 'Reach left heel': 'К левой пятке', 'Reach right heel': 'К правой пятке',
 'Hinge forward over the front shin': 'Наклон над голенью', 'Hold the hip stretch for 24 seconds': 'Удержание', 'Return upright': 'Возврат в исходную',
};
const selected = new Set();
const exercises = ids.map(id => {
 const clip = clips.find(clip => clip.id === id);
 if (!clip) throw Error('Missing clip configuration: ' + id);
 function regions(names) {
  return [...new Set(names.flatMap(name => {
   if (!atlas.mappings[name]) throw Error('Unknown source muscle label: ' + name);
   return atlas.mappings[name].regions.filter(region => !clip.highlight_sides?.[name]
    || clip.highlight_sides[name].includes(region.split('.').at(-1)));
  }))];
 }
 const primary = regions(clip.primary), secondary = regions(clip.secondary);
 for (const region of [...primary, ...secondary]) selected.add(region);
 if (!primary.length || !secondary.length) throw Error('This batch requires both source role channels: ' + id);
 if (cameras[id]?.length !== 2) throw Error('Missing complementary views: ' + id);
 if (!clip.phases?.length) throw Error('Missing authored timing: ' + id);
 const phases = clip.phases.map(phase => ({...phase, label: translatedPhases[phase.label] ?? phase.label}));
 return {id, ...presentation[id], primary, secondary, phases, cameras: cameras[id],
  displayMode: ['10565', '6560'].includes(id) ? 'stretch' : 'load'};
});
const config = {sourceVertices: atlas.source_vertices, exercises,
 regions: Object.fromEntries([...selected].map(name => [name, atlas.regions[name]]))};
const template = await readFile(new URL('template.html', root), 'utf8');
const nodePaths = [fileURLToPath(new URL('../../first-exercise-3d/runtime/node_modules', root))];
const entryPoints = [fileURLToPath(new URL('viewer.js', root))];
const offline = await build({entryPoints, nodePaths, bundle: true, write: false, minify: true, format: 'iife'});
const module = await build({entryPoints, nodePaths, bundle: true, write: false, minify: false, format: 'esm', external: ['three', 'three/*']});
const data = value => '<script id="heat-data" type="application/json">' + JSON.stringify(value).replaceAll('<', '\\u003c') + '</script>';
const html = template.replace('__POSTER__', '').replace('__SCRIPTS__', () => data({...config, model: model.toString('base64')})
 + '<script>' + offline.outputFiles[0].text + '</script>');
await writeFile(new URL('viewer.html', root), html);
let revision;
try {revision = JSON.parse(await readFile(new URL('source-revision.json', root))).revision;}
catch (error) {if (error.code !== 'ENOENT') throw error;}
let inline;
if (revision) {
 if (!/^[0-9a-f]{40}$/.test(revision)) throw Error('An immutable source commit is required');
 const imports = {three: 'https://cdn.jsdelivr.net/npm/three@0.186.1/build/three.module.js',
  'three/addons/': 'https://cdn.jsdelivr.net/npm/three@0.186.1/examples/jsm/'};
 let poster = '';
 try {poster = '<img id="poster" alt="" src="data:image/png;base64,' + (await readFile(new URL('poster.png', root))).toString('base64') + '">';}
 catch (error) {if (error.code !== 'ENOENT') throw error;}
 const modelUrl = `https://raw.githubusercontent.com/kolengri/openGym/${revision}/artifacts/bodyweight-next-five/next-five.glb`;
 inline = template.replace('__POSTER__', () => poster).replace('__SCRIPTS__', () =>
  '<script type="importmap">' + JSON.stringify({imports}) + '</script>' + data({...config, modelUrl})
  + '<script type="module">' + module.outputFiles[0].text + '</script>');
 if (Buffer.byteLength(inline) >= 512000) throw Error('Inline preview exceeds the host limit');
 await writeFile(new URL('inline.html', root), inline);
}
const hash = value => createHash('sha256').update(value).digest('hex');
const inputs = {};
for (const name of ['build.mjs', 'template.html', 'viewer.js', 'presentation.json', '../../chaturanga-heatmap/heat-field.js', '../../chaturanga-heatmap/heat-material.js'])
 inputs[name] = hash(await readFile(new URL(name, root)));
await writeFile(new URL('build-manifest.json', root), JSON.stringify({batch: '002', exercise_ids: ids,
 model_sha256: hash(model), model_revision: revision ?? null, selected_regions: [...selected], video_outputs: [], frame_sequence_outputs: [],
 runtime: 'Three.js0.186.1 / WebGLRenderer', scope: 'Live review artifact; application integration and physical mobile device testing remain separate.',
 display_role_note: 'Artistic source-label emphasis. Cyan represents stretching; warm colors represent load emphasis. Not measured EMG, force, temperature or recruitment.',
 offline_html_bytes: Buffer.byteLength(html), offline_html_sha256: hash(html),
 inline_html_bytes: inline ? Buffer.byteLength(inline) : null, inline_html_sha256: inline ? hash(inline) : null,
 input_files_sha256: inputs}, null, 2) + '\n');
console.log(JSON.stringify({offline_bytes: Buffer.byteLength(html), inline_bytes: inline ? Buffer.byteLength(inline) : null, exercises: ids, video_outputs: []}));
