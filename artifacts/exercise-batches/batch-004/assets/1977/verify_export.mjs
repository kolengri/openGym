import assert from 'node:assert/strict';
import { readFile, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { gunzipSync } from 'node:zlib';
import * as THREE from '../../../../first-exercise-3d/runtime/node_modules/three/build/three.module.js';
import { GLTFLoader } from '../../../../first-exercise-3d/runtime/node_modules/three/examples/jsm/loaders/GLTFLoader.js';

const root = new URL('./', import.meta.url);
const bytes = await readFile(new URL('motion.glb', root));
const gltf = JSON.parse(bytes.subarray(20, 20 + bytes.readUInt32LE(12)).toString());
assert.equal(gltf.images?.length ?? 0, 0);
assert.equal(gltf.textures?.length ?? 0, 0);
assert.equal(gltf.materials.length, 1);
const source = await readFile(new URL('source.blend', root));
const hash = value => createHash('sha256').update(value).digest('hex');
const reference = JSON.parse(gunzipSync(await readFile(new URL('linear-vertex-reference.json.gz', root))));
const topology = JSON.parse(gunzipSync(await readFile(new URL('topology-reference.json.gz', root))));
assert.equal(topology.source_sha256, hash(source));
const joints = JSON.parse(await readFile(new URL('pose-samples.json', root)));
const surface = JSON.parse(await readFile(new URL('surface-contact-report.json', root)));
assert.equal(surface.source_sha256, hash(source));
const model = await new Promise((resolve, reject) => new GLTFLoader().parse(
  bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength), '', resolve, reject));
const meshes = [];
model.scene.traverse(object => { if (object.isSkinnedMesh) meshes.push(object); });
assert.equal(meshes.length, 1);
assert.equal(model.animations.length, 1);
const clip = model.animations[0];
assert.equal(clip.name, 'Exercise_1977');
assert.equal(clip.duration, 5);
const mesh = meshes[0];
const geometry = mesh.geometry;
const position = geometry.getAttribute('position');
const normal = geometry.getAttribute('normal');
const sourceIndex = geometry.getAttribute('_source_index');
const skinIndex = geometry.getAttribute('skinIndex');
const skinWeight = geometry.getAttribute('skinWeight');
assert.equal(mesh.skeleton.bones.length, 51);
assert.equal(Object.keys(geometry.morphAttributes).length, 0);
assert.ok(sourceIndex);
assert.equal(geometry.getAttribute('color'), undefined);
assert.equal(new Set(Array.from(sourceIndex.array)).size, 10582);
const canonicalTriangle = triangle => {
  const smallest = triangle.indexOf(Math.min(...triangle));
  return [...triangle.slice(smallest), ...triangle.slice(0, smallest)].join(',');
};
const sourceTriangles = topology.triangles.map(canonicalTriangle).sort();
const runtimeTriangles = [];
for (let index = 0; index < geometry.index.count; index += 3) runtimeTriangles.push(canonicalTriangle(
  [0, 1, 2].map(offset => Math.round(sourceIndex.getX(geometry.index.getX(index + offset))))));
