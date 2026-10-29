"""Eight-second relaxed forward/reverse arm-circle demonstration."""
import math
from mathutils import Matrix,Quaternion,Vector
DURATION=8;FRAMES=240

def smooth(x):
 x=max(0.,min(1.,x));return x*x*x*(x*(x*6-15)+10)

def state(frame):
 t=(frame/30)%DURATION
 if t<=4:u=t/4;s=smooth(u);theta=6*math.pi*s;radius=.045+.095*s;direction='forward'
 else:u=(t-4)/4;s=smooth(u);theta=6*math.pi*(1-s);radius=.14-.095*s;direction='reverse'
 return {'frame':frame,'time':frame/30,'grounded':['Left','Right'],'flight':False,'direction':direction,'angle_radians':theta,'radius_m':radius,'phase':'Forward circles, gradually larger'if direction=='forward'else'Reverse circles, return to small radius'}

def transported(a,name,parent,q,direction):
 base=q@a.rest[parent].to_quaternion().inverted()@a.rest[name].to_quaternion()
 return (base@Vector((0,1,0))).rotation_difference(direction.normalized())@base

def pose(a,frame,offsets=None):
 offsets=offsets or{};st=state(frame);root=Vector((0,.025,.945));d=a.torso(root,[0,0,0,0,0]);cq=d['Spine1'].to_quaternion()@a.rest['Spine1'].to_quaternion().inverted();reach={}
 for side,sign in [('Left',1),('Right',-1)]:
  hip=d['Hips']@a.rest['Hips'].inverted()@a.heads[side+'UpLeg'];fq=a.rz(-sign*10);ankle=Vector((sign*.14,0,a.sole_height(side,fq)-.002+offsets.get(side,0)));knee,actual=a.two_joint(hip,ankle,a.length[side+'UpLeg'],a.length[side+'Leg'],hip+Vector((sign*.055,-1,0)));reach[side+'_ankle']=float((actual-ankle).length);ankle=actual;uq=a.orient(side+'UpLeg',knee-hip);lq=transported(a,side+'Leg',side+'UpLeg',uq,ankle-knee);footq=fq@a.rest[side+'Foot'].to_quaternion()
  for bone,head,q in [(side+'UpLeg',hip,uq),(side+'Leg',knee,lq),(side+'Foot',ankle,footq)]:d[bone]=Matrix.Translation(head)@q.to_matrix().to_4x4()
  toe=d[side+'Foot']@a.rest[side+'Foot'].inverted()@a.heads[side+'ToeBase'];tq=footq@a.rest[side+'Foot'].to_quaternion().inverted()@a.rest[side+'ToeBase'].to_quaternion();d[side+'ToeBase']=Matrix.Translation(toe)@tq.to_matrix().to_4x4()
  name=side+'Shoulder';sh=d['Spine1']@a.rest['Spine1'].inverted()@a.heads[name];d[name]=Matrix.Translation(sh)@(cq@a.rest[name].to_quaternion()).to_matrix().to_4x4();shoulder=d[name]@a.rest[name].inverted()@a.heads[side+'Arm']
  length=math.sqrt(a.length[side+'Arm']**2+a.length[side+'ForeArm']**2+2*a.length[side+'Arm']*a.length[side+'ForeArm']*math.cos(math.radians(12)));r=st['radius_m'];theta=st['angle_radians'];target=shoulder+Vector((sign*math.sqrt(length*length-r*r),-r*math.cos(theta),-r*math.sin(theta)));pole=shoulder+Vector((sign*.2,.08,-.5));elbow,wrist=a.two_joint(shoulder,target,a.length[side+'Arm'],a.length[side+'ForeArm'],pole);reach[side+'_wrist']=float((target-wrist).length)
  aq=cq@a.orient(side+'Arm',cq.inverted()@(elbow-shoulder));bq=transported(a,side+'ForeArm',side+'Arm',aq,wrist-elbow);hq=bq@a.rest[side+'ForeArm'].to_quaternion().inverted()@a.rest[side+'Hand'].to_quaternion()
  for bone,head,q in [(side+'Arm',shoulder,aq),(side+'ForeArm',elbow,bq),(side+'Hand',wrist,hq)]:d[bone]=Matrix.Translation(head)@q.to_matrix().to_4x4()
 for name,(head,tail,parent,digit,index)in a.finger_specs.items():
  sign=1 if name.startswith('Left')else-1;side='Left'if sign==1 else'Right';palmar=a.rest[side+'Hand'].to_3x3()@Vector((-sign,0,0));axis=a.rest[name].to_3x3().inverted()@(tail-head).normalized().cross(palmar).normalized();angle=([4,8,5]if digit=='Thumb'else[8,12,5])[index];d[name]=d[parent]@a.rest[parent].inverted()@a.rest[name]@Quaternion(axis,math.radians(angle)).to_matrix().to_4x4()
 for pb in a.rig.pose.bones:
  parent=pb.parent.name if pb.parent else None;pb.matrix_basis=a.rest[pb.name].inverted()@(a.rest[parent]@d[parent].inverted()if parent else Matrix.Identity(4))@d[pb.name]
 return d,{**st,'reach_errors_m':reach}
