import {readFile, writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {GLTFLoader} from '../../first-exercise-3d/runtime/node_modules/three/examples/jsm/loaders/GLTFLoader.js';

// Offline data preparation only: diffuse original labels over the neutral skin.
// No camera, pose, mesh, shared atlas or runtime shader is changed.
const root = new URL('./', import.meta.url);
const atlasBytes = await readFile(new URL('../../bodyweight-five/runtime-muscles.json', import.meta.url));
const atlas = JSON.parse(atlasBytes), count = atlas.source_vertices;
const bytes = await readFile(new URL('assets/5266/motion.glb', root));
const loaded = await new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength), '');
let geometry;
loaded.scene.traverse(object => {if (object.isMesh) geometry = object.geometry;});
const source = geometry.getAttribute('_source_index'), position = geometry.getAttribute('position');
const rest = new Array(count), adjacency = Array.from({length: count}, () => new Set());
for (let i = 0; i < source.count; i++) rest[source.getX(i)] ??= [position.getX(i), position.getY(i), position.getZ(i)];
const index = geometry.index;
for (let i = 0; i < (index?.count ?? source.count); i += 3) {
 const ids = [0, 1, 2].map(offset => source.getX(index ? index.getX(i + offset) : i + offset));
 for (const [a, b] of [[ids[0], ids[1]], [ids[1], ids[2]], [ids[2], ids[0]]]) {
  if (a !== b) {adjacency[a].add(b); adjacency[b].add(a);}
 }
}
const neighbors = adjacency.map((set, id) => [...set].map(other => ({id: other,
 weight: 1 / Math.max(.002, Math.hypot(...rest[id].map((value, axis) => value - rest[other][axis])))})));
const labels = ['abs', 'obliques', 'hip flexors', 'lower abs'];
const names = [...new Set(labels.flatMap(label => atlas.mappings[label].regions))], regions = {};
const passes = 24, blend = .55, threshold = .012;
for (const name of names) {
 let values = new Float64Array(count);
 const original = atlas.regions[name];
 original.indices.forEach((id, i) => {values[id] = original.weights[i];});
 for (let pass = 0; pass < passes; pass++) {
  const next = values.slice();
  neighbors.forEach((row, id) => {
   let total = 0, sum = 0;
   for (const neighbor of row) {sum += values[neighbor.id] * neighbor.weight; total += neighbor.weight;}
   if (total) next[id] = values[id] * (1 - blend) + blend * sum / total;
  });
  values = next;
 }
 const maximum = Math.max(...values), indices = [], weights = [];
 if (!(maximum > 0)) throw Error('Empty source region: ' + name);
 values.forEach((value, id) => {
  const normalized = value / maximum;
  const t = Math.max(0, Math.min(1, (normalized - threshold) / (.04 - threshold)));
  const weight = Math.round(normalized * t * t * (3 - 2 * t) * 1e6) / 1e6;
  if (weight > 0) {indices.push(id); weights.push(weight);}
 });
 regions[name] = {indices, weights};
}
const result = {sourceVertices: count, regions};
await writeFile(new URL('soft-abdominal-regions.json', root), JSON.stringify(result) + '\n');
await writeFile(new URL('soft-zone-preparation.json', root), JSON.stringify({
 sourceAtlas: 'artifacts/bodyweight-five/runtime-muscles.json',
 sourceAtlasSha256: createHash('sha256').update(atlasBytes).digest('hex'),
 neutralSurfaceGlbSha256: createHash('sha256').update(bytes).digest('hex'),
 method: '24 inverse-edge-length weighted graph heat steps, 55% neighbor blend; per-region normalization and smooth tiny-tail taper. Existing runtime surface falloff remains unchanged.',
 artisticParameters: {passes, blend, tailThreshold: threshold, fullTailWeight: .04},
 sourceVertices: count, regionVertices: Object.fromEntries(Object.entries(regions).map(([name, data]) => [name, data.indices.length])),
 scope: 'Softened source-label emphasis for 2395 and 5266 only. No measured activation claim. Graph adjacency prevents transfer between nearby unconnected limbs.',
 geometryAndRuntimeChanged: false
}, null, 2) + '\n');
console.log(JSON.stringify({sourceVertices: count, regions: names.length, bytes: Buffer.byteLength(JSON.stringify(result))}));
