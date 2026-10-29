import assert from 'node:assert/strict';
import {readFile,writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {GLTFLoader} from '../../../first-exercise-3d/runtime/node_modules/three/examples/jsm/loaders/GLTFLoader.js';
const root=new URL('./',import.meta.url),bytes=await readFile(new URL('motion.glb',root)),native=JSON.parse(await readFile(new URL('source-build-receipt.json',root)));
const gltf=await new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),'');let mesh;gltf.scene.traverse(o=>{if(o.isSkinnedMesh){assert.ok(!mesh);mesh=o;}});
const g=mesh.geometry,ids=g.getAttribute('_source_index'),si=g.getAttribute('skinIndex'),sw=g.getAttribute('skinWeight');assert.equal(si.itemSize,4);assert.equal(sw.itemSize,4);let maxSum=0,maxError=0,maxCount=0;
for(let i=0;i<ids.count;i++){
 const actual={},expected=native.actual_weights[Math.round(ids.getX(i))];let sum=0,count=0;
 for(let k=0;k<4;k++){const w=sw.array[i*4+k];sum+=w;if(w>0){count++;const name=mesh.skeleton.bones[si.array[i*4+k]].name;actual[name]=(actual[name]||0)+w;}}
 maxSum=Math.max(maxSum,Math.abs(sum-1));maxCount=Math.max(maxCount,count);for(const name of new Set([...Object.keys(actual),...Object.keys(expected)]))maxError=Math.max(maxError,Math.abs((actual[name]||0)-(expected[name]||0)));
}
assert.ok(maxSum<2e-6&&maxError<2e-6&&maxCount<=4);const report={pass:true,glb_sha256:createHash('sha256').update(bytes).digest('hex'),source_sha256:native.source_sha256,exported_vertices:ids.count,source_vertices:10582,actual_maximum_influences:maxCount,actual_maximum_weight_sum_error:maxSum,actual_maximum_source_weight_difference:maxError,all_uv_splits_checked:true,bones:mesh.skeleton.bones.length};await writeFile(new URL('export-weight-verification.json',root),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report));
