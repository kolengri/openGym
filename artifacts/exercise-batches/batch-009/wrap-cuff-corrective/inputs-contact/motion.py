"""Four source-facing standing arm demonstrations; authored 5-second cycles."""
import math
from mathutils import Vector, Matrix, Quaternion
IDS=['1405','4515','3995','1404']
SIDES=[('Left',1),('Right',-1)]
def smooth(x):
 x=max(0.,min(1.,x));return x*x*x*(x*(x*6-15)+10)
def path(t,knots):
 for (ta,pa),(tb,pb)in zip(knots,knots[1:]):
  if t<=tb:return Vector(pa).lerp(Vector(pb),smooth((t-ta)/(tb-ta)))
 return Vector(knots[-1][1])
def state(frame,ID):
 t=frame/30
 if ID=='3995':
  cycle=min(1,int(t/2.5));u=(t-cycle*2.5)/2.5;p=math.sin(math.pi*u)**2
  return dict(frame=frame,time=t,grounded=['Left','Right'],flight=False,tau=u*2,amount=p,top='Right',phase='Wrap to opposite upper back'if u<.5 else'Reopen outside shoulders')
 tau=min(t,5-t,2);p=smooth(tau/2)
 return dict(frame=frame,time=t,grounded=['Left','Right'],flight=False,tau=tau,amount=p,top='Right',phase='Enter'if t<2 else'Hold'if t<=3 else'Return')
def transported(a,name,parent,q,direction):
 base=q@a.rest[parent].to_quaternion().inverted()@a.rest[name].to_quaternion()
 return(base@Vector((0,1,0))).rotation_difference(direction.normalized())@base
def hand_frame(sign,direction,palm):
 y=Vector(direction).normalized();x=Vector(palm)*(-sign);x-=y*x.dot(y);x.normalize();z=x.cross(y).normalized();return Matrix((x,y,z)).transposed().to_quaternion()
def arm(a,d,side,elbow,wrist,handq,amount,hinge=False):
 sh=d[side+'Shoulder']@a.rest[side+'Shoulder'].inverted()@a.heads[side+'Arm'];upper=elbow-sh;lower=wrist-elbow
 # The shoulder owns the upper-arm frame; the forearm inherits that frame.
 aq=transported(a,side+'Arm',side+'Shoulder',d[side+'Shoulder'].to_quaternion(),upper)
 if hinge:
  ru=(a.tails[side+'Arm']-a.heads[side+'Arm']).normalized();rl=(a.tails[side+'ForeArm']-a.heads[side+'ForeArm']).normalized();ref=ru.cross(rl).normalized();target=upper.cross(lower).normalized();pred=(aq@a.rest[side+'Arm'].to_quaternion().inverted())@ref;axis=upper.normalized();theta=math.atan2(axis.dot(pred.cross(target)),pred.dot(target));aq=Quaternion(axis,theta*smooth(amount/.65))@aq
 fq=transported(a,side+'ForeArm',side+'Arm',aq,lower)
 for n,h,q in[(side+'Arm',sh,aq),(side+'ForeArm',elbow,fq),(side+'Hand',wrist,handq)]:d[n]=Matrix.Translation(h)@q.to_matrix().to_4x4()