assert.deepEqual(runtimeTriangles.sort(), sourceTriangles);
const mixer = new THREE.AnimationMixer(model.scene);
const action = mixer.clipAction(clip).setLoop(THREE.LoopOnce, 1);
action.clampWhenFinished = true;
action.play();
const convert = vector => new THREE.Vector3(vector[0], vector[2], -vector[1]);
const rows = [];
const loops = [];
let maximumWeightError = 0;
for (const ref of reference) {
  mixer.setTime(ref.frame / 30);
  model.scene.updateMatrixWorld(true);
  mesh.skeleton.update();
  const skinMatrices = mesh.skeleton.bones.map((_, index) => new THREE.Matrix4().fromArray(mesh.skeleton.boneMatrices, index * 16));
  const worldNormalMatrix = new THREE.Matrix3().getNormalMatrix(mesh.matrixWorld);
  let maxPosition = 0, sumPosition = 0, maxNormalAngle = 0, maxJoint = 0;
  let minimumNormalLength = Infinity;
  const evaluated = [];
  for (let index = 0; index < position.count; index++) {
    const original = Math.round(sourceIndex.getX(index));
    const actual = new THREE.Vector3().fromBufferAttribute(position, index);
    mesh.applyBoneTransform(index, actual);
    actual.applyMatrix4(mesh.matrixWorld);
    const error = actual.distanceTo(convert(ref.vertices[original]));
    maxPosition = Math.max(maxPosition, error);
    sumPosition += error;
    if (ref.frame === 0 || ref.frame === 150) evaluated.push(actual.toArray());
    const skinMatrix = new THREE.Matrix4();
    skinMatrix.elements.fill(0);
    let totalWeight = 0;
    for (let influence = 0; influence < 4; influence++) {
      const weight = skinWeight.array[index * 4 + influence];
      totalWeight += weight;
      const bone = skinIndex.array[index * 4 + influence];
      for (let component = 0; component < 16; component++) skinMatrix.elements[component] += weight * skinMatrices[bone].elements[component];
    }
    maximumWeightError = Math.max(maximumWeightError, Math.abs(totalWeight - 1));
    skinMatrix.premultiply(mesh.bindMatrixInverse).multiply(mesh.bindMatrix);
    const skinNormal = new THREE.Vector3().fromBufferAttribute(normal, index).applyMatrix3(new THREE.Matrix3().setFromMatrix4(skinMatrix));
    minimumNormalLength = Math.min(minimumNormalLength, skinNormal.length());
    skinNormal.applyMatrix3(worldNormalMatrix).normalize();
    const angle = skinNormal.angleTo(convert(ref.shader_normals[original]));
    assert.ok(Number.isFinite(angle));
    maxNormalAngle = Math.max(maxNormalAngle, angle);
  }
  const jointRef = joints.find(row => row.frame === ref.frame);
  assert.equal(Object.keys(jointRef.joints).length, 51);
  for (const [name, expected] of Object.entries(jointRef.joints)) {
    const node = model.scene.getObjectByName(name);
    assert.ok(node, name);
    maxJoint = Math.max(maxJoint, node.getWorldPosition(new THREE.Vector3()).distanceTo(convert(expected)));
  }
  if (evaluated.length) loops.push(evaluated);
  rows.push({ frame: ref.frame, max_skin_error_m: maxPosition, mean_skin_error_m: sumPosition / position.count,
    max_joint_error_m: maxJoint, max_shader_normal_angle_degrees: maxNormalAngle * 180 / Math.PI,
    minimum_unnormalized_shader_normal_length: minimumNormalLength });
}
let loopError = 0;
for (let i = 0; i < loops[0].length; i++) loopError = Math.max(loopError, new THREE.Vector3(...loops[0][i]).distanceTo(new THREE.Vector3(...loops[1][i])));
const maximumSkin = Math.max(...rows.map(row => row.max_skin_error_m));
const maximumJoint = Math.max(...rows.map(row => row.max_joint_error_m));
const maximumNormal = Math.max(...rows.map(row => row.max_shader_normal_angle_degrees));
const report = { ok: surface.ok && maximumSkin < .00001 && maximumJoint < .00001 && maximumNormal < .1 && loopError < .00001,
  source_sha256: hash(source), glb_sha256: hash(bytes), actual_action: clip.name, duration_seconds: clip.duration,
  source_vertices: 10582, exported_vertices: position.count, triangles: geometry.index.count / 3,
  bones: mesh.skeleton.bones.length, maximum_influences: 4, maximum_weight_normalization_error: maximumWeightError,
  morph_targets: 0, source_index_complete: true, oriented_source_triangles_preserved: true, textures: 0, materials: 1,
  max_skin_error_m: maximumSkin, max_joint_error_m: maximumJoint,
  max_shader_normal_angle_degrees: maximumNormal, loop_skin_error_m: loopError,
  method: 'Actual project Three.js GLTFLoader, AnimationMixer, Skeleton and applyBoneTransform. Source native positions and all 51 joints compared after Blender-to-runtime coordinate conversion. Normals evaluated with the exact Three.js skinnormal_vertex four-matrix equation and independently recorded native source normals transformed by source pose/bind matrices. No POSITION or NORMAL morphs exist.',
  contact_transfer: 'Complete original-index positions and unchanged triangles transfer the source-bound contact measurements to the actual Three.js linear runtime.',
  source_contact_ok: surface.ok, samples: rows };
await writeFile(new URL('export-parity-report.json', root), JSON.stringify(report, null, 2) + '\n');
console.log(JSON.stringify(report));
assert.ok(report.ok);
