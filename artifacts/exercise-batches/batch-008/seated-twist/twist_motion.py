"""Source-rig seated spinal twist; accepted seated binding and anatomy-derived IK frames."""
from pathlib import Path
import sys,math,json
sys.dont_write_bytecode=True
import bpy,numpy as np
from mathutils import Matrix,Quaternion,Vector
P=Path(__file__).resolve().parent
sys.path.insert(0,str(P.parents[1]/'batch-003'));import authoring as a
sys.path.insert(0,str(P.parents[1]/'batch-007/prone-family'));import palm_frame

ANKLE_X=-.245
ANKLE_Y=-.46
FOOT_YAW=-20.8
FORCE_WEIGHT=None
KNEE_POLE_ANGLE=0.
SWING_CLEARANCE_LIFT=.012
if(P/'authored-anchors.json').exists():
 solved=json.loads((P/'authored-anchors.json').read_text());ANKLE_X=solved['ankle_x'];ANKLE_Y=solved.get('ankle_y',-.46);FOOT_YAW=solved['foot_deformation_yaw_degrees']
def smooth(x):
 x=max(0.,min(1.,x));return x*x*x*(x*(6*x-15)+10)
def interpolate(A,B,u):return Matrix.Translation(A.translation.lerp(B.translation,u))@A.to_quaternion().slerp(B.to_quaternion(),u).to_matrix().to_4x4()
def apply(d):
 if a.body.data.shape_keys and 'TwistHipVolume'in a.body.data.shape_keys.key_blocks:
  k=component_weight(d)if FORCE_WEIGHT is None else FORCE_WEIGHT;a.body.data.shape_keys.key_blocks['TwistHipVolume'].value=k
  if 'ThighContactLead'in a.body.data.shape_keys.key_blocks:a.body.data.shape_keys.key_blocks['ThighContactLead'].value=math.sqrt(max(0.,k))-k
 for pb in a.rig.pose.bones:
  parent=pb.parent.name if pb.parent else None
  pb.matrix_basis=a.rest[pb.name].inverted()@(a.rest[parent]@d[parent].inverted()if parent else Matrix.Identity(4))@d[pb.name]
 bpy.context.view_layer.update()
def points():
 bpy.context.view_layer.update();e=a.body.evaluated_get(bpy.context.evaluated_depsgraph_get());m=e.to_mesh();X=np.array([v.co[:]for v in m.vertices]);e.to_mesh_clear();return X

