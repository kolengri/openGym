"""Source-facing prone and supported archer cycles on the original skeleton."""
import math
from mathutils import Matrix,Quaternion,Vector
import palm_frame
PALM_FRAMES=None
def configure(a):
 global PALM_FRAMES
 PALM_FRAMES=palm_frame.prepare(a)

def smooth(x):
 x=max(0.,min(1.,x));return x*x*x*(10+x*(-15+6*x))

def schedule(frame,exercise):
 f=frame%150;half=int(f//75);u=f-half*75
 # Each side: .5s lift/lower, one-second hold, .5s return, .5s neutral.
 if exercise in ['4702','4715']:
  p=smooth(u/15) if u<15 else 1. if u<45 else 1-smooth((u-45)/15) if u<60 else 0.
  return {'envelope':p,'arm':'Right'if half==0 else'Left','leg':'Left'if half==0 else'Right','phase':'Lift'if u<15 else'Hold'if u<45 else'Lower'if u<60 else'Neutral'}
 p=smooth(u/30) if u<30 else 1-smooth((u-30)/30) if u<60 else 0.
 return {'envelope':p,'load_side':'Right'if half==0 else'Left','phase':'Lower toward load arm'if u<30 else'Press to center'if u<60 else'High plank'}

def transported(a,name,parent,q,direction):
 base=q@a.rest[parent].to_quaternion().inverted()@a.rest[name].to_quaternion()
 return (base@Vector((0,1,0))).rotation_difference(direction.normalized())@base

def pose(a,frame,exercise,root_z=None,contact_offsets=None):
 state=schedule(frame,exercise);p=state['envelope'];offset=contact_offsets or{};superman=exercise in ['4702','4715']
 if superman:
  root=Vector((0,.04,.15 if root_z is None else root_z));d=a.torso(root,[90,88,84,84,84])
 else:
  sign=-1 if state['load_side']=='Right'else 1
  root=Vector((sign*.129*p,.01,.370-.180*p if root_z is None else root_z));pitch=80+4*p
  # A small pelvic yaw balances the two fixed toe reaches during lateral
  # transfer. Solve both exact leg reaches rather than bending/sliding toes.
  rz=0.;ry=.01
  def residual(y,ang):
   q=a.rz(ang)@a.rx(pitch);rr=Vector((root.x,y,root.z));vals=[]
   for ss,sg in [('Left',1),('Right',-1)]:
    hh=rr+q@(a.heads[ss+'UpLeg']-a.heads['Hips']);ank=Vector((sg*.18,.84,.18+offset.get(ss+'_foot',0)));reach=a.length[ss+'UpLeg']+a.length[ss+'Leg']-.0006;vals.append((ank-hh).length_squared-reach*reach)
   return vals
  for _ in range(8):
   v=residual(ry,rz)
   if max(abs(x)for x in v)<1e-12:break
   dy=residual(ry+1e-4,rz);da=residual(ry,rz+1e-3);A=(dy[0]-v[0])/1e-4;B=(da[0]-v[0])/1e-3;C=(dy[1]-v[1])/1e-4;D=(da[1]-v[1])/1e-3;det=A*D-B*C
   ry-=(D*v[0]-B*v[1])/det;rz-=(-C*v[0]+A*v[1])/det
  root.y=ry;d={}
  for n,yaw in [('Hips',rz),('Spine',0),('Spine1',sign*12*p),('Neck',sign*12*p),('Head',sign*12*p)]:
   parent=a.rig.data.bones[n].parent;h=root if parent is None else d[parent.name]@a.rest[parent.name].inverted()@a.heads[n];q=a.rz(yaw)@a.rx(pitch)@a.rest[n].to_quaternion();d[n]=Matrix.Translation(h)@q.to_matrix().to_4x4()
 cq=d['Spine1'].to_quaternion()@a.rest['Spine1'].to_quaternion().inverted();reach={}
 for side,sign in [('Left',1),('Right',-1)]:
  hip=d['Hips']@a.rest['Hips'].inverted()@a.heads[side+'UpLeg']
  if superman:
   lift=p if side==state['leg']else 0.;legdir=Vector((sign*.035,math.cos(math.radians(-8.4+20.4*lift)),math.sin(math.radians(-8.4+20.4*lift)))).normalized()
   knee=hip+legdir*a.length[side+'UpLeg'];ankle=knee+legdir*a.length[side+'Leg']
   uq=a.orient(side+'UpLeg',legdir);lq=transported(a,side+'Leg',side+'UpLeg',uq,legdir);fq=a.rx(150+20*lift)@a.rz(-sign*20.8);tq=fq
  else:
   fq=a.rx(50)@a.rz(-sign*20.8);tq=a.rz(-sign*20.8);ankle=Vector((sign*.18,.84,.18+offset.get(side+'_foot',0)))
   knee,actual=a.two_joint(hip,ankle,a.length[side+'UpLeg'],a.length[side+'Leg'],hip+Vector((0,-.1,-1)));reach[side+'_ankle']=float((actual-ankle).length);ankle=actual
   uq=a.orient(side+'UpLeg',knee-hip);lq=transported(a,side+'Leg',side+'UpLeg',uq,ankle-knee)
  d[side+'UpLeg']=Matrix.Translation(hip)@uq.to_matrix().to_4x4();d[side+'Leg']=Matrix.Translation(knee)@lq.to_matrix().to_4x4();d[side+'Foot']=Matrix.Translation(ankle)@(fq@a.rest[side+'Foot'].to_quaternion()).to_matrix().to_4x4()
  toe=d[side+'Foot']@a.rest[side+'Foot'].inverted()@a.heads[side+'ToeBase'];d[side+'ToeBase']=Matrix.Translation(toe)@(tq@a.rest[side+'ToeBase'].to_quaternion()).to_matrix().to_4x4()
  sh=d['Spine1']@a.rest['Spine1'].inverted()@a.heads[side+'Shoulder'];d[side+'Shoulder']=Matrix.Translation(sh)@(cq@a.rest[side+'Shoulder'].to_quaternion()).to_matrix().to_4x4();shoulder=d[side+'Shoulder']@a.rest[side+'Shoulder'].inverted()@a.heads[side+'Arm']
  if superman:
   lift=p if side==state['arm']else 0.;angle=math.radians(14*lift)
   direction=Vector((sign*.10,-math.cos(angle),math.sin(angle))).normalized();wrist=shoulder+Vector((sign*.035,-.485,.0));wrist.z=.045+.245*lift+offset.get(side+'_hand',0)*(1-lift);armreach=math.sqrt(a.length[side+'Arm']**2+a.length[side+'ForeArm']**2+2*a.length[side+'Arm']*a.length[side+'ForeArm']*math.cos(math.radians(10)));wrist.y=shoulder.y-math.sqrt(armreach*armreach-(wrist.x-shoulder.x)**2-(wrist.z-shoulder.z)**2)
   elbow,wrist=a.two_joint(shoulder,wrist,a.length[side+'Arm'],a.length[side+'ForeArm'],shoulder+Vector((sign*.4,-.1,.1)))
   angle+=math.radians(4*(1-lift));hq=palm_frame.hand(a,side,Vector((sign*.04,-math.cos(angle),math.sin(angle))),Vector((0,0,-1)),PALM_FRAMES)
  else:
   wrist=Vector((sign*.50,-.48,.06+offset.get(side+'_hand',0)));target=wrist.copy();elbow,wrist=a.two_joint(shoulder,wrist,a.length[side+'Arm'],a.length[side+'ForeArm'],shoulder+Vector((sign*.7,.6,-.08)));reach[side+'_wrist']=float((target-wrist).length)
   hq=palm_frame.hand(a,side,Vector((sign*.16,-1,math.tan(math.radians(4)))),Vector((0,0,-1)),PALM_FRAMES)
  aq=cq@a.orient(side+'Arm',cq.inverted()@(elbow-shoulder));bq=transported(a,side+'ForeArm',side+'Arm',aq,wrist-elbow)
  for name,head,q in [(side+'Arm',shoulder,aq),(side+'ForeArm',elbow,bq),(side+'Hand',wrist,hq)]:d[name]=Matrix.Translation(head)@q.to_matrix().to_4x4()
 for name,(head,tail,parent,digit,index)in a.finger_specs.items():d[name]=d[parent]@a.rest[parent].inverted()@a.rest[name]
 for bone in a.rig.pose.bones:
  parent=bone.parent.name if bone.parent else None;bone.matrix_basis=a.rest[bone.name].inverted()@(a.rest[parent]@d[parent].inverted()if parent else Matrix.Identity(4))@d[bone.name]
 return d,{**state,'reach_errors_m':reach}
