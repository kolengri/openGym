"""Provisional3905 native source and early keyed shoulder proofs."""
import bpy,numpy as np,sys,json,hashlib
from pathlib import Path
from mathutils import Vector
sys.dont_write_bytecode=True
F=Path(__file__).resolve().parent;P=F.parent/'assets/3905';sys.path[:0]=[str(F),str(F.parent.parent/'batch-003')]
import authoring as a,motion,plantar_binding
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert a.initialize()=='227ede3fc31d1a2b47ff40f20a4a7288fe7bb36179add23bae953993826c8b7b';b,r,s=a.body,a.rig,a.scene;report=plantar_binding.apply(b);report['runtime_binding_sha256']=a.binding_hash(b,r);(P/'local-binding-report.json').write_text(json.dumps(report,indent=2)+'\n')
for m in b.modifiers:
 m.show_viewport=m.show_render=m.type=='ARMATURE'
 if m.type=='ARMATURE':m.use_deform_preserve_volume=True
soles={side:np.array([v.index for v in b.data.vertices if v.co.z<.10 and sum(g.weight for g in v.groups if b.vertex_groups[g.group].name in[side+'Foot',side+'ToeBase'])>.5],int)for side in ['Left','Right']}
def points():
 bpy.context.view_layer.update();e=b.evaluated_get(bpy.context.evaluated_depsgraph_get());me=e.to_mesh();p=np.array([v.co[:]for v in me.vertices]);e.to_mesh_clear();return p
r.animation_data_create();action=bpy.data.actions.new('Exercise_3905');action.use_fake_user=True;slot=None;previous={};expected={};witness=[]
for f in range(241):
 r.animation_data.action=None;s.frame_set(f+1);desired,state=motion.pose(a,f);p=points();offsets={side:.001-float(p[idx,2].min())for side,idx in soles.items()};desired,state=motion.pose(a,f,offsets);p=points();err=max(float(np.max(abs(np.array(r.pose.bones[n].matrix)-np.array(m))))for n,m in desired.items());assert err<2e-6,(f,err);expected[f]=np.array([pb.matrix for pb in r.pose.bones]);state.update(ground_offsets_m=offsets,sole_minimum_z_m={side:float(p[idx,2].min())for side,idx in soles.items()},whole_skin_floor_z_m=float(p[:,2].min()),maximum_actual_matrix_error=err);witness.append(state)
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
attr=b.data.attributes.get('_SOURCE_INDEX')or b.data.attributes.new('_SOURCE_INDEX','FLOAT','POINT');attr.data.foreach_set('value',np.arange(10582,dtype=np.float32));s.frame_start=1;s.frame_end=241;s.render.fps=30;s.render.engine='BLENDER_WORKBENCH';s.render.resolution_x=900;s.render.resolution_y=900;s.render.resolution_percentage=100;s.render.film_transparent=True;s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGBA';sh=s.display.shading;sh.light='STUDIO';sh.color_type='MATERIAL';sh.show_shadows=False;sh.show_cavity=False;sh.show_specular_highlight=False;s.view_settings.view_transform='Standard';s.view_settings.look='None';cd=bpy.data.cameras.new('ReviewCamera');cam=bpy.data.objects.new('ReviewCamera',cd);s.collection.objects.link(cam);s.camera=cam;cd.type='ORTHO';views=[{'label':'front_oblique_whole_body','position':[3.4,-5,2.1],'target':[0,0,1.0],'scale':2.4},{'label':'back_oblique_whole_body','position':[-3.4,5,2.1],'target':[0,0,1.0],'scale':2.4}];v=views[0];cam.location=v['position'];cam.rotation_euler=(Vector(v['target'])-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=v['scale'];s.frame_set(1);bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(P/'source.blend'))
bpy.ops.wm.open_mainfile(filepath=str(P/'source.blend'));b=bpy.data.objects['SK_BlenderStudioHuman'];r=bpy.data.objects['RIG_BlenderStudioHuman'];s=bpy.context.scene;cam=s.camera;err=0
for f,matrices in expected.items():
 s.frame_set(f+1);bpy.context.view_layer.update();err=max(err,float(np.max(abs(np.array([pb.matrix for pb in r.pose.bones])-matrices))))
