"""1843: one gentle head turn, then outside approaches to chin and occiput.

The accepted1368 seated base and binding are immutable. Local arm quaternions
share a stable anatomical elbow frame; fingers remain relaxed and connected.
"""
import math
from mathutils import Matrix,Quaternion,Vector
BASE={};GOAL={};PASS={};ANCHORS={};TARGETS={}

def smooth(t):
 t=max(0.,min(1.,t));return t*t*(3-2*t)

def install(a):
 BASE.update({pb.name:pb.matrix.copy()for pb in a.rig.pose.bones})
 accepted={n:m.copy()for n,m in BASE.items()}
 # Only the seated lower body is reused exactly. Move the relaxed hands
 # outside the thighs and solve a coherent neutral humeral hinge, because
 # the accepted thigh-resting arm pose crosses the side trunk here.
 for side,sign in [('Left',1),('Right',-1)]:
  sh=BASE[side+'Arm'].translation;w=Vector((sign*.34,-.12,.31));el,w=a.two_joint(sh,w,a.length[side+'Arm'],a.length[side+'ForeArm'],Vector((sign*.45,.03,.42)));u=el-sh;l=w-el;ou=a.tails[side+'Arm']-a.heads[side+'Arm'];ol=a.tails[side+'ForeArm']-a.heads[side+'ForeArm'];hinge=u.cross(l);orig=ou.cross(ol)
  for n,h,v,ov in [(side+'Arm',sh,u,ou),(side+'ForeArm',el,l,ol)]:BASE[n]=Matrix.Translation(h)@((a.frame(v,hinge)@a.frame(ov,orig).transposed()).to_quaternion()@a.rest[n].to_quaternion()).to_matrix().to_4x4()
  BASE[side+'Hand'].translation=w
 for n,(_,_,parent,_,_)in a.finger_specs.items():BASE[n]=BASE[parent]@accepted[parent].inverted()@accepted[n]
 for side,sign in [('Left',1),('Right',-1)]:
  hand=side+'Hand';long=(a.tails[hand]-a.heads[hand]).normalized();desired=a.heads[hand]+long*.075+Vector((-sign*.02,0,0))
  ids=[v.index for v in a.body.data.vertices if sum(g.weight for g in v.groups if a.body.vertex_groups[g.group].name==hand)>.8]
  ANCHORS[side]=min((a.body.data.vertices[i]for i in ids),key=lambda v:(v.co-desired).length).co.copy()
 d=head(a,32.)
 # The chin pad stays below the face; the other palm lies on the occiput.
 for side,sign,target,direction,normal,pole in [
  ('Left',1,Vector((0,-.107,1.563)),Vector((-1,0,.10)),Vector((0,.4,.92)),Vector((.52,-.22,.64))),
  ('Right',-1,Vector((0,.087,1.685)),Vector((0,0,1)),Vector((0,-1,0)),Vector((-.65,-.10,.65)))]:
  H=d['Head']@a.rest['Head'].inverted();target=H@target;direction=H.to_3x3()@direction;normal=H.to_3x3()@normal
  q=a.palm_rotation(side,direction,normal);normal.normalize();wrist=target-normal*.0015-q@(ANCHORS[side]-a.heads[side+'Hand'])
  shoulder=BASE[side+'Arm'].translation;elbow,actual=a.two_joint(shoulder,wrist,a.length[side+'Arm'],a.length[side+'ForeArm'],pole)
  assert (actual-wrist).length<1e-6,(side,'unreachable')
  upper=elbow-shoulder;lower=wrist-elbow;orig_upper=a.tails[side+'Arm']-a.heads[side+'Arm'];orig_lower=a.tails[side+'ForeArm']-a.heads[side+'ForeArm'];hinge=upper.cross(lower);original=orig_upper.cross(orig_lower)
  for n,h,v,orig in [(side+'Arm',shoulder,upper,orig_upper),(side+'ForeArm',elbow,lower,orig_lower)]:
   aq=(a.frame(v,hinge)@a.frame(orig,original).transposed()).to_quaternion()@a.rest[n].to_quaternion();d[n]=Matrix.Translation(h)@aq.to_matrix().to_4x4()
  d[side+'Hand']=Matrix.Translation(wrist)@(q@a.rest[side+'Hand'].to_quaternion()).to_matrix().to_4x4();TARGETS[side]=target
 # Fit only a rigid hand translation to the actual scalp/jaw surface. No
 # vertex deformation, head flattening or body-binding fit is introduced.
 import bpy
 from mathutils.bvhtree import BVHTree
 headids={v.index for v in a.body.data.vertices if v.co.z>1.545 and abs(v.co.x)<.15}
 a.body.data.calc_loop_triangles();headfaces=[t.vertices[:]for t in a.body.data.loop_triangles if all(i in headids for i in t.vertices)]
 for side,sign in [('Left',1),('Right',-1)]:
  normal=(d['Head']@a.rest['Head'].inverted()).to_3x3()@Vector((0,.4,.92)if side=='Left'else(0,-1,0));normal.normalize();whole=[v.index for v in a.body.data.vertices if sum(g.weight for g in v.groups if a.body.vertex_groups[g.group].name.startswith(tuple(side+n for n in ['Hand','Thumb','Index','Middle','Ring','Little'])))>.7]
  for iteration in range(8):
   for n,(_,_,parent,_,_)in a.finger_specs.items():d[n]=d[parent]@BASE[parent].inverted()@BASE[n]
   for pb in a.rig.pose.bones:
    par=pb.parent.name if pb.parent else None;pb.matrix_basis=a.rest[pb.name].inverted()@(a.rest[par]@d[par].inverted()if par else Matrix.Identity(4))@d[pb.name]
   bpy.context.view_layer.update();ev=a.body.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh();pp=[v.co.copy()for v in me.vertices];ev.to_mesh_clear();tree=BVHTree.FromPolygons(pp,headfaces);minimum=1.
   for i in whole:
    co,no,fi,dist=tree.find_nearest(pp[i]);minimum=min(minimum,(pp[i]-co).dot(no))
   if minimum>=.001:break
   w=d[side+'Hand'].translation-normal*min(.012,.0015-minimum);sh=BASE[side+'Arm'].translation;el,w=a.two_joint(sh,w,a.length[side+'Arm'],a.length[side+'ForeArm'],Vector((.52,-.22,.64))if side=='Left'else Vector((-.65,-.10,.65)));u=el-sh;l=w-el;ou=a.tails[side+'Arm']-a.heads[side+'Arm'];ol=a.tails[side+'ForeArm']-a.heads[side+'ForeArm'];hinge=u.cross(l);orig=ou.cross(ol)
   for n,h,v,ov in [(side+'Arm',sh,u,ou),(side+'ForeArm',el,l,ol)]:d[n]=Matrix.Translation(h)@((a.frame(v,hinge)@a.frame(ov,orig).transposed()).to_quaternion()@a.rest[n].to_quaternion()).to_matrix().to_4x4()
   d[side+'Hand'].translation=w
 GOAL.update(d)
 for side,sign in [('Left',1),('Right',-1)]:
  sh=BASE[side+'Arm'].translation;w=Vector((sign*.45,-.16,.55))if side=='Left'else Vector((sign*.53,.12,.62));el,w=a.two_joint(sh,w,a.length[side+'Arm'],a.length[side+'ForeArm'],Vector((sign*.56,.05,.44)));u=el-sh;l=w-el;ou=a.tails[side+'Arm']-a.heads[side+'Arm'];ol=a.tails[side+'ForeArm']-a.heads[side+'ForeArm'];hinge=u.cross(l);orig=ou.cross(ol)
  for n,h,v,ov in [(side+'Arm',sh,u,ou),(side+'ForeArm',el,l,ol)]:PASS[n]=Matrix.Translation(h)@((a.frame(v,hinge)@a.frame(ov,orig).transposed()).to_quaternion()@a.rest[n].to_quaternion()).to_matrix().to_4x4()

