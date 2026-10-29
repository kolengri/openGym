import assert from 'node:assert/strict';
import {readFile,writeFile,mkdtemp} from 'node:fs/promises';
import {tmpdir} from 'node:os';import {join} from 'node:path';
import {createHash} from 'node:crypto';import {gunzipSync} from 'node:zlib';
import * as THREE from '../../../first-exercise-3d/runtime/node_modules/three/build/three.module.js';
import {GLTFLoader} from '../../../first-exercise-3d/runtime/node_modules/three/examples/jsm/loaders/GLTFLoader.js';
const id=process.argv[2],ids=['3220','3672','6097'];assert.ok(ids.includes(id));
const root=new URL('../assets/'+id+'/',import.meta.url),json=async name=>JSON.parse(await readFile(new URL(name,root)));
const sha=b=>createHash('sha256').update(b).digest('hex');
const adapterSource=(await readFile(new URL('../../dual-quaternion.js',import.meta.url),'utf8')).replace("from 'three'","from '"+new URL('../../../first-exercise-3d/runtime/node_modules/three/build/three.module.js',import.meta.url).href+"'");
const {addDualQuaternionSkinning}=await import('data:text/javascript;base64,'+Buffer.from(adapterSource).toString('base64'));
const bytes=await readFile(new URL('motion.glb',root));const gltf=await new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),'');
const meshes=[];gltf.scene.traverse(o=>{if(o.isSkinnedMesh)meshes.push(o)});assert.equal(meshes.length,1);
const mesh=meshes[0],g=mesh.geometry;assert.equal(mesh.skeleton.bones.length,51);assert.deepEqual(gltf.animations.map(c=>c.name).sort(),ids.map(i=>'Exercise_'+i));
assert.equal((g.morphAttributes.position??[]).length,0);assert.equal((g.morphAttributes.normal??[]).length,0);
const clip=gltf.animations.find(c=>c.name==='Exercise_'+id);assert.ok(Math.abs(clip.duration-5)<1e-6);
const idx=g.getAttribute('_source_index');assert.equal(new Set(idx.array).size,10582);
const sourceSha=sha(await readFile(new URL('source.blend',root))),pose=await json('pose-samples.json'),surface=await json('runtime-surface-reference.json'),landmarks=await json('surface-landmarks.json');
const dq=JSON.parse(gunzipSync(await readFile(new URL('dq-reference.json.gz',root)))),normals=JSON.parse(gunzipSync(await readFile(new URL('normal-reference.json.gz',root))));
assert.equal(normals.samples.length,5);
for(const ref of [surface,landmarks,dq,normals])assert.equal(ref.source_sha256,sourceSha);
let maxNormal=0,maxPartition=0,maxInfluences=0;const normal=g.getAttribute('normal'),weights=g.getAttribute('skinWeight'),indices=g.getAttribute('skinIndex');
for(let v=0;v<idx.count;v++){
 const i=Math.round(idx.getX(v)),n=[normal.getX(v),-normal.getZ(v),normal.getY(v)];maxNormal=Math.max(maxNormal,Math.hypot(...n.map((x,a)=>x-normals.basis[i][a])));
 const w=[weights.getX(v),weights.getY(v),weights.getZ(v),weights.getW(v)];maxPartition=Math.max(maxPartition,Math.abs(w.reduce((a,b)=>a+b,0)-1));maxInfluences=Math.max(maxInfluences,w.filter(x=>x>0).length);
}
assert.ok(maxNormal<.0002&&maxPartition<2e-6&&maxInfluences<=4);
const adapter=addDualQuaternionSkinning(mesh.material);adapter.installSurfaceProbe(mesh);
const mixer=new THREE.AnimationMixer(gltf.scene),action=mixer.clipAction(clip);action.setLoop(THREE.LoopOnce,1);action.clampWhenFinished=true;action.play();const v=new THREE.Vector3();
function evaluate(frame){
 action.reset().play();mixer.setTime(frame/30);gltf.scene.updateMatrixWorld(true);mesh.skeleton.update();adapter.update(mesh,true);
 const skin=new Array(10582);
 for(let k=0;k<idx.count;k++){
  mesh.getVertexPosition(k,v);mesh.localToWorld(v);const p=[v.x,-v.z,v.y],i=Math.round(idx.getX(k));
  if(skin[i])assert.ok(Math.hypot(...p.map((x,a)=>x-skin[i][a]))<1e-5,'UV split seam');else skin[i]=p;
 }
 return skin;
}
let maxFull=0,maxJoint=0,maxSurface=0,minFloor=Infinity,minArea=Infinity,maxShaderNormal=0;const samples=[],decoded=new Float32Array(151*10582*3);let first,last;
const q=new THREE.Quaternion(),qr=new THREE.Quaternion(),m=new THREE.Matrix4(),trans=new THREE.Vector3(),scale=new THREE.Vector3();
function verifyShaderNormals(reference){
 const quaternions=[];
 for(let b=0;b<51;b++){m.fromArray(mesh.skeleton.boneMatrices,b*16);m.decompose(trans,q,scale);assert.ok(Math.max(Math.abs(scale.x-1),Math.abs(scale.y-1),Math.abs(scale.z-1))<.0001);quaternions.push(q.clone().normalize());}
 const bindNormal=new THREE.Matrix3().setFromMatrix4(mesh.bindMatrix),inverseBindNormal=new THREE.Matrix3().setFromMatrix4(mesh.bindMatrixInverse),worldNormal=new THREE.Matrix3().getNormalMatrix(mesh.matrixWorld);
 for(let k=0;k<idx.count;k++){
  const i=Math.round(idx.getX(k)),firstq=quaternions[indices.getX(k)];qr.set(0,0,0,0);
  for(let slot=0;slot<4;slot++){
   const b=quaternions[indices.getComponent(k,slot)],w=weights.getComponent(k,slot)*(firstq.dot(b)<0?-1:1);qr.x+=b.x*w;qr.y+=b.y*w;qr.z+=b.z*w;qr.w+=b.w*w;
  }
  qr.normalize();v.fromBufferAttribute(normal,k).applyMatrix3(bindNormal).applyQuaternion(qr).applyMatrix3(inverseBindNormal).applyMatrix3(worldNormal).normalize();
  const expected=reference.normals[i],actual=[v.x,-v.z,v.y];maxShaderNormal=Math.max(maxShaderNormal,Math.hypot(...actual.map((x,a)=>x-expected[a])));
 }
}
for(let frame=0;frame<=150;frame++){
 const skin=evaluate(frame);if(frame===0)first=skin;if(frame===150)last=skin;
 const floor=Math.min(...skin.map(p=>p[2]));minFloor=Math.min(minFloor,floor);assert.ok(floor>=-.00035,'decoded floor');
 for(let i=0;i<10582;i++)decoded.set(skin[i],(frame*10582+i)*3);
 let area=Infinity;
 for(const [a,b,c] of landmarks.triangles){const A=skin[a],B=skin[b],C=skin[c],u=B.map((x,i)=>x-A[i]),w=C.map((x,i)=>x-A[i]);area=Math.min(area,Math.hypot(u[1]*w[2]-u[2]*w[1],u[2]*w[0]-u[0]*w[2],u[0]*w[1]-u[1]*w[0])/2);}
 assert.ok(area>1e-12);minArea=Math.min(minArea,area);
 const reference=dq.samples.find(s=>s.frame===frame);if(reference)for(let i=0;i<10582;i++)maxFull=Math.max(maxFull,Math.hypot(...skin[i].map((x,a)=>x-reference.positions[i][a])));
 const nr=normals.samples?.find(s=>s.frame===frame);if(nr)verifyShaderNormals(nr);
 samples.push({frame,minimum_floor_z_m:floor,minimum_triangle_area_m2:area});
}
for(const row of pose){
 const skin=evaluate(row.frame),expected=surface.samples.find(s=>s.frame===row.frame);
 for(const [n,p] of Object.entries(row.joints)){const b=mesh.skeleton.bones.find(b=>b.name===n);assert.ok(b);b.getWorldPosition(v);maxJoint=Math.max(maxJoint,Math.hypot(v.x-p[0],-v.z-p[1],v.y-p[2]));}
 for(const patch of Object.values(expected.patches))for(let j=0;j<patch.indices.length;j++)maxSurface=Math.max(maxSurface,Math.hypot(...skin[patch.indices[j]].map((x,a)=>x-patch.positions[j][a])));
}
let loop=0;for(let i=0;i<10582;i++)loop=Math.max(loop,Math.hypot(...first[i].map((x,a)=>x-last[i][a])));
assert.ok(maxFull<.0001&&maxJoint<.0001&&maxSurface<.0001&&loop<.0001&&maxShaderNormal<.0002,JSON.stringify({maxFull,maxJoint,maxSurface,loop,maxShaderNormal}));
const switches=[];
for(const exercise of [...ids,...ids]){
 mixer.stopAllAction();const a=mixer.clipAction(gltf.animations.find(c=>c.name==='Exercise_'+exercise));a.reset().setLoop(THREE.LoopOnce,1).play();a.clampWhenFinished=true;mixer.setTime(.625);gltf.scene.updateMatrixWorld(true);
 assert.equal(mesh.morphTargetInfluences?.length??0,0);switches.push({exercise,time:.625,morph_targets:0});
}
const dir=await mkdtemp(join(tmpdir(),'locomotion-'+id+'-verification-')),file=join(dir,'decoded-float32.bin');await writeFile(file,new Uint8Array(decoded.buffer));
const report={ok:true,source_sha256:sourceSha,glb_sha256:sha(bytes),bytes:bytes.length,animations:gltf.animations.map(c=>c.name),duration_seconds:clip.duration,bones:51,source_ids:10582,triangles:g.index.count/3,morph_targets:0,corrective_track_reset:'Not applicable: no targets or corrective tracks.',action_switch_readback:switches,maximum_basis_NORMAL_vector_error:maxNormal,maximum_DQ_shader_NORMAL_vector_error:maxShaderNormal,maximum_weight_partition_error:maxPartition,maximum_influences:maxInfluences,maximum_full_dq_vertex_error_m:maxFull,maximum_joint_error_m:maxJoint,maximum_sparse_surface_error_m:maxSurface,minimum_floor_z_m:minFloor,minimum_triangle_area_m2:minArea,loop_skin_error_m:loop,physical_readback:'All151 canonical GLB DQ positions sent to temporary local physical checker; no runtime vertex cache delivered.',samples};
await writeFile(new URL('export-verification.json',root),JSON.stringify(report,null,2)+'\n');await writeFile(new URL('verification-exchange-path.txt',root),file+'\n');
console.log(JSON.stringify({ok:true,id,sha256:report.glb_sha256,fullError:maxFull,jointError:maxJoint,basisNormalError:maxNormal,shaderNormalError:maxShaderNormal,decoded_physical_exchange:file}));
