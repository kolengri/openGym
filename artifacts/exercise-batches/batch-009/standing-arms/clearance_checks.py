"""Exact skin crossings with complete source-domain diagnostics, no hidden exclusions."""
from collections import Counter
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from self_clearance import SelfClearance as AcceptedSelfClearance
from triangle_intersection import intersect
class SelfClearance(AcceptedSelfClearance):
 def __init__(self,body,rig):
  super().__init__(body,rig);self.rest=np.array([v.co[:]for v in body.data.vertices]);names={g.index:g.name for g in body.vertex_groups};self.dominant=[names[max(v.groups,key=lambda g:g.weight).group]for v in body.data.vertices];self.heads={s:np.array(rig.data.bones[s+'Arm'].head_local)for s in ['Left','Right']};self.axes={s:np.array(rig.data.bones[s+'Arm'].tail_local)-self.heads[s]for s in self.heads}
 def sample(self,p):
  v=[Vector(q)for q in p];result={};fail=[]
  for label,A,B in [('left_arm_right_arm',self.arm['Left'],self.arm['Right']),('left_distal_arm_torso_head',self.distal['Left'],self.torso),('right_distal_arm_torso_head',self.distal['Right'],self.torso)]:
   at=BVHTree.FromPolygons(v,A,all_triangles=True);bt=BVHTree.FromPolygons(v,B,all_triangles=True);cross=[];parts=Counter();aid=set();bid=set()
   for ai,bi in at.overlap(bt):
    a,b=A[ai],B[bi]
    if set(a)&set(b):continue
    if intersect([v[i]for i in a],[v[i]for i in b]):
     cross.append([a,b]);aid.update(a);bid.update(b);parts[Counter(self.dominant[i]for i in a).most_common(1)[0][0]+'/'+Counter(self.dominant[i]for i in b).most_common(1)[0][0]]+=1
   involved=sorted(set(i for t in A for i in t));minimum=min(bt.find_nearest(v[i])[3]for i in involved);domains={}
   for n,ids in [('A',aid),('B',bid)]:
    ids=sorted(ids);domains[n]={'source_ids':ids,'source_bounds_m':[self.rest[ids].min(0).tolist(),self.rest[ids].max(0).tolist()]if ids else None,'posed_bounds_m':[p[ids].min(0).tolist(),p[ids].max(0).tolist()]if ids else None}
   result[label]={'exact_triangle_crossings':len(cross),'minimum_vertex_surface_distance_m':minimum,'first_crossing_source_faces':cross[:5],'dominant_bone_pairs':dict(parts),'crossing_domains':domains};self.crossings+=len(cross)
   if cross:fail.append(label+' source-bound actual skin crossings '+str(len(cross)))
  return result,fail
