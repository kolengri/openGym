// Actual GLTFLoader plus the unchanged shared CPU DQ adapter; no browser/GPU claim.
import assert from 'node:assert/strict';
import {readFile,writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';
import * as THREE from '../../../first-exercise-3d/runtime/node_modules/three/build/three.module.js';
import {GLTFLoader} from '../../../first-exercise-3d/runtime/node_modules/three/examples/jsm/loaders/GLTFLoader.js';
const root=new URL('./',import.meta.url),threeURL=new URL('../../../first-exercise-3d/runtime/node_modules/three/build/three.module.js',root);
const adapterSource=(await readFile(new URL('../../../exercise-batches/dual-quaternion.js',root),'utf8')).replace("from 'three'","from '"+threeURL.href+"'");
const {addDualQuaternionSkinning}=await import('data:text/javascript;base64,'+Buffer.from(adapterSource).toString('base64'));
const bytes=await readFile(new URL('motion.glb',root)),gltf=await new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),'');
const meshes=[];gltf.scene.traverse(o=>{if(o.isSkinnedMesh)meshes.push(o);});assert.equal(meshes.length,1);const mesh=meshes[0];assert.equal(mesh.skeleton.bones.length,51);
const adapter=addDualQuaternionSkinning(mesh.material);adapter.installSurfaceProbe(mesh);const ids=mesh.geometry.getAttribute('_source_index');assert.ok(ids);assert.equal(new Set(ids.array).size,10582);
assert.equal(mesh.geometry.morphAttributes.position.length,4);assert.equal(mesh.geometry.morphAttributes.normal.length,4);
const reference=JSON.parse(gunzipSync(await readFile(new URL('ninety-dq-reference.json.gz',root)))),joints=JSON.parse(await readFile(new URL('ninety-pose-samples.json',root))),sourceSha=createHash('sha256').update(await readFile(new URL('source.blend',root))).digest('hex');assert.equal(reference.source_sha256,sourceSha);
const mixer=new THREE.AnimationMixer(gltf.scene),vector=new THREE.Vector3();let maximumSkinError=0,maximumJointError=0,maximumMorphError=0;const rows=[];
for(const clip of gltf.animations){
 mixer.stopAllAction();const action=mixer.clipAction(clip);action.reset();action.setLoop(THREE.LoopOnce,1);action.clampWhenFinished=true;action.play();const identifier=clip.name.replace('Exercise_','');
 for(const witness of reference.samples.filter(s=>s.id===identifier)){
  mixer.setTime(witness.frame/30);gltf.scene.updateMatrixWorld(true);mesh.skeleton.update();adapter.update(mesh,true);const points=new Map();let duplicateError=0;
  for(let i=0;i<ids.count;i++){mesh.getVertexPosition(i,vector);mesh.localToWorld(vector);const p=[vector.x,-vector.z,vector.y],id=Math.round(ids.getX(i));if(points.has(id))duplicateError=Math.max(duplicateError,Math.hypot(...p.map((v,k)=>v-points.get(id)[k])));else points.set(id,p);}
  assert.ok(duplicateError<1e-5);let skinError=0,jointError=0,morphError=0;
  for(let id=0;id<10582;id++)skinError=Math.max(skinError,Math.hypot(...points.get(id).map((v,k)=>v-witness.positions[id][k])));
  for(const [name,p] of Object.entries(joints.find(s=>s.id===identifier&&s.frame===witness.frame).joints)){const bone=mesh.skeleton.bones.find(b=>b.name===name);assert.ok(bone);bone.getWorldPosition(vector);jointError=Math.max(jointError,Math.hypot(vector.x-p[0],-vector.z-p[1],vector.y-p[2]));}
  for(const [name,value] of Object.entries(witness.morph_weights))morphError=Math.max(morphError,Math.abs(mesh.morphTargetInfluences[mesh.morphTargetDictionary[name]]-value));
  maximumSkinError=Math.max(maximumSkinError,skinError);maximumJointError=Math.max(maximumJointError,jointError);maximumMorphError=Math.max(maximumMorphError,morphError);rows.push({id:identifier,frame:witness.frame,skin_error_max_m:skinError,joint_error_max_m:jointError,morph_error_max:morphError});
 }
}
assert.ok(maximumSkinError<.0001,maximumSkinError);assert.ok(maximumJointError<.0001,maximumJointError);assert.ok(maximumMorphError<1e-5,maximumMorphError);
const result={ok:true,scope:'Actual Three.js GLTFLoader and unchanged shared optional CPU DQ adapter, all12010 UV-split vertices compared to10582 source IDs across22 source-bound poses. GPU appearance remains primary-owned.',source_sha256:sourceSha,glb_sha256:createHash('sha256').update(bytes).digest('hex'),samples:rows.length,maximum_skin_error_m:maximumSkinError,maximum_joint_error_m:maximumJointError,maximum_morph_weight_error:maximumMorphError,rows,actual_gpu_visual_acceptance:false};await writeFile(new URL('three-parity.json',root),JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result,null,2));
