"""Bake one distinct upright clip and return actual keyed neutral early proofs."""
import hashlib,json,sys,math
from pathlib import Path
import bpy,numpy as np
from mathutils import Vector
F=Path(__file__).resolve().parent;ID=sys.argv[sys.argv.index('--')+1];P=F.parent/'assets'/ID
sys.path[:0]=[str(F),str(F.parent.parent/'batch-003')]
import authoring as a,motion,binding
assert a.initialize()=='227ede3fc31d1a2b47ff40f20a4a7288fe7bb36179add23bae953993826c8b7b'
body,rig,scene=a.body,a.rig,a.scene
sys.path.insert(0,str(Path.home()/'.codex/skills/blender-core/scripts'));import env_report
(P/'environment.json').write_text(json.dumps(env_report.run(),indent=2)+'\n')
assert bpy.app.version[:3]==(5,2,3)
report=binding.apply(body);report['original_binding_sha256']='227ede3fc31d1a2b47ff40f20a4a7288fe7bb36179add23bae953993826c8b7b';report['runtime_binding_sha256']=a.binding_hash(body,rig);(P/'local-binding-report.json').write_text(json.dumps(report,indent=2)+'\n')
for m in body.modifiers:
 m.show_viewport=m.show_render=m.type=='ARMATURE'
 if m.type=='ARMATURE':m.use_deform_preserve_volume=True
rest=np.array([v.co[:]for v in body.data.vertices]);soles={side:np.array([v.index for v in body.data.vertices if v.co.z<.10 and sum(g.weight for g in v.groups if body.vertex_groups[g.group].name in [side+'Foot',side+'ToeBase'])>.5],int)for side in ['Left','Right']}
def points():
 bpy.context.view_layer.update();ev=body.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh();p=np.array([v.co[:]for v in me.vertices]);ev.to_mesh_clear();return p
rig.animation_data_create();action=bpy.data.actions.new('Exercise_'+ID);action.use_fake_user=True;slot=None;previous={};expected={};witness=[]
for frame in range(151):
 rig.animation_data.action=None;scene.frame_set(frame+1);offsets={};desired,state=motion.pose(a,frame,ID);p=points()
 for side in state['grounded']:offsets[side]=.001-float(p[soles[side],2].min())
 if offsets:desired,state=motion.pose(a,frame,ID,offsets);p=points()
 error=max(float(np.max(abs(np.array(rig.pose.bones[n].matrix)-np.array(m))))for n,m in desired.items());assert error<2e-6,('Pose override',frame,error)
 expected[frame]={n:np.array(m)for n,m in desired.items()};state.update(frame=frame,ground_offsets_m=offsets,whole_skin_floor_z_m=float(p[:,2].min()),sole_minimum_z_m={s:float(p[ids,2].min())for s,ids in soles.items()},maximum_actual_matrix_error=error,root_z_m=float(rig.pose.bones['Hips'].head.z))
 witness.append(state)
 rig.animation_data.action=action
 if slot:rig.animation_data.action_slot=slot
 for bone in rig.pose.bones:
  if bone.name in previous and bone.rotation_quaternion.dot(previous[bone.name])<0:bone.rotation_quaternion.negate()
  previous[bone.name]=bone.rotation_quaternion.copy();bone.keyframe_insert('location',frame=frame+1);bone.keyframe_insert('rotation_quaternion',frame=frame+1)
 slot=rig.animation_data.action_slot
for layer in action.layers:
 for strip in layer.strips:
  for bag in strip.channelbags:
   for curve in bag.fcurves:
    for key in curve.keyframe_points:key.interpolation='LINEAR'
attr=body.data.attributes.get('_SOURCE_INDEX')or body.data.attributes.new('_SOURCE_INDEX','FLOAT','POINT');attr.data.foreach_set('value',np.arange(10582,dtype=np.float32))
scene.frame_start=1;scene.frame_end=151;scene.render.fps=30;scene.render.engine='BLENDER_WORKBENCH';scene.render.resolution_x=760;scene.render.resolution_y=900;scene.render.resolution_percentage=100;scene.render.film_transparent=True;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
shade=scene.display.shading;shade.light='STUDIO';shade.color_type='MATERIAL';shade.show_shadows=False;shade.show_cavity=False;shade.show_specular_highlight=False;scene.view_settings.view_transform='Standard';scene.view_settings.look='None'
cd=bpy.data.cameras.new('ExerciseReviewCamera');cam=bpy.data.objects.new('ExerciseReviewCamera',cd);scene.collection.objects.link(cam);scene.camera=cam;cd.type='ORTHO'
cameras=[{'label':'front_oblique_whole_body','position':[3.8,-5,2.1],'target':[0,-.04,1.02],'scale':2.25},{'label':'side_whole_body','position':[5,-.1,1.2],'target':[0,-.04,1.02],'scale':2.25}]
(P/'cameras.json').write_text(json.dumps(cameras,indent=2)+'\n');scene.frame_set(1);bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(P/'source.blend'))
bpy.ops.wm.open_mainfile(filepath=str(P/'source.blend'));body=bpy.data.objects['SK_BlenderStudioHuman'];rig=bpy.data.objects['RIG_BlenderStudioHuman'];scene=bpy.context.scene;cam=scene.camera;maximum_saved_error=0
for frame,matrices in expected.items():
 scene.frame_set(frame+1);bpy.context.view_layer.update();maximum_saved_error=max(maximum_saved_error,max(float(np.max(abs(np.array(rig.pose.bones[n].matrix)-m)))for n,m in matrices.items()))