def initialize():
 global D0,X0,PF,FINGER_REL,domains,neutral_hinge
 a.initialize();src=P.parents[1]/'batch-007/assets/1368/source.blend';bpy.ops.wm.open_mainfile(filepath=str(src));a.body=bpy.data.objects['SK_BlenderStudioHuman'];a.rig=bpy.data.objects['RIG_BlenderStudioHuman'];a.scene=bpy.context.scene
 act=bpy.data.actions['Exercise_1368'];a.rig.animation_data.action=act;a.scene.frame_set(1);bpy.context.view_layer.update();D0={pb.name:pb.matrix.copy()for pb in a.rig.pose.bones};X0=points();a.rig.animation_data_clear()
 if a.body.data.shape_keys:a.body.data.shape_keys.animation_data_clear()
 for action in list(bpy.data.actions):bpy.data.actions.remove(action)
 # Exact255-row causal rollback; preserve all other inherited seated/support weights.
 recipe=json.loads((P/'hip-binding-diagnosis.json').read_text())['changes']
 for row in recipe:
  i=row['source_id'];now={a.body.vertex_groups[g.group].name:float(g.weight)for g in a.body.data.vertices[i].groups};assert now==row['inherited']
  for n in now:a.body.vertex_groups[n].remove([i])
  for n,w in row['original'].items():a.body.vertex_groups[n].add([i],w,'REPLACE')
 assert all({a.body.vertex_groups[g.group].name:float(g.weight)for g in a.body.data.vertices[row['source_id']].groups}==row['original']for row in recipe)
 PF=palm_frame.prepare(a);FINGER_REL={n:D0[parent].inverted()@D0[n]for n,(_,_,parent,_,_)in a.finger_specs.items()}
 names={g.index:g.name for g in a.body.vertex_groups};domains={}
 for side in ['Left','Right']:
  domains[side+'Hand']=[v.index for v in a.body.data.vertices if sum(g.weight for g in v.groups if a.body.vertex_groups[g.group].name.startswith(side)and any(k in a.body.vertex_groups[g.group].name for k in ['Hand','Thumb','Index','Middle','Ring','Little']))>.5]
  domains[side+'Sole']=[v.index for v in a.body.data.vertices if v.co.z<.045 and sum(g.weight for g in v.groups if names[g.group]in[side+'Foot',side+'ToeBase'])>.8]
 domains['pelvis']=[v.index for v in a.body.data.vertices if abs(v.co.x)<.23 and v.co.y>.035 and .78<v.co.z<1.02]
 domains['LeftWholeLeg']=[v.index for v in a.body.data.vertices if sum(g.weight for g in v.groups if a.body.vertex_groups[g.group].name in ['LeftUpLeg','LeftLeg','LeftFoot','LeftToeBase'])>.5]
 domains['LeftKnee']=[v.index for v in a.body.data.vertices if (v.co-a.heads['LeftLeg']).length<.115 and v.co.x>.02]
 neutral_hinge={}
 for side in ['Left','Right']:
  for suffix,joints in [('leg',['UpLeg','Leg','Foot']),('arm',['Arm','ForeArm','Hand'])]:
   H,K,A=[D0[side+j].translation for j in joints];neutral_hinge[side+suffix]=(K-H).cross(A-K).normalized()
 apply(D0);return a

def limb(d,side,kind,H,K,A):
 names=['UpLeg','Leg']if kind=='leg'else['Arm','ForeArm'];last='Foot'if kind=='leg'else'Hand';N=(K-H).cross(A-K)
 if N.length<1e-7:N=neutral_hinge[side+kind]
 N.normalize();N0=neutral_hinge[side+kind]
 for name,start,end,ns,ne in [(names[0],H,K,names[0],names[1]),(names[1],K,A,names[1],last)]:
  initial=D0[side+ne].translation-D0[side+ns].translation;transport=a.frame(end-start,N)@a.frame(initial,N0).transposed();q=transport.to_quaternion()@D0[side+name].to_quaternion()
  if kind in ['leg','arm']:
   sourceN=(a.heads[side+names[1]]-a.heads[side+names[0]]).cross(a.heads[side+last]-a.heads[side+names[1]]).normalized();sourceDirection=a.heads[side+ne]-a.heads[side+ns];q=(a.frame(end-start,N)@a.frame(sourceDirection,sourceN).transposed()).to_quaternion()@a.rest[side+name].to_quaternion()
  d[side+name]=Matrix.Translation(start)@q.to_matrix().to_4x4()

def fingers(d):
 for n,(_,_,parent,_,_)in a.finger_specs.items():d[n]=d[parent]@FINGER_REL[n]

