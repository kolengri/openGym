"""Text-authored standing-leg trajectories on the immutable51-bone source rig."""
import math
import numpy as np
from mathutils import Matrix,Quaternion,Vector

def ease(t):
 t=max(0,min(1,t));return max(0,min(1,t*t*t*(10+t*(-15+6*t))))
def M(head,q):return Matrix.Translation(head)@q.to_matrix().to_4x4()
def transported(a,name,parent,q,direction):
 base=q@a.rest[parent].to_quaternion().inverted()@a.rest[name].to_quaternion()
 return (base@Vector((0,1,0))).rotation_difference(direction.normalized())@base

def stable_arm_pole(a,side,shoulder,wrist,goal,amount):
 axis0=(a.heads[side+'Hand']-a.heads[side+'Arm']).normalized();axis=(wrist-shoulder).normalized();initial=a.heads[side+'ForeArm']-a.heads[side+'Arm'];initial=(initial-axis0*initial.dot(axis0)).normalized();base=axis0.rotation_difference(axis)@initial;target=goal-shoulder;target-=axis*target.dot(axis)
 if target.length<1e-7:return shoulder+base
 target.normalize();twist=math.atan2(axis.dot(base.cross(target)),base.dot(target));return shoulder+Quaternion(axis,twist*amount)@base

