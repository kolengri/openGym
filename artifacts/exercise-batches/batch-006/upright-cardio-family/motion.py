"""Two distinct source-facing upright demonstrations on the original51-bone rig."""
import math
import numpy as np
from mathutils import Matrix,Quaternion,Vector
HOPS=4;TAKEOFF=.42;LAND=.66

def ease(t):
 t=max(0.,min(1.,t));return t*t*(3-2*t)
def hermite(t,x0,x1,v0,v1,duration):
 return (2*t**3-3*t*t+1)*x0+(t**3-2*t*t+t)*duration*v0+(-2*t**3+3*t*t)*x1+(t**3-t*t)*duration*v1

def punch_envelope(frame):
 """Six alternating punches:200ms attack,433ms return,200ms guard gap.

 This is authored demonstration timing, independent of the source30–60s interval.
 """
 f=frame%150;step=int(f//25);u=f-step*25
 def smooth5(x):
  x=max(0.,min(1.,x));return x*x*x*(x*(x*6-15)+10)
 if u<2:p=0.;phase='Guard'
 elif u<8:p=smooth5((u-2)/6);phase='Attack'
 elif u<21:p=1-smooth5((u-8)/13);phase='Retraction'
 else:p=0.;phase='Guard'
 side='Right'if step%2==0 else'Left'
 return {'punch_index':step,'punch_side':side,'punch_phase':phase,'punch_extension':p,
         'right_extension':p if side=='Right'else 0.,'left_extension':p if side=='Left'else 0.}

def schedule(frame,exercise):
 t=(frame/30)%5
 if exercise=='3531':return {'time':t,'grounded':['Left','Right'],'phase':punch_envelope(frame)['punch_phase'],'flight':False,**punch_envelope(frame)}
 step=min(HOPS-1,int(t*HOPS/5));u=t*HOPS/5-step;support='Right'if step%2==0 else'Left';drive='Left'if support=='Right'else'Right'
 grounded=[support]if u<=TAKEOFF else [drive]if u>=LAND else []
 phase='Preload'if u<.18 else'Toe push-off'if u<=TAKEOFF else'Flight with opposite knee drive'if u<LAND else'Soft ball landing'if u<.84 else'Recover'
 return {'time':t,'step':step,'u':u,'support':support,'drive':drive,'grounded':grounded,'phase':phase,'flight':not grounded}

def transported(a,name,parent,q,direction):
 base=q@a.rest[parent].to_quaternion().inverted()@a.rest[name].to_quaternion()
 return (base@Vector((0,1,0))).rotation_difference(direction.normalized())@base

def pose(a,frame,exercise,ground_offsets=None):
 offsets=ground_offsets or{};state=schedule(frame,exercise);t=state['time'];feet={};wrists={};poles={}
 if exercise=='4918':
  u=state['u'];step=state['step'];drive_sign=1 if state['drive']=='Left'else-1;duration=5/HOPS;flight_time=(LAND-TAKEOFF)*duration;velocity=9.81*flight_time/2
  if u<.18:z=.90+(.83-.90)*ease(u/.18)
  elif u<=TAKEOFF:z=hermite((u-.18)/(TAKEOFF-.18),.83,.98,0,velocity,(TAKEOFF-.18)*duration)
  elif u<LAND:
   tau=(u-TAKEOFF)*duration;z=.98+velocity*tau-.5*9.81*tau*tau
  elif u<.84:z=hermite((u-LAND)/(.84-LAND),.98,.85,-velocity,0,(.84-LAND)*duration)
  else:z=.85+.05*ease((u-.84)/.16)
  shift=ease((u-TAKEOFF)/(LAND-TAKEOFF));root=Vector((drive_sign*(-.045+.09*shift),.035,z));lean=5+5*(.90-z)/.10;lean=max(1,min(10,lean));d=a.torso(root,[lean,lean*.8,lean*.6,0,0])
  arm_swing=drive_sign*(2*ease(min(1,u/.50))-1)
  for side,sign in [('Left',1),('Right',-1)]:
   yaw=a.rz(-sign*12.8)
   if u<=TAKEOFF:
    if side==state['support']:
     pitch=25*ease((u-.18)/(TAKEOFF-.18));fq=a.rx(pitch)@yaw;ankle=Vector((sign*.14,.02,a.sole_height(side,fq)-.002+offsets.get(side,0)));toe_pitch=0
    else:
     progress=ease(u/TAKEOFF);pitch=-10;fq=a.rx(pitch)@yaw;ankle=Vector((sign*.14,.14+(-.26-.14)*progress,.22+(z-.30-.22)*progress));toe_pitch=pitch
   elif u<LAND:
    q=(u-TAKEOFF)/(LAND-TAKEOFF)
    if side==state['support']:
     pitch=25+(-10-25)*ease(q);fq=a.rx(pitch)@yaw;launch=a.sole_height(side,a.rx(25)@yaw)-.002;ankle=Vector((sign*.14,.02+.12*ease(q),launch+.18*ease(q)+.11*math.sin(math.pi*q)));toe_pitch=pitch*ease(q)
    else:
     progress=ease((q-.45)/.55);pitch=-10+28*ease(q);fq=a.rx(pitch)@yaw;landing=a.sole_height(side,a.rx(18)@yaw)-.002;ankle=Vector((sign*.14,-.26+(.02+.26)*progress,(z-.30)*(1-progress)+landing*progress));toe_pitch=pitch*(1-ease(q))
   else:
    if side==state['drive']:
     pitch=18*(1-ease((u-LAND)/(.84-LAND)));fq=a.rx(pitch)@yaw;ankle=Vector((sign*.14,.02,a.sole_height(side,fq)-.002+offsets.get(side,0)));toe_pitch=0
    else:
     pitch=-10;fq=a.rx(pitch)@yaw;launch=a.sole_height(side,a.rx(25)@yaw)-.002;ankle=Vector((sign*.14,.14,launch+.18+(.22-launch-.18)*ease((u-LAND)/(1-LAND))));toe_pitch=pitch
   feet[side]=(ankle,fq,a.rx(toe_pitch)@yaw)
   effect=-sign*arm_swing;wrists[side]=root+Vector((sign*.35,-.12-.22*effect,.20+.15*effect));poles[side]=root+Vector((sign*.43,.14,-.05))
 else:
  envelope=punch_envelope(frame);right=envelope['right_extension'];left=envelope['left_extension'];twist=8*(right-left);root=Vector((-.012*(right-left),.03,.925-.006*(right+left)));d=a.torso(root,[2,2,2,0,0],twist=twist)
  for side,sign in [('Left',1),('Right',-1)]:
   fq=a.rz(-sign*10);ankle=Vector((sign*.175,-.15 if side=='Left'else .18,a.sole_height(side,fq)-.002+offsets.get(side,0)));feet[side]=(ankle,fq,fq)
   sh=d['Spine1']@a.rest['Spine1'].inverted()@a.heads[side+'Shoulder'];chest_q=d['Spine1'].to_quaternion()@a.rest['Spine1'].to_quaternion().inverted();armhead=sh+chest_q@(a.heads[side+'Arm']-a.heads[side+'Shoulder'])
   p=left if side=='Left'else right;guard=root+Vector((sign*.175,-.275,.51));reach=math.sqrt(a.length[side+'Arm']**2+a.length[side+'ForeArm']**2+2*a.length[side+'Arm']*a.length[side+'ForeArm']*math.cos(math.radians(17)))
   forward=chest_q@Vector((sign*.025,-1,-.025)).normalized();wrists[side]=guard.lerp(armhead+forward*reach,p);poles[side]=armhead+Vector((sign*.18,.03,-.8))
 chest_q=d['Spine1'].to_quaternion()@a.rest['Spine1'].to_quaternion().inverted()
 reach_errors={}
 for side,sign in [('Left',1),('Right',-1)]:
  hip=d['Hips']@a.rest['Hips'].inverted()@a.heads[side+'UpLeg'];ankle,fq,tq=feet[side];knee,actual=a.two_joint(hip,ankle,a.length[side+'UpLeg'],a.length[side+'Leg'],hip+Vector((sign*.08,-1,0)));reach_errors[side+'_ankle']=float((actual-ankle).length);ankle=actual
  uq=a.orient(side+'UpLeg',knee-hip);lq=transported(a,side+'Leg',side+'UpLeg',uq,ankle-knee)
  d[side+'UpLeg']=Matrix.Translation(hip)@uq.to_matrix().to_4x4();d[side+'Leg']=Matrix.Translation(knee)@lq.to_matrix().to_4x4();d[side+'Foot']=Matrix.Translation(ankle)@(fq@a.rest[side+'Foot'].to_quaternion()).to_matrix().to_4x4()
  toe=d[side+'Foot']@a.rest[side+'Foot'].inverted()@a.heads[side+'ToeBase'];d[side+'ToeBase']=Matrix.Translation(toe)@(tq@a.rest[side+'ToeBase'].to_quaternion()).to_matrix().to_4x4()
  name=side+'Shoulder';sh=d['Spine1']@a.rest['Spine1'].inverted()@a.heads[name];d[name]=Matrix.Translation(sh)@(chest_q@a.rest[name].to_quaternion()).to_matrix().to_4x4();shoulder=d[name]@a.rest[name].inverted()@a.heads[side+'Arm'];elbow,wrist=a.two_joint(shoulder,wrists[side],a.length[side+'Arm'],a.length[side+'ForeArm'],poles[side]);reach_errors[side+'_wrist']=float((wrist-wrists[side]).length)
  aq=chest_q@a.orient(side+'Arm',chest_q.inverted()@(elbow-shoulder));bq=transported(a,side+'ForeArm',side+'Arm',aq,wrist-elbow);hq=bq@a.rest[side+'ForeArm'].to_quaternion().inverted()@a.rest[side+'Hand'].to_quaternion()
  for bone,head,q in [(side+'Arm',shoulder,aq),(side+'ForeArm',elbow,bq),(side+'Hand',wrist,hq)]:d[bone]=Matrix.Translation(head)@q.to_matrix().to_4x4()
 for name,(head,tail,parent,digit,index)in a.finger_specs.items():
  sign=1 if name.startswith('Left')else-1;axis=a.rest[name].to_3x3().inverted()@(tail-head).normalized().cross(Vector((-sign,0,0))).normalized()
  if exercise=='3531'and digit!='Thumb':
   side='Left'if sign==1 else'Right';palmar=a.rest[side+'Hand'].to_3x3()@Vector((-sign,0,0));axis=a.rest[name].to_3x3().inverted()@(tail-head).normalized().cross(palmar).normalized()
  angles=([0,25,10]if digit=='Thumb'else[60,70,30])if exercise=='3531'else([15,25,15]if digit=='Thumb'else[30,45,25])
  if exercise=='3531'and digit=='Thumb'and index==0:
   # Source thumb begins abducted. Oppose its MCP across the folded index,
   # keeping the thumb on the palmar exterior instead of inside the fingers.
   side='Left'if sign==1 else'Right';direction=a.rest[side+'Hand'].to_3x3()@Vector((-sign*.98,.15,.15));q=a.orient(name,direction)
   d[name]=d[parent]@a.rest[parent].inverted()@Matrix.Translation(head)@q.to_matrix().to_4x4()
  else:d[name]=d[parent]@a.rest[parent].inverted()@a.rest[name]@Quaternion(axis,math.radians(angles[index])).to_matrix().to_4x4()
 if exercise=='3531':
  import fist_pose;fist_pose.apply(a,d)
 for bone in a.rig.pose.bones:
  parent=bone.parent.name if bone.parent else None;bone.matrix_basis=a.rest[bone.name].inverted()@(a.rest[parent]@d[parent].inverted()if parent else Matrix.Identity(4))@d[bone.name]
 return d,{**state,'reach_errors_m':reach_errors}
