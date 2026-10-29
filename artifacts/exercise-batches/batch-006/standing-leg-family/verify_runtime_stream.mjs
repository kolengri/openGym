import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { spawn } from 'node:child_process';
import { once } from 'node:events';
import * as THREE from '../../../first-exercise-3d/runtime/node_modules/three/build/three.module.js';
import { GLTFLoader } from '../../../first-exercise-3d/runtime/node_modules/three/examples/jsm/loaders/GLTFLoader.js';
const root=new URL('./',import.meta.url);const id=process.argv[2]||'3479';assert.ok(['3479','3480'].includes(id));const bytes=await readFile(new URL('../assets/3479/motion.glb',root));
const model=await new Promise((resolve,reject)=>new GLTFLoader().parse(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),'',resolve,reject));
const meshes=[];model.scene.traverse(x=>{if(x.isSkinnedMesh)meshes.push(x)});assert.equal(meshes.length,1);const mesh=meshes[0],geometry=mesh.geometry;
const clip=model.animations.find(x=>x.name==='Exercise_'+id);const mixer=new THREE.AnimationMixer(model.scene);const action=mixer.clipAction(clip).setLoop(THREE.LoopOnce,1);action.clampWhenFinished=true;action.play();
const proc=spawn('/opt/homebrew/bin/blender',['-t','2','-b','--factory-startup','--offline-mode','--python-exit-code','1','--python',new URL('verify_runtime_stream.py',root).pathname,'--',id],{stdio:['pipe','pipe','pipe']});
proc.stdout.on('data',data=>process.stdout.write(data));proc.stderr.on('data',data=>process.stderr.write(data));const completion=once(proc,'exit');
const position=geometry.getAttribute('position'),normal=geometry.getAttribute('normal'),source=geometry.getAttribute('_source_index'),skinIndex=geometry.getAttribute('skinIndex'),skinWeight=geometry.getAttribute('skinWeight');
const point=new THREE.Vector3(),direction=new THREE.Vector3(),delta=new THREE.Vector3();
for(let frame=0;frame<=Math.round(clip.duration*30);frame++){
 mixer.setTime(frame/30);model.scene.updateMatrixWorld(true);mesh.skeleton.update();
 const bones=mesh.skeleton.bones.map((_,i)=>new THREE.Matrix4().fromArray(mesh.skeleton.boneMatrices,i*16));const worldNormals=new THREE.Matrix3().getNormalMatrix(mesh.matrixWorld);const output=Buffer.alloc(8+10582*24);output.writeUInt32LE(frame,0);output.writeUInt32LE(10582,4);const values=new Float32Array(output.buffer,output.byteOffset+8,10582*6);
 for(let index=0;index<position.count;index++){
  const id=Math.round(source.getX(index));point.fromBufferAttribute(position,index);direction.fromBufferAttribute(normal,index);
  for(let target=0;target<4;target++){point.addScaledVector(delta.fromBufferAttribute(geometry.morphAttributes.position[target],index),mesh.morphTargetInfluences[target]);direction.addScaledVector(delta.fromBufferAttribute(geometry.morphAttributes.normal[target],index),mesh.morphTargetInfluences[target]);}
  mesh.applyBoneTransform(index,point);point.applyMatrix4(mesh.matrixWorld);values[id*3]=point.x;values[id*3+1]=-point.z;values[id*3+2]=point.y;
  const matrix=new THREE.Matrix4();matrix.elements.fill(0);
  for(let influence=0;influence<4;influence++){const w=skinWeight.array[index*4+influence],b=skinIndex.array[index*4+influence];for(let component=0;component<16;component++)matrix.elements[component]+=w*bones[b].elements[component];}
  matrix.premultiply(mesh.bindMatrixInverse).multiply(mesh.bindMatrix);direction.applyMatrix3(new THREE.Matrix3().setFromMatrix4(matrix)).applyMatrix3(worldNormals).normalize();const n=10582*3+id*3;values[n]=direction.x;values[n+1]=-direction.z;values[n+2]=direction.y;
 }
 if(!proc.stdin.write(output))await once(proc.stdin,'drain');
}
proc.stdin.end();const [code]=await completion;assert.equal(code,0);