class StandingLegPoses:
 def __init__(self,a):
  self.a=a;self.body=a.body;self.rig=a.rig
  self.R=np.array([v.co[:] for v in self.body.data.vertices]);self.normal=np.array([v.normal[:] for v in self.body.data.vertices]);self.foot={};self.heel={};self.palm={}
  for side,sign in [('Left',1),('Right',-1)]:
   ids=np.flatnonzero((sign*self.R[:,0]>.12)&(self.R[:,2]<.012));weights=np.zeros((len(ids),2))
   for row,i in enumerate(ids):
    gs={self.body.vertex_groups[g.group].name:g.weight for g in self.body.data.vertices[int(i)].groups}
    weights[row]=[gs.get(side+'Foot',0),gs.get(side+'ToeBase',0)]
   assert np.max(abs(weights.sum(1)-1))<2e-6
   self.foot[side]=(ids,weights)
   mask=(sign*self.R[:,0]>.13)&(sign*self.R[:,0]<.25)&(self.R[:,1]>.105)&(self.R[:,2]>.02)&(self.R[:,2]<.075)&(self.normal[:,1]>.4)
   heelids=np.flatnonzero(mask);assert len(heelids)>2
   # A medial/posterior heel skin point, not an ankle/toe joint proxy.
   medial=(sign*self.R[:,0]>.13)&(sign*self.R[:,0]<.25)&(self.R[:,1]>.105)&(self.R[:,1]<.13)&(self.R[:,2]>.025)&(self.R[:,2]<.045)&((-sign*self.normal[:,0])>.95)
   apex=int(np.flatnonzero(medial)[np.argmin(sign*self.R[np.flatnonzero(medial),0])]);self.heel[side]={'ids':heelids,'apex':apex,'rest':Vector(self.R[apex]),'normal':Vector((-sign,0,0))}
   # Relaxed fingertip offset is derived from the actual distal skin and its
   # original finger weights, so the contact target is a skin point.
   fd={side+'Hand':a.rest[side+'Hand']}
   for name,(head,tail,parent,digit,index) in a.finger_specs.items():
    if not name.startswith(side):continue
    axis=a.rest[name].to_3x3().inverted()@(tail-head).normalized().cross(Vector((-sign,0,0))).normalized();fd[name]=fd[parent]@a.rest[parent].inverted()@a.rest[name]@Quaternion(axis,math.radians([5,10,7][index])).to_matrix().to_4x4()
   gi=self.body.vertex_groups[side+'Little3'].index;tipids=[v.index for v in self.body.data.vertices if any(g.group==gi and g.weight>.99 for g in v.groups)];tip=int(min(tipids,key=lambda i:(self.R[i]-np.array(a.tails[side+'Little3'])).dot(self.R[i]-np.array(a.tails[side+'Little3']))));co=Vector((0,0,0))
   for g in self.body.data.vertices[tip].groups:
    name=self.body.vertex_groups[g.group].name;co+=(fd.get(name,a.rest[name])@a.rest[name].inverted()@Vector(self.R[tip]))*g.weight
   self.heel[side]['finger_id']=tip;self.heel[side]['finger_offset']=a.rest[side+'Hand'].to_quaternion().inverted()@(co-a.heads[side+'Hand']);self.heel[side]['distal_vector']=a.rest[side+'ForeArm'].to_quaternion().inverted()@(co-a.heads[side+'ForeArm'])
   handgroup=self.body.vertex_groups[side+'Hand'].index
   rigid=np.array([any(g.group==handgroup and g.weight>.999 for g in v.groups) for v in self.body.data.vertices])
   mask=rigid&(sign*self.R[:,0]>.365)&(sign*self.R[:,0]<.445)&(self.R[:,2]>.875)&(self.R[:,2]<.928)&((-sign*self.normal[:,0])>.65)
   pids=np.flatnonzero(mask);assert len(pids)>3,(side,len(pids));self.palm[side]={'ids':pids,'rest':Vector(self.R[pids].mean(0))}
 def flatq(self,side):return self.a.rz(-(1 if side=='Left' else -1)*8.8)
 def foot_height(self,side,qf,qt):
  a=self.a;ids,W=self.foot[side];F=np.array([qf@(Vector(p)-a.heads[side+'Foot']) for p in self.R[ids]])
  T=np.array([qf@(a.heads[side+'ToeBase']-a.heads[side+'Foot'])+qt@(Vector(p)-a.heads[side+'ToeBase']) for p in self.R[ids]])
  return -float((F*W[:,0,None]+T*W[:,1,None])[:,2].min())+.0003
 def bladeq(self,side):
  sign=1 if side=='Left' else -1
  # Source forward(-Y)->upZ; source sole(-Z)->outward lateralX.
  return Matrix(((0,0,-sign),(sign,0,0),(0,-1,0))).to_quaternion()@self.a.rz(-sign*20.8)
 def state(self,id,f):
  t=f/30;half=min(2.5,t if t<2.5 else t-2.5);side='Left' if t<2.5 else 'Right';sign=1 if side=='Left' else -1
  feet={}
  for ss,sgn in [('Left',1),('Right',-1)]:
   fq=self.flatq(ss);feet[ss]={'ankle':Vector((sgn*.16,.078,self.foot_height(ss,fq,fq))),'footq':fq,'toeq':fq,'support':'whole_sole'}
  if id=='3479':
   squat=ease(half/.60) if half<=.60 else (1-ease((half-.60)/.45) if half<=1.05 else 0)
   kick=ease((half-.60)/.50) if half<=1.10 else (1 if half<=1.55 else 1-ease((half-1.55)/.95))
   contact=ease((half-1.0)/.20) if half<=1.20 else (1 if half<=1.55 else 1-ease((half-1.55)/.35))
   root=Vector((-sign*.10*kick,.04+.26*squat,.959-.504*squat-.029*kick+.0003));pitches=[22*squat,24*squat,20*squat,10*squat,4*squat];bend=sign*30*kick
   active=feet[side];flat=self.flatq(side);fq=flat.slerp(self.bladeq(side),kick)
   full=Vector((sign*.76,.078,.97));tap=Vector((sign*.58,.078,1.08));end=full.lerp(tap,contact);active['ankle']=active['ankle'].lerp(end,kick);active['footq']=active['toeq']=fq;active['support']='airborne' if kick>1e-7 else 'whole_sole'
   return {'id':id,'frame':f,'half':half,'side':side,'sign':sign,'root':root,'pitches':pitches,'bend':bend,'squat':squat,'kick':kick,'contact':contact,'feet':feet}
  q=math.sin(math.pi*half/2.5)**2
  step=ease(half/.50) if half<.50 else (1 if half<=1.9 else 1-ease((half-1.9)/.60))
  q=q+.35*step*(1-q)
  rear=feet[side];fq=self.a.rx(50*step)@self.flatq(side);qt=self.flatq(side)
  height=self.foot_height(side,fq,qt);lift=.075*math.sin(math.pi*half/.50) if half<.50 else (.075*math.sin(math.pi*(half-1.9)/.60) if half>1.9 else 0)
  rear.update({'ankle':Vector((sign*.16,.078+.70*step,height+lift)),'footq':fq,'toeq':qt,'support':'airborne' if (0<half<.5 or 1.9<half<2.5) else ('rear_toes' if step>.99 else 'whole_sole')})
  return {'id':id,'frame':f,'half':half,'side':side,'sign':sign,'root':Vector((-sign*.035*q,.04+.19*q,.959-.369*q+.0003)),'pitches':[0,0,0,0,0],'bend':0,'lunge':q,'step':step,'feet':feet}
 def pose(self,id,f):
  a=self.a;st=self.state(id,f);d=a.torso(st['root'],st['pitches'],bend=st['bend']);errors={}
  for side,sign in [('Left',1),('Right',-1)]:
   fp=st['feet'][side];hip=d['Hips']@a.rest['Hips'].inverted()@a.heads[side+'UpLeg'];ankle=fp['ankle'];pole=hip+Vector((sign*.25,-1,0))
   if id=='3479' and side==st['side'] and st['kick']>0:
    pole=pole.lerp(hip+Vector((sign*.30,-.6,.2)),st['kick'])
   knee,actual=a.two_joint(hip,ankle,a.length[side+'UpLeg'],a.length[side+'Leg'],pole);errors[side+'_ankle_target']=float((actual-ankle).length)
   uq=a.orient(side+'UpLeg',knee-hip);lq=transported(a,side+'Leg',side+'UpLeg',uq,actual-knee)
   d[side+'UpLeg']=M(hip,uq);d[side+'Leg']=M(knee,lq);d[side+'Foot']=M(actual,fp['footq']@a.rest[side+'Foot'].to_quaternion());toe=d[side+'Foot']@a.rest[side+'Foot'].inverted()@a.heads[side+'ToeBase'];d[side+'ToeBase']=M(toe,fp['toeq']@a.rest[side+'ToeBase'].to_quaternion())
  for side,sign in [('Left',1),('Right',-1)]:
   sh=side+'Shoulder';d[sh]=d['Spine1']@a.rest['Spine1'].inverted()@a.rest[sh];shoulder=d[sh]@a.rest[sh].inverted()@a.heads[side+'Arm'];restw=shoulder+(a.heads[side+'Hand']-a.heads[side+'Arm']);wrist=restw;pole=shoulder+(a.heads[side+'ForeArm']-a.heads[side+'Arm']);pole_amount=0;handgoal=None;touch=0;palmnormal=None;contact_lq=None;contact_elbow=None
   if id=='3479':
    reach=math.sqrt(a.length[side+'Arm']**2+a.length[side+'ForeArm']**2+2*a.length[side+'Arm']*a.length[side+'ForeArm']*math.cos(math.radians(10)))
    sw=shoulder+Vector((sign*.025,-math.cos(math.radians(30)),-math.sin(math.radians(30)))).normalized()*reach;wrist=restw.lerp(sw,st['squat'])
    if side==st['side']:
     wrist=wrist.lerp(shoulder+Vector((sign*.30,-.30,-.07)),st['kick']);pole_amount=st['kick'];touch=st['contact'];heelinfo=self.heel[side];fp=st['feet'][side];heel=fp['ankle']+fp['footq']@(heelinfo['rest']-a.heads[side+'Foot']);out=fp['footq']@heelinfo['normal'];palmnormal=-out;pole=shoulder+Vector((sign*.3,-.75,-.10));tiptarget=heel+out*.003;dv=heelinfo['distal_vector'];ce,ct=a.two_joint(shoulder,tiptarget,a.length[side+'Arm'],dv.length,pole);cuq=a.orient(side+'Arm',ce-shoulder);cb=cuq@a.rest[side+'Arm'].to_quaternion().inverted()@a.rest[side+'ForeArm'].to_quaternion();contact_lq=(cb@dv).rotation_difference(ct-ce)@cb;cw=ce+contact_lq@a.rest[side+'ForeArm'].to_quaternion().inverted()@(a.heads[side+'Hand']-a.heads[side+'ForeArm']);wrist=wrist.lerp(cw,touch);contact_elbow=ce;st['heel_contact_point']=list(heel);st['heel_contact_normal']=list(out);st['palm_target_point']=list(heel+out*.003)
    else:
     counter=shoulder+Vector((sign*.40,-.12,-.15));wrist=wrist.lerp(counter,st['kick']);pole=shoulder+Vector((sign*.4,.1,-.3));pole_amount=st['kick']
   else:
    q=st['lunge'];forward=side==st['side'];offset=Vector((sign*.05,-.30,-.035)) if forward else Vector((sign*.11,.28,-.34));target=shoulder+offset;wrist=restw.lerp(target,q);pole=shoulder+Vector((sign*.15,-.10 if forward else .32,-.27 if forward else -.12));pole_amount=q
   pole=stable_arm_pole(a,side,shoulder,wrist,pole,pole_amount)
   if contact_elbow is not None:pole=pole.lerp(contact_elbow,touch)
   elbow,actual=a.two_joint(shoulder,wrist,a.length[side+'Arm'],a.length[side+'ForeArm'],pole);errors[side+'_wrist_target']=float((actual-wrist).length);uq=a.orient(side+'Arm',elbow-shoulder);lq=transported(a,side+'ForeArm',side+'Arm',uq,actual-elbow);lq=lq.slerp((contact_lq@Vector((0,1,0))).rotation_difference((actual-elbow).normalized())@contact_lq,touch) if contact_lq is not None else lq;default_hand=lq@a.rest[side+'ForeArm'].to_quaternion().inverted()@a.rest[side+'Hand'].to_quaternion();hq=default_hand.slerp(handgoal,touch) if handgoal else default_hand
   d[side+'Arm']=M(shoulder,uq);d[side+'ForeArm']=M(elbow,lq);d[side+'Hand']=M(actual,hq)
  for name,(head,tail,parent,digit,index) in a.finger_specs.items():
   sign=1 if name.startswith('Left') else -1;axis=a.rest[name].to_3x3().inverted()@(tail-head).normalized().cross(Vector((-sign,0,0))).normalized();curl=([5,10,7] if id=='3479' else ([25,35,20] if digit=='Thumb' else [50,65,35]))[index];d[name]=d[parent]@a.rest[parent].inverted()@a.rest[name]@Quaternion(axis,math.radians(curl)).to_matrix().to_4x4()
  for pb in self.rig.pose.bones:
   parent=pb.parent.name if pb.parent else None;pb.matrix_basis=a.rest[pb.name].inverted()@(a.rest[parent]@d[parent].inverted() if parent else Matrix.Identity(4))@d[pb.name]
  return d,st,errors
