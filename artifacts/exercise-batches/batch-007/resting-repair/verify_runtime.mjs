/** Stream all151 actual project DQ/NORMAL surfaces and51 joints/matrices. */
import assert from 'node:assert/strict';
import{readFile}from'node:fs/promises';import{spawn}from'node:child_process';import{once}from'node:events';
import*as THREE from'../../../first-exercise-3d/runtime/node_modules/three/build/three.module.js';
import{GLTFLoader}from'../../../first-exercise-3d/runtime/node_modules/three/examples/jsm/loaders/GLTFLoader.js';
const family=new URL('./',import.meta.url),bytes=await readFile(new URL('../assets/4365/motion.glb',family));
const source=(await readFile(new URL('../../dual-quaternion.js',family),'utf8')).replace("from 'three'","from '"+new URL('../../../first-exercise-3d/runtime/node_modules/three/build/three.module.js',family).href+"'");
const{addDualQuaternionSkinning}=await import('data:text/javascript;base64,'+Buffer.from(source).toString('base64'));
const model=await new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),'');const meshes=[];model.scene.traverse(x=>{if(x.isSkinnedMesh)meshes.push(x)});assert.equal(meshes.length,1);assert.equal(model.animations.length,1);const mesh=meshes[0],g=mesh.geometry,clip=model.animations[0];assert.equal(clip.name,'Exercise_4365');assert.equal(clip.duration,5);
const adapter=addDualQuaternionSkinning(mesh.material);adapter.installSurfaceProbe(mesh);const mixer=new THREE.AnimationMixer(model.scene),action=mixer.clipAction(clip).setLoop(THREE.LoopOnce,1);action.clampWhenFinished=true;action.play();
const proc=spawn('/opt/homebrew/bin/blender',['-t','2','-b','--factory-startup','--offline-mode','--python-exit-code','1','--python',new URL('verify_runtime.py',family).pathname],{stdio:['pipe','pipe','pipe']});proc.stdout.on('data',data=>process.stdout.write(data));proc.stderr.on('data',data=>process.stderr.write(data));const completion=once(proc,'exit');
const index=g.getAttribute('_source_index'),normal=g.getAttribute('normal'),skinIndex=g.getAttribute('skinIndex'),skinWeight=g.getAttribute('skinWeight');const point=new THREE.Vector3(),direction=new THREE.Vector3(),delta=new THREE.Vector3(),q=new THREE.Quaternion(),scale=new THREE.Vector3(),offset=new THREE.Vector3(),matrix=new THREE.Matrix4();
const C=new THREE.Matrix4().set(1,0,0,0,0,0,1,0,0,-1,0,0,0,0,0,1),Ci=C.clone().invert();
proc.stdin.write(JSON.stringify({frames:151,bone_names:mesh.skeleton.bones.map(b=>b.name)})+'\n');
for(let frame=0;frame<=150;frame++){
 action.paused=false;mixer.setTime(frame/30);model.scene.updateMatrixWorld(true);mesh.skeleton.update();adapter.update(mesh,true);
 const bones=mesh.skeleton.bones.map((_,i)=>new THREE.Matrix4().fromArray(mesh.skeleton.boneMatrices,i*16));const real=bones.map(m=>{m.decompose(offset,q,scale);return q.clone().normalize()});const worldNormal=new THREE.Matrix3().getNormalMatrix(mesh.matrixWorld),bindNormal=new THREE.Matrix3().setFromMatrix4(mesh.bindMatrix),inverseBindNormal=new THREE.Matrix3().setFromMatrix4(mesh.bindMatrixInverse);
 const count=10582*6+51*19+1,output=Buffer.alloc(8+count*4);output.writeUInt32LE(frame,0);output.writeUInt32LE(10582,4);const values=new Float32Array(output.buffer,output.byteOffset+8,count);
 for(let i=0;i<index.count;i++){
  const id=Math.round(index.getX(i));mesh.getVertexPosition(i,point);mesh.localToWorld(point);values[id*3]=point.x;values[id*3+1]=-point.z;values[id*3+2]=point.y;
  const ref=real[skinIndex.getX(i)];q.set(0,0,0,0);for(let k=0;k<4;k++){const r=real[skinIndex.getComponent(i,k)],w=skinWeight.getComponent(i,k)*(ref.dot(r)<0?-1:1);q.x+=r.x*w;q.y+=r.y*w;q.z+=r.z*w;q.w+=r.w*w;}q.normalize();direction.fromBufferAttribute(normal,i).addScaledVector(delta.fromBufferAttribute(g.morphAttributes.normal[0],i),mesh.morphTargetInfluences[0]);direction.applyMatrix3(bindNormal).applyQuaternion(q).applyMatrix3(inverseBindNormal).applyMatrix3(worldNormal).normalize();const n=10582*3+id*3;values[n]=direction.x;values[n+1]=-direction.z;values[n+2]=direction.y;
 }
 for(let i=0;i<51;i++){
  mesh.skeleton.bones[i].getWorldPosition(point);const o=10582*6+i*3;values[o]=point.x;values[o+1]=-point.z;values[o+2]=point.y;const m=mesh.matrixWorld.clone().multiply(mesh.bindMatrixInverse).multiply(bones[i]).multiply(mesh.bindMatrix).multiply(mesh.matrixWorld.clone().invert());m.premultiply(Ci).multiply(C);for(let j=0;j<16;j++)values[10582*6+51*3+i*16+j]=m.elements[j];
 }
 values[count-1]=mesh.morphTargetInfluences[0];if(!proc.stdin.write(output))await once(proc.stdin,'drain');
}
proc.stdin.end();const[code]=await completion;assert.equal(code,0);
