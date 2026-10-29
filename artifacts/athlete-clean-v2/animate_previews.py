"""Bake three deterministic deformation previews on the repaired 24-bone athlete."""
import bpy,math,json,sys
from pathlib import Path
from mathutils import Vector,Matrix
P=Path(__file__).resolve().parent;bpy.ops.wm.open_mainfile(filepath=str(P/'athlete-clean.blend'))
rig=bpy.data.objects['RIG_Athlete'];rig.animation_data_clear()
for action in list(bpy.data.actions):bpy.data.actions.remove(action)
for pb in rig.pose.bones:pb.matrix_basis=Matrix.Identity(4);pb.rotation_mode='QUATERNION'
rest={b.name:b.matrix_local.copy() for b in rig.data.bones};heads={b.name:b.head_local.copy() for b in rig.data.bones};tails={b.name:b.tail_local.copy() for b in rig.data.bones}
ordered=[]
def visit(b):
 ordered.append(b)
 for c in b.children:visit(c)
for b in rig.data.bones:
 if b.parent is None:visit(b)
def solve(a,c,l1,l2,pole):
 axis=c-a;d=axis.length
 if d>l1+l2+.1:raise ValueError(f'Unreachable joint target: {d} > {l1+l2}')
 d=min(d,l1+l2-1e-5);axis.normalize();along=(l1*l1-l2*l2+d*d)/(2*d);height=math.sqrt(max(0,l1*l1-along*along));tangent=pole-axis*pole.dot(axis);tangent.normalize();return a+axis*along+tangent*height
def align(name,a,b):return Matrix.Translation(a)@(tails[name]-heads[name]).rotation_difference(b-a).to_matrix().to_4x4()@rest[name].to_3x3().to_4x4()
def smooth(t):return t*t*(3-2*t)
events={'Right':[(.35,.7,-50),(1.4,1.75,-50),(3.15,3.5,50),(4.2,4.55,50)],'Left':[(.8,1.15,-50),(1.85,2.2,-50),(2.7,3.05,50),(3.75,4.1,50)]}
def foot(t,side):
 p=heads[side+'Foot'].copy();moving=False
 for a,b,delta in events[side]:
  if t>=b:p.x+=delta
  elif t>a:
   u=(t-a)/(b-a);p.x+=delta*smooth(u);p.z+=5*math.sin(math.pi*u)**2;moving=True
 return p,moving
