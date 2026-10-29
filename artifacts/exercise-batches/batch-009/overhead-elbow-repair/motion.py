"""1986: staged forward arm elevation, elbow fold, delayed assisted hold.

Coherent local elbow/wrist rotations replace the rejected wrist-led IK route.
The endpoint hand placements retain the measured original upper-back contacts.
"""
import importlib.util,sys,math
from pathlib import Path
from mathutils import Matrix,Quaternion,Vector
F=Path(__file__).resolve().parent;W=F.parents[3];OLD=W/'artifacts/exercise-batches/batch-008/rotator-grips'
sys.path.insert(0,str(OLD))
spec=importlib.util.spec_from_file_location('batch008_rotator_motion',OLD/'motion.py');old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
smooth=old.smooth
_CACHE={}
def endpoint(a):
 if not _CACHE:
  d=old.overhead_raw(a,2)
  # Place the assisting elbow behind the crown. The rejected endpoint's
  # near-frontal assisting forearm crossed the occiput despite hand contact.
  side='Right';sh=a.heads[side+'Arm'];elbow,wrist=a.two_joint(sh,d[side+'Hand'].translation,a.length[side+'Arm'],a.length[side+'ForeArm'],Vector((-.45,.65,1.65)))
  u=elbow-sh;l=wrist-elbow
  old_upper=d[side+'Arm'].to_quaternion();old_direction=old_upper@Vector((0,1,0));aq=old_direction.rotation_difference(u.normalized())@old_upper
  fq=old.transported(a,side+'ForeArm',side+'Arm',aq,l)
  d[side+'Arm']=Matrix.Translation(sh)@aq.to_matrix().to_4x4();d[side+'ForeArm']=Matrix.Translation(elbow)@fq.to_matrix().to_4x4()
  _CACHE.update(d)
 return _CACHE

_FRAMES={}
def upper_frame(a,side,u):
 if side not in _FRAMES:
  q0=a.rest[side+'Arm'].to_quaternion();q1=endpoint(a)[side+'Arm'].to_quaternion();v0=q0@Vector((0,1,0));v1=q1@Vector((0,1,0));mid=Vector((.85 if side=='Left'else-.85,-.35,.70)).normalized();rows=[q0];last=v0
  for i in range(1,601):
   x=i/600;v=(v0*(1-x)**2+mid*(2*x*(1-x))+v1*x*x).normalized();q=last.rotation_difference(v)@rows[-1];q.normalize();rows.append(q);last=v
  a0=rows[-1]@Vector((1,0,0));a1=q1@Vector((1,0,0));twist=math.atan2(v1.dot(a0.cross(a1)),a0.dot(a1));_FRAMES[side]=(rows,twist)
 rows,twist=_FRAMES[side];x=min(600,max(0,u*600));i=min(599,int(x));q=rows[i].slerp(rows[i+1],x-i);axis=q@Vector((0,1,0));q=Quaternion(axis,twist*smooth(u))@q;q.normalize();return q

def assist_clock(tau):
 t=max(0.,min(.70,tau-1.30));r=.12;rate=1/(.70-r)
 def start(x):return rate*.5*(x-r/math.pi*math.sin(math.pi*x/r))
 return start(t)if t<r else 1-start(.70-t)if t>.70-r else rate*(t-r/2)

def assisting_wrist(a,u):
 p0=a.heads['RightHand'];p1=Vector((-.50,-.30,1.55));p2=Vector((-.30,.25,1.90));p3=endpoint(a)['RightHand'].translation
 w=p0*(1-u)**3+p1*(3*u*(1-u)**2)+p2*(3*u*u*(1-u))+p3*u**3
 if .94<u<1:w+=Vector((.92920136,.19857480,.31169364))*(.004*math.sin(math.pi*smooth((u-.94)/.06)))
 return w

_BEND={}
def assisting_geometry(a,u):
 sh=a.heads['RightArm'];goal=endpoint(a)
 if not _BEND:
  axis0=(a.heads['RightHand']-sh).normalized();v=a.heads['RightForeArm']-sh;v=(v-axis0*v.dot(axis0)).normalized();rows=[v];last=axis0
  for i in range(1,601):
   axis=(assisting_wrist(a,i/600)-sh).normalized();v=last.rotation_difference(axis)@v;v.normalize();rows.append(v.copy());last=axis
  v1=goal['RightForeArm'].translation-sh;v1=(v1-last*v1.dot(last)).normalized();twist=math.atan2(last.dot(rows[-1].cross(v1)),rows[-1].dot(v1));_BEND.update(rows=rows,twist=twist)
 wrist=assisting_wrist(a,u);axis=(wrist-sh).normalized();x=min(600,max(0,u*600));i=min(599,int(x));v=_BEND['rows'][i].lerp(_BEND['rows'][i+1],x-i);v=(v-axis*v.dot(axis)).normalized();v=Quaternion(axis,_BEND['twist']*smooth(u))@v
 return a.two_joint(sh,wrist,a.length['RightArm'],a.length['RightForeArm'],sh+v)

