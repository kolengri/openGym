"""Two actions on one unchanged body; return early actual keyed proofs."""
import bpy,numpy as np,sys,json,hashlib,os
from pathlib import Path
from mathutils import Vector
F=Path(__file__).resolve().parent;B=F.parent;sys.path[:0]=[str(F),str(B.parent/'batch-003')]
import authoring as a,motion,binding
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert a.initialize()=='227ede3fc31d1a2b47ff40f20a4a7288fe7bb36179add23bae953993826c8b7b';b,r,s=a.body,a.rig,a.scene
report=binding.apply(b);report['runtime_binding_sha256']=a.binding_hash(b,r);report['copied_from']='artifacts/exercise-batches/batch-006/upright-cardio-family/binding.py';report['copied_file_sha256']=sha(F/'binding.py');(F/'local-binding-report.json').write_text(json.dumps(report,indent=2)+'\n')
for m in b.modifiers:
 m.show_viewport=m.show_render=m.type=='ARMATURE'
 if m.type=='ARMATURE':m.use_deform_preserve_volume=True
soles={side:np.array([v.index for v in b.data.vertices if v.co.z<.10 and sum(g.weight for g in v.groups if b.vertex_groups[g.group].name in[side+'Foot',side+'ToeBase'])>.5],int)for side in ['Left','Right']}
def points():
 bpy.context.view_layer.update();e=b.evaluated_get(bpy.context.evaluated_depsgraph_get());me=e.to_mesh();p=np.array([v.co[:]for v in me.vertices]);e.to_mesh_clear();return p
r.animation_data_create();expected={};witness={}
for ID in ['4437','4436']:
 action=bpy.data.actions.new('Exercise_'+ID);action.use_fake_user=True;slot=None;previous={};expected[ID]={};witness[ID]=[]
 for f in range(151):
  r.animation_data.action=None;s.frame_set(f+1);desired,state=motion.pose(a,f,ID);p=points();offsets={side:.001-float(p[idx,2].min())for side,idx in soles.items()if side in state['grounded']}
  if offsets:desired,state=motion.pose(a,f,ID,offsets);p=points()
  err=max(float(np.max(abs(np.array(r.pose.bones[n].matrix)-np.array(m))))for n,m in desired.items());assert err<2e-6,(ID,f,err)
  expected[ID][f]=np.array([pb.matrix for pb in r.pose.bones]);state.update(whole_skin_floor_z_m=float(p[:,2].min()),sole_minimum_z_m={side:float(p[idx,2].min())for side,idx in soles.items()},ground_offsets_m=offsets,maximum_actual_bone_matrix_error=err);witness[ID].append(state)
  r.animation_data.action=action
  if slot:r.animation_data.action_slot=slot
  for pb in r.pose.bones:
   if pb.name in previous and pb.rotation_quaternion.dot(previous[pb.name])<0:pb.rotation_quaternion.negate()
   previous[pb.name]=pb.rotation_quaternion.copy();pb.keyframe_insert('location',frame=f+1);pb.keyframe_insert('rotation_quaternion',frame=f+1)
  slot=r.animation_data.action_slot
 for layer in action.layers:
  for strip in layer.strips:
   for bag in strip.channelbags:
    for curve in bag.fcurves:
     for key in curve.keyframe_points:key.interpolation='LINEAR'