def pose(a,frame,ID,base_pose,offsets=None):
 st=state(frame,ID);tau=st['tau'];p=st['amount'];offsets=offsets or{};d,_=base_pose(a,0,'6014',offsets)
 rounded=smooth((tau-1.05)/.95)if ID=='1404'else 0
 if rounded:
  torso=a.torso(Vector((0,.025,.945)),[0,5*rounded,17*rounded,24*rounded,29*rounded])
  for n in ['Hips','Spine','Spine1','Neck','Head']:d[n]=torso[n]
 cq=d['Spine1'].to_quaternion()@a.rest['Spine1'].to_quaternion().inverted();reach={};grip=smooth((tau-.9)/.25)if ID!='3995'else 0
 for side,sign in SIDES:
  if ID=='3995':pro=53*p
  elif ID=='4515':pro=-8*p
  else:pro=(23 if ID=='1404'else 28)*smooth(tau/1.5)
  n=side+'Shoulder';h=d['Spine1']@a.rest['Spine1'].inverted()@a.heads[n];q=cq@a.rz(-sign*pro)@a.rest[n].to_quaternion();d[n]=Matrix.Translation(h)@q.to_matrix().to_4x4()
  if ID=='3995':
   stack=smooth(p/.65);d[n].translation+=Vector((0,-.04*stack,(.04 if side==st['top']else-.025)*stack))
  sh=d[n]@a.rest[n].inverted()@a.heads[side+'Arm'];neutral=a.heads[side+'Hand']+Vector((0,.025,-.005));neutralq=a.rest[side+'Hand'].to_quaternion()
  if ID=='1404':
   wrist=path(tau,[(0,neutral),(.70,(sign*.24,-.37,1.12)),(.95,(sign*.100,-.43,1.20+(.006 if side=='Right'else-.006))),(1.15,(sign*.100,-.43,1.20+(.006 if side=='Right'else-.006))),(1.35,(sign*.0645,-.44,1.20+(.006 if side=='Right'else-.006))),(2,(sign*.0645,-.635,1.34+(.006 if side=='Right'else-.006)))])
   pole=sh+Vector((sign*.23,-.10,-.40));goal=hand_frame(sign,(0,-1,0),(-sign,0,0));orient=smooth(tau/.90)
  elif ID=='1405':
   # The two hooked hands share one long axis. A half-row transverse stagger
   # interleaves the fingers while the reachable forearms retain over/under depth.
   wrist=path(tau,[(0,neutral),(.52,(sign*.26,-.40,1.36+(.10 if side=='Right'else-.10))),(.90,(-sign*.19,-.35,1.40+(.20 if side=='Right'else-.20))),(1.15,(-sign*.19,-.35,1.40+(.20 if side=='Right'else-.20))),(1.35,(-sign*.120361,-.43,1.40-sign*.085712)),(2,(-sign*.120361,-.40,1.60-sign*.085712))])
   top=side=='Right';elbow_back=.16*math.sin(math.pi*(tau-4/3)/(2-4/3))**2 if top and 4/3<tau<2 else 0.;pole=sh+Vector((sign*.32,-.20+elbow_back,.18 if top else-.24));goal=hand_frame(sign,(sign,0,sign*.625),(0,-1,0));orient=smooth((tau-.40)/.50)
  elif ID=='4515':
   wrist=path(tau,[(0,neutral),(.60,(sign*.30,.22,.96)),(.95,(sign*.100,.27,.96+(.006 if side=='Right'else-.006))),(1.15,(sign*.100,.27,.96+(.006 if side=='Right'else-.006))),(1.35,(sign*.0615,.27,.96+(.006 if side=='Right'else-.006))),(2,(sign*.0615,.35,1.025+(.006 if side=='Right'else-.006)))])
   pole=sh+Vector((sign*.3,.20,-.35));goal=hand_frame(sign,(0,.2,-.98),(-sign,0,0));orient=smooth((tau-.35)/.60)
  else:
   top=side==st['top'];z=1.43+(.075 if top else-.075)
   # One coherent top-hand tangent frame and palm placement, computed from the
   # opposite posterior shoulder patch; the fingers retain their relaxed pose.
   held=(.165440619,-.119581543,1.495350003) if top else(-sign*.22,-.09,z)
   wrist=path(p,[(0,(sign*.68,-.03,1.43)),(.35,(sign*.46,-.35,1.43+(.10 if top else-.10))),(.70,(-sign*.34,-.22,1.43+(.125 if top else-.125))),(.88,(-sign*.30,-.12,1.43+(.09 if top else-.09))),(1,held)]);pole=sh+Vector((sign*.10,-.40,-.15*(1-p)+(.16 if top else-.20)*p))
   goal=Quaternion((.248861015,-.002205274,.967699587,-.040260226)) if top else hand_frame(sign,(sign*.10,.95,.30),(sign*.85,-.50,0));orient=smooth((p-.82)/.18);theta=math.pi*smooth(p/.80);neutralq=hand_frame(sign,(sign*math.cos(theta),-math.sin(theta),0),(0,0,-1))
  elbow,wrist_actual=a.two_joint(sh,wrist,a.length[side+'Arm'],a.length[side+'ForeArm'],pole);reach[side]=float((wrist_actual-wrist).length);wrist=wrist_actual
  handq=neutralq.slerp(goal,orient);arm(a,d,side,elbow,wrist,handq,p,hinge=ID=='3995')
 for name,(head,tail,parent,digit,index)in a.finger_specs.items():
  sign=1 if name.startswith('Left')else-1;side='Left'if sign==1 else'Right';palmar=a.rest[side+'Hand'].to_3x3()@Vector((-sign,0,0));axis=a.rest[name].to_3x3().inverted()@(tail-head).normalized().cross(palmar).normalized()
  relaxed=([4,8,5]if digit=='Thumb'else[8,12,5])[index];target=([12,25,18]if digit=='Thumb'else[38,65,40])[index];angle=relaxed+(target-relaxed)*grip
  base=d[parent]@a.rest[parent].inverted()@a.rest[name]
  if index==0 and digit!='Thumb':
   spread={'Index':-20,'Middle':-7,'Ring':8,'Little':23}[digit]*grip
   axis_global=d[side+'Hand'].to_3x3()@Vector((1,0,0));base=Matrix.Translation(base.translation)@(Quaternion(axis_global,math.radians(spread))@base.to_quaternion()).to_matrix().to_4x4()
  d[name]=base@Quaternion(axis,math.radians(angle)).to_matrix().to_4x4()
 for name,mat in d.items():d[name]=Matrix.Translation(mat.translation)@mat.to_quaternion().normalized().to_matrix().to_4x4()
 for pb in a.rig.pose.bones:
  parent=pb.parent.name if pb.parent else None;pb.matrix_basis=a.rest[pb.name].inverted()@(a.rest[parent]@d[parent].inverted()if parent else Matrix.Identity(4))@d[pb.name]
 return d,{**st,'grip_fraction':grip,'rounded_upper_back_fraction':rounded,'reach_errors_m':reach}
def morph_values(frame,ID):
 st=state(frame,ID);return [0.,0.]
