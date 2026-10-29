"""Shared seated ankle family, continuous shin-relative Foot/ToeBase frames."""
import math
from mathutils import Matrix,Quaternion,Vector
ROOT_Z=.18
HEEL_IDS={}
PALMS={}
HEEL_SKIN_IDS={}
CALF_IDS={}
THIGH_TARGET={}
PALM_ANCHOR={}
KNEE_FLEX=15
def ease(t):t=max(0,min(1,t));return t*t*(3-2*t)
def channel(t,start,end):return ease((t-start)/(end-start))
def motion(id,t,side):
 if id=='1368':
  local=t-(0 if side=='Left'else 6)
  if not 0<=local<=6:return 0,0,0
  lift=channel(local,0,.5)*(1-channel(local,5.5,6))
  if local<.5:return .045*lift,12*lift,0
  if local<=2.75:theta=2*math.pi*(local-.5)/2.25
  elif local<3:theta=2*math.pi
  elif local<=5.5:theta=-2*math.pi*(local-3)/2.5
  else:return .045*lift,12*lift,0
  return .045*lift,12*math.cos(theta),8*math.sin(theta)
 local=t-(0 if side=='Left'else 2.5)
 if not 0<=local<=2.5:return 0,0,0
 u=channel(local,.15,1.05)*(1-channel(local,1.45,2.35))
 return 0,(-15 if id=='2761'else 30)*u,0
def points(a):
 a.scene.view_layers.update()if hasattr(a.scene.view_layers,'update')else None
 import bpy,numpy as np
 bpy.context.view_layer.update();e=a.body.evaluated_get(bpy.context.evaluated_depsgraph_get());m=e.to_mesh();p=np.array([v.co[:]for v in m.vertices]);e.to_mesh_clear();return p
def apply(a,d):
 import bpy
 for pb in a.rig.pose.bones:
  parent=pb.parent.name if pb.parent else None
  pb.matrix_basis=a.rest[pb.name].inverted()@(a.rest[parent]@d[parent].inverted()if parent else Matrix.Identity(4))@d[pb.name]
 bpy.context.view_layer.update()
