"""Retime the accepted keyed3531 path; preserve body, binding and peak poses."""
import bpy,json,hashlib,sys,math
import numpy as np
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent;F=P.parents[1]/'upright-cardio-family';sys.path[:0]=[str(F),str(P.parents[2]/'batch-003')]
import authoring as a,motion
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(P/'source.blend'));r=bpy.data.objects['RIG_BlenderStudioHuman'];b=bpy.data.objects['SK_BlenderStudioHuman'];s=bpy.context.scene
assert [x.name for x in bpy.data.actions]==['Exercise_3531']
source_before=sha(P/'source.blend');binding_before=a.binding_hash(b,r)
assert binding_before=='185b028576708385e433d9d296ddda84e24f879dfb34f895fbbf242cd835c8ec'
bone_names=[x.name for x in r.pose.bones]
def points():
 bpy.context.view_layer.update();e=b.evaluated_get(bpy.context.evaluated_depsgraph_get());m=e.to_mesh();p=np.array([v.co[:]for v in m.vertices]);e.to_mesh_clear();return p
foundation_path=P/'punch-retiming-foundation.npz'
if foundation_path.exists():
 frozen=np.load(foundation_path,allow_pickle=False)
 assert frozen['bone_names'].tolist()==bone_names
 source_before=str(frozen['source_sha256'].item())
 assert source_before=='5588b98e6ce66b85d05f25cde916721bb8b6e925574330d5ab2e28627b1df4c5'
 foundation=frozen['locations_quaternions'];assert foundation.shape==(151,51,7)
 old=r.animation_data.action;r.animation_data.action=None;bpy.data.actions.remove(old)
 restored=bpy.data.actions.new('Exercise_3531');restored.use_fake_user=True;r.animation_data.action=restored
 for f,row in enumerate(foundation):
  s.frame_set(f+1)
  for pb,value in zip(r.pose.bones,row):
   pb.location=value[:3];pb.rotation_quaternion=value[3:];pb.keyframe_insert('location',frame=f+1);pb.keyframe_insert('rotation_quaternion',frame=f+1)
 for layer in restored.layers:
  for strip in layer.strips:
   for bag in strip.channelbags:
    for curve in bag.fcurves:
     for key in curve.keyframe_points:key.interpolation='LINEAR'
else:
 assert source_before=='5588b98e6ce66b85d05f25cde916721bb8b6e925574330d5ab2e28627b1df4c5','First bake requires the accepted slower source or frozen foundation keys'
 foundation=[]
 for f in range(151):
  s.frame_set(f+1);bpy.context.view_layer.update();foundation.append([[*pb.location,*pb.rotation_quaternion]for pb in r.pose.bones])
 np.savez_compressed(foundation_path,source_sha256=np.array(source_before),bone_names=np.array(bone_names),locations_quaternions=np.array(foundation,np.float32))
# Capture accepted exact guard/right/left full skin and matrices, including native
# interpolation at the previous37.5/112.5 peaks, before replacing the action.
accepted={}
for label,f in [('guard',0),('right_peak',37.5),('left_peak',112.5)]:
 s.frame_set(int(f)+1,subframe=f%1);bpy.context.view_layer.update();accepted[label]={'surface':points(),'matrices':np.array([pb.matrix for pb in r.pose.bones])}
records=[];expected={};witness=[]
for f in range(151):
 state=motion.schedule(f,'3531');p=state['punch_extension'];oldf=0 if p==0 else math.asin(math.sqrt(p))*150/(2*math.pi)+(75 if state['punch_side']=='Left'else 0)
 s.frame_set(int(oldf)+1,subframe=oldf%1);bpy.context.view_layer.update();records.append([[*pb.location,*pb.rotation_quaternion]for pb in r.pose.bones]);expected[f]=np.array([pb.matrix for pb in r.pose.bones]);witness.append({'frame':f,**state,'accepted_source_frame':oldf})