def kinematics(t,root_delta=0.,palm_delta=0.,hug_distance=0.):
 t=min(t,5-t)if t>3 else min(t,2);u=smooth((t-.3)/1.0);v=smooth((t-.5)/1.5);w=smooth((t-1.2)/.8);release=smooth(t/.3);support=smooth((t-.3)/1.5)
 d={k:m.copy()for k,m in D0.items()};target=a.torso(D0['Hips'].translation,[-8]*5,bend=12,twist=30)
 for n in ['Hips','Spine','Spine1','Neck','Head']:
  d[n]=interpolate(D0[n],target[n],v);d[n].translation+=Vector((0,0,root_delta))
 # Extended supporting leg keeps its ankle/heel plane while pelvis settles.
 H=d['Hips']@a.rest['Hips'].inverted()@a.heads['RightUpLeg'];A=D0['RightFoot'].translation;K,actual=a.two_joint(H,A,a.length['RightUpLeg'],a.length['RightLeg'],D0['RightLeg'].translation+Vector((0,0,.1)));assert(actual-A).length<1e-5
 limb(d,'Right','leg',H,K,A)
 # Continuous anatomical two-axis transport from accepted seated neutral frames.
 side='Left';hip=d['Hips']@a.rest['Hips'].inverted()@a.heads['LeftUpLeg'];flat=a.rz(FOOT_YAW);z=.0015-min((flat@(a.coords[i]-a.heads['LeftFoot'])).z for i in domains['LeftSole']);end=Vector((ANKLE_X,ANKLE_Y,z));ankle=D0['LeftFoot'].translation.lerp(end,u);ankle.z+=.18*math.sin(math.pi*u)+SWING_CLEARANCE_LIFT*math.sin(math.pi*u)**2
 pole=hip+Vector((math.sin(KNEE_POLE_ANGLE),0,math.cos(KNEE_POLE_ANGLE)));knee,actual=a.two_joint(hip,ankle,a.length['LeftUpLeg'],a.length['LeftLeg'],pole);assert(actual-ankle).length<1e-5,('leg unreachable',t)
 limb(d,'Left','leg',hip,knee,ankle);startdef=D0['LeftFoot'].to_quaternion()@a.rest['LeftFoot'].to_quaternion().inverted();fq=startdef.slerp(flat,u);d['LeftFoot']=Matrix.Translation(ankle)@(fq@a.rest['LeftFoot'].to_quaternion()).to_matrix().to_4x4();d['LeftToeBase']=d['LeftFoot']@a.rest['LeftFoot'].inverted()@a.rest['LeftToeBase']
 # Behind-floor support, source-derived palm frame and minimal clavicular lowering.
 side='Left';sh=side+'Shoulder';base=d['Spine1']@a.rest['Spine1'].inverted()@a.rest[sh];shroot=base.translation;sourceclav=(base@a.rest[sh].inverted()@a.heads[side+'Arm'])-shroot
 hq=palm_frame.hand(a,side,Vector((0,1,0)),Vector((0,0,-1)),PF);hdef=hq@a.rest[side+'Hand'].to_quaternion().inverted();wrist=Vector((.26,.15,.0));wrist.z=.0015+palm_delta-min((hdef@(a.coords[i]-a.heads[side+'Hand'])).z for i in domains[side+'Hand'])
 def clav(theta):
  axis=sourceclav.cross(Vector((0,0,-1))).normalized();q=Quaternion(axis,theta);return shroot+q@sourceclav,q
 length=a.length[side+'Arm']+a.length[side+'ForeArm'];lo=0.;hi=math.radians(35)
 for _ in range(35):
  mid=(lo+hi)/2;H,_=clav(mid)
  if (wrist-H).length>length*.975:lo=mid
  else:hi=mid
 H,lower=clav(hi);assert(wrist-H).length<length-.001,('support unreachable',t,(wrist-H).length,length)
 peaksh=Matrix.Translation(shroot)@(lower@base.to_quaternion()).to_matrix().to_4x4();d[sh]=interpolate(D0[sh],peaksh,support);H=d[sh]@a.rest[sh].inverted()@a.heads[side+'Arm'];wrist=D0[side+'Hand'].translation.lerp(Vector((.38,-.18,.34)),release).lerp(wrist,support);wrist.x+=.04*math.sin(math.pi*support);qhand=D0[side+'Hand'].to_quaternion().slerp(hq,support)
 elbow,actual=a.two_joint(H,wrist,a.length[side+'Arm'],a.length[side+'ForeArm'],H+Vector((.35,.18,-.35)));assert(actual-wrist).length<1e-5,('support transition unreachable',t)
 limb(d,side,'arm',H,elbow,wrist);d[side+'Hand']=Matrix.Translation(wrist)@qhand.to_matrix().to_4x4()
 # Other clavicle follows the upper torso. Hug targets actual posed knee skin.
 side='Right';sh=side+'Shoulder';d[sh]=d['Spine1']@a.rest['Spine1'].inverted()@a.rest[sh]
 # Temporarily carry neutral arm for the first knee readback.
 carry=d['Spine1']@D0['Spine1'].inverted()
 for n in [side+'Arm',side+'ForeArm',side+'Hand']:d[n]=carry@D0[n]
 fingers(d);apply(d);X=points();ids=domains['LeftKnee'];kn=np.array(knee);front=min([i for i in ids if X[i,2]>knee.z-.045],key=lambda i:X[i,1]);target=Vector(X[front]);a.body.data.calc_loop_triangles();tri=np.array([t.vertices[:]for t in a.body.data.loop_triangles]);cross=np.cross(X[tri[:,1]]-X[tri[:,0]],X[tri[:,2]]-X[tri[:,0]]);normals=np.zeros_like(X)
 for k in range(3):np.add.at(normals,tri[:,k],cross)
 normal=Vector(normals[[9048,9057,9023,8852]].sum(0));normal.x=0;normal.normalize();hq=palm_frame.hand(a,side,Vector((1,0,0)),-normal,PF);hdef=hq@a.rest[side+'Hand'].to_quaternion().inverted();anchor=Vector(PF[side]['center']);wrist=target+normal*(.002+hug_distance)-hdef@(anchor-a.heads[side+'Hand'])
 H=d[sh]@a.rest[sh].inverted()@a.heads[side+'Arm'];start=carry@D0[side+'Hand'];clear=carry@Vector((-.38,-.18,.34));wrist=start.translation.lerp(clear,release).lerp(wrist,w);wrist+=normal*(0.01609498908389958*math.sin(math.pi*w));hq=start.to_quaternion().slerp(hq,w);long=(hq@a.rest[side+'Hand'].to_quaternion().inverted()@(a.tails[side+'Hand']-a.heads[side+'Hand'])).normalized();axis=(wrist-H).normalized();sourceN=(a.heads[side+'ForeArm']-a.heads[side+'Arm']).cross(a.heads[side+'Hand']-a.heads[side+'ForeArm']).normalized();parentQ=d[sh].to_quaternion()@a.rest[sh].to_quaternion().inverted();carriedN=parentQ@sourceN;carriedN-=axis*carriedN.dot(axis);assert carriedN.length>.1,('elbow pole margin',t,carriedN.length);pole=H+axis.cross(carriedN.normalized())
 elbow,actual=a.two_joint(H,wrist,a.length[side+'Arm'],a.length[side+'ForeArm'],pole);assert(actual-wrist).length<1e-5,('hug unreachable',t,(wrist-H).length,length)
 limb(d,side,'arm',H,elbow,wrist);d[side+'Hand']=Matrix.Translation(wrist)@hq.to_matrix().to_4x4();fingers(d);apply(d)
 return d,{'leg':u,'support':v,'hug':w,'left_clavicle_depression_degrees':math.degrees(hi),'left_ankle':list(ankle),'left_knee':list(knee),'hug_front_source_id':front,'root_delta':root_delta,'palm_delta':palm_delta,'hug_distance':hug_distance,'hug_normal':list(normal),'hug_source_pad_ids':[9048,9057,9023,8852]}

