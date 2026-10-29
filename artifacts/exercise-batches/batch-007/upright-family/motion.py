"""Source-facing curl/punch and lateral-step motion; continuous leg frames."""
import math
from mathutils import Matrix, Quaternion, Vector
SIDES=[('Left',1),('Right',-1)]

def smooth(t):
 t=max(0.,min(1.,t));return t*t*t*(t*(t*6-15)+10)

def state(frame,ID):
 f=frame%150
 if ID=='4437':
  step=int(f//25);u=f-step*25;arm='Right'if step%2==0 else'Left';leg='Left'if arm=='Right'else'Right'
  curl=smooth(u/10)if u<=10 else 1-smooth((u-10)/13)if u<23 else 0.
  punch=smooth((u-4)/6)if u<=10 else 1-smooth((u-10)/13)if u<23 else 0.
  return {'frame':frame,'time':frame/30,'step':step,'u':u,'moving_side':leg,'punch_side':arm,'curl':curl,'punch':punch,'grounded':[s for s,_ in SIDES if s!=leg]if 0<u<23 else['Left','Right'],'flight':False,'phase':'Curl and punch attack'if u<10 else'Retraction and heel lowering'if u<23 else'Guard with both feet planted'}
 step=int(f/37.5);u=f/37.5-step;moving='Right'if step%2==0 else'Left'
 if u<.10:x=0.;lift=0.;phase='Prepare support';grounded=['Left','Right']
 elif u<.42:q=(u-.10)/.32;x=smooth(q);lift=.035*math.sin(math.pi*q)**2;phase='Lateral step out';grounded=[s for s,_ in SIDES if s!=moving]
 elif u<.56:x=1.;lift=0.;phase='Wide foot placement';grounded=['Left','Right']
 elif u<.88:q=(u-.56)/.32;x=1-smooth(q);lift=.035*math.sin(math.pi*q)**2;phase='Return foot to narrow stance';grounded=[s for s,_ in SIDES if s!=moving]
 else:x=0.;lift=0.;phase='Narrow stance reset';grounded=['Left','Right']
 return {'frame':frame,'time':frame/30,'step':step,'u':u,'moving_side':moving,'lateral_fraction':x,'swing_lift_m':lift,'grounded':grounded,'flight':False,'phase':phase}

def transported(a,name,parent,q,direction):
 base=q@a.rest[parent].to_quaternion().inverted()@a.rest[name].to_quaternion()
 return (base@Vector((0,1,0))).rotation_difference(direction.normalized())@base

def pose(a,frame,ID,offsets=None):
 offsets=offsets or{};st=state(frame,ID);sign=1 if st['moving_side']=='Left'else-1
 if ID=='4437':
  c=st['curl'];p=st['punch'];root=Vector((-sign*.055*c,.025,.935-.008*c));twist=(1 if st['punch_side']=='Right'else-1)*8*p;d=a.torso(root,[2,2,2,0,0],twist=twist)
 else:
  u=st['u'];shift=smooth(u/.10)if u<.10 else 1. if u<.88 else 1-smooth((u-.88)/.12)
  root=Vector((-sign*.035*shift,.025,.935-.030*st['lateral_fraction']));d=a.torso(root,[2,2,2,0,0],twist=0)
 chest_q=d['Spine1'].to_quaternion()@a.rest['Spine1'].to_quaternion().inverted();reach={};curl_angle={};ankle_relative={}
 for side,sgn in SIDES:
  hip=d['Hips']@a.rest['Hips'].inverted()@a.heads[side+'UpLeg'];fq=a.rz(-sgn*(10 if ID=='4437'else 15));x=sgn*(.13 if ID=='4437'else .075+(.255*st['lateral_fraction']if side==st['moving_side']else 0));lift=st['swing_lift_m']if ID=='4436'and side==st['moving_side']else 0
  ankle=Vector((x,0,a.sole_height(side,fq)-.002+offsets.get(side,0)+lift));knee,actual=a.two_joint(hip,ankle,a.length[side+'UpLeg'],a.length[side+'Leg'],hip+Vector((sgn*(.055+(.45*st['lateral_fraction']if ID=='4436'and side==st['moving_side']else 0)),-1,0)));reach[side+'_ankle']=float((actual-ankle).length);ankle=actual
  uq=a.orient(side+'UpLeg',knee-hip);base_lq=transported(a,side+'Leg',side+'UpLeg',uq,ankle-knee);lq=base_lq;foot_q=fq@a.rest[side+'Foot'].to_quaternion();angle=0.;delta=0.
  if ID=='4437'and side==st['moving_side']:
   # Flexion is a total joint angle, not an increment on the bent stance.
   femur=(knee-hip).normalized();shin=(ankle-knee).normalized();axis=femur.cross(shin).normalized();baseline=math.degrees(femur.angle(shin));c=st['curl'];increment=(130-baseline)*c;angle=baseline+increment;hip_sweep=24*c;delta=10*math.tanh(increment/10)
   hiprot=Quaternion(axis,math.radians(hip_sweep));uq=hiprot@uq;knee=hip+uq@Vector((0,a.length[side+'UpLeg'],0));lq=Quaternion(axis,math.radians(hip_sweep+increment))@base_lq;ankle=knee+lq@Vector((0,a.length[side+'Leg'],0));foot_q=Quaternion(axis,math.radians(hip_sweep+increment-delta))@foot_q
  for bone,head,q in [(side+'UpLeg',hip,uq),(side+'Leg',knee,lq),(side+'Foot',ankle,foot_q)]:d[bone]=Matrix.Translation(head)@q.to_matrix().to_4x4()
  toe=d[side+'Foot']@a.rest[side+'Foot'].inverted()@a.heads[side+'ToeBase'];tq=foot_q@a.rest[side+'Foot'].to_quaternion().inverted()@a.rest[side+'ToeBase'].to_quaternion();d[side+'ToeBase']=Matrix.Translation(toe)@tq.to_matrix().to_4x4();curl_angle[side]=angle;ankle_relative[side]=-delta
  # Clavicle, upper arm, forearm and wrist retain the accepted connected transport.
  name=side+'Shoulder';sh=d['Spine1']@a.rest['Spine1'].inverted()@a.heads[name];d[name]=Matrix.Translation(sh)@(chest_q@a.rest[name].to_quaternion()).to_matrix().to_4x4();shoulder=d[name]@a.rest[name].inverted()@a.heads[side+'Arm']
  guard=root+Vector((sgn*.175,-.275,.51))if ID=='4437'else root+Vector((sgn*.145,-.30,.385));p=st['punch']if ID=='4437'and side==st['punch_side']else 0.
  length=math.sqrt(a.length[side+'Arm']**2+a.length[side+'ForeArm']**2+2*a.length[side+'Arm']*a.length[side+'ForeArm']*math.cos(math.radians(17)));forward=chest_q@Vector((sgn*.025,-1,-.025)).normalized();target=guard.lerp(shoulder+forward*length,p);pole=shoulder+Vector((sgn*.18,.03,-.8));elbow,wrist=a.two_joint(shoulder,target,a.length[side+'Arm'],a.length[side+'ForeArm'],pole);reach[side+'_wrist']=float((target-wrist).length)
  aq=chest_q@a.orient(side+'Arm',chest_q.inverted()@(elbow-shoulder));bq=transported(a,side+'ForeArm',side+'Arm',aq,wrist-elbow);hq=bq@a.rest[side+'ForeArm'].to_quaternion().inverted()@a.rest[side+'Hand'].to_quaternion()
  for bone,head,q in [(side+'Arm',shoulder,aq),(side+'ForeArm',elbow,bq),(side+'Hand',wrist,hq)]:d[bone]=Matrix.Translation(head)@q.to_matrix().to_4x4()
 for name,(head,tail,parent,digit,index)in a.finger_specs.items():
  sgn=1 if name.startswith('Left')else-1;side='Left'if sgn==1 else'Right';palmar=a.rest[side+'Hand'].to_3x3()@Vector((-sgn,0,0));axis=a.rest[name].to_3x3().inverted()@(tail-head).normalized().cross(palmar).normalized()
  if digit=='Thumb':
   axis=a.rest[name].to_3x3().inverted()@(tail-head).normalized().cross(Vector((-sgn,0,0))).normalized()
  if digit=='Thumb'and index==0:
   q=a.orient(name,a.rest[side+'Hand'].to_3x3()@Vector((-sgn*.98,.15,.15)));d[name]=d[parent]@a.rest[parent].inverted()@Matrix.Translation(head)@q.to_matrix().to_4x4()
  else:
   angle=([0,25,10]if digit=='Thumb'else[60,70,30])[index];d[name]=d[parent]@a.rest[parent].inverted()@a.rest[name]@Quaternion(axis,math.radians(angle)).to_matrix().to_4x4()
 for pb in a.rig.pose.bones:
  parent=pb.parent.name if pb.parent else None;pb.matrix_basis=a.rest[pb.name].inverted()@(a.rest[parent]@d[parent].inverted()if parent else Matrix.Identity(4))@d[pb.name]
 return d,{**st,'reach_errors_m':reach,'authored_curl_degrees':curl_angle,'authored_shin_relative_ankle_degrees':ankle_relative}
