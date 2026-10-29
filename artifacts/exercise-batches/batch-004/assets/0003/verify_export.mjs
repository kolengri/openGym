import assert from 'node:assert/strict';
import {readFile,writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';
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
const clip=gltf.animations[0];assert.equal(clip.name,'Exercise_0003');assert.ok(Math.abs(clip.duration-5)<1e-6);
const names=['JointNeutral','JointRightCross','JointLeftCross'];
assert.equal(geometry.morphAttributes.position.length,3);assert.equal(geometry.morphAttributes.normal.length,3);assert.ok(geometry.morphTargetsRelative);
assert.deepEqual(Object.keys(mesh.morphTargetDictionary),names);
assert.ok(gltf.parser.json.meshes.every(value=>value.primitives.every(primitive=>primitive.targets.length===3&&primitive.targets.every(target=>target.POSITION!==undefined&&target.NORMAL!==undefined))));
const indices=geometry.getAttribute('_source_index');assert.equal(new Set(indices.array).size,10582);
const sourceSha=sha(await readFile(new URL('source.blend',root)));
const pose=await json('pose-samples.json'),surface=await json('runtime-surface-reference.json'),morph=await json('source-morph-samples.json');
const dq=JSON.parse(gunzipSync(await readFile(new URL('dq-reference.json.gz',root))));
const normals=JSON.parse(gunzipSync(await readFile(new URL('joint-normal-reference.json.gz',root))));
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
  if(patch.state==='supported')assert.ok(patches[name].min_z<=.012&&patches[name].fraction_near_floor>=.2,name+' pelvic support');
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