old=r.animation_data.action;r.animation_data.action=None;bpy.data.actions.remove(old);action=bpy.data.actions.new('Exercise_3531');action.use_fake_user=True;r.animation_data.action=action
previous={}
for f,row in enumerate(records):
 s.frame_set(f+1)
 for pb,value in zip(r.pose.bones,row):
  pb.location=value[:3];pb.rotation_quaternion=value[3:]
  if pb.name in previous and pb.rotation_quaternion.dot(previous[pb.name])<0:pb.rotation_quaternion.negate()
  previous[pb.name]=pb.rotation_quaternion.copy();pb.keyframe_insert('location',frame=f+1);pb.keyframe_insert('rotation_quaternion',frame=f+1)
for layer in action.layers:
 for strip in layer.strips:
  for bag in strip.channelbags:
   for curve in bag.fcurves:
    for key in curve.keyframe_points:key.interpolation='LINEAR'
s.frame_start=1;s.frame_end=151;s.render.fps=30;s.frame_set(1);bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(P/'source.blend'))
bpy.ops.wm.open_mainfile(filepath=str(P/'source.blend'));r=bpy.data.objects['RIG_BlenderStudioHuman'];b=bpy.data.objects['SK_BlenderStudioHuman'];s=bpy.context.scene
assert a.binding_hash(b,r)==binding_before
maximum_error=0
for f,target in expected.items():
 s.frame_set(f+1);bpy.context.view_layer.update();maximum_error=max(maximum_error,float(np.max(abs(np.array([pb.matrix for pb in r.pose.bones])-target))))
assert maximum_error<2e-6,maximum_error
peak_report={}
for label,f in [('guard',0),('right_peak',8),('left_peak',33)]:
 s.frame_set(f+1);bpy.context.view_layer.update();skin_error=float(np.linalg.norm(points()-accepted[label]['surface'],axis=1).max());matrix_error=float(np.max(abs(np.array([pb.matrix for pb in r.pose.bones])-accepted[label]['matrices'])));peak_report[label]={'frame':f,'previous_accepted_frame':{'guard':0,'right_peak':37.5,'left_peak':112.5}[label],'full_skin_error_m':skin_error,'maximum_bone_matrix_error':matrix_error};assert skin_error<2e-6 and matrix_error<2e-6,(label,skin_error,matrix_error)
views=json.loads((P/'cameras.json').read_text());cam=s.camera;proofs=[]
for f,label,view in [(0,'guard',0),(5,'right-attack',0),(8,'right-punch',0),(16,'right-retraction',0),(25,'between-punches-guard',0),(33,'left-punch',1),(150,'guard-return',1)]:
 s.frame_set(f+1);bpy.context.view_layer.update();v=views[view];cam.location=v['position'];cam.rotation_euler=(Vector(v['target'])-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=v['scale'];before=points();s.render.filepath=str(P/f'fast-{label}.png');bpy.ops.render.render(write_still=True);assert np.array_equal(before,points());proofs.append({'frame':f,'time_seconds':f/30,'file':Path(s.render.filepath).name,'pre_post_render_skin_delta_m':0})
report={'ok':True,'previous_source_sha256':source_before,'source_sha256':sha(P/'source.blend'),'runtime_binding_sha256':binding_before,'change':'Animation timing only: six alternating punches in five seconds on accepted native keyed path. No mesh/binding/stance/fist/wrist/extent change.','punch_count':6,'per_punch_frames':25,'attack_frames':[2,8],'return_frames':[8,21],'guard_gap_frames':6,'attack_seconds':.2,'retraction_seconds':13/30,'guard_gap_seconds':.2,'peak_frames':[8,33,58,83,108,133],'envelope':'Piecewise quintic smoothstep, zero first/second derivative at guard and peak; runtime samples baked30fps with linear translation/quaternion interpolation.','source_workout_interval_seconds':[30,60],'maximum_saved_151_matrix_error':maximum_error,'preserved_accepted_poses':peak_report,'proofs':proofs,'samples':witness}
(P/'punch-timing-report.json').write_text(json.dumps(report,indent=2)+'\n');print('RETIME',json.dumps({k:v for k,v in report.items()if k not in ['samples']}))