def pose(a,id,t,root_z=None):
 root=ROOT_Z if root_z is None else root_z
 d=a.torso(Vector((0,0,root)),[-8]*5)
 offsets={'Left':0.,'Right':0.}
 def legs():
  for side,sign in [('Left',1),('Right',-1)]:
   hip=d['Hips']@a.rest['Hips'].inverted()@a.heads[side+'UpLeg'];lift,pitch,roll=motion(id,t,side);ankle_z=.075
   l1=a.length[side+'UpLeg'];l2=a.length[side+'Leg'];D=math.sqrt(l1*l1+l2*l2+2*l1*l2*math.cos(math.radians(KNEE_FLEX)));dx=sign*.045
   def chain(z):
    dz=z-hip.z;dy=-math.sqrt(D*D-dx*dx-dz*dz);ankle=hip+Vector((dx,dy,dz));axis=(ankle-hip).normalized();along=(l1*l1-l2*l2+D*D)/(2*D);up=(Vector((0,0,1))-axis*axis.z).normalized();knee=hip+axis*along+up*math.sqrt(max(0,l1*l1-along*along));return knee,ankle
   for _ in range(5):
    knee,ankle=chain(ankle_z);legq=a.orient(side+'Leg',ankle-knee,(-sign,0,0));legdef=legq@a.rest[side+'Leg'].to_quaternion().inverted();fq=legdef@a.rx(pitch)@a.rz(roll-sign*20.8);ankle_z=.0015-min((fq@(a.coords[i]-a.heads[side+'Foot'])).z for i in HEEL_IDS[side])+lift+offsets[side]
   knee,ankle=chain(ankle_z);thighq=a.orient(side+'UpLeg',knee-hip,(-sign,0,0));legq=a.orient(side+'Leg',ankle-knee,(-sign,0,0));legdef=legq@a.rest[side+'Leg'].to_quaternion().inverted();fq=legdef@a.rx(pitch)@a.rz(roll-sign*20.8)
   d[side+'UpLeg']=Matrix.Translation(hip)@thighq.to_matrix().to_4x4();d[side+'Leg']=Matrix.Translation(knee)@legq.to_matrix().to_4x4();d[side+'Foot']=Matrix.Translation(ankle)@(fq@a.rest[side+'Foot'].to_quaternion()).to_matrix().to_4x4();d[side+'ToeBase']=d[side+'Foot']@a.rest[side+'Foot'].inverted()@a.rest[side+'ToeBase']
 for _ in range(4):
  legs()
  for pb in a.rig.pose.bones:
   if pb.name not in d:continue
   parent=pb.parent.name if pb.parent else None
   pb.matrix_basis=a.rest[pb.name].inverted()@(a.rest[parent]@d[parent].inverted()if parent else Matrix.Identity(4))@d[pb.name]
  pp=points(a)
  for side in ['Left','Right']:offsets[side]+=.0015+motion(id,t,side)[0]-float(pp[HEEL_SKIN_IDS[side],2].min())
 for side,sign in [('Left',1),('Right',-1)]:
  sh=side+'Shoulder';d[sh]=d['Spine1']@a.rest['Spine1'].inverted()@a.rest[sh]
  shoulder=d[sh]@a.rest[sh].inverted()@a.heads[side+'Arm'];hand=side+'Hand'
  # Relaxed palms rest on the actual pure-thigh skin, tracking a lifted leg.
  source_id=THIGH_TARGET[side];transform=d[side+'UpLeg']@a.rest[side+'UpLeg'].inverted();target=transform@a.coords[source_id];normal=(transform.to_3x3()@a.body.data.vertices[source_id].normal).normalized();direction=d[side+'Leg'].translation-d[side+'UpLeg'].translation;q=a.palm_rotation(side,direction,-normal);wrist=target+normal*.003-q@(PALM_ANCHOR[side]-a.heads[hand]);reach=(wrist-shoulder).length;length=a.length[side+'Arm']+a.length[side+'ForeArm']
  # The tangential hand anchor is not the lowest palmar skin. Place the
  # actual palmar envelope above the thigh tangent plane, preserving the
  # accepted flat hand orientation and avoiding a buried palm heel.
  minimum=min((q@(a.coords[i]-a.heads[hand])).dot(normal)for i in PALMS[side]);wrist+=normal*(target.dot(normal)+.0015-wrist.dot(normal)-minimum)
  reach=(wrist-shoulder).length;assert reach<length-.001,('Thigh-resting hand unreachable',side,reach,length)
  hand_long=(q@(a.heads[side+'Middle1']-a.heads[hand])).normalized();ideal_elbow=wrist-hand_long*a.length[side+'ForeArm'];ideal_elbow.x=sign*max(sign*ideal_elbow.x,.25)
  elbow,actual=a.two_joint(shoulder,wrist,a.length[side+'Arm'],a.length[side+'ForeArm'],ideal_elbow);assert(actual-wrist).length<1e-6
  for name,start,end in [(side+'Arm',shoulder,elbow),(side+'ForeArm',elbow,wrist)]:d[name]=Matrix.Translation(start)@a.orient(name,end-start,(-sign,0,0)).to_matrix().to_4x4()
  d[hand]=Matrix.Translation(wrist)@(q@a.rest[hand].to_quaternion()).to_matrix().to_4x4()
 for name,(head,tail,parent,digit,index)in a.finger_specs.items():
  side='Left'if name.startswith('Left')else'Right';sign=1 if side=='Left'else-1;axis=a.rest[name].to_3x3().inverted()@(tail-head).normalized().cross(Vector((-sign,0,0))).normalized();angle=([1,2,1]if digit!='Thumb'else[0,-18,-17])[index]
  d[name]=d[parent]@a.rest[parent].inverted()@a.rest[name]@Quaternion(axis,math.radians(angle)).to_matrix().to_4x4()
 return d
