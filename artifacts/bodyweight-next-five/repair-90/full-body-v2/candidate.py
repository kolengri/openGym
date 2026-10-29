"""Corrected seated limb layout and anatomically consistent frames, v2 draft.

Original Basis, UVs, source IDs and 51 rest bones are preserved. No geometry
solver, subdivision, corrective smoothing, helper bone, or media derivatives.
"""
import bpy,json,math,sys,hashlib
from pathlib import Path
from mathutils import Matrix,Quaternion,Vector
P=Path(__file__).resolve().parent;BASE=P.parents[1]
sys.path.insert(0,str(BASE));sys.path.insert(0,str(P));import ninety_pose as a
V=Vector

def smooth(x):
 x=max(0,min(1,x));return x*x*(3-2*x)

def orient_frame(name,direction,source_axis,target_axis):
 return (a.frame(direction,target_axis)@a.frame(a.tails[name]-a.heads[name],source_axis).transposed()).to_quaternion()@a.rest[name].to_quaternion()

def pose(identifier,seconds):
 h=smooth(seconds/2) if seconds<2 else 1.0 if seconds<=3 else smooth((5-seconds)/2)
 pitch=(20+16*h) if identifier=='10565' else (8+28*h)
 desired=a.torso(V((0,.04,.113-.0055*h)),[pitch,pitch,pitch,pitch-3,pitch-5])
 for side,sign in [('Left',1),('Right',-1)]:
  hip=desired['Hips']@a.rest['Hips'].inverted()@a.heads[side+'UpLeg']
  thigh=V((0,-1,-.035)) if sign==1 else V((-1,0,.075))
  calf=V((-1,0,.005)) if sign==1 else V((0,1,-.147))
  knee=hip+thigh.normalized()*a.length[side+'UpLeg'];ankle=knee+calf.normalized()*a.length[side+'Leg']
  original_axis=(a.tails[side+'UpLeg']-a.heads[side+'UpLeg']).cross(a.tails[side+'Leg']-a.heads[side+'Leg']).normalized()
  target_axis=(knee-hip).cross(ankle-knee).normalized()
  for name,start,end in [(side+'UpLeg',hip,knee),(side+'Leg',knee,ankle)]:
   q=orient_frame(name,end-start,original_axis,target_axis);desired[name]=Matrix.Translation(start)@q.to_matrix().to_4x4()
  normal=-thigh.cross(calf).normalized()*sign
  q=a.orient(side+'Foot',calf,normal)@a.rest[side+'Foot'].to_quaternion().inverted()
  desired[side+'Foot']=Matrix.Translation(ankle)@(q@a.rest[side+'Foot'].to_quaternion()).to_matrix().to_4x4()
  toe=desired[side+'Foot']@a.rest[side+'Foot'].inverted()@a.heads[side+'ToeBase']
  desired[side+'ToeBase']=Matrix.Translation(toe)@(q@a.rest[side+'ToeBase'].to_quaternion()).to_matrix().to_4x4()
  sh=desired['Spine1']@a.rest['Spine1'].inverted()@a.heads[side+'Shoulder'];pq=desired['Spine1'].to_quaternion()@a.rest['Spine1'].to_quaternion().inverted()
  depression=Quaternion(V((0,1,0)),math.radians(sign*6)) if identifier=='6560' else Quaternion()
  desired[side+'Shoulder']=Matrix.Translation(sh)@(pq@depression@a.rest[side+'Shoulder'].to_quaternion()).to_matrix().to_4x4()
  armhead=desired[side+'Shoulder']@a.rest[side+'Shoulder'].inverted()@a.heads[side+'Arm']
  if identifier=='6560':
   wrist=V((.29 if sign==1 else -.30,-.13-.09*h if sign==1 else -.10-.12*h,.049));hdir=V((0,-1,-.10));pole=armhead+V((sign*.25,-.16,-.22))
  else:
   wrist=V((.15 if sign==1 else -.26,-.34 if sign==1 else -.42,.191 if sign==1 else .136-.003*h));hdir=V((-.6,-.2,-.1)) if sign==1 else V((.6,.05,-.1));pole=armhead+V((sign*.19,-.10,-.30))
  elbow,wrist=a.two_joint(armhead,wrist,a.length[side+'Arm'],a.length[side+'ForeArm'],pole)
  source_axis=(a.tails[side+'Arm']-a.heads[side+'Arm']).cross(a.tails[side+'ForeArm']-a.heads[side+'ForeArm']).normalized()
  target_axis=(elbow-armhead).cross(wrist-elbow).normalized()
  upper_q=orient_frame(side+'Arm',elbow-armhead,source_axis,target_axis)
  fore_q=orient_frame(side+'ForeArm',wrist-elbow,source_axis,target_axis)
  hand_q=a.seated_hand(side,hdir)[0]
  if identifier=='10565' and side=='Right':
   # The shin rises toward its medial/index side. Tilt the whole relaxed palm
   # across that round surface instead of driving the index/thumb into it.
   hand_q=Quaternion(hdir.normalized(),math.radians(16))@hand_q
  # Share pronation between the forearm and wrist; the upper arm remains in
  # the measured elbow plane rather than shortest-arc/quarter-roll blending.
  hd=hand_q@a.rest[side+'Hand'].to_quaternion().inverted();hint=hd@(a.tails[side+'ForeArm']-a.heads[side+'ForeArm']).normalized()
  palm_fore=hint.rotation_difference((wrist-elbow).normalized())@hd@a.rest[side+'ForeArm'].to_quaternion()
  fore_q=fore_q.slerp(palm_fore,.7)
  for name,start,q in [(side+'Arm',armhead,upper_q),(side+'ForeArm',elbow,fore_q),(side+'Hand',wrist,hand_q)]:desired[name]=Matrix.Translation(start)@q.to_matrix().to_4x4()
 for bone,(start,end,parent,digit,index) in a.finger_specs.items():
  parent_matrix=desired[parent]@a.rest[parent].inverted()
  if identifier in ['6560','10565']:
   proximal=bone[:-1]+'1';side='Left' if bone.startswith('Left') else 'Right';normal=a.seated_hand(side,(1,0,0))[1]
   flat=(a.tails[proximal]-a.heads[proximal]).normalized();flat=(flat-normal*flat.dot(normal)).normalized()
   slope={'Index':.45,'Middle':.40,'Ring':.20,'Little':.20,'Thumb':0}[digit] if identifier=='6560' else 0
   flat=(flat+normal*([slope,.10 if identifier=='6560' else 0,0][index] if digit!='Thumb' else 0)).normalized()
   straight=(end-start).normalized().rotation_difference(flat);delta=desired[side+'Hand']@a.rest[side+'Hand'].inverted()
   desired[bone]=Matrix.Translation(parent_matrix@start)@(delta.to_quaternion()@straight@a.rest[bone].to_quaternion()).to_matrix().to_4x4()
  else:
   normal=V((-1 if bone.startswith('Left') else 1,0,0));axis=a.rest[bone].to_3x3().inverted()@(end-start).normalized().cross(normal).normalized()
   desired[bone]=parent_matrix@a.rest[bone]@Quaternion(axis,math.radians([2,4,3][index])).to_matrix().to_4x4()
 for pb in a.rig.pose.bones:
  parent=pb.parent.name if pb.parent else None
  pb.matrix_basis=a.rest[pb.name].inverted()@(a.rest[parent]@desired[parent].inverted() if parent else Matrix.Identity(4))@desired[pb.name]
  pb.rotation_quaternion.normalize();pb.scale=(1,1,1)
 bpy.context.view_layer.update()
 return desired

