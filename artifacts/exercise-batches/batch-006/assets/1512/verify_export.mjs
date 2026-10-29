import assert from 'node:assert/strict';
import {readFile,writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import * as THREE from '../../../../first-exercise-3d/runtime/node_modules/three/build/three.module.js';
import {GLTFLoader} from '../../../../first-exercise-3d/runtime/node_modules/three/examples/jsm/loaders/GLTFLoader.js';
const root=new URL('./',import.meta.url),json=async name=>JSON.parse(await readFile(new URL(name,root)));
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
// Execute the exact shared adapter; only Node's bare dependency resolution changes.
const adapterSource=(await readFile(new URL('../../../dual-quaternion.js',root),'utf8')).replace("from 'three'","from '"+new URL('../../../../first-exercise-3d/runtime/node_modules/three/build/three.module.js',root).href+"'");
const {addDualQuaternionSkinning}=await import('data:text/javascript;base64,'+Buffer.from(adapterSource).toString('base64'));
const bytes=await readFile(new URL('motion.glb',root));
const gltf=await new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),'');
const meshes=[];gltf.scene.traverse(object=>{if(object.isSkinnedMesh)meshes.push(object);});
assert.equal(meshes.length,1);const mesh=meshes[0],geometry=mesh.geometry;
assert.equal(mesh.skeleton.bones.length,51);assert.equal(gltf.animations.length,1);
const clip=gltf.animations[0];assert.equal(clip.name,'Exercise_1512');assert.ok(Math.abs(clip.duration-5)<1e-6);
const names=['LocalStart','LocalEntry','LocalHold'];
assert.equal(geometry.morphAttributes.position.length,3);assert.equal(geometry.morphAttributes.normal.length,3);assert.ok(geometry.morphTargetsRelative);
assert.deepEqual(Object.keys(mesh.morphTargetDictionary),names);
assert.ok(gltf.parser.json.meshes.every(value=>value.primitives.every(primitive=>primitive.targets.length===3&&primitive.targets.every(target=>target.POSITION!==undefined&&target.NORMAL!==undefined))));
const indices=geometry.getAttribute('_source_index');assert.equal(new Set(indices.array).size,10582);
const sourceSha=sha(await readFile(new URL('source.blend',root)));
const pose=await json('pose-samples.json'),surface=await json('runtime-surface-reference.json'),morph=await json('source-morph-samples.json');
const dq=JSON.parse(gunzipSync(await readFile(new URL('dq-reference.json.gz',root))));
const normals=JSON.parse(gunzipSync(await readFile(new URL('morph-normal-reference.json.gz',root))));
for(const reference of [surface,morph,dq,normals])assert.equal(reference.source_sha256,sourceSha);
const normal=geometry.getAttribute('normal');let maximumBasisNormalError=0;
const normalErrors=names.map(()=>0);
for(let vertex=0;vertex<indices.count;vertex++){
 const id=Math.round(indices.getX(vertex)),base=[normal.getX(vertex),-normal.getZ(vertex),normal.getY(vertex)];
 maximumBasisNormalError=Math.max(maximumBasisNormalError,Math.hypot(...base.map((value,axis)=>value-normals.basis[id][axis])));
 for(let target=0;target<3;target++){
  const delta=geometry.morphAttributes.normal[target];
  const result=[base[0]+delta.getX(vertex),base[1]-delta.getZ(vertex),base[2]+delta.getY(vertex)];
  normalErrors[target]=Math.max(normalErrors[target],Math.hypot(...result.map((value,axis)=>value-normals.targets[names[target]][id][axis])));
 }
}
assert.ok(maximumBasisNormalError<.0002&&normalErrors.every(value=>value<.0002),'NORMAL targets must match independently calculated source-key normals');
const adapter=addDualQuaternionSkinning(mesh.material);adapter.installSurfaceProbe(mesh);
const mixer=new THREE.AnimationMixer(gltf.scene),action=mixer.clipAction(clip);action.setLoop(THREE.LoopOnce,1);action.clampWhenFinished=true;action.play();
const vector=new THREE.Vector3();let maximumJointError=0,maximumSurfaceError=0,maximumFullError=0,maximumMorphError=0;
let first,last;const samples=[];
function evaluate(frame){
 // LoopOnce pauses at the endpoint. Each random-access sample must resume
 // before setTime, including a new traversal after the sampled final frame.
 action.paused=false;action.enabled=true;
 mixer.setTime(frame/30);gltf.scene.updateMatrixWorld(true);mesh.skeleton.update();adapter.update(mesh,true);
 const skin=new Map();
 for(let vertex=0;vertex<indices.count;vertex++){
  mesh.getVertexPosition(vertex,vector);mesh.localToWorld(vector);const point=[vector.x,-vector.z,vector.y],id=Math.round(indices.getX(vertex));
  if(skin.has(id))assert.ok(Math.hypot(...point.map((value,axis)=>value-skin.get(id)[axis]))<1e-5,'UV-split seam mismatch');
  else skin.set(id,point);
 }
 return skin;
}
for(const row of pose){
 const skin=evaluate(row.frame),expected=surface.samples.find(value=>value.frame===row.frame),morphExpected=morph.samples.find(value=>value.frame===row.frame);
 let jointError=0,surfaceError=0;
 for(const [name,point]of Object.entries(row.joints)){
  const bone=mesh.skeleton.bones.find(value=>value.name===name);assert.ok(bone);bone.getWorldPosition(vector);
  jointError=Math.max(jointError,Math.hypot(vector.x-point[0],-vector.z-point[1],vector.y-point[2]));
 }
 for(let target=0;target<3;target++)maximumMorphError=Math.max(maximumMorphError,Math.abs(mesh.morphTargetInfluences[target]-morphExpected.weights[names[target]]));
 const patches={};
 for(const [name,patch]of Object.entries(expected.patches)){
  const points=patch.indices.map(id=>skin.get(id));
  for(let i=0;i<points.length;i++)surfaceError=Math.max(surfaceError,Math.hypot(...points[i].map((value,axis)=>value-patch.positions[i][axis])));
  const z=points.map(point=>point[2]);patches[name]={min_z:Math.min(...z),max_z:Math.max(...z),fraction_near_floor:z.filter(value=>Math.abs(value)<=.012).length/z.length};
  if(patch.state==='supported')assert.ok(patches[name].min_z<=.012&&patches[name].fraction_near_floor>=.2,name+' skin support');
  if(patch.state==='lifted')assert.ok(patches[name].min_z>=.05,name+' airborne clearance');
 }
 const full=dq.samples.find(value=>value.frame===row.frame);
 if(full){assert.equal(full.positions.length,10582);for(let id=0;id<10582;id++)maximumFullError=Math.max(maximumFullError,Math.hypot(...skin.get(id).map((value,axis)=>value-full.positions[id][axis])));}
 const floor=Math.min(...Array.from(skin.values(),point=>point[2]));assert.ok(floor>=-.004,'Floor penetration');
 maximumJointError=Math.max(maximumJointError,jointError);maximumSurfaceError=Math.max(maximumSurfaceError,surfaceError);
 samples.push({frame:row.frame,joint_error_m:jointError,surface_error_m:surfaceError,morph_weights:[...mesh.morphTargetInfluences],floor_min_z:floor,patches});
 if(row.frame===0)first=skin;if(row.frame===150)last=skin;
}
let loop=0;for(const [id,point]of first)loop=Math.max(loop,Math.hypot(...point.map((value,axis)=>value-last.get(id)[axis])));
assert.ok(maximumFullError<=.0001&&maximumJointError<=.0001&&maximumSurfaceError<=.0001&&loop<=.0001&&maximumMorphError<=1e-5);
const report={ok:true,source_sha256:sourceSha,sha256:sha(bytes),bytes:bytes.byteLength,animations:[clip.name],duration_seconds:clip.duration,bones:51,original_vertex_ids:10582,triangles:geometry.index.count/3,morph_position_targets:names,morph_normal_targets:names,maximum_basis_normal_vector_error:maximumBasisNormalError,maximum_target_normal_vector_errors:normalErrors,normal_scope:'Every GLTFLoader UV-split Basis/key NORMAL compared to independently calculated source rest normals. Three morphs before unit DQ rotation, which preserves this vector-error bound. Actual GPU raster appearance remains primary-owned.',maximum_full_dq_vertex_error_m:maximumFullError,maximum_joint_error_m:maximumJointError,maximum_surface_error_m:maximumSurfaceError,maximum_morph_weight_error:maximumMorphError,loop_skin_error_m:loop,samples,scope:'Actual canonical GLB + exact shared optional CPU DQ adapter against the corrective-bearing native DQ cage. No generic linear-skin appearance claim.'};
await writeFile(new URL('export-verification.json',root),JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify({ok:true,sha256:report.sha256,full_dq_error_m:maximumFullError,joint_error_m:maximumJointError,normal_vector_errors:normalErrors,loop_skin_error_m:loop}));
if(process.argv.includes('--triangles')){
 const groups={LeftArm:new Set(),RightArm:new Set(),LeftLeg:new Set(),RightLeg:new Set()};
 const skinIndex=geometry.getAttribute('skinIndex'),skinWeight=geometry.getAttribute('skinWeight');
 for(let vertex=0;vertex<indices.count;vertex++){
  const sums={LeftArm:0,RightArm:0,LeftLeg:0,RightLeg:0};
  for(let influence=0;influence<4;influence++){
   const bone=mesh.skeleton.bones[skinIndex.array[vertex*4+influence]].name,w=skinWeight.array[vertex*4+influence];
   for(const side of ['Left','Right']){
    if(new RegExp('^'+side+'(Arm|ForeArm|Hand|Index|Middle|Ring|Little|Thumb)').test(bone))sums[side+'Arm']+=w;
    if(new RegExp('^'+side+'(UpLeg|Leg|Foot|ToeBase)').test(bone))sums[side+'Leg']+=w;
   }
  }
  for(const [name,value]of Object.entries(sums))if(value>.5)groups[name].add(Math.round(indices.getX(vertex)));
 }
 const triangles=[];
 for(let i=0;i<geometry.index.count;i+=3)triangles.push([0,1,2].map(k=>Math.round(indices.getX(geometry.index.getX(i+k)))));
 const domains=Object.fromEntries(Object.entries(groups).map(([name,set])=>[name,triangles.filter(triangle=>triangle.some(id=>set.has(id)))]));
 const frames=[],physics=[];
 const native=await json('early-native-readback.json');assert.equal(native.source_sha256,sourceSha);
 let minimumArea=Infinity,maximumAllFrameJointError=0;
 for(let frame=0;frame<=150;frame++){
  const skin=evaluate(frame),positions=Array.from({length:10582},(_,id)=>skin.get(id));
  const floor=Math.min(...positions.map(point=>point[2]));assert.ok(floor>=-.004,'All151 decoded floor penetration');
  const supports={};
  for(const [name,patch]of Object.entries(surface.samples[0].patches))if(patch.state==='supported'){
   const pp=patch.indices.map(id=>positions[id]),z=pp.map(point=>point[2]);
   const drift=Math.max(...pp.map((point,i)=>Math.hypot(point[0]-patch.positions[i][0],point[1]-patch.positions[i][1])));
   supports[name]={min_z:Math.min(...z),fraction_near_floor:z.filter(value=>Math.abs(value)<=.012).length/z.length,maximum_tangential_drift_m:drift};
   assert.ok(supports[name].min_z<=.012&&supports[name].fraction_near_floor>=.2,'All151 decoded '+name+' support');
   if(name==='palm_Right')assert.ok(drift<=.005,'All151 decoded supporting palm drift');
  }
  let area=Infinity;
  for(const ids of triangles){
   const [a,b,c]=ids.map(id=>positions[id]),u=b.map((v,i)=>v-a[i]),v=c.map((x,i)=>x-a[i]);
   area=Math.min(area,.5*Math.hypot(u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]));
  }
  assert.ok(area>1e-12,'All151 decoded positive triangle areas');minimumArea=Math.min(minimumArea,area);
  let jointError=0;
  for(const [name,point]of Object.entries(native.samples[frame].joints)){
   mesh.skeleton.bones.find(bone=>bone.name===name).getWorldPosition(vector);
   jointError=Math.max(jointError,Math.hypot(vector.x-point[0],-vector.z-point[1],vector.y-point[2]));
  }
  assert.ok(jointError<.0001,'All151 decoded native joint parity frame '+frame+' error '+jointError);maximumAllFrameJointError=Math.max(maximumAllFrameJointError,jointError);
  physics.push({frame,floor_min_z:floor,minimum_triangle_area_m2:area,joint_error_m:jointError,supports});
  frames.push({frame,positions});
 }
 const physicalReport={pass:true,source_sha256:sourceSha,glb_sha256:sha(bytes),frames:151,minimum_triangle_area_m2:minimumArea,maximum_joint_error_m:maximumAllFrameJointError,minimum_floor_z:Math.min(...physics.map(row=>row.floor_min_z)),samples:physics,scope:'All151 actual GLTFLoader plus exact shared DQ adapter samples: full skin floor/positive areas, actual source-bound support patches and all51 native joint heads. Discrete sampled evidence; no continuous-time collision claim.'};
 await writeFile(new URL('decoded-physical-report.json',root),JSON.stringify(physicalReport,null,2)+'\n');
 const footDomain=await json('foot-return-repair/repaired-native-diagnosis.json');assert.equal(footDomain.source_sha256,sourceSha);
 const packet={source_sha256:sourceSha,glb_sha256:sha(bytes),adapter_sha256:sha(await readFile(new URL('../../../dual-quaternion.js',root))),domains,frames,foot_domain:{ankle_edges:footDomain.ankle_edges,foot_edges:footDomain.foot_edges}};
 const result=spawnSync('/opt/homebrew/bin/blender',['-b','-t','2','--python-exit-code','1','--factory-startup','--python',fileURLToPath(new URL('verify_decoded_contacts.py',root))],{input:JSON.stringify(packet),encoding:'utf8',maxBuffer:16*1024*1024});
 process.stdout.write(result.stdout||'');process.stderr.write(result.stderr||'');assert.equal(result.status,0,'Decoded DQ triangle crossing check');
}