_LOWER={}
def assisting_lower_frame(a,u):
 if not _LOWER:
  q=a.rest['RightForeArm'].to_quaternion();last=q@Vector((0,1,0));rows=[q]
  for i in range(1,601):
   elbow,wrist=assisting_geometry(a,i/600);v=(wrist-elbow).normalized();q=last.rotation_difference(v)@q;q.normalize();rows.append(q);last=v
  goal=endpoint(a)['RightForeArm'].to_quaternion();n0=rows[-1]@Vector((1,0,0));n1=goal@Vector((1,0,0));twist=math.atan2(last.dot(n0.cross(n1)),n0.dot(n1));_LOWER.update(rows=rows,twist=twist)
 x=min(600,max(0,u*600));i=min(599,int(x));q=_LOWER['rows'][i].slerp(_LOWER['rows'][i+1],x-i);axis=q@Vector((0,1,0));q=Quaternion(axis,_LOWER['twist']*smooth(u))@q;q.normalize();return q

def assisting_frame(a,u):
 # Carry the proven outside-lift axial frame onto the reachable elbow path;
 # choosing its frame afresh from the changing bend plane rolls the biceps
 # into the scapula during the posterior approach.
 elbow,wrist=assisting_geometry(a,u);reference=upper_frame(a,'Right',u);direction=(elbow-a.heads['RightArm']).normalized();q=(reference@Vector((0,1,0))).rotation_difference(direction)@reference;q.normalize();return q

def overhead(a,t):
 tau=min(t,5-t);goal=endpoint(a);d={n:m.copy()for n,m in a.rest.items()}
 for side in ['Left']:
  # Working palm settles before assistance; early assisting elbow flexion
  # creates a bent outside approach, with no straight overhead waypoint.
  lift=smooth(tau/.70)if side=='Left'else smooth((tau-1.30)/.70)
  fold=smooth((tau-.70)/.60)if side=='Left'else smooth((tau-1.30)/.25)
  wrist=smooth((tau-.90)/.40)if side=='Left'else smooth((tau-1.30)/.25)
  aq0=a.rest[side+'Arm'].to_quaternion();aq1=goal[side+'Arm'].to_quaternion()
  aq=upper_frame(a,side,lift)
  sh=a.heads[side+'Arm'];elbow=sh+aq@(a.rest[side+'Arm'].to_quaternion().inverted()@(a.heads[side+'ForeArm']-sh))
  fl0=aq0.inverted()@a.rest[side+'ForeArm'].to_quaternion();fl1=aq1.inverted()@goal[side+'ForeArm'].to_quaternion();fq=aq@fl0.slerp(fl1,fold)
  w=elbow+fq@(a.rest[side+'ForeArm'].to_quaternion().inverted()@(a.heads[side+'Hand']-a.heads[side+'ForeArm']))
  hl0=a.rest[side+'ForeArm'].to_quaternion().inverted()@a.rest[side+'Hand'].to_quaternion();hl1=goal[side+'ForeArm'].to_quaternion().inverted()@goal[side+'Hand'].to_quaternion();hq=fq@hl0.slerp(hl1,wrist)
  for n,h,q in [(side+'Arm',sh,aq),(side+'ForeArm',elbow,fq),(side+'Hand',w,hq)]:d[n]=Matrix.Translation(h)@q.to_matrix().to_4x4()
 # The assisting hand rises outside the chest/temple on a bent chain;
 # its wrist never uses a straight overhead arm as a passing pose.
 u=assist_clock(tau);elbow,w=assisting_geometry(a,u);aq=assisting_frame(a,u);fq=assisting_lower_frame(a,u)
 relative=a.rest['RightForeArm'].to_quaternion().inverted()@a.rest['RightHand'].to_quaternion();neutral=fq@relative;final_neutral=goal['RightForeArm'].to_quaternion()@relative;delta=final_neutral.inverted()@goal['RightHand'].to_quaternion();hq=neutral@Quaternion((1,0,0,0)).slerp(delta,smooth((u-.55)/.45))
 for n,h,q in [('RightArm',a.heads['RightArm'],aq),('RightForeArm',elbow,fq),('RightHand',w,hq)]:d[n]=Matrix.Translation(h)@q.to_matrix().to_4x4()
 for name,(head,tail,parent,digit,index)in a.finger_specs.items():
  side='Left'if name.startswith('Left')else'Right';sign=1 if side=='Left'else-1
  amount=smooth((tau-1.60)/.40)if side=='Right'else smooth((tau-.70)/.60)
  axis=a.rest[name].to_3x3().inverted()@(tail-head).normalized().cross(Vector((-sign,0,0))).normalized();angles=([20,45,30]if digit!='Thumb'else[8,15,10])if side=='Right'else[3,5,3]
  q=Quaternion(axis,math.radians(angles[index]*amount));d[name]=d[parent]@a.rest[parent].inverted()@a.rest[name]@q.to_matrix().to_4x4()
 return d

def pose(a,ID,frame,offsets=None):
 old.overhead=overhead
 return old.pose(a,'1986',frame,offsets)
