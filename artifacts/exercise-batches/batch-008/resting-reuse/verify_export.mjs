/** Verify actual standalone6539 GLB with the unchanged project DQ adapter. */
import assert from 'node:assert/strict';
import {readFile,writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';
import * as THREE from '../../../first-exercise-3d/runtime/node_modules/three/build/three.module.js';
import {GLTFLoader} from '../../../first-exercise-3d/runtime/node_modules/three/examples/jsm/loaders/GLTFLoader.js';
const family=new URL('./',import.meta.url),root=new URL('../assets/6539/',family),json=async name=>JSON.parse(await readFile(new URL(name,root)));
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
const adapterBytes=await readFile(new URL('../../dual-quaternion.js',family));
const adapterSource=adapterBytes.toString().replace("from 'three'","from '"+new URL('../../../first-exercise-3d/runtime/node_modules/three/build/three.module.js',family).href+"'");
const {addDualQuaternionSkinning}=await import('data:text/javascript;base64,'+Buffer.from(adapterSource).toString('base64'));
const bytes=await readFile(new URL('motion.glb',root)),document=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)).toString());
assert.equal(document.images?.length??0,0);assert.equal(document.materials.length,1);
const model=await new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),'');
const meshes=[];model.scene.traverse(x=>{if(x.isSkinnedMesh)meshes.push(x)});assert.equal(meshes.length,1);assert.equal(model.animations.length,1);
const mesh=meshes[0],g=mesh.geometry,clip=model.animations[0],names=['RestingHipVolume'];assert.equal(clip.name,'Exercise_6539');assert.equal(clip.duration,5);assert.equal(mesh.skeleton.bones.length,51);
assert.deepEqual(Object.keys(mesh.morphTargetDictionary),names);assert.equal(g.morphAttributes.position.length,1);assert.equal(g.morphAttributes.normal.length,1);assert.ok(g.morphTargetsRelative);
assert.ok(document.meshes.every(m=>m.primitives.every(p=>p.targets.length===1&&p.targets.every(t=>t.POSITION!==undefined&&t.NORMAL!==undefined))));
const index=g.getAttribute('_source_index'),normal=g.getAttribute('normal'),skinIndex=g.getAttribute('skinIndex'),skinWeight=g.getAttribute('skinWeight');assert.equal(new Set(index.array).size,10582);
const sourceSha=sha(await readFile(new URL('source.blend',root))),pose=await json('pose-samples.json'),surface=await json('runtime-surface-reference.json'),morph=await json('source-morph-samples.json');
const dq=JSON.parse(gunzipSync(await readFile(new URL('dq-reference.json.gz',root)))),normals=JSON.parse(gunzipSync(await readFile(new URL('joint-normal-reference.json.gz',root)))),topology=JSON.parse(gunzipSync(await readFile(new URL('topology-reference.json.gz',root))));
for(const ref of [surface,morph,dq,normals,topology])assert.equal(ref.source_sha256,sourceSha);
const canonical=tri=>{const i=tri.indexOf(Math.min(...tri));return [...tri.slice(i),...tri.slice(0,i)].join(',')};
const actualTriangles=[];for(let i=0;i<g.index.count;i+=3)actualTriangles.push(canonical([0,1,2].map(j=>Math.round(index.getX(g.index.getX(i+j))))));assert.deepEqual(actualTriangles.sort(),topology.triangles.map(canonical).sort());
let baseN=0,targetN=0,weightError=0;
for(let i=0;i<index.count;i++){
 const id=Math.round(index.getX(i)),n=[normal.getX(i),-normal.getZ(i),normal.getY(i)],delta=g.morphAttributes.normal[0];baseN=Math.max(baseN,Math.hypot(...n.map((v,k)=>v-normals.basis[id][k])));
 const target=[n[0]+delta.getX(i),n[1]-delta.getZ(i),n[2]+delta.getY(i)];targetN=Math.max(targetN,Math.hypot(...target.map((v,k)=>v-normals.targets.RestingHipVolume[id][k])));weightError=Math.max(weightError,Math.abs([0,1,2,3].reduce((sum,k)=>sum+skinWeight.getComponent(i,k),0)-1));
}
assert.ok(baseN<.0002&&targetN<.0002&&weightError<2e-6);
const adapter=addDualQuaternionSkinning(mesh.material);adapter.installSurfaceProbe(mesh);
const mixer=new THREE.AnimationMixer(model.scene),action=mixer.clipAction(clip).setLoop(THREE.LoopOnce,1);action.clampWhenFinished=true;action.play();
const point=new THREE.Vector3(),q=new THREE.Quaternion(),scale=new THREE.Vector3(),offset=new THREE.Vector3(),matrix=new THREE.Matrix4(),direction=new THREE.Vector3();
let maximumPosition=0,maximumJoint=0,maximumPatch=0,maximumMorph=0,maximumNormal=0,minimumNormalLength=Infinity,first,last;const rows=[];
for(const row of pose){
 action.paused=false;mixer.setTime(row.frame/30);model.scene.updateMatrixWorld(true);mesh.skeleton.update();adapter.update(mesh,true);const actual=new Map();let positionError=0,jointError=0,patchError=0,normalError=0;
 const expected=dq.samples.find(x=>x.frame===row.frame),patches=surface.samples.find(x=>x.frame===row.frame),expectedMorph=morph.samples.find(x=>x.frame===row.frame);
 const real=mesh.skeleton.bones.map((_,j)=>{matrix.fromArray(mesh.skeleton.boneMatrices,j*16).decompose(offset,q,scale);assert.ok(Math.max(Math.abs(scale.x-1),Math.abs(scale.y-1),Math.abs(scale.z-1))<.0001);return q.clone().normalize()});
 const worldNormal=new THREE.Matrix3().getNormalMatrix(mesh.matrixWorld),bindNormal=new THREE.Matrix3().setFromMatrix4(mesh.bindMatrix),inverseBindNormal=new THREE.Matrix3().setFromMatrix4(mesh.bindMatrixInverse);
 for(let i=0;i<index.count;i++){
  const id=Math.round(index.getX(i));mesh.getVertexPosition(i,point);mesh.localToWorld(point);const p=[point.x,-point.z,point.y];if(actual.has(id))assert.ok(Math.hypot(...p.map((v,k)=>v-actual.get(id)[k]))<1e-5);else actual.set(id,p);
  if(expected){
   positionError=Math.max(positionError,Math.hypot(...p.map((v,k)=>v-expected.positions[id][k])));q.set(0,0,0,0);const reference=real[skinIndex.getX(i)];
   for(let k=0;k<4;k++){const qr=real[skinIndex.getComponent(i,k)],w=skinWeight.getComponent(i,k)*(reference.dot(qr)<0?-1:1);q.x+=qr.x*w;q.y+=qr.y*w;q.z+=qr.z*w;q.w+=qr.w*w;}q.normalize();direction.fromBufferAttribute(normal,i).addScaledVector(new THREE.Vector3().fromBufferAttribute(g.morphAttributes.normal[0],i),mesh.morphTargetInfluences[0]);minimumNormalLength=Math.min(minimumNormalLength,direction.length());direction.applyMatrix3(bindNormal).applyQuaternion(q).applyMatrix3(inverseBindNormal).applyMatrix3(worldNormal).normalize();const en=expected.shader_normals[id];normalError=Math.max(normalError,direction.angleTo(new THREE.Vector3(en[0],en[2],-en[1]))*180/Math.PI);
  }
 }
 for(const [name,p]of Object.entries(row.joints)){const bone=mesh.skeleton.bones.find(b=>b.name===name);bone.getWorldPosition(point);jointError=Math.max(jointError,Math.hypot(point.x-p[0],-point.z-p[1],point.y-p[2]));}
 for(const patch of Object.values(patches.patches))for(let i=0;i<patch.indices.length;i++)patchError=Math.max(patchError,Math.hypot(...actual.get(patch.indices[i]).map((v,k)=>v-patch.positions[i][k])));
 maximumPosition=Math.max(maximumPosition,positionError);maximumJoint=Math.max(maximumJoint,jointError);maximumPatch=Math.max(maximumPatch,patchError);maximumNormal=Math.max(maximumNormal,normalError);maximumMorph=Math.max(maximumMorph,Math.abs(mesh.morphTargetInfluences[0]-expectedMorph.weights.RestingHipVolume));
 if(row.frame===0)first=actual;if(row.frame===150)last=actual;rows.push({frame:row.frame,position_error_m:expected?positionError:null,joint_error_m:jointError,patch_error_m:patchError,shader_normal_error_degrees:expected?normalError:null,morph:mesh.morphTargetInfluences[0],minimum_body_z:Math.min(...[...actual.values()].map(p=>p[2]))});
}
let loop=0;for(const[id,p]of first)loop=Math.max(loop,Math.hypot(...p.map((v,k)=>v-last.get(id)[k])));
assert.ok(maximumPosition<1e-5&&maximumJoint<1e-5&&maximumPatch<1e-5&&maximumMorph<1e-5&&maximumNormal<.1&&loop<1e-5);
const report={ok:true,source_sha256:sourceSha,glb_sha256:sha(bytes),runtime_adapter_sha256:sha(adapterBytes),action:clip.name,duration_seconds:5,source_vertices:10582,exported_vertices:index.count,triangles:g.index.count/3,bones:51,maximum_influences:4,maximum_weight_error:weightError,original_oriented_triangles_exact:true,POSITION_targets:names,NORMAL_targets:names,maximum_basis_normal_vector_error:baseN,maximum_target_normal_vector_error:targetN,maximum_full_DQ_position_error_m:maximumPosition,maximum_joint_error_m:maximumJoint,maximum_patch_error_m:maximumPatch,maximum_morph_weight_error:maximumMorph,maximum_shader_normal_error_degrees:maximumNormal,minimum_unnormalized_shader_normal_length:minimumNormalLength,loop_skin_error_m:loop,scope:'Actual GLTFLoader/AnimationMixer and exact unchanged shared DQ CPU/GPU transport contract, five complete native original-ID DQ skins and independently calculated source/key normals, all51 joint witnesses. No generic LBS appearance claim. Actual GPU raster review is primary-owned.',samples:rows};
await writeFile(new URL('export-verification.json',root),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify({...report,samples:rows.length}));
