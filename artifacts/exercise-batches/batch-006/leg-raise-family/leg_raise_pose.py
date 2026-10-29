"""Four source-text lying-leg records on the original51-bone source rig."""
import math
import numpy as np
from mathutils import Matrix,Quaternion,Vector
POSTURE={'pelvis':-108.6706671531987,'spine':-81.90411001127993,'chest':-85.,'neck_flat':-100.,'head_flat':-90.,'neck_up':-85.,'head_up':-80.,'root_z':.10501975631713867,'wrist_z':.027}
_palm={}

def source_palm(a,side,sign):
 if side not in _palm:
  g=a.body.vertex_groups[side+'Hand'].index
  p=np.array([v.co[:]for v in a.body.data.vertices if any(k.group==g and k.weight>.6 for k in v.groups)])
  _,axes=np.linalg.eigh(np.cov(p.T));n=Vector(axes[:,0])
  if n.x*sign>0:n=-n
  _palm[side]=n
 return _palm[side]

def segment(a,bone,direction):
 source=a.tails[bone]-a.heads[bone]
 delta=(a.frame(direction,Vector((1,0,0)))@a.frame(source,Vector((1,0,0))).transposed()).to_quaternion()
 return delta@a.rest[bone].to_quaternion(),delta

def pose(a,frame,exercise_id,posture=None):
 p=POSTURE if posture is None else posture;exercise_id=str(exercise_id);swing=math.sin(2*math.pi*frame/150)
 desired={};root=Vector((0,0,p['root_z']));head_up=exercise_id=='4001'
 pitches=[p['pelvis'],p['spine'],p['chest'],p['neck_up']if head_up else p['neck_flat'],p['head_up']if head_up else p['head_flat']]
 for name,pitch in zip(['Hips','Spine','Spine1','Neck','Head'],pitches):
  parent=a.rig.data.bones[name].parent
  head=root if parent is None else desired[parent.name]@a.rest[parent.name].inverted()@a.heads[name]
  q=a.rx(pitch)@a.rest[name].to_quaternion();desired[name]=Matrix.Translation(head)@q.to_matrix().to_4x4()
 leg_angles={}
 for side,sign in [('Left',1),('Right',-1)]:
  if exercise_id=='5106':angle=86+4*sign*swing;reach=(1+sign*swing)/2;plantar=10+35*reach;toe=6*reach
  else:angle=4+86*(1+sign*swing)/2;reach=0;plantar=22;toe=0
  leg_angles[side]=angle
  u=Vector((0,-math.cos(math.radians(angle)),math.sin(math.radians(angle))))
  hip=desired['Hips']@a.rest['Hips'].inverted()@a.heads[side+'UpLeg'];knee=hip+u*a.length[side+'UpLeg'];ankle=knee+u*a.length[side+'Leg']
  for bone,start,end in [(side+'UpLeg',hip,knee),(side+'Leg',knee,ankle)]:
   q,delta=segment(a,bone,end-start);desired[bone]=Matrix.Translation(start)@q.to_matrix().to_4x4()
  _,leg_delta=segment(a,side+'Leg',u)
  footq=leg_delta@a.rx(plantar)@a.rest[side+'Foot'].to_quaternion();desired[side+'Foot']=Matrix.Translation(ankle)@footq.to_matrix().to_4x4()
  toehead=desired[side+'Foot']@a.rest[side+'Foot'].inverted()@a.heads[side+'ToeBase'];toeq=leg_delta@a.rx(plantar+toe)@a.rest[side+'ToeBase'].to_quaternion();desired[side+'ToeBase']=Matrix.Translation(toehead)@toeq.to_matrix().to_4x4()
  chest_delta=desired['Spine1'].to_quaternion()@a.rest['Spine1'].to_quaternion().inverted();shoulder=side+'Shoulder';sh=desired['Spine1']@a.rest['Spine1'].inverted()@a.heads[shoulder]
  desired[shoulder]=Matrix.Translation(sh)@(chest_delta@a.rest[shoulder].to_quaternion()).to_matrix().to_4x4();arm_head=desired[shoulder]@a.rest[shoulder].inverted()@a.heads[side+'Arm']
  wrist=Vector((sign*p.get('wrist_x',.225),arm_head.y-(a.length[side+'Arm']+a.length[side+'ForeArm'])*.975,p['wrist_z']))
  pole=arm_head+Vector((sign*.17,-.25,.02));elbow,wrist=a.two_joint(arm_head,wrist,a.length[side+'Arm'],a.length[side+'ForeArm'],pole)
  for bone,start,end in [(side+'Arm',arm_head,elbow),(side+'ForeArm',elbow,wrist)]:
   q=chest_delta@a.orient(bone,chest_delta.inverted()@(end-start));desired[bone]=Matrix.Translation(start)@q.to_matrix().to_4x4()
  bone=side+'Hand';hand_delta=(a.frame(Vector((0,-1,0)),Vector((0,0,-1)))@a.frame(a.tails[bone]-a.heads[bone],source_palm(a,side,sign)).transposed()).to_quaternion();handq=hand_delta@a.rest[bone].to_quaternion();desired[bone]=Matrix.Translation(wrist)@handq.to_matrix().to_4x4()
 for name,(head,tail,parent,digit,index)in a.finger_specs.items():desired[name]=desired[parent]@a.rest[parent].inverted()@a.rest[name]
 for bone in a.rig.pose.bones:
  parent=bone.parent.name if bone.parent else None
  bone.matrix_basis=a.rest[bone.name].inverted()@(a.rest[parent]@desired[parent].inverted()if parent else Matrix.Identity(4))@desired[bone.name]
 return desired,{'leg_elevation_degrees':leg_angles,'root_z':p['root_z'],'head_up':head_up}
