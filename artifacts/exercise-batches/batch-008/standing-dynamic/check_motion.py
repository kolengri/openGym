"""Frozen continuous-joint, internal-foot and complete triangle checks."""
import numpy as np, math
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from triangle_intersection import intersect

class MotionChecks:
 def __init__(self,b,r):
  self.b=b;self.r=r;self.previous={};self.maximum_step=0.;self.edge_reference={};self.edge_range=[1.,1.];self.maximum_toe_error=0.;self.crossings=0
  self.rest=np.array([v.co[:]for v in b.data.vertices]);names={g.index:g.name for g in b.vertex_groups}
  def ids(side,parts):return {v.index for v in b.data.vertices if sum(g.weight for g in v.groups if any(names[g.group].startswith(side+p)for p in parts))>.5}
  b.data.calc_loop_triangles();tri=[list(t.vertices)for t in b.data.loop_triangles];self.armtri={};self.legtri={};self.edges={};self.ankle_edges={};self.native_ankle_reference={};self.ankle_reference={};self.ankle_range=[1.,1.];self.native_ankle_range=[1.,1.]
  for side,sign in [('Left',1),('Right',-1)]:
   arm=ids(side,['Arm','ForeArm','Hand','Index','Middle','Ring','Little','Thumb']);leg=ids(side,['UpLeg','Leg','Foot','ToeBase']);foot=ids(side,['Foot','ToeBase']);forefoot={i for i in foot if self.rest[i,2]<.06 and self.rest[i,1]<-.025};self.edges[side]=np.array([e.vertices[:]for e in b.data.edges if all(i in forefoot for i in e.vertices)],int)
   ankle={i for i in leg if .07<self.rest[i,2]<.22};self.ankle_edges[side]=np.array([e.vertices[:]for e in b.data.edges if all(i in ankle for i in e.vertices)],int)
   assert len(self.edges[side])>20 and len(self.ankle_edges[side])>20
   self.armtri[side]=[t for t in tri if any(i in arm for i in t)];self.legtri[side]=[t for t in tri if any(i in leg for i in t)]
 def sample(self,p,f,ID,native_p=None):
  fail=[];foot={};knee={};step={};vec=[Vector(q)for q in p]
  arms={s:BVHTree.FromPolygons(vec,t)for s,t in self.armtri.items()};legs={s:BVHTree.FromPolygons(vec,t)for s,t in self.legtri.items()};crossings={}
  for arm in arms:
   for leg in legs:
    count=0
    for ai,li in arms[arm].overlap(legs[leg]):
     aa,ll=self.armtri[arm][ai],self.legtri[leg][li]
     if set(aa)&set(ll):continue
     if intersect([vec[i]for i in aa],[vec[i]for i in ll]):count+=1
    crossings[arm+'_arm_to_'+leg+'_leg']=count;self.crossings+=count
    if count:fail.append(f'frame{f}: {arm}/{leg} actual triangle crossings {count}')
  for side in arms:
   edges=self.edges[side];lens=np.linalg.norm(p[edges[:,1]]-p[edges[:,0]],axis=1)
   if f==0:self.edge_reference[side]=lens.copy()
   ratio=lens/self.edge_reference[side];lo=float(ratio.min());hi=float(ratio.max());self.edge_range=[min(self.edge_range[0],lo),max(self.edge_range[1],hi)]
   if lo<.85 or hi>1.15:fail.append(f'frame{f}: {side} forefoot edge ratio outside frozen15percentQC {lo}/{hi}')
   leg=self.r.pose.bones[side+'Leg'];fq=self.r.pose.bones[side+'Foot'].matrix.to_quaternion();tq=self.r.pose.bones[side+'ToeBase'].matrix.to_quaternion()
   toe=(fq.inverted()@tq).to_matrix();rest=(self.r.data.bones[side+'Foot'].matrix_local.to_quaternion().inverted()@self.r.data.bones[side+'ToeBase'].matrix_local.to_quaternion()).to_matrix();err=float(np.max(abs(np.array(toe)-np.array(rest))));self.maximum_toe_error=max(self.maximum_toe_error,err)
   if err>2e-5:fail.append(f'frame{f}: {side} forefoot rotates relativeFoot beyond float tolerance {err}')
   for name in [side+'UpLeg',side+'Leg',side+'Foot',side+'ToeBase']:
    q=self.r.pose.bones[name].matrix.to_quaternion();ang=0.
    if name in self.previous:
     ang=math.degrees(self.previous[name].rotation_difference(q).angle);ang=min(ang,360-ang);self.maximum_step=max(self.maximum_step,ang)
     if ang>45:fail.append(f'frame{f}: {name} orientation step exceeds45degrees {ang}')
    step[name]=ang;self.previous[name]=q.copy()
   hip=self.r.pose.bones[side+'UpLeg'].head;kn=leg.head;ank=self.r.pose.bones[side+'Foot'].head;knee[side]=180-math.degrees((hip-kn).angle(ank-kn))
   if ID=='4437'and knee[side]>130.05:fail.append(f'frame{f}: {side} total knee flexion above130degreebound {knee[side]}')
   ae=self.ankle_edges[side];al=np.linalg.norm(p[ae[:,1]]-p[ae[:,0]],axis=1);nl=np.linalg.norm(native_p[ae[:,1]]-native_p[ae[:,0]],axis=1)if native_p is not None else al
   if f==0:self.ankle_reference[side]=al.copy();self.native_ankle_reference[side]=nl.copy()
   ar=al/self.ankle_reference[side];nr=nl/self.native_ankle_reference[side];alo,ahi=float(ar.min()),float(ar.max());nlo,nhi=float(nr.min()),float(nr.max());self.ankle_range=[min(self.ankle_range[0],alo),max(self.ankle_range[1],ahi)];self.native_ankle_range=[min(self.native_ankle_range[0],nlo),max(self.native_ankle_range[1],nhi)]
   if min(alo,nlo)<.65 or max(ahi,nhi)>1.35:fail.append(f'frame{f}: {side} internal ankle edge ratio exceeds frozen35percentQC {alo}/{ahi}/{nlo}/{nhi}')
   foot[side]={'mixed_ankle_edge_ratio_min':alo,'mixed_ankle_edge_ratio_max':ahi,'native_mixed_ankle_edge_ratio_min':nlo,'native_mixed_ankle_edge_ratio_max':nhi,'forefoot_edge_ratio_from_planted_min':lo,'forefoot_edge_ratio_from_planted_max':hi,'rigid_forefoot_relative_matrix_error':err}
  return {'actual_total_knee_flexion_degrees':knee,'foot_shape':foot,'orientation_step_degrees':step,'triangle_crossings':crossings},fail
