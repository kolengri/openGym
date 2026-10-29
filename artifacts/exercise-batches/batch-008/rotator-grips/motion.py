"""Standing one-sided rotator stretches; authored five-second demonstration."""
import math
from mathutils import Matrix,Quaternion,Vector
DURATION=5;FRAMES=150
OVERHEAD_WRIST_ENTRY=(0.11065127334917374, 0.1531945158972586, 1.477355352293878)
OVERHEAD_WRIST_HOLD=(0.11065127334917374, 0.1551945158972586, 1.476355352293878)
OVERHEAD_HAND_GOAL=(0.7413167649421031, -0.28273252813363103, -0.39997652065882416, 0.45883608671572634)

def smooth(x):
 x=max(0.,min(1.,x));return x*x*x*(x*(x*6-15)+10)

def lerp_path(t,knots):
 for (ta,pa),(tb,pb) in zip(knots,knots[1:]):
  if t<=tb:return Vector(pa).lerp(Vector(pb),smooth((t-ta)/(tb-ta)))
 return Vector(knots[-1][1])

def transported(a,name,parent,q,direction):
 base=q@a.rest[parent].to_quaternion().inverted()@a.rest[name].to_quaternion();return(base@Vector((0,1,0))).rotation_difference(direction.normalized())@base

def stable_pole(a,side,wrist,endpoint,goalpole,u):
 shoulder=a.heads[side+'Arm'];axis0=(a.heads[side+'Hand']-shoulder).normalized();axis=(wrist-shoulder).normalized();initial=a.heads[side+'ForeArm']-shoulder;initial=(initial-axis0*initial.dot(axis0)).normalized();end_axis=(endpoint-shoulder).normalized();end_base=axis0.rotation_difference(end_axis)@initial;goal=Vector(goalpole)-shoulder;goal=(goal-end_axis*goal.dot(end_axis)).normalized();twist=math.atan2(end_axis.dot(end_base.cross(goal)),end_base.dot(goal));bend=Quaternion(axis,twist*u)@(axis0.rotation_difference(axis)@initial);return shoulder+bend

def arm_geometry(a,tau):
 u=smooth(tau/1.5);wrist=lerp_path(tau,[(0,a.heads['LeftHand']),(.80,(.34,-.26,1.88)),(1.12,(.30,.23,1.86)),(1.50,OVERHEAD_WRIST_ENTRY),(2,OVERHEAD_WRIST_HOLD)]);wrist.y+=.015*math.sin(math.pi*smooth((tau-1.12)/.68))if 1.12<tau<1.80 else 0;sh=a.heads['LeftArm'];elbow,wrist=a.two_joint(sh,wrist,a.length['LeftArm'],a.length['LeftForeArm'],stable_pole(a,'Left',wrist,Vector(OVERHEAD_WRIST_HOLD),sh+Vector((.10,.03,1)),u));target=elbow+Vector((-.085,0,.072));rw=lerp_path(tau,[(0,a.heads['RightHand']),(.45,a.heads['RightHand']),(.95,(-.38,-.27,1.70)),(1.28,(-.18,.22,1.90)),(1.45,(.04,.28,1.80)),(1.65,target),(2,target)]);sh=a.heads['RightArm'];left_final,_=a.two_joint(a.heads['LeftArm'],Vector(OVERHEAD_WRIST_HOLD),a.length['LeftArm'],a.length['LeftForeArm'],a.heads['LeftArm']+Vector((.10,.03,1)));right_final=left_final+Vector((-.085,0,.072));re,rw=a.two_joint(sh,rw,a.length['RightArm'],a.length['RightForeArm'],stable_pole(a,'Right',rw,right_final,Vector((-.5,-.25,1.65)),smooth((tau-.45)/1.20)));return {'Left':(elbow,wrist),'Right':(re,rw)}

