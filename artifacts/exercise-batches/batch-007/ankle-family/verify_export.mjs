import assert from 'node:assert/strict';
import {readFile,writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';
import {spawn} from 'node:child_process';
import {once} from 'node:events';
import {fileURLToPath} from 'node:url';
import * as THREE from '../../../first-exercise-3d/runtime/node_modules/three/build/three.module.js';
import {GLTFLoader} from '../../../first-exercise-3d/runtime/node_modules/three/examples/jsm/loaders/GLTFLoader.js';
const root=new URL('./',import.meta.url),json=async url=>JSON.parse(await readFile(url));
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
const bytes=await readFile(new URL('motion.glb',root)),sourceSha=sha(await readFile(new URL('source.blend',root))),glbSha=sha(bytes);
const adapterFile=new URL('../../dual-quaternion.js',root),adapterBytes=await readFile(adapterFile),adapterSha=sha(adapterBytes);
const adapterSource=adapterBytes.toString().replace("from 'three'","from '"+new URL('../../../first-exercise-3d/runtime/node_modules/three/build/three.module.js',root).href+"'");
const {addDualQuaternionSkinning}=await import('data:text/javascript;base64,'+Buffer.from(adapterSource).toString('base64'));
const gltf=await new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),'');
assert.deepEqual(gltf.animations.map(c=>c.name).sort(),['Exercise_1368','Exercise_2761','Exercise_2762']);const meshes=[];gltf.scene.traverse(o=>{if(o.isSkinnedMesh)meshes.push(o);});assert.equal(meshes.length,1);const mesh=meshes[0],g=mesh.geometry;assert.equal(mesh.skeleton.bones.length,51);assert.equal(g.index.count/3,21160);assert.equal(g.morphAttributes.position?.length??0,0);
const ids=g.getAttribute('_source_index');assert.equal(new Set(ids.array).size,10582);const normals=JSON.parse(gunzipSync(await readFile(new URL('basis-normal-reference.json.gz',root))));assert.equal(normals.source_sha256,sourceSha);const n=g.getAttribute('normal');let normalError=0;
for(let i=0;i<ids.count;i++){const id=Math.round(ids.getX(i));normalError=Math.max(normalError,Math.hypot(n.getX(i)-normals.normals[id][0],-n.getZ(i)-normals.normals[id][1],n.getY(i)-normals.normals[id][2]));}assert.ok(normalError<.0002);
const adapter=addDualQuaternionSkinning(mesh.material);adapter.installSurfaceProbe(mesh);const mixer=new THREE.AnimationMixer(gltf.scene),v=new THREE.Vector3();let action;
function evaluate(frame){action.paused=false;action.enabled=true;mixer.setTime(frame/30);gltf.scene.updateMatrixWorld(true);mesh.skeleton.update();adapter.update(mesh,true);const skin=new Map();for(let i=0;i<ids.count;i++){mesh.getVertexPosition(i,v);mesh.localToWorld(v);const id=Math.round(ids.getX(i)),p=[v.x,-v.z,v.y];if(skin.has(id))assert.ok(Math.hypot(...p.map((x,k)=>x-skin.get(id)[k]))<1e-5);else skin.set(id,p);}return Array.from({length:10582},(_,i)=>skin.get(i));}
const triangles=[];for(let i=0;i<g.index.count;i+=3)triangles.push([0,1,2].map(k=>Math.round(ids.getX(g.index.getX(i+k)))));
for(const id of ['1368','2761','2762']){
 const out=new URL('../assets/'+id+'/',root),clip=gltf.animations.find(c=>c.name==='Exercise_'+id),total=id==='1368'?360:150;assert.ok(Math.abs(clip.duration-total/30)<1e-6);mixer.stopAllAction();action=mixer.clipAction(clip);action.reset().setLoop(THREE.LoopOnce,1);action.clampWhenFinished=true;action.play();
 const poses=await json(new URL('pose-samples.json',out)),surface=await json(new URL('runtime-surface-reference.json',out)),native=await json(new URL('native-joint-readback.json',out)),landmarks=await json(new URL('landmarks.json',out)),dq=JSON.parse(gunzipSync(await readFile(new URL('dq-reference.json.gz',out))));for(const ref of [surface,native,landmarks,dq])assert.equal(ref.source_sha256,sourceSha);
 let jointMax=0,surfaceMax=0,fullMax=0;
 for(const row of poses){const skin=evaluate(row.frame);for(const[name,p]of Object.entries(row.joints)){mesh.skeleton.bones.find(b=>b.name===name).getWorldPosition(v);jointMax=Math.max(jointMax,Math.hypot(v.x-p[0],-v.z-p[1],v.y-p[2]));}for(const patch of Object.values(surface.samples.find(r=>r.frame===row.frame).patches))for(let i=0;i<patch.indices.length;i++)surfaceMax=Math.max(surfaceMax,Math.hypot(...skin[patch.indices[i]].map((x,k)=>x-patch.positions[i][k])));}
 for(const row of dq.samples){const skin=evaluate(row.frame);for(let i=0;i<10582;i++)fullMax=Math.max(fullMax,Math.hypot(...skin[i].map((x,k)=>x-row.positions[i][k])));}assert.ok(jointMax<.0001&&surfaceMax<.0001&&fullMax<.0001);
 const triangle_domains=Object.fromEntries(['LeftArm','RightArm','LeftLeg','RightLeg'].map(name=>{const set=new Set(landmarks.domains[name]);return[name,triangles.filter(t=>t.some(i=>set.has(i)))];}));
 const child=spawn('/opt/homebrew/bin/blender',['-b','-t','2','--python-exit-code','1','--factory-startup','--python',fileURLToPath(new URL('verify_decoded.py',root))],{stdio:['pipe','pipe','pipe']});let stdout='',stderr='';child.stdout.on('data',d=>stdout+=d);child.stderr.on('data',d=>stderr+=d);child.stdin.on('error',()=>{});const closed=once(child,'close');
 async function send(packet){if(!child.stdin.write(JSON.stringify(packet)+'\n'))await once(child.stdin,'drain');}
 await send({id,source_sha256:sourceSha,glb_sha256:glbSha,adapter_sha256:adapterSha,frames:total+1,landmarks,triangles,triangle_domains});
 for(let frame=0;frame<=total;frame++){const positions=evaluate(frame);const row=native.samples[frame];for(const[name,p]of Object.entries(row.joints)){mesh.skeleton.bones.find(b=>b.name===name).getWorldPosition(v);jointMax=Math.max(jointMax,Math.hypot(v.x-p[0],-v.z-p[1],v.y-p[2]));}assert.ok(jointMax<.0001);await send({frame,positions});}child.stdin.end();const[code]=await closed;process.stdout.write(stdout);process.stderr.write(stderr);assert.equal(code,0,'Complete actual decoded physics '+id);
 const report={id,ok:true,source_sha256:sourceSha,glb_sha256:glbSha,adapter_sha256:adapterSha,bytes:bytes.length,actions:gltf.animations.map(c=>c.name),action:clip.name,duration_seconds:clip.duration,frames:total+1,bones:51,original_vertices:10582,triangles:21160,maximum_full_dq_vertex_error_m:fullMax,maximum_all_frame_joint_error_m:jointMax,maximum_source_patch_error_m:surfaceMax,maximum_basis_normal_vector_error:normalError,scope:'Actual canonical multi-action GLB and exact shared DQ adapter; all-frame joint readback, five complete native DQ surfaces and selected skin patches. Physical streamed decode checked separately; actual GPU raster remains primary-owned.'};await writeFile(new URL('export-verification.json',out),JSON.stringify(report,null,2)+'\n');console.log('EXPORT_RESULT',JSON.stringify({id,ok:true,fullMax,jointMax,surfaceMax}));
}
