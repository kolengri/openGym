import {Matrix4, Mesh, Quaternion, Vector3} from 'three';

// Rigid dual-quaternion blending, Kavan et al.2008:
// https://users.cs.utah.edu/~ladislav/dq/index.html
// Optional renderer behavior; GLB itself continues to contain standard skin data.
const limit = 64;
const declarations = `
#ifdef USE_SKINNING
uniform bool dqEnabled;
uniform vec4 dqReal[64];
uniform vec4 dqDual[64];
vec3 dqRotate(vec4 q, vec3 v) {
 return v + 2.0 * cross(q.xyz, cross(q.xyz, v) + q.w * v);
}
void dqBlend(out vec4 real, out vec4 dual) {
 ivec4 indices = ivec4(skinIndex);
 vec4 reference = dqReal[indices.x];
 real = vec4(0.0); dual = vec4(0.0);
 for (int i = 0; i < 4; i++) {
  float weight = skinWeight[i] * (dot(reference, dqReal[indices[i]]) < 0.0 ? -1.0 : 1.0);
  real += dqReal[indices[i]] * weight;
  dual += dqDual[indices[i]] * weight;
 }
 float magnitude = max(length(real), 0.000001);
 real /= magnitude; dual /= magnitude;
}
#endif`;

export function addDualQuaternionSkinning(material) {
 const uniforms = {dqEnabled: {value: false}, dqReal: {value: new Float32Array(limit * 4)}, dqDual: {value: new Float32Array(limit * 4)}};
 const compile = material.onBeforeCompile, key = material.customProgramCacheKey.bind(material);
 material.onBeforeCompile = (shader, renderer) => {
  compile.call(material, shader, renderer); Object.assign(shader.uniforms, uniforms);
  shader.vertexShader = shader.vertexShader.replace('#include <common>', '#include <common>\n' + declarations)
   .replace('#include <skinnormal_vertex>', `
   #ifdef USE_SKINNING
   if (dqEnabled) {
    vec4 real, dual; dqBlend(real, dual);
    objectNormal = (bindMatrixInverse * vec4(dqRotate(real, (bindMatrix * vec4(objectNormal, 0.0)).xyz), 0.0)).xyz;
    #ifdef USE_TANGENT
    objectTangent = (bindMatrixInverse * vec4(dqRotate(real, (bindMatrix * vec4(objectTangent, 0.0)).xyz), 0.0)).xyz;
    #endif
   } else {
    #include <skinnormal_vertex>
   }
   #endif`)
   .replace('#include <skinning_vertex>', `
   #ifdef USE_SKINNING
   if (dqEnabled) {
    vec4 real, dual; dqBlend(real, dual);
    vec3 translation = 2.0 * (real.w * dual.xyz - dual.w * real.xyz + cross(real.xyz, dual.xyz));
    vec3 point = (bindMatrix * vec4(transformed, 1.0)).xyz;
    transformed = (bindMatrixInverse * vec4(dqRotate(real, point) + translation, 1.0)).xyz;
   } else {
    #include <skinning_vertex>
   }
   #endif`);
 };
 material.customProgramCacheKey = () => key() + '-optional-rigid-dq-v1';
 const matrix = new Matrix4(), position = new Vector3(), scale = new Vector3(), real = new Quaternion(), dual = new Quaternion();
 function update(mesh, enabled) {
  uniforms.dqEnabled.value = enabled;
  if (!enabled) return;
  if (mesh.skeleton.bones.length > limit) throw Error('DQ bone budget exceeded');
  mesh.skeleton.update();
  for (let index = 0; index < mesh.skeleton.bones.length; index++) {
   matrix.fromArray(mesh.skeleton.boneMatrices, index * 16).decompose(position, real, scale);
   if (Math.max(Math.abs(scale.x - 1), Math.abs(scale.y - 1), Math.abs(scale.z - 1)) > .0001)
    throw Error('Rigid DQ skinning requires unit bone scale');
   real.normalize(); dual.set(position.x, position.y, position.z, 0).multiply(real);
   uniforms.dqReal.value.set(real.toArray(), index * 4);
   uniforms.dqDual.value.set(dual.toArray().map(value => value * .5), index * 4);
  }
 }
 function installSurfaceProbe(mesh) {
  const linear = mesh.getVertexPosition;
  const qr = new Quaternion(), qd = new Quaternion(), offset = new Vector3();
  mesh.getVertexPosition = function(index, target) {
   if (!uniforms.dqEnabled.value) return linear.call(this, index, target);
   Mesh.prototype.getVertexPosition.call(this, index, target); target.applyMatrix4(this.bindMatrix);
   const indices = this.geometry.getAttribute('skinIndex'), weights = this.geometry.getAttribute('skinWeight');
   const first = indices.getX(index) * 4, r = uniforms.dqReal.value, d = uniforms.dqDual.value;
   qr.set(0, 0, 0, 0); qd.set(0, 0, 0, 0);
   for (let slot = 0; slot < 4; slot++) {
    const bone = indices.getComponent(index, slot) * 4;
    const sign = r[first] * r[bone] + r[first + 1] * r[bone + 1] + r[first + 2] * r[bone + 2] + r[first + 3] * r[bone + 3] < 0 ? -1 : 1;
    const weight = weights.getComponent(index, slot) * sign;
    qr.x += r[bone] * weight; qr.y += r[bone + 1] * weight; qr.z += r[bone + 2] * weight; qr.w += r[bone + 3] * weight;
    qd.x += d[bone] * weight; qd.y += d[bone + 1] * weight; qd.z += d[bone + 2] * weight; qd.w += d[bone + 3] * weight;
   }
   const inverse = 1 / Math.max(qr.length(), .000001);
   qr.set(qr.x * inverse, qr.y * inverse, qr.z * inverse, qr.w * inverse);
   qd.set(qd.x * inverse, qd.y * inverse, qd.z * inverse, qd.w * inverse);
   offset.set(
    2 * (qr.w * qd.x - qd.w * qr.x + qr.y * qd.z - qr.z * qd.y),
    2 * (qr.w * qd.y - qd.w * qr.y + qr.z * qd.x - qr.x * qd.z),
    2 * (qr.w * qd.z - qd.w * qr.z + qr.x * qd.y - qr.y * qd.x));
   return target.applyQuaternion(qr).add(offset).applyMatrix4(this.bindMatrixInverse);
  };
 }
 return {update, installSurfaceProbe};
}