# Endpoint contact offsets are measured from the actual keyed finger/hand skin.
CONTACT={'palm_delta':0.,'hug_distance':0.}
def pose(t):
 root=0.
 for _ in range(5):
  d,p=kinematics(t,root,**CONTACT);X=points();gap=.0015-float(X[domains['pelvis'],2].min())
  if abs(gap)<1e-7:break
  root+=gap
 return d,p
def solve_contacts():
 for _ in range(5):
  d,p=pose(2.5);X=points();CONTACT['palm_delta']+=.0015-float(X[PF['Left']['source_ids'],2].min())
  # Anterior knee tangent: whole hand stays outside, not only its centroid.
  hand=X[domains['RightHand']];lo=hand.min(0)-.015;hi=hand.max(0)+.015;local=[i for i in domains['LeftWholeLeg']if lo[2]<X[i,2]<hi[2]and lo[0]<X[i,0]<hi[0]];assert local
  normal=np.array(p['hug_normal']);plane=float((X[local]@normal).max());minimum=float((hand@normal).min());CONTACT['hug_distance']+=plane+.0015-minimum
 # Refine the conservative plane against actual nearest knee skin.
 from mathutils.bvhtree import BVHTree
 a.body.data.calc_loop_triangles();tri=np.array([t.vertices[:]for t in a.body.data.loop_triangles]);knee_ids={v.index for v in a.body.data.vertices if(v.co-a.heads['LeftLeg']).length<.18 and v.co.x>.015};faces=[t.tolist()for t in tri if all(i in knee_ids for i in t)]
 for _ in range(6):
  d,p=pose(2.5);X=points();tree=BVHTree.FromPolygons(X.tolist(),faces,all_triangles=True);pairs=[(tree.find_nearest(tuple(X[i])),i)for i in domains['RightHand']];nearest,i=min(pairs,key=lambda item:item[0][3]);gap=nearest[3];derivative=Vector(p['hug_normal']).dot(nearest[1]);assert derivative>.3,(gap,derivative);CONTACT['hug_distance']+=(.002-gap)/derivative
 d,p=pose(2.5);return CONTACT.copy(),p

