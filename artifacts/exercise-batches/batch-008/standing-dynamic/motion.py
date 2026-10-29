"""Source-facing arm crossover and low-impact stepping/overhead actions."""
import math
from mathutils import Vector,Matrix,Quaternion
SIDES=[('Left',1),('Right',-1)]
PEAK_PROTRACTION_EXTRA_DEGREES=24.43164532715521

def smooth(x):
 x=max(0.,min(1.,x));return x*x*x*(x*(x*6-15)+10)

def state(frame,ID):
 f=frame%150
 if ID=='5172':
  cycle=int(f//75);u=(f-cycle*75)/75;p=math.sin(math.pi*u)**2
  return {'frame':frame,'time':frame/30,'grounded':['Left','Right'],'flight':False,'cross_fraction':p,'upper_arm':'Right'if cycle%2==0 else'Left','phase':'Swing arms across chest'if u<.5 else'Reopen arms at shoulder height'}
 step=int(f//37.5);u=(f-step*37.5)/37.5;moving='Left'if step%2==0 else'Right';lift=math.sin(math.pi*u)**2
 return {'frame':frame,'time':frame/30,'step':step,'u':u,'moving_side':moving,'lift_fraction':lift,'raise_fraction':lift,'grounded':[side for side,_ in SIDES if side!=moving]if .000001<u<.999999 else['Left','Right'],'flight':False,'phase':'Lift knee and raise arms overhead'if u<.5 else'Softly lower foot and arms'}

def transported(a,name,parent,q,direction):
 base=q@a.rest[parent].to_quaternion().inverted()@a.rest[name].to_quaternion()
 return (base@Vector((0,1,0))).rotation_difference(direction.normalized())@base

def pose(a,frame,ID,offsets=None,protraction_extra_degrees=PEAK_PROTRACTION_EXTRA_DEGREES):
 offsets=offsets or{};st=state(frame,ID);lift=st.get('lift_fraction',0.);sgn=1 if st.get('moving_side')=='Left'else-1;root=Vector((-sgn*.025*lift if ID=='6014'else 0,.025,.945-.006*lift));d=a.torso(root,[0,0,0,0,0]);cq=d['Spine1'].to_quaternion()@a.rest['Spine1'].to_quaternion().inverted();reach={}
 for side,sign in SIDES:
  hip=d['Hips']@a.rest['Hips'].inverted()@a.heads[side+'UpLeg'];fq=a.rz(-sign*10);baseankle=Vector((sign*.14,0,a.sole_height(side,fq)-.002+offsets.get(side,0)));baseknee,baseankle=a.two_joint(hip,baseankle,a.length[side+'UpLeg'],a.length[side+'Leg'],hip+Vector((sign*.055,-1,0)));baseuq=a.orient(side+'UpLeg',baseknee-hip);baselq=transported(a,side+'Leg',side+'UpLeg',baseuq,baseankle-baseknee)
  active=ID=='6014'and side==st['moving_side'];ankle=baseankle+Vector((0,-.14*lift,.14*lift))if active else baseankle;knee,actual=a.two_joint(hip,ankle,a.length[side+'UpLeg'],a.length[side+'Leg'],hip+Vector((sign*.055,-1,0)));reach[side+'_ankle']=float((actual-ankle).length);ankle=actual;uq=a.orient(side+'UpLeg',knee-hip);lq=transported(a,side+'Leg',side+'UpLeg',uq,ankle-knee);footq=fq@a.rest[side+'Foot'].to_quaternion()
  if active:footq=lq@baselq.inverted()@footq
  for bone,head,q in [(side+'UpLeg',hip,uq),(side+'Leg',knee,lq),(side+'Foot',ankle,footq)]:d[bone]=Matrix.Translation(head)@q.to_matrix().to_4x4()
  toe=d[side+'Foot']@a.rest[side+'Foot'].inverted()@a.heads[side+'ToeBase'];tq=footq@a.rest[side+'Foot'].to_quaternion().inverted()@a.rest[side+'ToeBase'].to_quaternion();d[side+'ToeBase']=Matrix.Translation(toe)@tq.to_matrix().to_4x4()
  name=side+'Shoulder';sh=d['Spine1']@a.rest['Spine1'].inverted()@a.heads[name];scapular=a.rz(sign*(3*(1-st['cross_fraction'])-(10+protraction_extra_degrees)*st['cross_fraction']))if ID=='5172'else Quaternion(Vector((0,1,0)),math.radians(-sign*8*lift));d[name]=Matrix.Translation(sh)@(cq@scapular@a.rest[name].to_quaternion()).to_matrix().to_4x4();shoulder=d[name]@a.rest[name].inverted()@a.heads[side+'Arm'];elbow_soft=15 if ID=='5172'else 18;length=math.sqrt(a.length[side+'Arm']**2+a.length[side+'ForeArm']**2+2*a.length[side+'Arm']*a.length[side+'ForeArm']*math.cos(math.radians(elbow_soft)))
  if ID=='5172':
   p=st['cross_fraction'];target_shoulder=shoulder
   theta=math.radians(120)*p;z=(.105 if side==st['upper_arm']else-.105)*p;radius=math.sqrt(length*length-z*z);target=target_shoulder+Vector((sign*radius*math.cos(theta),-radius*math.sin(theta),z));pole=shoulder+Vector((sign*.20,.06,-.35*(1-p)+3*z))
  else:
   angle=math.radians(25+140*lift);target=shoulder+Vector((sign*length*math.sin(angle),-.065-.045*math.sin(angle),-length*math.cos(angle)));direction=target-shoulder;target=shoulder+direction.normalized()*length;pole=shoulder+Vector((sign*.20,.10,-.40))
  elbow,wrist=a.two_joint(shoulder,target,a.length[side+'Arm'],a.length[side+'ForeArm'],pole);reach[side+'_wrist']=float((target-wrist).length);aq=transported(a,side+'Arm',side+'Shoulder',d[side+'Shoulder'].to_quaternion(),elbow-shoulder);bq=transported(a,side+'ForeArm',side+'Arm',aq,wrist-elbow);hq=bq@a.rest[side+'ForeArm'].to_quaternion().inverted()@a.rest[side+'Hand'].to_quaternion()
  if ID=='6014':
   # Preserve exact source-rest upper/lower arm frames at the lowered endpoint.
   sq=d[side+'Shoulder'].to_quaternion();baseaq=sq@a.rest[side+'Shoulder'].to_quaternion().inverted()@a.rest[side+'Arm'].to_quaternion();baserel=a.rest[side+'Arm'].to_quaternion().inverted()@a.rest[side+'ForeArm'].to_quaternion();targetrel=aq.inverted()@bq;aq=baseaq.slerp(aq,lift);bq=aq@baserel.slerp(targetrel,lift);elbow=shoulder+aq@Vector((0,a.length[side+'Arm'],0));wrist=elbow+bq@Vector((0,a.length[side+'ForeArm'],0));hq=bq@a.rest[side+'ForeArm'].to_quaternion().inverted()@a.rest[side+'Hand'].to_quaternion()
  for bone,head,q in [(side+'Arm',shoulder,aq),(side+'ForeArm',elbow,bq),(side+'Hand',wrist,hq)]:d[bone]=Matrix.Translation(head)@q.to_matrix().to_4x4()
 for name,(head,tail,parent,digit,index)in a.finger_specs.items():
  sign=1 if name.startswith('Left')else-1;side='Left'if sign==1 else'Right';palmar=a.rest[side+'Hand'].to_3x3()@Vector((-sign,0,0));axis=a.rest[name].to_3x3().inverted()@(tail-head).normalized().cross(palmar).normalized();angle=([4,8,5]if digit=='Thumb'else[8,12,5])[index];d[name]=d[parent]@a.rest[parent].inverted()@a.rest[name]@Quaternion(axis,math.radians(angle)).to_matrix().to_4x4()
 for name,mat in d.items():d[name]=Matrix.Translation(mat.translation)@mat.to_quaternion().normalized().to_matrix().to_4x4()
 for pb in a.rig.pose.bones:
  parent=pb.parent.name if pb.parent else None;pb.matrix_basis=a.rest[pb.name].inverted()@(a.rest[parent]@d[parent].inverted()if parent else Matrix.Identity(4))@d[pb.name]
 return d,{**st,'reach_errors_m':reach}
