"""Text-authored kneeling mechanics on the original51-bone rig."""
import math,numpy as np,importlib.util,sys
sys.dont_write_bytecode=True
from pathlib import Path
from mathutils import Matrix,Quaternion,Vector
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/"kneeling-family"))
from anatomical_frames import knee_frames

def ease(t):
 t=max(0,min(1,t));return max(0,min(1,t*t*t*(10+t*(-15+6*t))))
def M(p,q):return Matrix.Translation(p)@q.to_matrix().to_4x4()
def smooth_max(a,b,width):
 if width<1e-10 or abs(a-b)>=width:return max(a,b)
 t=(a-b)/width;return .5*(a+b)+width*(.1875+.375*t*t-.0625*t**4)
def transported(a,name,parent,q,direction):
 base=q@a.rest[parent].to_quaternion().inverted()@a.rest[name].to_quaternion();return (base@Vector((0,1,0))).rotation_difference(direction.normalized())@base

class KneelingMotion:
 def __init__(self,a):
  self.a=a;self.R=np.array([v.co[:] for v in a.body.data.vertices]);self.normals=np.array([v.normal[:] for v in a.body.data.vertices]);self.foot={};self.hand={}
  for side,sgn in [('Left',1),('Right',-1)]:
   self.foot[side]=np.flatnonzero((sgn*self.R[:,0]>.12)&(self.R[:,2]<.115));handnames={side+'Hand'}|{n for n in a.finger_specs if n.startswith(side)};rigid=np.array([sum(g.weight for g in v.groups if a.body.vertex_groups[g.group].name in handnames)>.999 for v in a.body.data.vertices]);self.hand[side]=np.flatnonzero(rigid);
  self.forehead=np.flatnonzero((self.R[:,2]>1.64)&(self.R[:,2]<1.74)&(self.R[:,1]<-.06)&(self.normals[:,1]<-.4))
  self.head=np.flatnonzero(self.R[:,2]>1.55)
  spec=importlib.util.spec_from_file_location('source_palm_frame',Path(__file__).resolve().parent.parent/'prone-family/palm_frame.py');self.palm_module=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.palm_module);self.palm_frames=self.palm_module.prepare(a)
  self.knee_heights={};self.child_thorax=105.;self.default_knee_z=.032;self.palm_height_offset={"Left":0.,"Right":0.};self.clavicle_correction=None;self.foot_offsets={}
 def foot_q(self,side,kind):
  a=self.a;sgn=1 if side=='Left' else -1
  return a.rz(sgn*15)@a.rx(145)@a.rz(-sgn*20.8) if kind=='child' else a.rx(145)@a.rz(-sgn*20.8)
 def contact_height(self,side,q):
  a=self.a;z=[(q@(Vector(self.R[i])-a.heads[side+'Foot'])).z for i in self.foot[side]];return .0005-min(z)
 def state(self,id,f):
  a=self.a;t=f/30;sgn=1 if t<4 else -1;side='Left' if sgn==1 else 'Right';half=t if t<4 else t-4
  if id=='10058':
   q=ease(half/1.4) if half<1.4 else (1 if half<1.9 else 1-ease((half-1.9)/1.4));kw=.18;aw=.18;kz=self.knee_heights.get((id,f),self.default_knee_z);root=Vector((-sgn*.025*q,.04-.10*q,0));rear='Right' if side=='Left' else 'Left';dy=root.y;dx=root.x+(-1 if rear=='Left' else 1)*(.18-.105);root.z=kz+math.sqrt(a.length[rear+'UpLeg']**2-dx*dx-dy*dy)+.03;pitches=[0]*5;feet={}
   for ss,sign in [('Left',1),('Right',-1)]:
    fq=self.foot_q(ss,'kneel');az=self.contact_height(ss,fq);ay=math.sqrt(a.length[ss+'Leg']**2-(az-kz)**2);ankle=Vector((sign*aw,ay,az));support='dorsum'
    if ss==side:
     flat=a.rz(-sign*8.8);fz=self.contact_height(ss,flat);ankle=ankle.lerp(Vector((sign*aw,-.43,fz)),q);ankle.z+=.12*math.sin(math.pi*q);fq=fq.slerp(flat,q);lift=math.sin(math.pi*q)**2;ankle.z=smooth_max(ankle.z,self.contact_height(ss,fq)+.003*lift,.002*lift);support='sole' if q>1-1e-7 else ('dorsum' if q<1e-7 else 'airborne')
    feet[ss]={'ankle':ankle,'q':fq,'support':support,'knee':Vector((sign*kw,0,kz))}
   return {'id':id,'frame':f,'q':q,'root':root,'pitches':pitches,'side':side,'feet':feet,'active':side,'hand_contact':False,'forehead_contact':False}
  q=ease(t/2) if t<2 else (1 if t<=3 else 1-ease((t-3)/2));kw=.30;aw=.11;kz=self.knee_heights.get((id,f),self.default_knee_z);rootz=(kz+math.sqrt(a.length['LeftUpLeg']**2-(kw-.105)**2-.04**2)+.03)*(1-q)+.22*q;pelvis=75*q;hipoff=a.rx(pelvis)@(a.heads['LeftUpLeg']-a.heads['Hips']);dz=rootz+hipoff.z-kz;rooty=math.sqrt(a.length['LeftUpLeg']**2-(kw-.105)**2-dz*dz)-hipoff.y;feet={}
  for ss,sign in [('Left',1),('Right',-1)]:
   fq=self.foot_q(ss,'child');az=self.contact_height(ss,fq)+self.foot_offsets.get(f,0.);ay=math.sqrt(a.length[ss+'Leg']**2-(aw-kw)**2-(az-kz)**2);feet[ss]={'ankle':Vector((sign*aw,ay,az)),'q':fq,'support':'dorsum','knee':Vector((sign*kw,0,kz))}
  return {'id':id,'frame':f,'q':q,'root':Vector((0,rooty,rootz)),'pitches':[pelvis,95*q,self.child_thorax*q,110*q,120*q],'side':None,'feet':feet,'hand_contact':q>1-1e-7,'forehead_contact':q>1-1e-7}
 def pose(self,id,f):
  a=self.a;st=self.state(id,f);d=a.torso(st['root'],st['pitches']);errors={}
  for side,sgn in [('Left',1),('Right',-1)]:
   fp=st['feet'][side];hip=d['Hips']@a.rest['Hips'].inverted()@a.heads[side+'UpLeg'];ankle=fp['ankle']
   if id=='10058' and side==st['active'] and st['q']>1e-7:
    pole=fp['knee'].lerp(hip+Vector((sgn*.12,-1,0)),st['q'])
    knee,actual=a.two_joint(hip,ankle,a.length[side+'UpLeg'],a.length[side+'Leg'],pole)
   else:knee=fp['knee'];actual=ankle
   errors[side+'_upper_length_m']=abs((hip-knee).length-a.length[side+'UpLeg']);errors[side+'_lower_length_m']=abs((knee-actual).length-a.length[side+'Leg']);errors[side+'_ankle_target_m']=(actual-ankle).length;parentq=d['Hips'].to_quaternion()@a.rest['Hips'].to_quaternion().inverted();uq,lq,hinge=knee_frames(a,side,hip,knee,actual,parentq);errors[side+'_hinge_fallback']=hinge['fallback_used'];errors[side+'_hinge_sine']=hinge['hinge_sine'];fp['knee']=knee;fp['ankle']=actual;d[side+'UpLeg']=M(hip,uq);d[side+'Leg']=M(knee,lq);fq=fp['q']@a.rest[side+'Foot'].to_quaternion();d[side+'Foot']=M(actual,fq);toe=d[side+'Foot']@a.rest[side+'Foot'].inverted()@a.heads[side+'ToeBase'];d[side+'ToeBase']=M(toe,fp['q']@a.rest[side+'ToeBase'].to_quaternion())
  for side,sgn in [('Left',1),('Right',-1)]:
   sh=side+'Shoulder';d[sh]=d['Spine1']@a.rest['Spine1'].inverted()@a.rest[sh];
   if self.clavicle_correction:
    from clavicle import shoulder as clavicle_frame
    d[sh]=clavicle_frame(a,side,d['Spine1'],st['q'],self.clavicle_correction)
   shoulder=d[sh]@a.rest[sh].inverted()@a.heads[side+'Arm'];restw=shoulder+(a.heads[side+'Hand']-a.heads[side+'Arm']);wrist=restw;hq=None
   relaxed=Vector((sgn*.20,-.045,-.46))
   if id=='10058':wrist=shoulder+relaxed;pole=shoulder+Vector((sgn*.18,-.10,-.25))
   else:
    hq=self.palm_module.hand(a,side,(sgn*.04,-math.cos(math.radians(4)),math.sin(math.radians(4))),(0,0,-1),self.palm_frames);offset=np.array([hq@a.rest[side+'Hand'].to_quaternion().inverted()@(Vector(self.R[i])-a.heads[side+'Hand']) for i in self.palm_frames[side]['source_ids']]);wz=.001-float(offset[:,2].min())+self.palm_height_offset[side];peak=self.state(id,75);pd=a.torso(peak['root'],peak['pitches']);psh=pd['Spine1']@a.rest['Spine1'].inverted()@a.heads[side+'Arm'];dx=sgn*.18-psh.x;reach=(a.length[side+'Arm']+a.length[side+'ForeArm'])*.985;drop=psh.z-wz;dy=math.sqrt(max(.0001,reach**2-dx*dx-drop*drop));target=Vector((dx,-dy,-drop));turn=relaxed.normalized().rotation_difference(target.normalized());direction=Quaternion().slerp(turn,st['q'])@relaxed.normalized();wrist=shoulder+direction*((1-st['q'])*relaxed.length+st['q']*target.length);pole=shoulder+Vector((sgn*.20,0,.2))
   elbow,actual=a.two_joint(shoulder,wrist,a.length[side+'Arm'],a.length[side+'ForeArm'],pole);errors[side+'_wrist_target_m']=(actual-wrist).length;parentq=d[sh].to_quaternion()@a.rest[sh].to_quaternion().inverted();uq=parentq@a.orient(side+'Arm',parentq.inverted()@(elbow-shoulder));lq=transported(a,side+'ForeArm',side+'Arm',uq,actual-elbow);handq=lq@a.rest[side+'ForeArm'].to_quaternion().inverted()@a.rest[side+'Hand'].to_quaternion();handq=handq.slerp(hq,st['q']) if hq else handq;d[side+'Arm']=M(shoulder,uq);d[side+'ForeArm']=M(elbow,lq);d[side+'Hand']=M(actual,handq)
  for name,(head,tail,parent,digit,index) in a.finger_specs.items():d[name]=d[parent]@a.rest[parent].inverted()@a.rest[name]
  for pb in a.rig.pose.bones:
   parent=pb.parent.name if pb.parent else None;pb.matrix_basis=a.rest[pb.name].inverted()@(a.rest[parent]@d[parent].inverted() if parent else Matrix.Identity(4))@d[pb.name]
  return d,st,errors
