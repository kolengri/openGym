"""Two controlled palms-up prone chest/arm lifts; legs remain invariant and grounded."""
import math
from mathutils import Matrix, Vector
import palm_frame
PALMS=None
def configure(a):
 global PALMS
 PALMS=palm_frame.prepare(a)
def smooth(t):
 t=max(0.,min(1.,t));return t*t*t*(10+t*(-15+6*t))
def schedule(frame,exercise='4663'):
 f=frame%75
 p=smooth(f/22)if f<22 else 1. if f<30 else 1-smooth((f-30)/32)if f<62 else 0.
 return {'envelope':p,'repetition':min(2,frame//75+1),'phase':'Small chest and arms lift'if f<22 else 'Pause and reach back'if f<30 else 'Lower slowly'if f<62 else 'Grounded pause'}
def transported(a,name,parent,q,direction):
 base=q@a.rest[parent].to_quaternion().inverted()@a.rest[name].to_quaternion()
 return(base@Vector((0,1,0))).rotation_difference(direction.normalized())@base

def pose(a,frame,exercise,root_z,offsets=None):
 state=schedule(frame);p=state['envelope'];offsets=offsets or {}
 # Hips and lumbar segment stay fixed; the small thoracic extension carries the neutral neck.
 d=a.torso(Vector((0,.04,root_z)),[90,88,84-8*p,84-8*p,84-8*p])
 cq=d['Spine1'].to_quaternion()@a.rest['Spine1'].to_quaternion().inverted();reach={}
 for side,sign in [('Left',1),('Right',-1)]:
  hip=d['Hips']@a.rest['Hips'].inverted()@a.heads[side+'UpLeg'];angle=math.radians(-8.4)
  direction=Vector((sign*.035,math.cos(angle),math.sin(angle))).normalized();knee=hip+direction*a.length[side+'UpLeg'];ankle=knee+direction*a.length[side+'Leg']
  uq=a.orient(side+'UpLeg',direction);lq=transported(a,side+'Leg',side+'UpLeg',uq,direction);fq=a.rx(150)@a.rz(-sign*20.8)
  for name,head,q in [(side+'UpLeg',hip,uq),(side+'Leg',knee,lq),(side+'Foot',ankle,fq@a.rest[side+'Foot'].to_quaternion())]:d[name]=Matrix.Translation(head)@q.to_matrix().to_4x4()
  toe=d[side+'Foot']@a.rest[side+'Foot'].inverted()@a.heads[side+'ToeBase'];d[side+'ToeBase']=Matrix.Translation(toe)@(fq@a.rest[side+'ToeBase'].to_quaternion()).to_matrix().to_4x4()
  sh=d['Spine1']@a.rest['Spine1'].inverted()@a.heads[side+'Shoulder'];d[side+'Shoulder']=Matrix.Translation(sh)@(cq@a.rest[side+'Shoulder'].to_quaternion()).to_matrix().to_4x4()
  shoulder=d[side+'Shoulder']@a.rest[side+'Shoulder'].inverted()@a.heads[side+'Arm']
  length=math.sqrt(a.length[side+'Arm']**2+a.length[side+'ForeArm']**2+2*a.length[side+'Arm']*a.length[side+'ForeArm']*math.cos(math.radians(7)))
  wz=.045+.12*p+offsets.get(side+'_hand',0);hz=wz-shoulder.z
  horizontal=Vector((sign*(.19-.035*p),1,0)).normalized();wrist=shoulder+horizontal*math.sqrt(max(.001,length*length-hz*hz));wrist.z=wz
  pole=shoulder+Vector((sign*.7,0,.1));elbow,actual=a.two_joint(shoulder,wrist,a.length[side+'Arm'],a.length[side+'ForeArm'],pole);reach[side+'_wrist']=(actual-wrist).length;wrist=actual
  aq=cq@a.orient(side+'Arm',cq.inverted()@(elbow-shoulder));bq=transported(a,side+'ForeArm',side+'Arm',aq,wrist-elbow);direction=(wrist-shoulder).normalized()
  hq=palm_frame.hand(a,side,direction,Vector((0,0,1)),PALMS)
  for name,head,q in [(side+'Arm',shoulder,aq),(side+'ForeArm',elbow,bq),(side+'Hand',wrist,hq)]:d[name]=Matrix.Translation(head)@q.to_matrix().to_4x4()
 for name,(_,_,parent,_,_)in a.finger_specs.items():d[name]=d[parent]@a.rest[parent].inverted()@a.rest[name]
 for bone in a.rig.pose.bones:
  parent=bone.parent.name if bone.parent else None;bone.matrix_basis=a.rest[bone.name].inverted()@(a.rest[parent]@d[parent].inverted()if parent else Matrix.Identity(4))@d[bone.name]
 return d,{**state,'reach_errors_m':reach}
