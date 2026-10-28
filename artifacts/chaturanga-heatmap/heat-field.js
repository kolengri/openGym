import {BufferAttribute} from 'three';

// Diffuse along the actual surface, across glTF UV splits via original IDs.
// Nearby limbs do not exchange heat merely because they touch in a pose.
export function attachHeatField(mesh, config) {
 const source = mesh.geometry.getAttribute('_source_index');
 if (!source) throw Error('The model has no original-vertex lookup');
 const count = config.sourceVertices, adjacency = Array.from({length: count}, () => new Map());
 const positions = mesh.geometry.getAttribute('position'), rest = new Array(count);
 for (let i = 0; i < source.count; i++) {
  const id = Math.round(source.getX(i));
  rest[id] ??= [positions.getX(i), positions.getY(i), positions.getZ(i)];
 }
 const index = mesh.geometry.index;
 function edge(a, b) {
  if (a === b || adjacency[a].has(b)) return;
  const distance = Math.hypot(...rest[a].map((value, axis) => value - rest[b][axis]));
  adjacency[a].set(b, distance); adjacency[b].set(a, distance);
 }
 for (let i = 0; i < (index?.count ?? source.count); i += 3) {
  const ids = [0, 1, 2].map(offset => Math.round(source.getX(index ? index.getX(i + offset) : i + offset)));
  edge(ids[0], ids[1]); edge(ids[1], ids[2]); edge(ids[2], ids[0]);
 }
 function field(names, falloff) {
  let values = new Float32Array(count);
  for (const name of names) {
   const region = config.regions[name];
   if (!region) throw Error('Unknown heat region: ' + name);
   region.indices.forEach((id, index) => {values[id] = Math.max(values[id], region.weights[index]);});
  }
  for (let pass = 0; pass < 22; pass++) {
   const next = values.slice();
   adjacency.forEach((neighbors, id) => {
    for (const [neighbor, distance] of neighbors) next[id] = Math.max(next[id], values[neighbor] * Math.exp(-distance / falloff));
   });
   values = next;
  }
  for (let pass = 0; pass < 3; pass++) {
   const next = values.slice();
   adjacency.forEach((neighbors, id) => {
    if (!neighbors.size) return;
    let sum = 0; for (const neighbor of neighbors.keys()) sum += values[neighbor];
    next[id] = .45 * values[id] + .55 * sum / neighbors.size;
   });
   values = next;
  }
  const maximum = Math.max(...values);
  if (maximum <= 0) throw Error('Empty heat field');
  return values.map(value => value / maximum);
 }
 const primary = field(config.primary, .036), secondary = field(config.secondary, .032);
 const attribute = new Float32Array(source.count * 2);
 for (let i = 0; i < source.count; i++) {
  const id = Math.round(source.getX(i));
  attribute[i * 2] = primary[id]; attribute[i * 2 + 1] = secondary[id];
 }
 mesh.geometry.setAttribute('heatZone', new BufferAttribute(attribute, 2));
 return {primary, secondary, sourceVertexCount: count, exportedVertexCount: source.count,
  falloffMeters: {primary: .036, secondary: .032}, diffusionPasses: 22, smoothingPasses: 3};
}
