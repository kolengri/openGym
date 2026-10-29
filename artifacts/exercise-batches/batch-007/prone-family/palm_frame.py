"""Source-derived flat palm frame, no posed binding or topology change."""
import numpy as np
from mathutils import Vector

def prepare(a):
 result={}
 for side,sg in [('Left',1),('Right',-1)]:
  h=a.heads[side+'Hand'];axis=(a.tails[side+'Hand']-h).normalized();names={g.index:g.name for g in a.body.vertex_groups};idx=[]
  for v in a.body.data.vertices:
   t=(v.co-h).dot(axis)
   if sum(g.weight for g in v.groups if names[g.group]==side+'Hand')>.8 and .025<t<.105 and v.normal.dot(Vector((-sg,0,0)))>.45:idx.append(v.index)
  pp=np.array([a.body.data.vertices[i].co[:]for i in idx]);center=pp.mean(axis=0);_,_,vv=np.linalg.svd(pp-center,full_matrices=False);normal=Vector(vv[-1]);normal*=1 if normal.dot(Vector((-sg,0,0)))>0 else-1
  result[side]={'source_ids':idx,'normal':normal,'center':center.tolist(),'plane_residual_mm':float(np.max(abs((pp-center)@np.array(normal)))*1000)}
 return result

def hand(a,side,direction,normal,frames):
 return (a.frame(direction,normal)@a.frame(a.tails[side+'Hand']-a.heads[side+'Hand'],frames[side]['normal']).transposed()).to_quaternion()@a.rest[side+'Hand'].to_quaternion()
