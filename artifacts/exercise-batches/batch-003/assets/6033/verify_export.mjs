import assert from 'node:assert/strict';
import {readFile,writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';
import * as THREE from '../../../../first-exercise-3d/runtime/node_modules/three/build/three.module.js';
import {GLTFLoader} from '../../../../first-exercise-3d/runtime/node_modules/three/examples/jsm/loaders/GLTFLoader.js';
const root=new URL('./',import.meta.url);
// Reuse the exact shared adapter, changing only Node's dependency resolution.
const modulePath=new URL('../../../dual-quaternion.js',root);
const dqSource=(await readFile(modulePath,'utf8')).replace("from 'three'","from '"+new URL('../../../../first-exercise-3d/runtime/node_modules/three/build/three.module.js',root).href+"'");
const {addDualQuaternionSkinning}=await import('data:text/javascript;base64,'+Buffer.from(dqSource).toString('base64'));
const bytes=await readFile(new URL('motion.glb',root));
const hash=createHash('sha256').update(bytes).digest('hex');
const buffer=bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength);
const gltf=await new GLTFLoader().parseAsync(buffer,'');
const meshes=[];gltf.scene.traverse(o=>{if(o.isSkinnedMesh)meshes.push(o);});
assert.equal(meshes.length,1);const mesh=meshes[0];const expected=JSON.parse(await readFile(new URL('build-report.json',root)));assert.equal(mesh.skeleton.bones.length,expected.bones);assert.equal(expected.skinning,'dualQuaternion');const adapter=addDualQuaternionSkinning(mesh.material);adapter.installSurfaceProbe(mesh);
assert.equal(gltf.animations.length,1);const clip=gltf.animations[0];assert.equal(clip.name,'Exercise_6033');assert.ok(Math.abs(clip.duration-5)<1e-6);
const primitive=mesh.geometry;assert.equal(primitive.morphAttributes.position?.length,1);assert.equal(primitive.morphAttributes.normal?.length,1);assert.equal(primitive.morphTargetsRelative,true);
assert.ok(gltf.parser.json.meshes.every(m=>m.primitives.every(p=>p.targets?.length===1&&p.targets[0].POSITION!==undefined&&p.targets[0].NORMAL!==undefined)),'POSITION/NORMAL knee target missing');const indices=primitive.getAttribute('_source_index');assert.ok(indices);assert.equal(new Set(Array.from(indices.array)).size,10582);
const source=JSON.parse(await readFile(new URL('pose-samples.json',root)));
const surface=JSON.parse(await readFile(new URL('runtime-surface-reference.json',root)));
const dqReference=JSON.parse(gunzipSync(await readFile(new URL('dq-reference.json.gz',root))));
const sha=createHash('sha256').update(await readFile(new URL('source.blend',root))).digest('hex');assert.equal(surface.source_sha256,sha);assert.equal(dqReference.source_sha256,sha);
// Compare actual GLTFLoader NORMAL values to the source key's independently
// calculated rest normals. The shared shader applies the same unit DQ rotation
// after the normal morph, so it preserves this vector-error bound.
const normalReference=JSON.parse(gunzipSync(await readFile(new URL('knee-normal-reference.json.gz',root))));
assert.equal(normalReference.source_sha256,sha);
const baseNormal=primitive.getAttribute('normal'),normalDelta=primitive.morphAttributes.normal[0];
let maxBasisNormalError=0,maxTargetNormalError=0,maxNormalDelta=0;
for(let i=0;i<indices.count;i++){
 const id=Math.round(indices.getX(i));
 const base=[baseNormal.getX(i),-baseNormal.getZ(i),baseNormal.getY(i)];
 const target=[baseNormal.getX(i)+normalDelta.getX(i),-baseNormal.getZ(i)-normalDelta.getZ(i),baseNormal.getY(i)+normalDelta.getY(i)];
 maxBasisNormalError=Math.max(maxBasisNormalError,Math.hypot(...base.map((v,k)=>v-normalReference.basis[id][k])));
 maxTargetNormalError=Math.max(maxTargetNormalError,Math.hypot(...target.map((v,k)=>v-normalReference.target[id][k])));
 maxNormalDelta=Math.max(maxNormalDelta,Math.hypot(normalDelta.getX(i),normalDelta.getY(i),normalDelta.getZ(i)));
}
assert.ok(maxBasisNormalError<.0002&&maxTargetNormalError<.0002,'Export normals do not match original Basis/corrective normals');
assert.ok(maxNormalDelta>0,'Normal corrective must be nonzero');
const mixer=new THREE.AnimationMixer(gltf.scene);const action=mixer.clipAction(clip);action.setLoop(THREE.LoopOnce,1);action.clampWhenFinished=true;action.play();
const vector=new THREE.Vector3();let maxJointError=0,maxSkinError=0,maxFullDqError=0;const sampled=[];const morphSamples=[];let first=null,last=null;
function pose(time){mixer.setTime(time);gltf.scene.updateMatrixWorld(true);mesh.skeleton.update();adapter.update(mesh,true);}
function geometry(){const results=new Map();for(let i=0;i<indices.count;i++){mesh.getVertexPosition(i,vector);mesh.localToWorld(vector);const p=[vector.x,-vector.z,vector.y];const id=Math.round(indices.getX(i));if(results.has(id)){assert.ok(Math.hypot(...p.map((v,k)=>v-results.get(id)[k]))<1e-5);}else results.set(id,p);}return results;}
for(const row of source){pose(row.frame/30);const skin=geometry();const morph=mesh.morphTargetInfluences[0];morphSamples.push({frame:row.frame,weight:morph});if(row.frame===0||row.frame===150)assert.ok(Math.abs(morph)<1e-7,'Knee key must be zero at entry/return');if(row.frame===75)assert.ok(Math.abs(morph-1)<1e-6,'Knee key must reach accepted target at peak');const full=dqReference.samples.find(s=>s.frame===row.frame);if(full){assert.equal(full.positions.length,10582);for(let i=0;i<10582;i++)maxFullDqError=Math.max(maxFullDqError,Math.hypot(...skin.get(i).map((v,k)=>v-full.positions[i][k])));assert.ok(maxFullDqError<=.0001,'DQ parity exceeds0.1mm');}let error=0;for(const [name,p] of Object.entries(row.joints)){const bone=mesh.skeleton.bones.find(b=>b.name===name);assert.ok(bone,name);bone.getWorldPosition(vector);error=Math.max(error,Math.hypot(vector.x-p[0],-vector.z-p[1],vector.y-p[2]));}maxJointError=Math.max(error,maxJointError);const expected=surface.samples.find(s=>s.frame===row.frame);let skinError=0;const patches={};
for(const [name,patch] of Object.entries(expected.patches)){const points=patch.indices.map(id=>skin.get(id));for(let i=0;i<points.length;i++)skinError=Math.max(skinError,Math.hypot(...points[i].map((v,k)=>v-patch.positions[i][k])));const z=points.map(p=>p[2]);patches[name]={min_z:Math.min(...z),max_z:Math.max(...z),fraction_near_floor:z.filter(v=>Math.abs(v)<=.012).length/z.length};if(patch.state==='supported'){assert.ok(patches[name].min_z<=.012,name+' support gap');assert.ok(patches[name].fraction_near_floor>=.2,name+' support fraction');}if(patch.state==='lifted')assert.ok(patches[name].min_z>=.05,name+' foot clearance');}
maxSkinError=Math.max(maxSkinError,skinError);const floor=Math.min(...Array.from(skin.values(),p=>p[2]));assert.ok(floor>=-.004,'floor penetration');sampled.push({frame:row.frame,joint_error_m:error,surface_error_m:skinError,floor_min_z:floor,patches});if(row.frame===0)first=skin;if(row.frame===150)last=skin;
}
let loop=0;for(const [id,p]of first)loop=Math.max(loop,Math.hypot(...p.map((v,i)=>v-last.get(id)[i])));
assert.ok(maxJointError<.0001);assert.ok(maxSkinError<.0001);assert.ok(loop<.0001);
const report={ok:true,scope:'Actual standard GLB parsed with Three.js GLTFLoader and exact shared optional CPU DQ adapter; full original-ID comparison against Blender PreserveVolume DQcage. GPU/browser appearance remains primary-owned; no LBS quality claim.',sha256:hash,bytes:bytes.byteLength,animations:[clip.name],duration_seconds:clip.duration,bones:mesh.skeleton.bones.length,original_vertex_ids:new Set(Array.from(indices.array)).size,triangles:primitive.index.count/3,maximum_full_dq_vertex_error_m:maxFullDqError,maximum_joint_error_m:maxJointError,maximum_surface_error_m:maxSkinError,loop_skin_error_m:loop,morph_position_targets:1,morph_normal_targets:1,maximum_basis_normal_vector_error:maxBasisNormalError,maximum_target_normal_vector_error:maxTargetNormalError,normal_comparison_scope:'GLTFLoader Basis and full key normals compared in original rest space at every exported UV-split vertex. Shared GPU shader morphs normals before unit DQ rotation, which preserves the vector-error bound. GPU raster appearance remains primary-owned.',morph_samples:morphSamples,samples:sampled};
await writeFile(new URL('export-verification.json',root),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify({ok:true,sha256:hash,maximum_full_dq_vertex_error_m:maxFullDqError,maximum_joint_error_m:maxJointError,maximum_surface_error_m:maxSkinError,loop_skin_error_m:loop}));
