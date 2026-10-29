/** Stream actual project Three.js deformation into the frozen source checks. */
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { spawn } from 'node:child_process';
import { once } from 'node:events';
import * as THREE from '../../../first-exercise-3d/runtime/node_modules/three/build/three.module.js';
import { GLTFLoader } from '../../../first-exercise-3d/runtime/node_modules/three/examples/jsm/loaders/GLTFLoader.js';
const family=new URL('./',import.meta.url);
const bytes=await readFile(new URL('../assets/10058/motion.glb',family));
const model=await new Promise((resolve,reject)=>new GLTFLoader().parse(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),'',resolve,reject));
const meshes=[];model.scene.traverse(x=>{if(x.isSkinnedMesh)meshes.push(x)});
assert.equal(meshes.length,1);assert.equal(model.animations.length,1);
const mesh=meshes[0],geometry=mesh.geometry,clip=model.animations[0];
assert.equal(clip.name,'Exercise_10058');assert.equal(clip.duration,8);
assert.equal(geometry.morphAttributes.position?.length??0,0);
const mixer=new THREE.AnimationMixer(model.scene);
const action=mixer.clipAction(clip).setLoop(THREE.LoopOnce,1);action.clampWhenFinished=true;action.play();
const proc=spawn('/opt/homebrew/bin/blender',['-t','2','-b','--factory-startup','--offline-mode','--python-exit-code','1','--python',new URL('verify_10058_runtime.py',family).pathname],{stdio:['pipe','pipe','pipe']});
proc.stdout.on('data',data=>process.stdout.write(data));proc.stderr.on('data',data=>process.stderr.write(data));
const completion=once(proc,'exit');
const position=geometry.getAttribute('position'),normal=geometry.getAttribute('normal'),source=geometry.getAttribute('_source_index'),skinIndex=geometry.getAttribute('skinIndex'),skinWeight=geometry.getAttribute('skinWeight');
const point=new THREE.Vector3(),direction=new THREE.Vector3();
const C=new THREE.Matrix4().set(1,0,0,0, 0,0,1,0, 0,-1,0,0, 0,0,0,1),Ci=C.clone().invert();
proc.stdin.write(JSON.stringify({bone_names:mesh.skeleton.bones.map(b=>b.name),frames:241})+'\n');
for(let frame=0;frame<=240;frame++){
 action.paused=false;mixer.setTime(frame/30);model.scene.updateMatrixWorld(true);mesh.skeleton.update();
 const bones=mesh.skeleton.bones.map((_,i)=>new THREE.Matrix4().fromArray(mesh.skeleton.boneMatrices,i*16));
 const worldNormals=new THREE.Matrix3().getNormalMatrix(mesh.matrixWorld);
 const totalFloats=10582*6+51*19,output=Buffer.alloc(8+totalFloats*4);output.writeUInt32LE(frame,0);output.writeUInt32LE(10582,4);
 const values=new Float32Array(output.buffer,output.byteOffset+8,totalFloats);
 for(let index=0;index<position.count;index++){
  const id=Math.round(source.getX(index));point.fromBufferAttribute(position,index);direction.fromBufferAttribute(normal,index);
  mesh.applyBoneTransform(index,point);point.applyMatrix4(mesh.matrixWorld);
  values[id*3]=point.x;values[id*3+1]=-point.z;values[id*3+2]=point.y;
  const matrix=new THREE.Matrix4();matrix.elements.fill(0);
  for(let influence=0;influence<4;influence++){
   const w=skinWeight.array[index*4+influence],b=skinIndex.array[index*4+influence];
   for(let component=0;component<16;component++)matrix.elements[component]+=w*bones[b].elements[component];
  }
  matrix.premultiply(mesh.bindMatrixInverse).multiply(mesh.bindMatrix);
  direction.applyMatrix3(new THREE.Matrix3().setFromMatrix4(matrix)).applyMatrix3(worldNormals).normalize();
  const n=10582*3+id*3;values[n]=direction.x;values[n+1]=-direction.z;values[n+2]=direction.y;
 }
 for(let i=0;i<51;i++){
  mesh.skeleton.bones[i].getWorldPosition(point);const o=10582*6+i*3;
  values[o]=point.x;values[o+1]=-point.z;values[o+2]=point.y;
  const matrix=mesh.matrixWorld.clone().multiply(mesh.bindMatrixInverse).multiply(bones[i]).multiply(mesh.bindMatrix).multiply(mesh.matrixWorld.clone().invert());
  matrix.premultiply(Ci).multiply(C);
  for(let j=0;j<16;j++)values[10582*6+51*3+i*16+j]=matrix.elements[j];
 }
 if(!proc.stdin.write(output))await once(proc.stdin,'drain');
}
proc.stdin.end();const [code]=await completion;assert.equal(code,0);
