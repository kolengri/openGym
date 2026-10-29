"""Decode one asset's actual GLB skin/normal equation for controlled proof."""
import ast,json
from pathlib import Path
import numpy as np
from mathutils import Matrix,Quaternion,Vector
from glb_normals import read_glb,decode,unit
class Runtime:
 def __init__(self,path):
  self.doc,self.binary=read_glb(path);d=self.doc
  self.primitive=d['meshes'][0]['primitives'][0];p=self.primitive;a=p['attributes'];self.pos=self.acc(a['POSITION']);self.normal=self.acc(a['NORMAL']);self.source=self.acc(a['_SOURCE_INDEX']).ravel().astype(int);self.joints=self.acc(a['JOINTS_0']).astype(int);self.weights=self.acc(a['WEIGHTS_0']);self.tri=self.acc(p['indices']).ravel().reshape(-1,3);self.ibm=self.acc(d['skins'][0]['inverseBindMatrices']).reshape(-1,4,4).transpose(0,2,1);self.parents={j:i for i,n in enumerate(d['nodes']) for j in n.get('children',[])}
 def acc(self,i):return decode(self.doc,self.binary,i)
 def values(self,t):
  values={}
  for ch in self.doc['animations'][0]['channels']:
   s=self.doc['animations'][0]['samplers'][ch['sampler']];times=self.acc(s['input']).ravel();out=self.acc(s['output']);i=max(0,min(int(np.searchsorted(times,t,side='right'))-1,len(times)-1));j=min(i+1,len(times)-1);f=np.clip((t-times[i])/(times[j]-times[i]),0,1) if times[j]>times[i] else 0;path=ch['target']['path']
   if path=='rotation':
    x,y,z,w=out[i];x2,y2,z2,w2=out[j];q=Quaternion((w,x,y,z)).slerp(Quaternion((w2,x2,y2,z2)),float(f));v=[q.x,q.y,q.z,q.w]
   else:v=(out[i]*(1-f)+out[j]*f).tolist()
   values.setdefault(ch['target']['node'],{})[path]=v
  return values
 def sample(self,t):
  values=self.values(t);mats={}
  def world(i):
   if i not in mats:
    n=self.doc['nodes'][i];v=values.get(i,{})
    if 'matrix'in n:m=np.array(n['matrix']).reshape(4,4).T
    else:
     r=v.get('rotation',n.get('rotation',[0,0,0,1]));m=np.array(Matrix.LocRotScale(Vector(v.get('translation',n.get('translation',[0,0,0]))),Quaternion((r[3],r[0],r[1],r[2])),Vector(v.get('scale',n.get('scale',[1,1,1])))),float)
    mats[i]=(world(self.parents[i]) if i in self.parents else np.eye(4))@m
   return mats[i]
  transforms=np.array([world(i) for i in self.doc['skins'][0]['joints']])@self.ibm
  blend=sum(self.weights[:,k,None,None]*transforms[self.joints[:,k]] for k in range(4));p=self.pos.copy().astype(float);normal=self.normal.copy().astype(float);morph_weights=self.doc['meshes'][0].get('weights',[])
  for node,n in enumerate(self.doc['nodes']):
   if n.get('mesh')==0:morph_weights=values.get(node,{}).get('weights',n.get('weights',morph_weights));break
  for w,target in zip(morph_weights,self.primitive.get('targets',[])):
   p+=w*self.acc(target['POSITION'])
   if 'NORMAL'in target:normal+=w*self.acc(target['NORMAL'])
  xyz=np.einsum('nij,nj->ni',blend,np.column_stack((p,np.ones(len(p)))))[:,:3];normal_raw=np.einsum('nij,nj->ni',blend[:,:3,:3],normal);normal_lengths=np.linalg.norm(normal_raw,axis=1);normal=unit(normal_raw)
  tri=self.tri;cross=np.cross(xyz[tri[:,1]]-xyz[tri[:,0]],xyz[tri[:,2]]-xyz[tri[:,0]]);total=np.zeros((10582,3))
  for col in range(3):np.add.at(total,self.source[tri[:,col]],cross)
  return {'positions':xyz,'normals':normal,'geometric_normals':unit(total[self.source]),'blend':blend,'morph_weights':morph_weights,'joint_world':mats,'normal_lengths':normal_lengths}
