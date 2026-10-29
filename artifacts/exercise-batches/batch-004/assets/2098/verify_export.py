"""Decode actual GLB animation and linear blend skin, compare every source vertex."""
import json,struct,hashlib,math
from pathlib import Path
import numpy as np
from mathutils import Matrix,Quaternion,Vector
P=Path(__file__).resolve().parent
b=(P/'motion.glb').read_bytes();length=struct.unpack_from('<I',b,12)[0];D=json.loads(b[20:20+length]);offset=20+length;blen,bkind=struct.unpack_from('<II',b,offset);BIN=b[offset+8:offset+8+blen]
TYPES={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT4':16};DT={5126:'<f4',5125:'<u4',5123:'<u2',5121:'u1'}
def accessor(i):
 a=D['accessors'][i];v=D['bufferViews'][a['bufferView']];dt=np.dtype(DT[a['componentType']]);n=TYPES[a['type']];start=v.get('byteOffset',0)+a.get('byteOffset',0);stride=v.get('byteStride',n*dt.itemsize)
 return np.ndarray((a['count'],n),dtype=dt,buffer=BIN,offset=start,strides=(stride,dt.itemsize)).copy()
parents={j:i for i,n in enumerate(D['nodes']) for j in n.get('children',[])}
def local(n,values):
 if 'matrix' in n:return np.array(n['matrix']).reshape(4,4).T
 t=values.get('translation',n.get('translation',[0,0,0]));r=values.get('rotation',n.get('rotation',[0,0,0,1]));s=values.get('scale',n.get('scale',[1,1,1]))
 return np.array(Matrix.LocRotScale(Vector(t),Quaternion((r[3],r[0],r[1],r[2])),Vector(s)),float)
def evaluate(t):
 values={}
 for ch in D['animations'][0]['channels']:
  sampler=D['animations'][0]['samplers'][ch['sampler']];times=accessor(sampler['input']).ravel();out=accessor(sampler['output']);i=int(np.searchsorted(times,t,side='right'))-1;i=max(0,min(i,len(times)-1));j=min(i+1,len(times)-1)
  f=(t-float(times[i]))/(float(times[j]-times[i])) if times[j]>times[i] else 0;f=max(0,min(1,f));path=ch['target']['path']
  if path=='weights':out=out.reshape(len(times),-1)
  if path=='rotation':
   x,y,z,w=out[i];x2,y2,z2,w2=out[j];q=Quaternion((w,x,y,z)).slerp(Quaternion((w2,x2,y2,z2)),f);v=[q.x,q.y,q.z,q.w]
  else:v=(out[i]*(1-f)+out[j]*f).tolist()
  values.setdefault(ch['target']['node'],{})[path]=v
 mats={}
 def world(i):
  if i not in mats:mats[i]=(world(parents[i]) if i in parents else np.eye(4))@local(D['nodes'][i],values.get(i,{}))
  return mats[i]
 for i in range(len(D['nodes'])):world(i)
 return mats
skin=D['skins'][0];ibm=accessor(skin['inverseBindMatrices']).reshape(-1,4,4).transpose(0,2,1)
p=D['meshes'][0]['primitives'][0];attrs=p['attributes'];pos=accessor(attrs['POSITION']);src=accessor(attrs['_SOURCE_INDEX']).ravel().astype(int);joints=accessor(attrs['JOINTS_0']).astype(int);weights=accessor(attrs['WEIGHTS_0']);homo=np.column_stack((pos,np.ones(len(pos))))
assert set(src)==set(range(10582));assert len(D['animations'])==1 and D['animations'][0]['name']=='Exercise_2098'
assert len(D['skins'])==1 and len(skin['joints'])==51 and len(D['meshes'])==1 and len(D.get('images',[]))==0 and len(D['materials'])==1 and not p.get('targets')
assert all(D['accessors'][s['input']]['max'][0]<=5.000001 for s in D['animations'][0]['samplers'])
refs=json.loads((P/'linear-vertex-reference.json').read_text());bone_refs=json.loads((P/'pose-samples.json').read_text());rows=[];skins={}
for ref in refs:
 f=ref['frame'];mats=evaluate(f/30);jointmats=np.array([mats[i] for i in skin['joints']]);trans=jointmats@ibm
 runtime=np.zeros((len(pos),4))
 for k in range(4):runtime+=weights[:,k,None]*np.einsum('nij,nj->ni',trans[joints[:,k]],homo)
 expected=np.array(ref['vertices'])[src];expected=expected[:,[0,2,1]]*np.array([1,1,-1]);error=np.linalg.norm(runtime[:,:3]-expected,axis=1)
 bones=next(x['joints'] for x in bone_refs if x['frame']==f);boneerror=[]
 for node in skin['joints']:
  name=D['nodes'][node]['name'];v=np.array(bones[name]);v=v[[0,2,1]]*np.array([1,1,-1]);boneerror.append(np.linalg.norm(mats[node][:3,3]-v))
 rows.append({'frame':f,'max_skin_error_m':float(error.max()),'mean_skin_error_m':float(error.mean()),'max_joint_error_m':float(max(boneerror))})
 if f in [0,150]:skins[f]=runtime[:,:3]
maxskin=max(x['max_skin_error_m'] for x in rows);maxbone=max(x['max_joint_error_m'] for x in rows);loop=float(np.linalg.norm(skins[0]-skins[150],axis=1).max())
report={'ok':maxskin<.00001 and maxbone<.00001 and loop<.00001,'glb_sha256':hashlib.sha256(b).hexdigest(),'source_sha256':hashlib.sha256((P/'source.blend').read_bytes()).hexdigest(),'actual_animation':D['animations'][0]['name'],'duration_seconds':5,'source_vertices':10582,'exported_uv_split_vertices':len(pos),'unique_source_indices':len(set(src)),'source_index_complete':True,'triangles':D['accessors'][p['indices']]['count']//3,'bones':len(skin['joints']),'normal_only_morph_targets':len(p.get('targets',[])),'position_morph_delta_max_m':0,'max_skin_error_m':maxskin,'max_joint_error_m':maxbone,'loop_skin_error_m':loop,'skin_method':'Independently decoded GLB node TRS, quaternion slerp, inverse bind matrices and four-influence linear blend skin. All exported UV-split vertices compared to original-index Armature-only linear references. No morph targets.','samples':rows}
(P/'export-parity-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
assert report['ok']
