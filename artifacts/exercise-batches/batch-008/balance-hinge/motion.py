"""One five-second bilateral, same-side circular reach and rear-leg balance hinge."""
import math
from mathutils import Matrix, Quaternion, Vector
DURATION=5; FRAMES=150

def smooth(x):
 x=max(0.,min(1.,x)); return x*x*x*(10+x*(-15+6*x))

def state(frame):
 t=frame/30; local=t%2.5 if frame<150 else 0.; side='Right' if frame<75 or frame==150 else 'Left'; sign=-1 if side=='Right' else 1
 if local<.25:q=0.; phase='Transfer over stance foot'
 elif local<1.05:q=smooth((local-.25)/.80);phase='Circle down and lift opposite leg'
 elif local<1.20:q=1.;phase='Reach towards stance toes'
 elif local<2.20:q=1-smooth((local-1.20)/1.00);phase='Return arm and rear leg together'
 else:q=0.;phase='Upright reset before changing sides'
 shift=smooth(local/.25) if local<.25 else 1-smooth((local-2.20)/.30) if local>2.20 else 1.
 if frame in [0,75,150]:shift=0.
 grounded=['Left','Right'] if q<1e-10 else [side]
 return {'frame':frame,'time':t,'side':side,'lift_side':'Left' if side=='Right' else 'Right','sign':sign,'hinge':q,'weight_shift':shift,'phase':phase,'grounded':grounded,'flight':False}

def transported(a,name,parent,q,direction):
 base=q@a.rest[parent].to_quaternion().inverted()@a.rest[name].to_quaternion()
 return (base@Vector((0,1,0))).rotation_difference(direction.normalized())@base

def M(h,q):return Matrix.Translation(h)@q.to_matrix().to_4x4()

def pose(a,frame,offsets=None):
 offsets=offsets or {};st=state(frame);q=st['hinge'];sign=st['sign'];shift=st['weight_shift'];root=Vector((sign*.180*shift,.025+.015*q,.958-.028*shift-.009*q));d=a.torso(root,[80*q,85*q,88*q,83*q,78*q],bend=sign*10*q);reach={}
 for side,sgn in [('Left',1),('Right',-1)]:
  hip=d['Hips']@a.rest['Hips'].inverted()@a.heads[side+'UpLeg'];baseq=a.rz(-sgn*8.8);baseank=Vector((sgn*.14,0,a.sole_height(side,baseq)-.002+offsets.get(side,0)))
  if side==st['lift_side']:
   # Rotate the actual straight-ish neutral leg axis about the hip. The ankle
   # rises continuously; only the stance foot is locked once the lift begins.
   delta=baseank-hip;distance=min(delta.length,.826)*(1-q)+.825*q
   ankle=hip+a.rx(70*q)@delta.normalized()*distance
  else:ankle=baseank
  knee,actual=a.two_joint(hip,ankle,a.length[side+'UpLeg'],a.length[side+'Leg'],hip+Vector((sgn*.10,-1,0)));reach[side+'_ankle']=float((actual-ankle).length);uq=a.orient(side+'UpLeg',knee-hip);lq=transported(a,side+'Leg',side+'UpLeg',uq,actual-knee)
  if side==st['lift_side'] and q>0:
   # Coherent shin-relative ankle transport, blended only during takeoff.
   neutralroot=Vector((0,.025,.958));neutralhip=neutralroot+(a.heads[side+'UpLeg']-a.heads['Hips']);nk,na=a.two_joint(neutralhip,baseank,a.length[side+'UpLeg'],a.length[side+'Leg'],neutralhip+Vector((sgn*.10,-1,0)));nu=a.orient(side+'UpLeg',nk-neutralhip);nl=transported(a,side+'Leg',side+'UpLeg',nu,na-nk);fq=baseq.to_matrix().to_quaternion().slerp(lq@nl.inverted()@baseq,q)
  else:fq=baseq
  footq=fq@a.rest[side+'Foot'].to_quaternion();d[side+'UpLeg']=M(hip,uq);d[side+'Leg']=M(knee,lq);d[side+'Foot']=M(actual,footq);toe=d[side+'Foot']@a.rest[side+'Foot'].inverted()@a.heads[side+'ToeBase'];tq=footq@a.rest[side+'Foot'].to_quaternion().inverted()@a.rest[side+'ToeBase'].to_quaternion();d[side+'ToeBase']=M(toe,tq)
 cq=d['Spine1'].to_quaternion()@a.rest['Spine1'].to_quaternion().inverted()
 for side,sgn in [('Left',1),('Right',-1)]:
  sh=side+'Shoulder';d[sh]=d['Spine1']@a.rest['Spine1'].inverted()@a.rest[sh];shoulder=d[sh]@a.rest[sh].inverted()@a.heads[side+'Arm'];arm_length=math.sqrt(a.length[side+'Arm']**2+a.length[side+'ForeArm']**2+2*a.length[side+'Arm']*a.length[side+'ForeArm']*math.cos(math.radians(12)))
  if side==st['side']:
   alpha=math.radians(88*q);direction=Vector((sgn*math.cos(alpha),.20*math.sin(alpha)-.14*math.sin(math.pi*q),-math.sin(alpha))).normalized()
  else:direction=Vector((sgn,-.12*q,.10*q)).normalized()
  wrist=shoulder+direction*arm_length;pole=shoulder+Vector((sgn*.20,.15,-.5));elbow,actual=a.two_joint(shoulder,wrist,a.length[side+'Arm'],a.length[side+'ForeArm'],pole);reach[side+'_wrist']=float((actual-wrist).length);aq=cq@a.orient(side+'Arm',cq.inverted()@(elbow-shoulder));bq=transported(a,side+'ForeArm',side+'Arm',aq,actual-elbow);hq=bq@a.rest[side+'ForeArm'].to_quaternion().inverted()@a.rest[side+'Hand'].to_quaternion()
  d[side+'Arm']=M(shoulder,aq);d[side+'ForeArm']=M(elbow,bq);d[side+'Hand']=M(actual,hq)
 for name,(head,tail,parent,digit,index) in a.finger_specs.items():
  sgn=1 if name.startswith('Left')else -1;side='Left'if sgn==1 else'Right';palmar=a.rest[side+'Hand'].to_3x3()@Vector((-sgn,0,0));axis=a.rest[name].to_3x3().inverted()@(tail-head).normalized().cross(palmar).normalized();angle=([4,8,5]if digit=='Thumb'else[8,12,5])[index];d[name]=d[parent]@a.rest[parent].inverted()@a.rest[name]@Quaternion(axis,math.radians(angle)).to_matrix().to_4x4()
 for pb in a.rig.pose.bones:
  parent=pb.parent.name if pb.parent else None;pb.matrix_basis=a.rest[pb.name].inverted()@(a.rest[parent]@d[parent].inverted()if parent else Matrix.Identity(4))@d[pb.name]
 return d,{**st,'reach_errors_m':reach}