def head(a,degrees):
 d={n:m.copy()for n,m in BASE.items()}
 for n,total in [('Neck',degrees*.35),('Head',degrees)]:
  parent=a.rig.data.bones[n].parent.name;h=d[parent]@a.rest[parent].inverted()@a.heads[n]
  deformation=BASE[n].to_quaternion()@a.rest[n].to_quaternion().inverted();q=deformation@Quaternion(Vector((0,0,1)),math.radians(total))@a.rest[n].to_quaternion();d[n]=Matrix.Translation(h)@q.to_matrix().to_4x4()
 return d

def pose(a,t):
 tau=min(t,5-t);turn=smooth(tau/.85);d=head(a,32*turn)
 for side,sign in [('Left',1),('Right',-1)]:
  progress=smooth((tau-.55)/1.4);wrist_turn=smooth((tau-1.15)/.75)
  ua=side+'Arm';fa=side+'ForeArm';ha=side+'Hand';q0=BASE[ua].to_quaternion();q1=GOAL[ua].to_quaternion();qmid=PASS[ua].to_quaternion();pivot=.43
  q=q0.slerp(qmid,progress/pivot)if progress<pivot else qmid.slerp(q1,(progress-pivot)/(1-pivot))
  if side=='Right'and progress<.6:q=Quaternion(Vector((0,1,0)),math.radians(35*math.sin(math.pi*progress/.6)**2))@q
  shoulder=BASE[ua].translation;elbow=shoulder+q@(a.rest[ua].to_quaternion().inverted()@(a.heads[fa]-a.heads[ua]))
  local0=q0.inverted()@BASE[fa].to_quaternion();local1=q1.inverted()@GOAL[fa].to_quaternion();localmid=qmid.inverted()@PASS[fa].to_quaternion();local=local0.slerp(localmid,progress/pivot)if progress<pivot else localmid.slerp(local1,(progress-pivot)/(1-pivot));fq=q@local
  wrist=elbow+fq@(a.rest[fa].to_quaternion().inverted()@(a.heads[ha]-a.heads[fa]));h0=BASE[fa].to_quaternion().inverted()@BASE[ha].to_quaternion();h1=GOAL[fa].to_quaternion().inverted()@GOAL[ha].to_quaternion();hq=fq@h0.slerp(h1,wrist_turn)
  for n,h,rot in [(ua,shoulder,q),(fa,elbow,fq),(ha,wrist,hq)]:d[n]=Matrix.Translation(h)@rot.to_matrix().to_4x4()
 for n,(_,_,parent,_,_)in a.finger_specs.items():
  # Retain the accepted open relaxed finger pose in hand-local space.
  d[n]=d[parent]@BASE[parent].inverted()@BASE[n]
 return d
