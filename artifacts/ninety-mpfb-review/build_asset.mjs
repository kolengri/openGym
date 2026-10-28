import {mkdir, readFile, writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {parseArgs} from 'node:util';
import {resolve} from 'node:path';
import * as THREE from '../first-exercise-3d/runtime/node_modules/three/build/three.module.js';
import {GLTFExporter} from '../first-exercise-3d/runtime/node_modules/three/examples/jsm/exporters/GLTFExporter.js';
import {GLTFLoader} from '../first-exercise-3d/runtime/node_modules/three/examples/jsm/loaders/GLTFLoader.js';

const here = new URL('./', import.meta.url);
const read = async name => JSON.parse(await readFile(new URL(name, here)));
const hash = bytes => createHash('sha256').update(bytes).digest('hex');
const {values: options} = parseArgs({options: {
 'weight-override': {type: 'string'}, correctives: {type: 'string'}, 'output-dir': {type: 'string'},
}});
const outputDirectory = options['output-dir'] ? resolve(options['output-dir']) : new URL('./', here);
await mkdir(outputDirectory, {recursive: true});
const writeOutput = (name, bytes) => writeFile(typeof outputDirectory === 'string'
 ? resolve(outputDirectory, name) : new URL(name, outputDirectory), bytes);
async function optionalInput(path) {
 if (!path) return null;
 const bytes = await readFile(resolve(path));
 return {data: JSON.parse(bytes), sha256: hash(bytes)};
}
globalThis.FileReader ??= class {
 async readAsArrayBuffer(blob) {
  this.result = await blob.arrayBuffer(); this.onloadend?.();
 }
};
const meshInput = await read('mesh-input.json'), motion = await read('motion-input.json');
const override = await optionalInput(options['weight-override']);
const correctiveInput = await optionalInput(options.correctives);
const runtimeWeights = motion.weights.map(values => ({...values}));
for (const [key, values] of Object.entries(override?.data.weights ?? {})) {
 const vertex = Number(key), entries = Object.entries(values);
 if (!Number.isInteger(vertex) || vertex < 0 || vertex >= runtimeWeights.length || entries.length < 1 || entries.length > 4)
  throw Error('Invalid runtime weight override vertex/influence count');
 for (const [group, mass] of entries) {
  if (!Number.isInteger(Number(group)) || Number(group) < 0 || Number(group) >= motion.groups.length || !Number.isFinite(mass) || mass <= 0)
   throw Error('Invalid runtime weight override influence');
 }
 const total = entries.reduce((sum, [, mass]) => sum + mass, 0);
 if (Math.abs(total - 1) > 1e-5) throw Error('Runtime weight override is not normalized');
 runtimeWeights[vertex] = Object.fromEntries(entries.map(([group, mass]) => [group, mass / total]));
}
const geometry = new THREE.BufferGeometry();
geometry.setAttribute('position', new THREE.Float32BufferAttribute(meshInput.positions.flat(), 3));
geometry.setAttribute('normal', new THREE.Float32BufferAttribute(meshInput.normals.flat(), 3));
geometry.setAttribute('_source_index', new THREE.Float32BufferAttribute(meshInput.positions.map((_, i) => i), 1));
geometry.setAttribute('_native_source_index', new THREE.Float32BufferAttribute(meshInput.native_source_ids, 1));
geometry.setIndex(meshInput.triangles.flat());
const correctives = correctiveInput?.data;
const morphDeltas = [];
if (correctives) {
 if (correctives.sourceMotionSha256 !== hash(await readFile(new URL('motion-input.json', here))))
  throw Error('Correctives use a different source motion');
 if (correctives.targets.length !== 2 || correctives.times.length !== motion.times.length || correctives.weights.length !== motion.times.length)
  throw Error('Expected two corrective targets over the complete clip');
 if (correctives.weightOverrideSha256 !== (override?.sha256 ?? null)) throw Error('Correctives use a different runtime weight source');
 correctives.times.forEach((time, frame) => {
  const values = correctives.weights[frame];
  if (Math.abs(time - motion.times[frame]) > 1e-6 || values.length !== 2 || values.some(value => !Number.isFinite(value) || value < 0 || value > 1))
   throw Error('Invalid corrective timing/weights');
  if ((frame === 0 || frame === motion.times.length - 1) && values.some(value => value !== 0))
   throw Error('Correctives change the seated bind or loop seam');
 });
 geometry.morphTargetsRelative = true;
 geometry.morphAttributes.position = [];
 geometry.morphAttributes.normal = [];
 for (const target of correctives.targets) {
  const delta = new Float32Array(meshInput.source_vertices * 3);
  for (const [key, values] of Object.entries(target.deltas)) {
   const vertex = Number(key);
   if (!Number.isInteger(vertex) || vertex < 0 || vertex >= meshInput.source_vertices || values.length !== 3 || values.some(value => !Number.isFinite(value)) || Math.hypot(...values) > .0080001)
    throw Error('Invalid or unbounded corrective delta');
   delta.set(values, vertex * 3);
  }
  morphDeltas.push(delta);
  const attribute = new THREE.Float32BufferAttribute(delta, 3); attribute.name = target.name;
  geometry.morphAttributes.position.push(attribute);
  const targetGeometry = geometry.clone();
  const positions = targetGeometry.getAttribute('position').array;
  for (let i = 0; i < positions.length; i++) positions[i] += delta[i];
  targetGeometry.computeVertexNormals();
  const normals = targetGeometry.getAttribute('normal').array, baseNormals = geometry.getAttribute('normal').array;
  const normalDelta = Float32Array.from(normals, (value, index) => value - baseNormals[index]);
  geometry.morphAttributes.normal.push(new THREE.Float32BufferAttribute(normalDelta, 3));
  targetGeometry.dispose();
 }
}
const indices = new Uint16Array(meshInput.positions.length * 4), weights = new Float32Array(indices.length);
runtimeWeights.forEach((values, vertex) => {
 Object.entries(values).sort((a, b) => Number(a[0]) - Number(b[0])).forEach(([group, value], slot) => {
  if (slot >= 4) throw Error('More than four runtime influences');
  indices[vertex * 4 + slot] = Number(group) + 1; weights[vertex * 4 + slot] = value;
 });
});
geometry.setAttribute('skinIndex', new THREE.Uint16BufferAttribute(indices, 4));
geometry.setAttribute('skinWeight', new THREE.Float32BufferAttribute(weights, 4));
const root = new THREE.Group(); root.name = 'Seated90'; root.rotation.x = -Math.PI / 2;
const jointRoot = new THREE.Bone(); jointRoot.name = 'ExerciseRoot'; root.add(jointRoot);
const bones = [jointRoot];
motion.groups.forEach((members, group) => {
 const bone = new THREE.Bone(); bone.name = 'Deform_' + String(group).padStart(3, '0');
 bone.userData.nativeMembers = members; jointRoot.add(bone); bones.push(bone);
});
const mesh = new THREE.SkinnedMesh(geometry, new THREE.MeshStandardMaterial({color: '#aeb8bf', roughness: 1, metalness: 0}));
mesh.name = 'SeatedMannequin'; mesh.frustumCulled = false; mesh.normalizeSkinWeights(); root.add(mesh);
root.updateMatrixWorld(true);
const tracks = [], referenceMatrices = motion.trajectories.map(frame => frame.map(values => new THREE.Matrix4().set(...values.flat())));
const trsMatrices = motion.trajectories.map(frame => frame.map(() => new THREE.Matrix4()));
const matrix = new THREE.Matrix4(), position = new THREE.Vector3(), quaternion = new THREE.Quaternion(), scale = new THREE.Vector3();
let maxDecompositionComponentError = 0;
motion.groups.forEach((members, group) => {
 const positions = [], rotations = [], scales = []; let previous;
 for (let frame = 0; frame < motion.times.length; frame++) {
  matrix.set(...motion.bind_trajectories[frame][group].flat());
  if (matrix.determinant() <= 0) throw Error('Reflected deformation group: ' + group);
  matrix.decompose(position, quaternion, scale); quaternion.normalize();
  if (previous && previous.dot(quaternion) < 0) quaternion.set(-quaternion.x, -quaternion.y, -quaternion.z, -quaternion.w);
  previous = quaternion.clone();
  const reconstructed = trsMatrices[frame][group].compose(position, quaternion, scale);
  maxDecompositionComponentError = Math.max(maxDecompositionComponentError,
   ...matrix.elements.map((value, index) => Math.abs(value - reconstructed.elements[index])));
  positions.push(...position.toArray()); rotations.push(...quaternion.toArray()); scales.push(...scale.toArray());
 }
 const bone = bones[group + 1];
 bone.position.fromArray(positions); bone.quaternion.fromArray(rotations); bone.scale.fromArray(scales);
 const inverseBind = trsMatrices[0][group].clone().invert();
 for (let frame = 0; frame < motion.times.length; frame++) trsMatrices[frame][group].multiply(inverseBind);
 tracks.push(new THREE.VectorKeyframeTrack(bone.uuid + '.position', motion.times, positions),
  new THREE.QuaternionKeyframeTrack(bone.uuid + '.quaternion', motion.times, rotations),
  new THREE.VectorKeyframeTrack(bone.uuid + '.scale', motion.times, scales));
});
root.updateMatrixWorld(true);
mesh.bind(new THREE.Skeleton(bones), mesh.matrixWorld);
if (correctives) tracks.push(new THREE.NumberKeyframeTrack(mesh.uuid + '.morphTargetInfluences', motion.times, correctives.weights.flat()));
const clip = new THREE.AnimationClip(motion.clip_name, 5, tracks);
clip.optimize();
root.userData = {assetLicense: 'CC0-1.0', source: 'MakeHuman community MPFB2v2.0.18',
 sourceExerciseId: '10565', runtimeSkinning: 'standardLinearSeatedBind',
 timing: {durationSeconds: 5, enterSeconds: 2, holdSeconds: 1, returnSeconds: 2},
 anatomicalRig: 'Preserved in native authoring files; this skin contains clip-specific deformation groups.'};
const output = await new GLTFExporter().parseAsync(root, {binary: true, animations: [clip], trs: true});
const bytes = Buffer.from(output);
await writeOutput('ninety.glb', bytes);
const loaded = await new GLTFLoader().parseAsync(output, '');
const meshes = []; loaded.scene.traverse(object => {if (object.isSkinnedMesh) meshes.push(object);});
if (meshes.length !== 1 || loaded.animations.length !== 1) throw Error('Unexpected GLB structure');
const actualMesh = meshes[0], source = actualMesh.geometry.getAttribute('_source_index');
if (source.count !== meshInput.source_vertices) throw Error('Unexpected split/missing vertices');
if ((actualMesh.morphTargetInfluences?.length ?? 0) !== morphDeltas.length) throw Error('GLB lost corrective targets');
const mixer = new THREE.AnimationMixer(loaded.scene), action = mixer.clipAction(loaded.animations[0]);
action.setLoop(THREE.LoopOnce, 1); action.clampWhenFinished = true; action.play();
const samples = new Float32Array(motion.times.length * source.count * 3), p = new THREE.Vector3(), expected = new THREE.Vector3(), point = new THREE.Vector3(), referencePoint = new THREE.Vector3();
let codecError = 0, referenceError = 0, bindError = 0, loopError = 0;
const parsedWeights = runtimeWeights.map(values => Object.entries(values).map(([group, mass]) => [Number(group), mass]));
for (let frame = 0; frame < motion.times.length; frame++) {
 mixer.setTime(motion.times[frame]); loaded.scene.updateMatrixWorld(true); actualMesh.skeleton.update();
 for (let vertex = 0; vertex < source.count; vertex++) {
  const id = Math.round(source.getX(vertex)); p.fromArray(meshInput.positions[id]);
  if (correctives) for (let target = 0; target < morphDeltas.length; target++) {
   p.x += morphDeltas[target][id * 3] * correctives.weights[frame][target];
   p.y += morphDeltas[target][id * 3 + 1] * correctives.weights[frame][target];
   p.z += morphDeltas[target][id * 3 + 2] * correctives.weights[frame][target];
  }
  expected.set(0, 0, 0);
  for (const [group, mass] of parsedWeights[id]) expected.addScaledVector(point.copy(p).applyMatrix4(trsMatrices[frame][group]), mass);
  actualMesh.getVertexPosition(vertex, point);
  codecError = Math.max(codecError, point.distanceTo(expected));
  if (frame === 0) bindError = Math.max(bindError, point.distanceTo(p));
  if (frame === motion.times.length - 1) loopError = Math.max(loopError, point.distanceTo(p));
  point.toArray(samples, (frame * source.count + id) * 3);
  expected.set(0, 0, 0);
  for (const [group, mass] of parsedWeights[id]) {
   expected.addScaledVector(referencePoint.copy(p).applyMatrix4(referenceMatrices[frame][group]), mass);
  }
  referenceError = Math.max(referenceError, point.distanceTo(expected));
 }
}
await writeOutput('runtime-linear-samples.bin', Buffer.from(samples.buffer));
const report = {status: 'exported_pending_actual_surface_contact_and_browser_review', bytes: bytes.length,
 sha256: hash(bytes), vertices: source.count, triangles: geometry.index.count / 3,
 bones: actualMesh.skeleton.bones.length, deformationGroups: motion.groups.length,
 runtimeWeightOverride: override ? {sha256: override.sha256, vertices: Object.keys(override.data.weights).length} : null,
 correctiveTargets: correctiveInput ? {sha256: correctiveInput.sha256, names: correctives.targets.map(target => target.name)} : null,
 animations: loaded.animations.map(item => ({name: item.name, duration: item.duration})),
 maximumTRSDecompositionComponentError: maxDecompositionComponentError,
 maximumGLBCodecSurfaceErrorMeters: codecError, maximumNativeDeltaApproximationSurfaceErrorMeters: referenceError,
 maximumBindSurfaceErrorMeters: bindError, maximumLoopSurfaceErrorMeters: loopError,
 samples: {file: 'runtime-linear-samples.bin', shape: [151, source.count, 3], dtype: 'little-endian-float32', space: 'BlenderZup mesh local'},
 standardGLB: true, customSkinningShaderRequired: false, vertexCacheInDelivery: false,
 textures: 0, promotion_map: {}};
await writeOutput('asset-build.json', JSON.stringify(report, null, 2) + '\n');
console.log(JSON.stringify(report));
if (codecError > 5e-6 || bindError > 5e-6 || loopError > 5e-6) throw Error('GLB skin/loop roundtrip failed');