scene=bpy.context.scene;scene.render.fps=30;clips=[];max_error=0;samples={}
for kind,duration in [('LateralShuffle',5.2),('SquatPreview',3.2),('ArmRaisePreview',3.2)]:
 rig.animation_data_clear();count=round(duration*30);scene.frame_start=1;scene.frame_end=count+1;records=[]
 for frame in range(1,count+2):
  t=(frame-1)/30;scene.frame_set(frame);u=.5-.5*math.cos(2*math.pi*t/duration);feet={};moving={}
  for side in ['Left','Right']:
   feet[side],moving[side]=foot(t,side) if kind=='LateralShuffle' else (heads[side+'Foot'].copy(),False)
  if kind=='LateralShuffle':
   root_x=(feet['Left'].x+feet['Right'].x-heads['LeftFoot'].x-heads['RightFoot'].x)/2;span=abs(feet['Left'].x-feet['Right'].x);delta=Vector((root_x,-2.5,-9-6*max(0,(span-34)/50)));lean=.045
  elif kind=='SquatPreview':delta=Vector((0,8*u,-22*u-2));lean=.24*u
  else:delta=Vector((0,0,-1));lean=0
  torso=Matrix.Translation(delta)@Matrix.Translation(heads['Hips'])@Matrix.Rotation(lean,4,'X')@Matrix.Translation(-heads['Hips'])
  desired={name:torso@rest[name] for name in ['Hips','Spine02','Spine01','Spine','neck','Head','head_end','headfront','LeftShoulder','RightShoulder']}
  for side,sign in [('Left',1),('Right',-1)]:
   hip=torso@heads[side+'UpLeg'];ankle=feet[side];knee=solve(hip,ankle,(heads[side+'Leg']-heads[side+'UpLeg']).length,(heads[side+'Foot']-heads[side+'Leg']).length,Vector((0,-1,0)))
   desired[side+'UpLeg']=align(side+'UpLeg',hip,knee);desired[side+'Leg']=align(side+'Leg',knee,ankle)
   for name in [side+'Foot',side+'ToeBase']:desired[name]=Matrix.Translation(ankle-heads[side+'Foot'])@rest[name]
   shoulder_transform=torso
   if kind=='ArmRaisePreview':
    pivot=heads[side+'Shoulder'];shoulder_transform=torso@Matrix.Translation(pivot)@Matrix.Rotation(-sign*.18*u,4,'Y')@Matrix.Translation(-pivot);desired[side+'Shoulder']=shoulder_transform@rest[side+'Shoulder']
   shoulder=shoulder_transform@heads[side+'Arm'];l1=(heads[side+'ForeArm']-heads[side+'Arm']).length;l2=(heads[side+'Hand']-heads[side+'ForeArm']).length
   if kind=='ArmRaisePreview':
    direction=Vector((sign*(.45*(1-u)+.12*u),-.05,-.90*(1-u)+.95*u));direction.normalize();wrist=shoulder+direction*(l1+l2-2.8);hand_end=wrist+direction*14
   else:
    wrist=torso@Vector((sign*14,-30,126 if kind=='LateralShuffle' else 119));hand_end=wrist+Vector((-sign*5,-6,3))
   elbow=solve(shoulder,wrist,l1,l2,Vector((sign*.8,.2,-1)))
   desired[side+'Arm']=align(side+'Arm',shoulder,elbow);desired[side+'ForeArm']=align(side+'ForeArm',elbow,wrist);desired[side+'Hand']=align(side+'Hand',wrist,hand_end)
  for bone in ordered:
   name=bone.name;parent=bone.parent;pp=desired[parent.name] if parent else Matrix.Identity(4);pr=rest[parent.name] if parent else Matrix.Identity(4)
   if name not in desired:desired[name]=pp@pr.inverted()@rest[name]
   basis=rest[name].inverted()@pr@pp.inverted()@desired[name] if parent else rest[name].inverted()@desired[name];pb=rig.pose.bones[name];pb.matrix_basis=basis;pb.keyframe_insert('location',frame=frame);pb.keyframe_insert('rotation_quaternion',frame=frame)
  bpy.context.view_layer.update();error=max((rig.pose.bones[s+'Foot'].matrix.translation-feet[s]).length for s in ['Left','Right']);max_error=max(max_error,error);assert error<.001,error
  records.append({'time':t,'feet':{s:list(rig.matrix_world@feet[s]) for s in feet},'moving':moving})
 action=rig.animation_data.action;action.name='Athlete_'+kind;action.use_fake_user=True;clips.append({'name':action.name,'duration':duration,'frames':count+1});samples[action.name]=records
rig.animation_data_clear()
rig.animation_data_create();rig.animation_data.action=action
if len(action.slots):rig.animation_data.action_slot=action.slots[0]
for pb in rig.pose.bones:pb.matrix_basis=Matrix.Identity(4)
scene.frame_set(1);bpy.context.view_layer.update();bpy.ops.wm.save_as_mainfile(filepath=str(P/'athlete-motion.blend'))
sys.path.insert(0,str(Path.home()/'.codex/skills/blender-export-pipelines/scripts'));import export_asset
result=export_asset.run(preset='gltf',collection='ASSET_Athlete',out=str(P/'athlete-motion.glb'),set=['export_anim_slide_to_zero=true','export_frame_range=false']);assert result['ok'],result
assert result['files'][0]['summary']['animations']==3,result
(P/'motion-export.json').write_text(json.dumps(result,indent=2));(P/'motion-samples.json').write_text(json.dumps(samples,indent=2));(P/'motion-report.json').write_text(json.dumps({'clips':clips,'max_foot_joint_error_m':max_error*.01,'foot_contacts':'Analytic two-link IK with fixed planted targets. Visual deformation still reviewed separately.'},indent=2));print('@@MOTION@@'+json.dumps({'clips':clips,'max_foot_joint_error_m':max_error*.01,'export':result}))
