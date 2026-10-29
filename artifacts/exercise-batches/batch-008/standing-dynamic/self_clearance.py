"""Source-bound mutually crossing arms and distal-arm/body clearance gates."""
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from triangle_intersection import intersect
class SelfClearance:
 def __init__(self,body,rig):
  names={g.index:g.name for g in body.vertex_groups};R=np.array([v.co[:]for v in body.data.vertices]);body.data.calc_loop_triangles();T=np.array([t.vertices[:]for t in body.data.loop_triangles],int);self.arm={};self.distal={};self.ids={};self.crossings=0
  torso=set(v.index for v in body.data.vertices if sum(g.weight for g in v.groups if names[g.group]in['Spine','Spine1','Neck','Head','Hips'])>.5);self.torso=T[np.all(np.isin(T,list(torso)),axis=1)].tolist()
  for side in ['Left','Right']:
   ids=set();distal=set();origin=np.array(rig.data.bones[side+'Arm'].head_local)
   for v in body.data.vertices:
    arm=sum(g.weight for g in v.groups if names[g.group].startswith(side)and any(k in names[g.group]for k in ['Arm','ForeArm','Hand','Index','Middle','Ring','Little','Thumb']))
    if arm>.5:
     ids.add(v.index)
     if np.linalg.norm(R[v.index]-origin)>.08:distal.add(v.index)
   self.ids[side]=sorted(ids);self.arm[side]=T[np.all(np.isin(T,list(ids)),axis=1)].tolist();self.distal[side]=T[np.all(np.isin(T,list(distal)),axis=1)].tolist()
 def sample(self,p):
  v=[Vector(q)for q in p];result={};fail=[]
  for label,A,B in [('left_arm_right_arm',self.arm['Left'],self.arm['Right']),('left_distal_arm_torso_head',self.distal['Left'],self.torso),('right_distal_arm_torso_head',self.distal['Right'],self.torso)]:
   at=BVHTree.FromPolygons(v,A,all_triangles=True);bt=BVHTree.FromPolygons(v,B,all_triangles=True);cross=[]
   for ai,bi in at.overlap(bt):
    a,b=A[ai],B[bi]
    if set(a)&set(b):continue
    if intersect([v[i]for i in a],[v[i]for i in b]):cross.append([a,b])
   involved=sorted(set(i for tri in A for i in tri));minimum=min(bt.find_nearest(v[i])[3]for i in involved);result[label]={'exact_triangle_crossings':len(cross),'minimum_vertex_surface_distance_m':minimum,'first_crossing_source_faces':cross[:5]};self.crossings+=len(cross)
   if cross:fail.append(label+' source-bound actual skin crossings '+str(len(cross)))
  return result,fail
