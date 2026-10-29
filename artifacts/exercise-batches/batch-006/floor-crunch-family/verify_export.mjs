import assert from 'node:assert/strict';
import {readFile,writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';
import * as THREE from '../../../first-exercise-3d/runtime/node_modules/three/build/three.module.js';
import {GLTFLoader} from '../../../first-exercise-3d/runtime/node_modules/three/examples/jsm/loaders/GLTFLoader.js';
const root=new URL('./',import.meta.url),sha=b=>createHash('sha256').update(b).digest('hex');
const adapterSource=(await readFile(new URL('../../dual-quaternion.js',root),'utf8')).replace("from 'three'","from '"+new URL('../../../first-exercise-3d/runtime/node_modules/three/build/three.module.js',root).href+"'");
const {addDualQuaternionSkinning}=await import('data:text/javascript;base64,'+Buffer.from(adapterSource).toString('base64'));
const bytes=await readFile(new URL('motion.glb',root)),sourceSha=sha(await readFile(new URL('source.blend',root)));
const gltf=await new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),'');
const meshes=[];gltf.scene.traverse(o=>{if(o.isSkinnedMesh)meshes.push(o);});assert.equal(meshes.length,1);
const mesh=meshes[0],g=mesh.geometry,indices=g.getAttribute('_source_index');assert.equal(mesh.skeleton.bones.length,51);assert.equal(new Set(indices.array).size,10582);
assert.deepEqual(gltf.animations.map(a=>a.name).sort(),['Exercise_0006','Exercise_4354']);assert.equal(g.morphAttributes.position.length,6);assert.equal(g.morphAttributes.normal.length,6);assert.ok(g.morphTargetsRelative);
const names=Object.keys(mesh.morphTargetDictionary);assert.equal(names.length,6);assert.ok(names.every(n=>n.startsWith('Shoulder')));assert.ok(gltf.parser.json.meshes.every(m=>m.primitives.every(p=>p.targets.length===6&&p.targets.every(t=>t.POSITION!==undefined&&t.NORMAL!==undefined))));
const exportedTriangles=[];for(let i=0;i<g.index.count;i+=3)exportedTriangles.push([0,1,2].map(k=>Math.round(indices.getX(g.index.getX(i+k)))));
await writeFile(new URL('.decoded-topology.json',root),JSON.stringify(exportedTriangles));
const adapter=addDualQuaternionSkinning(mesh.material);adapter.installSurfaceProbe(mesh);const v=new THREE.Vector3();
for(const id of ['0006','4354']){
 const out=new URL('../assets/'+id+'/',root),json=async n=>JSON.parse(await readFile(new URL(n,out)));
 const normal=JSON.parse(gunzipSync(await readFile(new URL('joint-normal-reference.json.gz',out))));assert.equal(normal.source_sha256,sourceSha);
 let normalError=0;const targetNormalErrors={};for(const n of names)targetNormalErrors[n]=0;
 const attr=g.getAttribute('normal');
 for(let i=0;i<indices.count;i++){
  const source=Math.round(indices.getX(i)),base=[attr.getX(i),-attr.getZ(i),attr.getY(i)];normalError=Math.max(normalError,Math.hypot(...base.map((x,k)=>x-normal.basis[source][k])));
  for(let k=0;k<names.length;k++){
   const delta=g.morphAttributes.normal[k],actual=[base[0]+delta.getX(i),base[1]-delta.getZ(i),base[2]+delta.getY(i)];targetNormalErrors[names[k]]=Math.max(targetNormalErrors[names[k]],Math.hypot(...actual.map((x,j)=>x-normal.targets[names[k]][source][j])));
  }
 }
 assert.ok(normalError<.0002&&Object.values(targetNormalErrors).every(x=>x<.0002));
 const native=gunzipSync(await readFile(new URL('.native-all151-'+id+'.f32.gz',root))),view=new DataView(native.buffer,native.byteOffset,native.byteLength);assert.equal(native.length,151*10582*3*4);
 const pose=await json('pose-samples.json'),surface=await json('runtime-surface-reference.json'),morph=await json('source-morph-samples.json'),physical=await json('surface-contact-report.json');assert.equal(surface.source_sha256,sourceSha);assert.equal(morph.source_sha256,sourceSha);assert.ok(physical.ok);
 const clip=gltf.animations.find(c=>c.name==='Exercise_'+id);assert.ok(Math.abs(clip.duration-5)<1e-6);
 const mixer=new THREE.AnimationMixer(gltf.scene),action=mixer.clipAction(clip);action.setLoop(THREE.LoopOnce,1);action.clampWhenFinished=true;action.play();
 const decoded=Buffer.alloc(151*10582*3*8);
 let maximumFullError=0,maximumJointError=0,maximumPatchError=0,maximumMorphError=0,first,last;const samples=[];
 function evaluate(frame){
  action.paused=false;action.enabled=true;mixer.setTime(frame/30);gltf.scene.updateMatrixWorld(true);mesh.skeleton.update();adapter.update(mesh,true);const skin=new Map();
  for(let i=0;i<indices.count;i++){
   mesh.getVertexPosition(i,v);mesh.localToWorld(v);const p=[v.x,-v.z,v.y],source=Math.round(indices.getX(i));
   if(skin.has(source))assert.ok(Math.hypot(...p.map((x,k)=>x-skin.get(source)[k]))<1e-5,'UV seam split');else skin.set(source,p);
  }
  return skin;
 }
 for(let frame=0;frame<=150;frame++){
  const skin=evaluate(frame);let error=0,minZ=Infinity;
  for(const [source,p]of skin){for(let k=0;k<3;k++)decoded.writeDoubleLE(p[k],((frame*10582+source)*3+k)*8);let sum=0;for(let k=0;k<3;k++){const expected=view.getFloat32(((frame*10582+source)*3+k)*4,true);sum+=(p[k]-expected)**2;}error=Math.max(error,Math.sqrt(sum));minZ=Math.min(minZ,p[2]);}
  maximumFullError=Math.max(maximumFullError,error);assert.ok(error<.0001,JSON.stringify({id,frame,error,morph:mesh.morphTargetInfluences,jointProbe:mesh.skeleton.bones.find(b=>b.name==='LeftHand').getWorldPosition(new THREE.Vector3()).toArray(),expectedHand:pose.find(p=>p.frame===frame)?.joints.LeftHand}));assert.ok(minZ>=-.004,'decoded floor frame'+frame);
  const expectedMorph=morph.samples.find(r=>r.frame===frame);for(let k=0;k<names.length;k++)maximumMorphError=Math.max(maximumMorphError,Math.abs(mesh.morphTargetInfluences[k]-expectedMorph.weights[names[k]]));
  const patches={};for(const [name,patch]of Object.entries(surface.samples[0].patches))if(patch.state==='supported'){
   const z=patch.indices.map(i=>skin.get(i)[2]);patches[name]={min_z:Math.min(...z),fraction_near_floor:z.filter(v=>Math.abs(v)<=.012).length/z.length};assert.ok(patches[name].min_z<=.012&&patches[name].fraction_near_floor>=.2,'decoded support '+name+' frame'+frame);
  }
  samples.push({frame,maximum_full_native_vertex_error_m:error,floor_min_z_m:minZ,supported_patches:patches});if(frame===0)first=skin;if(frame===150)last=skin;
 }
 for(const row of pose){
  const skin=evaluate(row.frame);
  for(const [name,p]of Object.entries(row.joints)){
   const bone=mesh.skeleton.bones.find(b=>b.name===name);assert.ok(bone);bone.getWorldPosition(v);maximumJointError=Math.max(maximumJointError,Math.hypot(v.x-p[0],-v.z-p[1],v.y-p[2]));
  }
  const expected=surface.samples.find(s=>s.frame===row.frame);for(const patch of Object.values(expected.patches))for(let i=0;i<patch.indices.length;i++)maximumPatchError=Math.max(maximumPatchError,Math.hypot(...skin.get(patch.indices[i]).map((x,k)=>x-patch.positions[i][k])));
 }
 let loop=0;for(const [source,p]of first)loop=Math.max(loop,Math.hypot(...p.map((x,k)=>x-last.get(source)[k])));
 assert.ok(maximumJointError<.0001&&maximumPatchError<.0001&&loop<.0001&&maximumMorphError<1e-5,JSON.stringify({id,maximumFullError,maximumJointError,maximumPatchError,loop,maximumMorphError}));
 const nativeClearance=physical.minimum_arm_hand_leg_clearance_m;assert.ok(nativeClearance-2*maximumFullError>=.0005,'Full pointwise parity preserves native clearance margin');
 const report={ok:true,id,source_sha256:sourceSha,sha256:sha(bytes),bytes:bytes.length,animations:gltf.animations.map(c=>c.name),action:clip.name,duration_seconds:clip.duration,bones:51,original_vertex_ids:10582,triangles:g.index.count/3,morph_position_targets:names,morph_normal_targets:names,maximum_basis_normal_vector_error:normalError,maximum_target_normal_vector_errors:targetNormalErrors,maximum_full_dq_vertex_error_m:maximumFullError,maximum_joint_error_m:maximumJointError,maximum_surface_patch_error_m:maximumPatchError,maximum_morph_weight_error:maximumMorphError,loop_skin_error_m:loop,native_mechanical_clearance_m:nativeClearance,decoded_mechanical_clearance_lower_bound_m:nativeClearance-2*maximumFullError,samples,scope:'Actual canonical shared two-action GLB, exact shared optional DQ CPU adapter, all10582 source vertices across all151frames versus canonical native source. Full-body pointwise parity carries native triangle/clearance witnesses with explicit error margin; native joint/patch subframes and all6 independent NORMAL target buffers checked. Actual GPU raster review remains root-owned.'};
 await writeFile(new URL('.decoded-all151-'+id+'.f64',root),decoded);
 await writeFile(new URL('export-verification.json',out),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify({id,ok:true,sha256:report.sha256,maximum_full_dq_vertex_error_m:maximumFullError,maximum_joint_error_m:maximumJointError,loop_skin_error_m:loop,maximum_normal_error:Math.max(normalError,...Object.values(targetNormalErrors))}));mixer.stopAllAction();mixer.uncacheRoot(gltf.scene);
}