def setup():
 binding=a.initialize();changes=[]
 for m in a.body.modifiers:m.show_viewport=m.show_render=m.type=='ARMATURE'
 next(m for m in a.body.modifiers if m.type=='ARMATURE').use_deform_preserve_volume=True
 (P/'weight-edits.json').write_text(json.dumps({'source_binding':binding,'changed_count':len(changes),'vertices':changes},indent=2)+'\n')

def proof():
 scene=a.scene;scene.render.engine='BLENDER_WORKBENCH';scene.render.resolution_x=720;scene.render.resolution_y=720;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.render.film_transparent=True;scene.view_settings.view_transform='Standard'
 s=scene.display.shading;s.light='STUDIO';s.color_type='SINGLE';s.single_color=(.60,.62,.64);s.show_shadows=False;s.show_cavity=False;s.show_specular_highlight=False
 cd=bpy.data.cameras.new('CandidateProof');cam=bpy.data.objects.new('CandidateProof',cd);scene.collection.objects.link(cam);scene.camera=cam;cd.type='ORTHO';cd.ortho_scale=1.7
 out=P/'early-proof';out.mkdir(exist_ok=True)
 for identifier,t,label in [('6560',0,'start'),('6560',2.5,'hinge'),('10565',2.5,'press')]:
  pose(identifier,t)
  if a.body.data.shape_keys:
   import correctives;correctives.set_values(a.body,identifier,t);bpy.context.view_layer.update()
  for view,pos in [('front',(0,-5,1.25)),('oblique',(3.4,-5,2.5)),('side',(5,0,.75)),('rear',(-1.5,5,1.5))]:
   cam.location=pos;cam.rotation_euler=(V((0,0,.46))-cam.location).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(out/f'{label}-{view}.png');bpy.ops.render.render(write_still=True)
 bpy.ops.wm.save_as_mainfile(filepath=str(P/'candidate.blend'))

if __name__=='__main__':
 setup()
 import correctives
 report=correctives.prepare(sys.modules[__name__]);(P/'corrective-edits.json').write_text(json.dumps(report,indent=2)+'\n')
 proof()