import fist_pose;fist_pose.install_target(b,r,['4437'],['4436'])
attr=b.data.attributes.get('_SOURCE_INDEX')or b.data.attributes.new('_SOURCE_INDEX','FLOAT','POINT');attr.data.foreach_set('value',np.arange(10582,dtype=np.float32))
s.frame_start=1;s.frame_end=151;s.render.fps=30;s.render.engine='BLENDER_WORKBENCH';s.render.resolution_x=760;s.render.resolution_y=900;s.render.resolution_percentage=100;s.render.film_transparent=True;s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGBA';sh=s.display.shading;sh.light='STUDIO';sh.color_type='MATERIAL';sh.show_shadows=False;sh.show_cavity=False;sh.show_specular_highlight=False;s.view_settings.view_transform='Standard';s.view_settings.look='None'
cd=bpy.data.cameras.new('ReviewCamera');cam=bpy.data.objects.new('ReviewCamera',cd);s.collection.objects.link(cam);s.camera=cam;cd.type='ORTHO';views=[{'label':'front_oblique_whole_body','position':[3.8,-5,2.1],'target':[0,0,1.0],'scale':2.25},{'label':'side_whole_body','position':[5,-.1,1.35],'target':[0,0,1.0],'scale':2.25}];v=views[0];cam.location=v['position'];cam.rotation_euler=(Vector(v['target'])-cam.location).to_track_quat('-Z','Y').to_euler();cd.ortho_scale=v['scale'];r.animation_data.action=bpy.data.actions['Exercise_4437'];r.animation_data.action_slot=r.animation_data.action.slots[0];s.frame_set(1);bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(F/'source.blend'))
bpy.ops.wm.open_mainfile(filepath=str(F/'source.blend'));b=bpy.data.objects['SK_BlenderStudioHuman'];r=bpy.data.objects['RIG_BlenderStudioHuman'];s=bpy.context.scene;cam=s.camera
assert a.binding_hash(b,r)==report['runtime_binding_sha256'];assert max(len(v.groups)for v in b.data.vertices)<=4;assert max(abs(sum(g.weight for g in v.groups)-1)for v in b.data.vertices)<2e-6
for ID in ['4437','4436']:
 P=B/'assets'/ID
 for name in ['source.blend']:
  target=P/name
  if target.exists():target.unlink()
  os.link(F/name,target)
 (P/'cameras.json').write_text(json.dumps(views,indent=2)+'\n');(P/'local-binding-report.json').write_bytes((F/'local-binding-report.json').read_bytes());(P/'authoring-context.json').write_bytes((B/'contexts'/f'{ID}.json').read_bytes());r.animation_data.action=bpy.data.actions['Exercise_'+ID];r.animation_data.action_slot=r.animation_data.action.slots[0];err=0
 for f,matrices in expected[ID].items():
  s.frame_set(f+1);bpy.context.view_layer.update();err=max(err,float(np.max(abs(np.array([pb.matrix for pb in r.pose.bones])-matrices))))
 assert err<2e-6,(ID,err)
 proofs=[];pose_refs=[];states=[(0,'start',0),(7,'attack',0),(10,'left-curl-right-punch',1),(23,'return',0),(35,'right-curl-left-punch',0),(150,'loop-return',0)]if ID=='4437'else[(0,'start',0),(10,'step-out-travel',0),(18,'right-step-out',0),(35,'return',0),(55,'left-step-out',0),(150,'loop-return',0)]
 for f,label,vi in states:
  s.frame_set(f+1);bpy.context.view_layer.update();v=views[vi];cam.location=v['position'];cam.rotation_euler=(Vector(v['target'])-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=2.25;before=points();s.render.filepath=str(P/f'early-{label}.png');bpy.ops.render.render(write_still=True);assert np.array_equal(before,points());proofs.append({'frame':f,'seconds':f/30,'phase':motion.state(f,ID)['phase'],'file':Path(s.render.filepath).name,'pre_post_render_surface_delta_m':0});pose_refs.append({'id':ID,'frame':f,'joints':{pb.name:list(r.matrix_world@pb.head)for pb in r.pose.bones}})
 record=json.loads((B.parents[2]/'catalogue/exercises'/f'{ID}.json').read_text());clip={'id':ID,'name':record['name'],'action':'Exercise_'+ID,'duration':5,'duration_seconds':5,'frames':150,'fps':30,'native_frame_origin':1,'skinning':'dualQuaternion','primary':[record['target']],'secondary':record['secondaryMuscles'],'display_mode':'heat','highlight_sides':{},'source_instructions':record['instructions'],'source_record_sha256':sha(B.parents[2]/'catalogue/exercises'/f'{ID}.json'),'source_hold_recommendation_seconds':None,'source_workout_interval_seconds':[30,60]if ID=='4436'else None,'interpretation':('Authored six opposite-arm punches with alternating heel curls in five seconds, 200ms punch attack; source does not specify arm/leg pairing or exact cadence. Shin-relative ankle flexion bounded10degrees and rigid forefoot transport avoid the previous hooked-foot failure.'if ID=='4437'else'Authored four alternating lateral step-outs/returns in five seconds, narrow starting feet, low35mm swing lift, soft knees and hands held in front of chest. Source30–60second workout interval retained separately.'),'phases':[{'start':0,'end':5,'label':'Six alternating curl/punch combinations'if ID=='4437'else'Four alternating lateral step-outs and returns'}],'review_status':'early_native_keyed_shape_review_pending'}
 (P/'clip.json').write_text(json.dumps(clip,indent=2)+'\n');(P/'pose-samples.json').write_text(json.dumps(pose_refs,indent=2)+'\n');(P/'motion-witnesses.json').write_text(json.dumps({'id':ID,'source_sha256':sha(F/'source.blend'),'samples':witness[ID]},indent=2)+'\n');early={'id':ID,'source_sha256':sha(F/'source.blend'),'runtime_binding_sha256':report['runtime_binding_sha256'],'actual_saved_weights_normalized_max4':True,'maximum_saved_151_matrix_error':err,'minimum_full_cycle_floor_z_m':min(x['whole_skin_floor_z_m']for x in witness[ID]),'proofs':proofs,'status':'Early native keyed proofs; shape acceptance and full physical/export QA pending.'};(P/'early-report.json').write_text(json.dumps(early,indent=2)+'\n');print('EARLY',json.dumps(early))