DRIVE=None
def hip_coordinates(d):
 delta=d['Hips'].to_quaternion()@a.rest['Hips'].to_quaternion().inverted();direction=delta.inverted()@(d['LeftLeg'].translation-d['LeftUpLeg'].translation).normalized();return np.array([math.degrees(math.atan2(-direction.y,-direction.z)),math.degrees(math.atan2(-direction.x,math.hypot(direction.y,direction.z)))])
def component_weight(d):
 if DRIVE is None:return 0.
 value=(hip_coordinates(d)-DRIVE['neutral'])/(DRIVE['peak']-DRIVE['neutral']);return smooth(value[0])*smooth(value[1])
def install_component():
 global DRIVE
 neutral,_=pose(0);peak,_=pose(2.5);DRIVE={'neutral':hip_coordinates(neutral),'peak':hip_coordinates(peak)};data=np.load(P/'thigh-contact-margin.npz');key=a.body.shape_key_add(name='TwistHipVolume',from_mix=False);key.data.foreach_set('co',data['key_coordinates'].ravel());key.value=0
 # Entry-only interpolation of the SAME frozen contact vector. The held key
 # remains exact and the total contact amplitude is sqrt(k), never above1.
 hip=np.load(P/'hip-volume-component.npz');hipcoords=hip['source_basis']+hip['position_delta'];delta=data['key_coordinates'].astype(float)-hipcoords.astype(float);lead=a.body.shape_key_add(name='ThighContactLead',from_mix=False);lead.data.foreach_set('co',(data['source_basis'].astype(float)+delta).astype(np.float32).ravel());lead.value=0
 calibrate_drive()
 return {k:v.tolist()for k,v in DRIVE.items()}

def calibrate_drive():
 global DRIVE,FORCE_WEIGHT
 FORCE_WEIGHT=0.;neutral,_=pose(0);FORCE_WEIGHT=1.;peak,_=pose(2.5);DRIVE={'neutral':hip_coordinates(neutral),'peak':hip_coordinates(peak)};FORCE_WEIGHT=None

def prepare():
 global CONTACT,DRIVE,FORCE_WEIGHT
 CONTACT={'palm_delta':0.,'hug_distance':0.};DRIVE=None;FORCE_WEIGHT=None
 initialize();solve_contacts();install_component();solve_contacts();calibrate_drive();return a
