"""Two source-distinct floor crunches on one unchanged source rig.

Grounded bent legs are an authored choice for4354 and explicit for0006.
Arm/hand math reuses the source-frame transport and occiput construction from
batch005; no tabletop/pedal targets or pose-dependent old buffers are imported.
"""
import math
import numpy as np
from mathutils import Matrix,Quaternion,Vector
PALMS={}
ROOT_Z=.13
ANKLE_Y=-.36
HEEL_WRIST_LATERAL=0.1136217348292371

def palm_normal(a,side,sign):
 if side not in PALMS:
  group=a.body.vertex_groups[side+'Hand'].index
  points=np.array([v.co[:]for v in a.body.data.vertices if any(g.group==group and g.weight>.6 for g in v.groups)])
  _,axes=np.linalg.eigh(np.cov(points.T));normal=Vector(axes[:,0])
  if normal.x*sign>0:normal=-normal
  PALMS[side]=normal
 return PALMS[side]

def segment(a,name,direction,source_axis,target_axis):
 q=(a.frame(direction,target_axis)@a.frame(a.tails[name]-a.heads[name],source_axis).transposed()).to_quaternion()
 return q@a.rest[name].to_quaternion()

def pose(a,frame,id,root_z=None):
 swing=math.sin(2*math.pi*frame/150);effort=swing*swing
 root=Vector((0,0,ROOT_Z if root_z is None else root_z))
 d={}
 for i,name in enumerate(['Hips','Spine','Spine1','Neck','Head']):
  parent=a.rig.data.bones[name].parent
  h=root if parent is None else d[parent.name]@a.rest[parent.name].inverted()@a.heads[name]
  pitch=[-90,-89,-66,-62,-62][i]
  if id=='0006':
   # Lateral upper-trunk crunch about the supine anterior/posterior axis.
   bend=[0,0,19,19,19][i]*swing;twist=0
  else:
   pitch+=[0,0,10,10,10][i]*effort;bend=0;twist=[0,0,29,29,29][i]*swing
  q=a.rx(pitch)@Quaternion(Vector((0,1,0)),math.radians(bend))@Quaternion(Vector((0,0,1)),math.radians(twist))@a.rest[name].to_quaternion()
  d[name]=Matrix.Translation(h)@q.to_matrix().to_4x4()
 knees={};ankles={}
 for side,sign in [('Left',1),('Right',-1)]:
  hip=d['Hips']@a.rest['Hips'].inverted()@a.heads[side+'UpLeg']
  fq=a.rz(-sign*8)
  ankle=Vector((sign*.17,ANKLE_Y,a.sole_height(side,fq)-.003+.001))
  knee,ankle=a.two_joint(hip,ankle,a.length[side+'UpLeg'],a.length[side+'Leg'],hip+Vector((sign*.13,0,1)))
  source_axis=(a.tails[side+'UpLeg']-a.heads[side+'UpLeg']).cross(a.tails[side+'Leg']-a.heads[side+'Leg']).normalized()
  target_axis=(knee-hip).cross(ankle-knee).normalized()
  for name,start,end in [(side+'UpLeg',hip,knee),(side+'Leg',knee,ankle)]:
   q=segment(a,name,end-start,source_axis,target_axis);d[name]=Matrix.Translation(start)@q.to_matrix().to_4x4()
  d[side+'Foot']=Matrix.Translation(ankle)@(fq@a.rest[side+'Foot'].to_quaternion()).to_matrix().to_4x4()
  d[side+'ToeBase']=d[side+'Foot']@a.rest[side+'Foot'].inverted()@a.rest[side+'ToeBase']
  knees[side]=knee;ankles[side]=ankle
 for side,sign in [('Left',1),('Right',-1)]:
  chest=d['Spine1']@a.rest['Spine1'].inverted();cq=chest.to_quaternion()
  shoulder=side+'Shoulder';d[shoulder]=chest@a.rest[shoulder]
  armhead=d[shoulder]@a.rest[shoulder].inverted()@a.heads[side+'Arm']
  if id=='4354':
   head=d['Head']@a.rest['Head'].inverted();hq=head.to_quaternion()
   wrist=head@Vector((sign*.208,.130,1.66));lateral=hq@Vector((sign,0,0));back=hq@Vector((0,1,0));up=hq@Vector((0,0,1))
   openpole=armhead+lateral*.55+back*.03+up*.04
   approach=max(0,-sign*swing);other='Right'if side=='Left'else'Left';pole=openpole.lerp(knees[other],.85*approach)
   hand=side+'Hand';handq=(a.frame(-lateral+up*.12,-back)@a.frame(a.tails[hand]-a.heads[hand],palm_normal(a,side,sign)).transposed()).to_quaternion()@a.rest[hand].to_quaternion()
   palm_direction=(handq@a.rest[hand].to_quaternion().inverted())@(a.heads[side+'Middle1']-a.heads[hand])
   def elbow_at(amount):return a.two_joint(armhead,wrist,a.length[side+'Arm'],a.length[side+'ForeArm'],openpole.lerp(pole,amount))[0]
   if (wrist-elbow_at(1)).angle(palm_direction)>math.radians(35):
    lower,upper=0.,1.
    for _ in range(18):
     middle=(lower+upper)/2
     if (wrist-elbow_at(middle)).angle(palm_direction)<=math.radians(35):lower=middle
     else:upper=middle
    pole=openpole.lerp(pole,lower)
  else:
   active=max(0,sign*swing)
   # Authored source-cue resolution: arms hover alongside the torso toward
   # the feet, parallel to ground. Lateral flexion supplies the heel reach;
   # there is no T-pose sweep between sides. Fingers approach the heel.
   reach=(a.length[side+'Arm']+a.length[side+'ForeArm'])*.997
   neutral_x=sign*.37
   dx=neutral_x-armhead.x
   neutral=Vector((neutral_x,armhead.y-math.sqrt(max(.01,reach*reach-dx*dx-.025*.025)),armhead.z-.025))
   heel=ankles[side]+Vector((0,.060,-.065))
   target=heel+Vector((sign*HEEL_WRIST_LATERAL,.195,.020))
   wrist=neutral.lerp(target,active)
   pole=armhead+Vector((sign*.35,-.12,.30))
   hand=side+'Hand'
   direction=Vector((-sign*(.15+.30*active),-1,0)).normalized()
   # Palms face the floor; fingers point diagonally toward the outer heel.
   # Wrists and forearms remain outside the calf instead of crossing it.
   handq=(a.frame(direction,Vector((0,0,-1)))@a.frame(a.tails[hand]-a.heads[hand],palm_normal(a,side,sign)).transposed()).to_quaternion()@a.rest[hand].to_quaternion()
  elbow,wrist=a.two_joint(armhead,wrist,a.length[side+'Arm'],a.length[side+'ForeArm'],pole)
  for name,start,end in [(side+'Arm',armhead,elbow),(side+'ForeArm',elbow,wrist)]:
   q=cq@a.orient(name,cq.inverted()@(end-start));d[name]=Matrix.Translation(start)@q.to_matrix().to_4x4()
  d[side+'Hand']=Matrix.Translation(wrist)@handq.to_matrix().to_4x4()
 for name,(head,tail,parent,digit,index)in a.finger_specs.items():
  direction=(tail-head).normalized();normal=Vector((-1 if name.startswith('Left')else 1,0,0));axis=a.rest[name].to_3x3().inverted()@direction.cross(normal).normalized()
  angles=([6,10,7]if digit!='Thumb'else[5,8,5])if id=='4354'else([2,5,3]if digit!='Thumb'else[4,6,4])
  d[name]=d[parent]@a.rest[parent].inverted()@a.rest[name]@Quaternion(axis,math.radians(angles[index])).to_matrix().to_4x4()
 for bone in a.rig.pose.bones:
  parent=bone.parent.name if bone.parent else None
  bone.matrix_basis=a.rest[bone.name].inverted()@(a.rest[parent]@d[parent].inverted()if parent else Matrix.Identity(4))@d[bone.name]
 return d