_TRANSPORT={}
def arm_frames(a,tau):
 # Path integration in fine fixed steps never asks a shortest arc to choose an
 # antipodal swing. The endpoint axial correction retains the accepted basis.
 key=(tuple(OVERHEAD_WRIST_ENTRY),tuple(OVERHEAD_WRIST_HOLD))
 if _TRANSPORT.get('key')!=key:
  rows={side:[a.rest[side+'Arm'].to_quaternion()]for side in['Left','Right']};directions={side:(a.heads[side+'ForeArm']-a.heads[side+'Arm']).normalized()for side in rows};lower_rows={side:[a.rest[side+'ForeArm'].to_quaternion()]for side in rows};lower_directions={side:(a.heads[side+'Hand']-a.heads[side+'ForeArm']).normalized()for side in rows}
  for i in range(1,601):
   geo=arm_geometry(a,i/300)
   for side in rows:
    direction=(geo[side][0]-a.heads[side+'Arm']).normalized();q=directions[side].rotation_difference(direction)@rows[side][-1];q.normalize();rows[side].append(q);directions[side]=direction;ld=(geo[side][1]-geo[side][0]).normalized();lq=lower_directions[side].rotation_difference(ld)@lower_rows[side][-1];lq.normalize();lower_rows[side].append(lq);lower_directions[side]=ld
  endpoint=arm_geometry(a,2);twists={};lower_twists={};lower_goals={}
  for side in rows:
   elbow,wrist=endpoint[side];upper=elbow-a.heads[side+'Arm'];lower=wrist-elbow
   if side=='Left':goal=a.orient(side+'Arm',upper)
   else:
    ou=a.tails[side+'Arm']-a.heads[side+'Arm'];of=a.tails[side+'ForeArm']-a.heads[side+'ForeArm'];goal=(a.frame(upper,upper.cross(lower))@a.frame(ou,ou.cross(of)).transposed()).to_quaternion()@a.rest[side+'Arm'].to_quaternion()
   axis=upper.normalized();n0=rows[side][-1]@Vector((1,0,0));n1=goal@Vector((1,0,0));twists[side]=math.atan2(axis.dot(n0.cross(n1)),n0.dot(n1));lgoal=transported(a,side+'ForeArm',side+'Arm',goal,lower);lower_goals[side]=lgoal;laxis=lower.normalized();ln0=lower_rows[side][-1]@Vector((1,0,0));ln1=lgoal@Vector((1,0,0));lower_twists[side]=math.atan2(laxis.dot(ln0.cross(ln1)),ln0.dot(ln1))
  _TRANSPORT.update(key=key,rows=rows,twists=twists,directions=directions,lower_rows=lower_rows,lower_twists=lower_twists,lower_goals=lower_goals)
 index=min(600,max(0,round(tau*300)));geo=arm_geometry(a,tau);result={}
 for side in['Left','Right']:
  axis=(geo[side][0]-a.heads[side+'Arm']).normalized();result[side]=Quaternion(axis,_TRANSPORT['twists'][side]*smooth(tau/2))@_TRANSPORT['rows'][side][index];result[side].normalize();laxis=(geo[side][1]-geo[side][0]).normalized();result[side+'ForeArm']=Quaternion(laxis,_TRANSPORT['lower_twists'][side]*smooth(tau/2))@_TRANSPORT['lower_rows'][side][index];result[side+'ForeArm'].normalize()
 return result

def overhead_raw(a,t):
 tau=min(t,5-t);u=smooth(tau/1.5);grip=smooth((tau-1.50)/.25);d={n:m.copy()for n,m in a.rest.items()};geo=arm_geometry(a,tau);frames=arm_frames(a,tau)
 for side in['Left','Right']:
  sh=a.heads[side+'Arm'];elbow,wrist=geo[side];aq=frames[side];fq=frames[side+'ForeArm']
  if side=='Left':
   weight=1-smooth((tau-1.10)/.40)
   if weight>0:
    upper=elbow-sh;lower=wrist-elbow;ou=a.tails['LeftArm']-a.heads['LeftArm'];of=a.tails['LeftForeArm']-a.heads['LeftForeArm'];normal=upper.cross(lower);original_normal=ou.cross(of);aligned=[]
    for name,direction,original,q in[('LeftArm',upper,ou,aq),('LeftForeArm',lower,of,fq)]:
     goal=(a.frame(direction,normal)@a.frame(original,original_normal).transposed()).to_quaternion()@a.rest[name].to_quaternion();axis=direction.normalized();n0=q@Vector((1,0,0));n1=goal@Vector((1,0,0));angle=math.atan2(axis.dot(n0.cross(n1)),n0.dot(n1));q=Quaternion(axis,weight*angle)@q;q.normalize();aligned.append(q)
    aq,fq=aligned
  goal=Quaternion(OVERHEAD_HAND_GOAL)if side=='Left'else a.orient('RightHand',(.98,0,-.20),(-.20,0,-.98));relative=a.rest[side+'ForeArm'].to_quaternion().inverted()@a.rest[side+'Hand'].to_quaternion();neutral=fq@relative;final_neutral=_TRANSPORT['lower_goals'][side]@relative;delta=final_neutral.inverted()@goal;amount=smooth((tau-1.10)/.40)if side=='Left'else smooth((tau-.95)/.70);hq=neutral@Quaternion((1,0,0,0)).slerp(delta,amount)
  for n,h,q in[(side+'Arm',sh,aq),(side+'ForeArm',elbow,fq),(side+'Hand',wrist,hq)]:d[n]=Matrix.Translation(h)@q.to_matrix().to_4x4()
 for name,(head,tail,parent,digit,index)in a.finger_specs.items():
  sign=1 if name.startswith('Left')else-1;axis=a.rest[name].to_3x3().inverted()@(tail-head).normalized().cross(Vector((-sign,0,0))).normalized();angles=([20,45,30]if digit!='Thumb'else[8,15,10])if sign==-1 else[3,5,3];amount=grip if sign==-1 else u;q=Quaternion(axis,math.radians(angles[index]*amount));d[name]=d[parent]@a.rest[parent].inverted()@a.rest[name]@q.to_matrix().to_4x4()
 return d

