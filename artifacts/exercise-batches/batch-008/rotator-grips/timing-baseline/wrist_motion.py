"""Pose-only adaptation of accepted1977 wrist grasp, retaining its contact frame."""
import math
from mathutils import Matrix,Quaternion,Vector
import authoring as a
def transported(name,parent,q,direction):
 base=q@a.rest[parent].to_quaternion().inverted()@a.rest[name].to_quaternion()
 return (base@Vector((0,1,0))).rotation_difference(direction.normalized())@base

def stable_pole(side,amount,wrist):
 shoulder=a.heads[side+'Arm'];axis0=(a.heads[side+'Hand']-shoulder).normalized();axis=(wrist-shoulder).normalized()
 initial=a.heads[side+'ForeArm']-shoulder;initial=(initial-axis0*initial.dot(axis0)).normalized()
 endpoint=Vector((-.055,.265,1.025)) if side=='Left' else Vector((-.125,.329,1.115))
 end_axis=(endpoint-shoulder).normalized();end_base=axis0.rotation_difference(end_axis)@initial
 goal=Vector(((.05 if side=='Left' else -.17),.20,-.27));goal=(goal-end_axis*goal.dot(end_axis)).normalized()
 twist=math.atan2(end_axis.dot(end_base.cross(goal)),end_base.dot(goal))
 # Parallel-transport the original bend plane, then gradually apply the known
 # endpoint axial twist. This never projects an interpolated point through the
 # limb axis and retains the reviewed final lowered-elbow silhouette.
 bend=Quaternion(axis,twist*amount)@(axis0.rotation_difference(axis)@initial)
 return shoulder+bend

def active_solution(tau):
 u=a.ease(tau/1.0);pull=a.ease((tau-1.5)/.5)
 wrist=a.heads['LeftHand'].lerp(Vector((.05,.265,1.025)),u)
 medial=a.ease((u-.25)/.75);wrist.x=a.heads['LeftHand'].x*(1-medial)+.05*medial-.105*pull;wrist.y+=.12*math.sin(math.pi*u)
 shoulder=a.heads['LeftArm'];pole=stable_pole('Left',u,wrist)
 elbow,wrist=a.two_joint(shoulder,wrist,a.length['LeftArm'],a.length['LeftForeArm'],pole)
 uq=a.orient('LeftArm',elbow-shoulder);lq=transported('LeftForeArm','LeftArm',uq,wrist-elbow)
 return u,shoulder,elbow,wrist,uq,lq
HOLD_LOWER=active_solution(2.5)[-1]
HAND_GOAL=a.orient('RightHand',(.13,-.012,-.085),(0,-1,0))

def wrist_pose(t):
 tau=min(t,5-t);u,shoulder,elbow,active,uq,lq=active_solution(tau)
 v=a.ease((tau-.65)/.85);grip=a.ease((tau-1.20)/.30);orient_amount=a.ease(v*1.7)
 d={k:m.copy() for k,m in a.rest.items()}
 d['LeftArm']=Matrix.Translation(shoulder)@uq.to_matrix().to_4x4()
 d['LeftForeArm']=Matrix.Translation(elbow)@lq.to_matrix().to_4x4()
 hq=lq@a.rest['LeftForeArm'].to_quaternion().inverted()@a.rest['LeftHand'].to_quaternion()
 d['LeftHand']=Matrix.Translation(active)@hq.to_matrix().to_4x4()
 # Once acquired, the actual grasp is transported with the active forearm.
 # The rear approach arc reaches clearance before the hand moves medially.
 relative=lq@HOLD_LOWER.inverted();target=active+relative@Vector((-.070,.064,.090))
 wrist=a.heads['RightHand'].lerp(target,v);medial=a.ease((v-.35)/.50)
 wrist.x=a.heads['RightHand'].x*(1-medial)+target.x*medial;wrist.y+=.14*math.sin(math.pi*v);wrist.z+=.18*math.sin(math.pi*v)
 shoulder=a.heads['RightArm'];pole=stable_pole('Right',v,wrist)
 elbow,wrist=a.two_joint(shoulder,wrist,a.length['RightArm'],a.length['RightForeArm'],pole)
 original_upper=a.tails['RightArm']-a.heads['RightArm'];original_lower=a.tails['RightForeArm']-a.heads['RightForeArm']
 transport=(a.frame(elbow-shoulder,(elbow-shoulder).cross(wrist-elbow))@a.frame(original_upper,original_upper.cross(original_lower)).transposed()).to_quaternion()
 uq=transport@a.rest['RightArm'].to_quaternion();lq=transported('RightForeArm','RightArm',uq,wrist-elbow)
 hq=lq@a.rest['RightForeArm'].to_quaternion().inverted()@a.rest['RightHand'].to_quaternion();hq=hq.slerp(relative@HAND_GOAL,orient_amount)
 d['RightArm']=Matrix.Translation(shoulder)@uq.to_matrix().to_4x4();d['RightForeArm']=Matrix.Translation(elbow)@lq.to_matrix().to_4x4();d['RightHand']=Matrix.Translation(wrist)@hq.to_matrix().to_4x4()
 for name,(head,tail,parent,digit,index) in a.finger_specs.items():
  sign=1 if name.startswith('Left') else -1
  axis=(tail-head).normalized().cross(Vector((-sign,0,0))).normalized();local=a.rest[name].to_3x3().inverted()@axis
  if name.startswith('Right'):
   scale={'Index':.75,'Middle':.75,'Ring':.6,'Little':.5,'Thumb':.6}[digit]
   angle=([30,45,30][index] if digit!='Thumb' else [15,24,12][index])*grip*scale
  else:angle=[6,10,7][index]*u
  q=Quaternion(local,math.radians(angle))
  if name=='RightThumb1':
   axis=a.rest[name].to_3x3().inverted()@Vector((1,0,0));q=Quaternion(axis,math.radians(-60*orient_amount))@q
  d[name]=d[parent]@a.rest[parent].inverted()@a.rest[name]@q.to_matrix().to_4x4()
 return d
