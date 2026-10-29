"""Verify actual GLB animated morph/LBS positions, joints and normal stability."""
import json,hashlib,sys
from pathlib import Path
import numpy as np
P=Path(__file__).resolve().parent;sys.path.insert(0,str(P))
from glb_runtime import Runtime
r=Runtime(P/'motion.glb');D=r.doc;ids=r.source
assert set(ids)==set(range(10582));assert len(D['animations'])==1 and D['animations'][0]['name']=='Exercise_1906';assert len(r.primitive['targets'])==1
assert all(D['accessors'][s['input']]['max'][0]<=5.000001 for s in D['animations'][0]['samplers'])
refs=json.loads((P/'linear-vertex-reference.json').read_text());bones=json.loads((P/'pose-samples.json').read_text());rows=[];endpoints={}
for ref in refs:
 f=ref['frame'];s=r.sample(f/30);expected=np.array(ref['vertices'])[ids];expected=expected[:,[0,2,1]]*np.array([1,1,-1]);errors=np.linalg.norm(s['positions']-expected,axis=1);bone_ref=next(x['joints'] for x in bones if x['frame']==f);berr=[]
 for node in D['skins'][0]['joints']:
  name=D['nodes'][node]['name'];v=np.array(bone_ref[name]);v=v[[0,2,1]]*np.array([1,1,-1]);berr.append(np.linalg.norm(s['joint_world'][node][:3,3]-v))
 rows.append({'frame':f,'morph_weights':s['morph_weights'],'max_skin_error_m':float(errors.max()),'mean_skin_error_m':float(errors.mean()),'max_joint_error_m':float(max(berr)),'minimum_pre_normalization_normal_length':float(s['normal_lengths'].min())})
 assert np.isfinite(s['normals']).all() and s['normal_lengths'].min()>.05
 if f in [0,150]:endpoints[f]=s['positions'];assert max(abs(x) for x in s['morph_weights'])<1e-8
maxskin=max(x['max_skin_error_m'] for x in rows);maxjoint=max(x['max_joint_error_m'] for x in rows);loop=float(np.linalg.norm(endpoints[0]-endpoints[150],axis=1).max());sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
report={'ok':maxskin<.00001 and maxjoint<.00001 and loop<.00001,'glb_sha256':sha(P/'motion.glb'),'source_sha256':sha(P/'source.blend'),'actual_animation':D['animations'][0]['name'],'duration_seconds':5,'source_vertices':10582,'exported_uv_split_vertices':len(ids),'unique_source_indices':len(set(ids)),'source_index_complete':True,'triangles':D['accessors'][r.primitive['indices']]['count']//3,'bones':len(D['skins'][0]['joints']),'morphs':1,'morph_normal_target':True,'morph_zero_at_both_endpoints':True,'max_skin_error_m':maxskin,'max_joint_error_m':maxjoint,'loop_skin_error_m':loop,'minimum_pre_normalization_normal_length':min(x['minimum_pre_normalization_normal_length'] for x in rows),'skin_method':'Independently decoded actual GLB TRS, animation weights, morph POSITION/NORMAL, inverse binds and four-influence linear skin; every exported UV-split vertex compared to original-index source linear references. Normal transport uses actual Three.js blend3x3*(base+weight*delta), not Blender importer shading.','samples':rows}
(P/'export-parity-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report));assert report['ok']