_ENTRY_TIMING=None
def entry_clock(tau):
 global _ENTRY_TIMING
 if tau>=2:return 2.
 if _ENTRY_TIMING is None:
  import json
  from pathlib import Path
  _ENTRY_TIMING=json.loads((Path(__file__).resolve().parent/'entry-timing.json').read_text())
 from bisect import bisect_right
 knots=_ENTRY_TIMING['knots_seconds'];c=_ENTRY_TIMING['cubic_coefficients'];i=max(0,min(len(knots)-2,bisect_right(knots,tau)-1));u=tau-knots[i];return ((c[0][i]*u+c[1][i])*u+c[2][i])*u+c[3][i]

def overhead(a,t):
 return overhead_raw(a,entry_clock(min(t,5-t)))

def pose(a,ID,frame,offsets=None):
 from wrist_motion import wrist_pose
 t=frame/30;d=wrist_pose(t)if ID=='1987'else overhead(a,t)
 # Accepted3905 planted hip-width lower body; upper body is translated rigidly.
 root=Vector((0,.025,.945));delta=root-a.heads['Hips'];old=d;d=a.torso(root,[0,0,0,0,0]);offsets=offsets or{}
 for n,m in old.items():
  if n not in d and not any(p in n for p in ['UpLeg','ToeBase','Foot','Leg']):d[n]=Matrix.Translation(delta)@m
 for side,sign in [('Left',1),('Right',-1)]:
  hip=d['Hips']@a.rest['Hips'].inverted()@a.heads[side+'UpLeg'];fq=a.rz(-sign*10);ankle=Vector((sign*.14,0,a.sole_height(side,fq)-.002+offsets.get(side,0)));knee,ankle=a.two_joint(hip,ankle,a.length[side+'UpLeg'],a.length[side+'Leg'],hip+Vector((sign*.055,-1,0)));uq=a.orient(side+'UpLeg',knee-hip);lq=transported(a,side+'Leg',side+'UpLeg',uq,ankle-knee);footq=fq@a.rest[side+'Foot'].to_quaternion()
  for n,h,q in[(side+'UpLeg',hip,uq),(side+'Leg',knee,lq),(side+'Foot',ankle,footq)]:d[n]=Matrix.Translation(h)@q.to_matrix().to_4x4()
  toe=d[side+'Foot']@a.rest[side+'Foot'].inverted()@a.heads[side+'ToeBase'];tq=footq@a.rest[side+'Foot'].to_quaternion().inverted()@a.rest[side+'ToeBase'].to_quaternion();d[side+'ToeBase']=Matrix.Translation(toe)@tq.to_matrix().to_4x4()
 for pb in a.rig.pose.bones:
  parent=pb.parent.name if pb.parent else None;pb.matrix_basis=a.rest[pb.name].inverted()@(a.rest[parent]@d[parent].inverted()if parent else Matrix.Identity(4))@d[pb.name]
 return d,{'frame':frame,'time':t,'grounded':['Left','Right'],'flight':False,'phase':'Enter'if t<2 else'Hold'if t<=3 else'Return'}