assert err<2e-6;assert a.binding_hash(b,r)==report['runtime_binding_sha256'];assert max(len(v.groups)for v in b.data.vertices)<=4;assert max(abs(sum(g.weight for g in v.groups)-1)for v in b.data.vertices)<2e-6
proofs=[];poses=[]
for f,label,vi in [(0,'start',0),(75,'forward-large',0),(100,'forward-upper',1),(120,'reversal',0),(165,'reverse-large',1),(240,'loop-return',0)]:
 s.frame_set(f+1);bpy.context.view_layer.update();v=views[vi];cam.location=v['position'];cam.rotation_euler=(Vector(v['target'])-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=v['scale'];before=points();s.render.filepath=str(P/f'early-{label}.png');bpy.ops.render.render(write_still=True);assert np.array_equal(before,points());proofs.append({'frame':f,'seconds':f/30,'phase':motion.state(f)['phase'],'file':Path(s.render.filepath).name,'pre_post_render_skin_delta_m':0});poses.append({'id':'3905','frame':f,'joints':{pb.name:list(r.matrix_world@pb.head)for pb in r.pose.bones}})
record=json.loads((F.parents[3]/'catalogue/exercises/3905.json').read_text());clip={'id':'3905','name':record['name'],'action':'Exercise_3905','duration':8,'duration_seconds':8,'frames':240,'fps':30,'native_frame_origin':1,'skinning':'dualQuaternion','primary':[record['target']],'secondary':record['secondaryMuscles'],'display_mode':'heat','highlight_sides':{},'source_instructions':record['instructions'],'source_record_sha256':sha(F.parents[3]/'catalogue/exercises/3905.json'),'source_hold_recommendation_seconds':None,'source_workout_interval_seconds':None,'source_repetitions_before_reverse':[10,15],'authored_demo_circles_per_direction':3,'phases':[{'start':0,'end':4,'label':'Three forward circles, gradually larger'},{'start':4,'end':8,'label':'Three reverse circles, return to small radius'}],'interpretation':'Provisional fallback, not a confirmed replacement selection. Eight-second authored demonstration: three forward and three reverse circles, wrist radius45→140→45mm,12-degree soft elbow and open relaxed hands. Source10–15circles before reversing retained separately. Original Shoulder/Arm/Neck/Head weights preserved; only distal plantar repair. Static mirror-time poses are identical while motion direction reverses; direction must be assessed in playback. No measured activation or clinical claim.','review_status':'provisional_early_native_shape_pending'}
for name,d in [('clip.json',clip),('cameras.json',views),('pose-samples.json',poses),('motion-witnesses.json',{'id':'3905','source_sha256':sha(P/'source.blend'),'samples':witness}),('early-report.json',{'id':'3905','status':'Provisional fallback. Early actual native keyed shape; no final QA/selection claim.','source_sha256':sha(P/'source.blend'),'runtime_binding_sha256':report['runtime_binding_sha256'],'upper_body_weights_original':True,'maximum_saved_241_matrix_error':err,'maximum_reach_error_m':max(v for x in witness for v in x['reach_errors_m'].values()),'minimum_sole_z_m':min(z for x in witness for z in x['sole_minimum_z_m'].values()),'maximum_sole_z_m':max(z for x in witness for z in x['sole_minimum_z_m'].values()),'proofs':proofs})]:
 (P/name).write_text(json.dumps(d,indent=2)+'\n')
(P/'authoring-context.json').write_bytes((F.parent/'contexts/3905.json').read_bytes());print('EARLY',json.dumps({'source':sha(P/'source.blend'),'maximum_saved_error':err,'proofs':proofs}))
