import {readFile, writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {relative} from 'node:path';
import {fileURLToPath} from 'node:url';
import {build} from '../first-exercise-3d/runtime/node_modules/esbuild/lib/main.js';
import {GLTFLoader} from '../first-exercise-3d/runtime/node_modules/three/examples/jsm/loaders/GLTFLoader.js';

const hash = value => createHash('sha256').update(value).digest('hex');
const repo = new URL('../../', import.meta.url);
const translatedPhases = {
 'Start': 'Начальная позиция', 'Enter': 'Вход в положение', 'Center': 'По центру', 'Hold': 'Удержание', 'Return': 'Возврат',
 'Descend': 'Опускание', 'Stand': 'Подъём',
 'Left reach': 'К левой пятке', 'Right reach': 'К правой пятке', 'Left twist': 'Поворот влево', 'Right twist': 'Поворот вправо',
 'Left knee / right elbow': 'Левое колено / правый локоть', 'Right knee / left elbow': 'Правое колено / левый локоть',
 'Return through center': 'Возврат через центр', 'Reach left heel': 'К левой пятке', 'Reach right heel': 'К правой пятке',
 'Hinge forward over the front shin': 'Наклон над голенью', 'Hold the hip stretch for 1 second': 'Удержание', 'Return upright': 'Возврат в исходную',
};

export async function buildReview({root, batch, ids, clips, cameras, presentation, assetFiles, initialExerciseId, inputFiles = [], atlasOverrides = {},
 atlasFile = new URL('../bodyweight-five/runtime-muscles.json', import.meta.url)}) {
 const atlas = JSON.parse(await readFile(atlasFile));
 const models = {}, encodedAssets = {};
 for (const [key, file] of Object.entries(assetFiles)) {
  const bytes = await readFile(file), document = JSON.parse(bytes.subarray(20, 20 + bytes.readUInt32LE(12)).toString());
  if (document.meshes.length !== 1 || document.skins.length !== 1 || document.images?.length) throw Error('Expected one untextured continuous skin: ' + key);
  const loaded = await new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength), '');
  const meshes = []; loaded.scene.traverse(object => {if (object.isMesh) meshes.push(object);});
  const source = meshes[0]?.geometry.getAttribute('_source_index');
  if (meshes.length !== 1 || !source) throw Error('Missing single-body source lookup: ' + key);
  const sourceIds = new Set(Array.from({length: source.count}, (_, index) => source.getX(index)));
  const sourceVertices = sourceIds.size;
  if (!sourceVertices || [...sourceIds].some(id => !Number.isInteger(id) || id < 0 || id >= sourceVertices)) throw Error('Source lookup is not a dense original-vertex domain: ' + key);
  models[key] = {path: relative(fileURLToPath(repo), fileURLToPath(file)), sha256: hash(bytes), bytes: bytes.length,
   bones: document.skins[0].joints.length, sourceVertices, animations: document.animations.map(action => action.name)};
  encodedAssets[key] = {model: bytes.toString('base64')};
 }
 const selected = new Set();
 const exercises = ids.map(id => {
  const clip = clips.find(clip => clip.id === id), asset = clip?.asset ?? 'default';
  if (!clip || !models[asset]?.animations.includes('Exercise_' + id)) throw Error('Missing action or asset: ' + id);
  function regions(names) {
   return [...new Set(names.flatMap(name => {
    if (!atlas.mappings[name]) throw Error('Unknown source muscle label: ' + name);
    return atlas.mappings[name].regions.filter(region => !clip.highlight_sides?.[name] || clip.highlight_sides[name].includes(region.split('.').at(-1)));
   }))];
  }
  const primary = regions(clip.primary), secondary = regions(clip.secondary);
  const override = atlasOverrides[id], sourceVertices = models[asset].sourceVertices;
  if (override && (!override.regions || typeof override.regions !== 'object' || Array.isArray(override.regions))) throw Error('Missing body-specific muscle regions: ' + id);
  if ((override?.sourceVertices ?? atlas.source_vertices) !== sourceVertices) throw Error('Muscle atlas does not match body topology: ' + id);
  for (const name of [...primary, ...secondary]) {
   const region = (override?.regions ?? atlas.regions)[name];
   if (!region || !region.indices.length || region.indices.length !== region.weights.length ||
    region.indices.some(index => !Number.isInteger(index) || index < 0 || index >= sourceVertices) ||
    region.weights.some(value => !Number.isFinite(value) || value < 0 || value > 1)) throw Error('Invalid muscle region for body: ' + id + '/' + name);
  }
  for (const region of [...primary, ...secondary]) selected.add(region);
  if (!primary.length || (!secondary.length && !clip.allow_unmapped_secondary) || cameras[id]?.length !== 2 || !clip.phases?.length) throw Error('Missing roles, views or phases: ' + id);
  return {id, ...presentation[id], asset, expectedBones: models[asset].bones, sourceVertices,
   ...(override ? {regions: override.regions} : {}), skinning: clip.skinning ?? 'linear', primary, secondary,
   phases: clip.phases.map(phase => ({...phase, label: translatedPhases[phase.label] ?? phase.label})), cameras: cameras[id],
   displayMode: clip.display_mode === 'stretch' ? 'stretch' : 'load'};
 });
 const config = {sourceVertices: atlas.source_vertices, initialExerciseId, exercises,
  regions: Object.fromEntries([...selected].map(name => [name, atlas.regions[name]]))};
 const template = await readFile(new URL('template.html', root), 'utf8');
 const nodePaths = [fileURLToPath(new URL('../first-exercise-3d/runtime/node_modules', import.meta.url))];
 const entryPoints = [fileURLToPath(new URL('viewer.js', root))];
 const offline = await build({entryPoints, nodePaths, bundle: true, write: false, minify: true, format: 'iife'});
 const module = await build({entryPoints, nodePaths, bundle: true, write: false, minify: false, format: 'esm', external: ['three', 'three/*']});
 const data = value => '<script id="heat-data" type="application/json">' + JSON.stringify(value).replaceAll('<', '\\u003c') + '</script>';
 const html = template.replace('__POSTER__', '').replace('__SCRIPTS__', () => data({...config, assets: encodedAssets}) + '<script>' + offline.outputFiles[0].text + '</script>');
 await writeFile(new URL('viewer.html', root), html);
 let revision;
 try {revision = JSON.parse(await readFile(new URL('source-revision.json', root))).revision;}
 catch (error) {if (error.code !== 'ENOENT') throw error;}
 let inline;
 if (revision) {
  if (!/^[0-9a-f]{40}$/.test(revision)) throw Error('An immutable source commit is required');
  const imports = {three: 'https://cdn.jsdelivr.net/npm/three@0.186.1/build/three.module.js', 'three/addons/': 'https://cdn.jsdelivr.net/npm/three@0.186.1/examples/jsm/'};
  let poster = '';
  try {poster = '<img id="poster" alt="" src="data:image/png;base64,' + (await readFile(new URL('poster.png', root))).toString('base64') + '">';}
  catch (error) {if (error.code !== 'ENOENT') throw error;}
  const assets = Object.fromEntries(Object.entries(models).map(([key, model]) => [key,
   {modelUrl: `https://raw.githubusercontent.com/kolengri/openGym/${revision}/${model.path}`} ]));
  inline = template.replace('__POSTER__', () => poster).replace('__SCRIPTS__', () => '<script type="importmap">' + JSON.stringify({imports})
   + '</script>' + data({...config, assets}) + '<script type="module">' + module.outputFiles[0].text + '</script>');
  if (Buffer.byteLength(inline) >= 512000) throw Error('Inline preview exceeds the host limit');
  await writeFile(new URL('inline.html', root), inline);
 }
 const inputs = {};
 for (const file of [new URL('build.mjs', root), new URL('template.html', root), new URL('viewer.js', root), new URL('presentation.json', root),
  new URL('./build-review.mjs', import.meta.url), new URL('./batch-002/viewer.js', import.meta.url), new URL('./dual-quaternion.js', import.meta.url),
  new URL('../chaturanga-heatmap/heat-field.js', import.meta.url), new URL('../chaturanga-heatmap/heat-material.js', import.meta.url), atlasFile, ...inputFiles])
  inputs[relative(fileURLToPath(repo), fileURLToPath(file))] = hash(await readFile(file));
 const manifest = {batch, exercise_ids: ids, initial_exercise_id: initialExerciseId, models, model_revision: revision ?? null, selected_regions: [...selected],
  video_outputs: [], frame_sequence_outputs: [], runtime: 'Three.js0.186.1 / WebGLRenderer',
  scope: 'Live review artifact; application integration and physical mobile testing remain separate.',
  display_role_note: 'Artistic source-label emphasis: cyan stretching, warm load. Not measured EMG, force, temperature or recruitment.',
  offline_html_bytes: Buffer.byteLength(html), offline_html_sha256: hash(html),
  inline_html_bytes: inline ? Buffer.byteLength(inline) : null, inline_html_sha256: inline ? hash(inline) : null, input_files_sha256: inputs};
 await writeFile(new URL('build-manifest.json', root), JSON.stringify(manifest, null, 2) + '\n');
 console.log(JSON.stringify({batch, offline_bytes: Buffer.byteLength(html), inline_bytes: inline ? Buffer.byteLength(inline) : null, exercises: ids, assets: Object.keys(models)}));
}
