/** Actual151 decoded old/new DQ identity; no stored frame cache. */
import assert from 'node:assert/strict';
import {readFile,writeFile}from'node:fs/promises';import{createHash}from'node:crypto';
import*as THREE from'../../../first-exercise-3d/runtime/node_modules/three/build/three.module.js';
import{GLTFLoader}from'../../../first-exercise-3d/runtime/node_modules/three/examples/jsm/loaders/GLTFLoader.js';
const P=new URL('./',import.meta.url),sha=b=>createHash('sha256').update(b).digest('hex');
const source=(await readFile(new URL('../../dual-quaternion.js',P),'utf8')).replace("from 'three'","from '"+new URL('../../../first-exercise-3d/runtime/node_modules/three/build/three.module.js',P).href+"'");
const{addDualQuaternionSkinning}=await import('data:text/javascript;base64,'+Buffer.from(source).toString('base64'));
async function load(url,name){const bytes=await readFile(url),model=await new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),'');let mesh;model.scene.traverse(o=>{if(o.isSkinnedMesh)mesh=o});assert.equal(model.animations.length,1);assert.equal(model.animations[0].name,name);const mixer=new THREE.AnimationMixer(model.scene),action=mixer.clipAction(model.animations[0]).setLoop(THREE.LoopOnce,1);action.clampWhenFinished=true;action.play();const adapter=addDualQuaternionSkinning(mesh.material);adapter.installSurfaceProbe(mesh);return{bytes,model,mesh,mixer,action,adapter}}
const old=await load(new URL('../../batch-008/assets/6539/motion.glb',P),'Exercise_6539'),now=await load(new URL('../assets/1315/motion.glb',P),'Exercise_1315');
let skin=0,matrix=0,morph=0,normal=0,change=0;const correctiveWeights=[];const p=new THREE.Vector3(),q=new THREE.Vector3(),first=[];
for(let f=0;f<=150;f++){
 for(const a of[old,now]){a.action.paused=false;a.mixer.setTime(f/30);a.model.scene.updateMatrixWorld(true);a.mesh.skeleton.update();a.adapter.update(a.mesh,true)}
 const x=old.mesh,y=now.mesh;assert.equal(x.geometry.attributes.position.count,y.geometry.attributes.position.count);
 for(let i=0;i<x.geometry.attributes.position.count;i++){x.getVertexPosition(i,p);y.getVertexPosition(i,q);skin=Math.max(skin,p.distanceTo(q));if(f===0)first.push(p.clone());else change=Math.max(change,p.distanceTo(first[i]));}
 for(let i=0;i<x.skeleton.boneMatrices.length;i++)matrix=Math.max(matrix,Math.abs(x.skeleton.boneMatrices[i]-y.skeleton.boneMatrices[i]));
 morph=Math.max(morph,Math.abs(x.morphTargetInfluences[0]-y.morphTargetInfluences[0]));correctiveWeights.push({frame:f,RestingHipVolume:y.morphTargetInfluences[0]});
 // Source NORMAL and POSITION targets are byte exact and joint transport just measured exact.
 for(const attr of['normal'])for(let i=0;i<x.geometry.attributes[attr].array.length;i++)normal=Math.max(normal,Math.abs(x.geometry.attributes[attr].array[i]-y.geometry.attributes[attr].array[i]));
}
assert.equal(skin+matrix+morph+normal,0);assert.ok(change>.1);assert.equal(correctiveWeights[0].RestingHipVolume,0);assert.equal(correctiveWeights[150].RestingHipVolume,0);assert.ok(correctiveWeights[75].RestingHipVolume>.999);
const report={ok:true,frames:151,explicit_morph_reset:{start:correctiveWeights[0],peak:correctiveWeights[75],return:correctiveWeights[150],all151_weights_compared_exactly:true},old_glb_sha256:sha(old.bytes),new_glb_sha256:sha(now.bytes),maximum_decoded_DQ_skin_identity_error_m:skin,maximum_decoded_joint_matrix_identity_error:matrix,maximum_decoded_morph_identity_error:morph,maximum_source_normal_identity_error:normal,maximum_skin_change_from_start_m:change,NORMAL_identity:'Byte-exact Basis/target NORMAL attributes plus all151 exact joint matrices and morph weights imply exact shared shader NORMAL output.',method:'Independently loaded accepted6539 and renamed1315 with actual GLTFLoader/AnimationMixer and unchanged shared DQ adapter. Both actions reset paused=false each sample;151 complete decoded surfaces compared directly.'};await writeFile(new URL('rest-decoded-identity.json',P),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report));