assert maximum_saved_error<2e-6,maximum_saved_error
assert a.binding_hash(body,rig)==report['runtime_binding_sha256']
assert max(len(v.groups)for v in body.data.vertices)<=4
assert max(abs(sum(g.weight for g in v.groups)-1)for v in body.data.vertices)<2e-6
proof_states=[(0,'ready',0),(20.25,'left-knee-flight',0),(28.5,'soft-left-landing',1),(57.75,'right-knee-flight',0)]if ID=='4918'else[(0,'guard',0),(37.5,'right-punch',0),(112.5,'left-punch',1),(150,'guard-return',1)]
proofs=[];poses=[]
for frame,label,view_index in proof_states:
 scene.frame_set(int(frame)+1,subframe=frame%1);bpy.context.view_layer.update();view=cameras[view_index];cam.location=view['position'];cam.rotation_euler=(Vector(view['target'])-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=view['scale'];before=points();scene.render.filepath=str(P/f'early-v5-{label}.png');bpy.ops.render.render(write_still=True);after=points();assert np.array_equal(before,after),'Render changed actual keyed surface'
 proofs.append({'frame':frame,'file':Path(scene.render.filepath).name,'pre_post_render_surface_delta_m':0});poses.append({'id':ID,'frame':frame,'joints':{b.name:list(rig.matrix_world@b.head)for b in rig.pose.bones}})
record=json.loads((F.parents[3]/'catalogue/exercises'/f'{ID}.json').read_text());primary=['calves','quadriceps']if ID=='4918'else['shoulders','triceps'];secondary=['glutes']if ID=='4918'else['core','obliques']
clip={'id':ID,'name':record['name'],'action':'Exercise_'+ID,'duration':5,'duration_seconds':5,'frames':150,'fps':30,'native_frame_origin':1,'skinning':'dualQuaternion','primary':[record['target']],'secondary':record['secondaryMuscles'],'display_primary':primary,'display_secondary':secondary,'display_role_basis':'Source-informed artistic visible load proxies; cardiovascular system is not a surface muscle. Source target/secondary labels are retained, not rewritten; no measured activation claim.','source_roles':{'primary':[record['target']],'secondary':record['secondaryMuscles']},'display_mode':'heat','highlight_sides':{},'source_instructions':record['instructions'],'source_hold_recommendation_seconds':None,'source_workout_interval_seconds':[30,60]if ID=='3531'else None,'phases':[{'start':0,'end':5,'label':'Four alternating spring hops with declared ground/flight phases'if ID=='4918'else'Right punch and retraction; left punch and retraction'}],'interpretation':'Authored slowed five-second demonstration, not a claimed source tempo or clinical/force/stability certification. '+('Four one-foot spring hops with opposite knee drive, 0.30-second ballistic flight per hop, toe push-off and ball landing; knee/ankle flexion and opposing arm swing absorb/prepare each contact.'if ID=='4918'else'Fixed staggered stance, closed guard fists and alternating forward punches;17-degree soft elbow at extension,8-degree upper torso rotation; no strike target or impact props. Source30–60second workout interval retained separately.'),'source_record_sha256':hashlib.sha256((F.parents[3]/'catalogue/exercises'/f'{ID}.json').read_bytes()).hexdigest(),'review_status':'early_neutral_native_review_pending'}
(P/'clip.json').write_text(json.dumps(clip,indent=2)+'\n');(P/'pose-samples.json').write_text(json.dumps(poses,indent=2)+'\n');(P/'motion-witnesses.json').write_text(json.dumps({'id':ID,'source_sha256':hashlib.sha256((P/'source.blend').read_bytes()).hexdigest(),'skinning':'dualQuaternion','sole_source_ids':{s:ids.tolist()for s,ids in soles.items()},'samples':witness},indent=2)+'\n')
(P/'authoring-context.json').write_bytes((F.parent/'contexts'/f'{ID}.json').read_bytes());early={'id':ID,'status':'early_neutral_keyed_source_review_pending','source_sha256':hashlib.sha256((P/'source.blend').read_bytes()).hexdigest(),'runtime_binding_sha256':a.binding_hash(body,rig),'maximum_saved_151_matrix_error':maximum_saved_error,'actual_weights_normalized_max4':True,'proofs':proofs,'remaining':'Primary source mechanics/shape review before full native/decoded support, flight, clearance, positive area, game and export checks.'};(P/'early-report.json').write_text(json.dumps(early,indent=2)+'\n');print('EARLY_UPRIGHT_ASSET',json.dumps(early))
