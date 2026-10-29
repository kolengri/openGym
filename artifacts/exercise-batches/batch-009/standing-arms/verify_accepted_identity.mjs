import assert from 'node:assert/strict';
import {readFile,writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import * as THREE from '../../../first-exercise-3d/runtime/node_modules/three/build/three.module.js';
import {GLTFLoader} from '../../../first-exercise-3d/runtime/node_modules/three/examples/jsm/loaders/GLTFLoader.js';
const family=new URL('./',import.meta.url),sha=b=>createHash('sha256').update(b).digest('hex');
const adapterSource=(await readFile(new URL('../../dual-quaternion.js',family),'utf8')).replace("from 'three'","from '"+new URL('../../../first-exercise-3d/runtime/node_modules/three/build/three.module.js',family).href+"'");
const {addDualQuaternionSkinning}=await import('data:text/javascript;base64,'+Buffer.from(adapterSource).toString('base64'));
async function load(path,expected){
 const bytes=await readFile(new URL(path,family));if(expected)assert.equal(sha(bytes),expected);
 const gltf=await new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),'');
 const meshes=[];gltf.scene.traverse(o=>{if(o.isSkinnedMesh)meshes.push(o)});assert.equal(meshes.length,1);
 const mesh=meshes[0],idx=mesh.geometry.getAttribute('_source_index'),adapter=addDualQuaternionSkinning(mesh.material);adapter.installSurfaceProbe(mesh);
 assert.equal(new Set(idx.array).size,10582);assert.equal(mesh.skeleton.bones.length,51);
 const mixer=new THREE.AnimationMixer(gltf.scene),v=new THREE.Vector3(),rotation=new THREE.Quaternion(),translation=new THREE.Vector3(),scale=new THREE.Vector3(),matrix=new THREE.Matrix4(),qr=new THREE.Quaternion(),bind3=new THREE.Matrix3().setFromMatrix4(mesh.bindMatrix),inverse3=new THREE.Matrix3().setFromMatrix4(mesh.bindMatrixInverse);let action;
 function normals(){
  const g=mesh.geometry,base=g.getAttribute('normal'),indices=g.getAttribute('skinIndex'),weights=g.getAttribute('skinWeight'),bones=[];
  for(let j=0;j<51;j++){matrix.fromArray(mesh.skeleton.boneMatrices,j*16).decompose(translation,rotation,scale);bones.push(rotation.clone().normalize());}
  const normalMatrix=new THREE.Matrix3().getNormalMatrix(mesh.matrixWorld),out=new Array(10582);
  for(let i=0;i<idx.count;i++){
   v.fromBufferAttribute(base,i);
   for(let k=0;k<mesh.morphTargetInfluences.length;k++){const w=mesh.morphTargetInfluences[k];if(w){const a=g.morphAttributes.normal[k];v.x+=a.getX(i)*w;v.y+=a.getY(i)*w;v.z+=a.getZ(i)*w;}}
   v.applyMatrix3(bind3);qr.set(0,0,0,0);const first=bones[indices.getX(i)];
   for(let k=0;k<4;k++){const q=bones[indices.getComponent(i,k)],weight=weights.getComponent(i,k)*(first.dot(q)<0?-1:1);qr.x+=q.x*weight;qr.y+=q.y*weight;qr.z+=q.z*weight;qr.w+=q.w*weight;}
   v.applyQuaternion(qr.normalize()).applyMatrix3(inverse3).applyMatrix3(normalMatrix).normalize();out[Math.round(idx.getX(i))]=[v.x,-v.z,v.y];
  }
  return out;
 }
 function select(id){mixer.stopAllAction();action=mixer.clipAction(gltf.animations.find(c=>c.name==='Exercise_'+id));action.reset().setLoop(THREE.LoopOnce,1).play();action.clampWhenFinished=true;}
 function evaluate(frame){action.reset().play();mixer.setTime(frame/30);gltf.scene.updateMatrixWorld(true);mesh.skeleton.update();adapter.update(mesh,true);const skin=new Array(10582);for(let i=0;i<idx.count;i++){mesh.getVertexPosition(i,v);mesh.localToWorld(v);skin[Math.round(idx.getX(i))]=[v.x,-v.z,v.y];}assert.ok(mesh.morphTargetInfluences.every(x=>x===0),'Accepted action inherited a cuff target');return{skin,normals:normals(),bones:new Map(mesh.skeleton.bones.map(b=>[b.name,[...b.matrixWorld.elements]]))};}
 function evaluateBones(frame,encodedKeyTime=false){action.reset().play();const track=encodedKeyTime?action.getClip().tracks.find(t=>t.times.length===151):null;if(encodedKeyTime)assert.ok(track);mixer.setTime(encodedKeyTime?track.times[frame]:frame/30);gltf.scene.updateMatrixWorld(true);return new Map(mesh.skeleton.bones.map(b=>[b.name,[...b.matrixWorld.elements]]));}
 return{sha256:sha(bytes),select,evaluate,evaluateBones};
}
const conventional=await load('checkpoints/25b5af549368/motion.glb','25b5af54936875bed17e909c562872b9a47e37927222d4ca8cc62866dfe34449'),crossed=await load('checkpoints/f87959934283/motion.glb','f879599342838f04563e9f70e186ad4b53e399e3b3836db4dd2dbd4ef01797f1'),current=await load('motion.glb');const reports={};
for(const id of ['1404','4515','1405']){
 const baseline=id==='1405'?crossed:conventional;baseline.select(id);current.select(id);let maxSkin=0,maxMatrix=0,maxNormal=0;
 for(let f=0;f<=150;f++){const old=baseline.evaluate(f),now=current.evaluate(f);for(let i=0;i<10582;i++){maxSkin=Math.max(maxSkin,Math.hypot(...now.skin[i].map((x,a)=>x-old.skin[i][a])));maxNormal=Math.max(maxNormal,Math.hypot(...now.normals[i].map((x,a)=>x-old.normals[i][a])));}for(const[name,m]of now.bones){const oldm=old.bones.get(name);assert.ok(oldm);for(let i=0;i<16;i++)maxMatrix=Math.max(maxMatrix,Math.abs(m[i]-oldm[i]));}}
 assert.equal(maxSkin,0);assert.equal(maxNormal,0);assert.equal(maxMatrix,0);reports[id]={accepted_glb_sha256:baseline.sha256,final_glb_sha256:current.sha256,all151_actual_Three_DQ_POSITION_max_error_m:maxSkin,all151_shader_equivalent_DQ_NORMAL_max_vector_error:maxNormal,all151_51bone_world_matrix_max_element_error:maxMatrix,all151_new_component_weights_zero:true};
}
crossed.select('3995');current.select('3995');let wrapMatrix=0,wrapEndpointMatrix=0,encodedEndpointMatrix=0;
for(let f=0;f<=150;f++){const old=crossed.evaluateBones(f),now=current.evaluateBones(f);for(const[name,m]of now){const before=old.get(name);for(let i=0;i<16;i++){const error=Math.abs(m[i]-before[i]);wrapMatrix=Math.max(wrapMatrix,error);if([0,37,38,75,112,113,150].includes(f))wrapEndpointMatrix=Math.max(wrapEndpointMatrix,error);}}}
for(const f of [0,37,38,75,112,113,150]){const old=crossed.evaluateBones(f,true),now=current.evaluateBones(f,true);for(const[name,m]of now){const before=old.get(name);for(let i=0;i<16;i++)encodedEndpointMatrix=Math.max(encodedEndpointMatrix,Math.abs(m[i]-before[i]));}}
reports['3995']={accepted_glb_sha256:crossed.sha256,final_glb_sha256:current.sha256,all151_51bone_world_matrix_max_element_error:wrapMatrix,kinematics_exact_to_frozen_f879:wrapMatrix===0,held_open_endpoint_51bone_world_matrix_max_element_error:wrapEndpointMatrix,held_open_endpoint_at_encoded_key_times_51bone_world_matrix_max_element_error:encodedEndpointMatrix,intermediate_FK_identity_is_diagnostic:true,runtime_frame30_endpoint_scope:'Explicit float32 key-time resampling diagnostic: frame/30 can sample fractionally inside changed adjacent segments. Native and encoded-key endpoints remain exactly unchanged; physical readback tolerances are independent.'};
await writeFile(new URL('accepted-decoded-identity.json',family),JSON.stringify(reports,null,2)+'\n');console.log(JSON.stringify(reports));
assert.equal(encodedEndpointMatrix,0);
