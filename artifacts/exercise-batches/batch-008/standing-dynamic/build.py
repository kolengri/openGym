"""Bake two source-facing actions and return early native neutral proof packet."""
import bpy,numpy as np,json,hashlib,sys,os
from pathlib import Path
from mathutils import Vector
F=Path(__file__).resolve().parent;B=F.parent;sys.path[:0]=[str(F),str(B.parent/'batch-003')];import authoring as a,motion,plantar_binding
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();assert a.initialize()=='227ede3fc31d1a2b47ff40f20a4a7288fe7bb36179add23bae953993826c8b7b';b,r,s=a.body,a.rig,a.scene;binding=plantar_binding.apply(b);binding['runtime_binding_sha256']=a.binding_hash(b,r);(F/'local-binding-report.json').write_text(json.dumps(binding,indent=2)+'\n')
for m in b.modifiers:
 m.show_viewport=m.show_render=m.type=='ARMATURE'
 if m.type=='ARMATURE':m.use_deform_preserve_volume=True
soles={side:np.array([v.index for v in b.data.vertices if v.co.z<.10 and sum(g.weight for g in v.groups if b.vertex_groups[g.group].name in[side+'Foot',side+'ToeBase'])>.5],int)for side,_ in motion.SIDES}
def points():
 bpy.context.view_layer.update();e=b.evaluated_get(bpy.context.evaluated_depsgraph_get());me=e.to_mesh();p=np.array([v.co[:]for v in me.vertices]);e.to_mesh_clear();return p
r.animation_data_create();expected={};witness={}
for ID in ['5172','6014']:
 expected[ID]={};witness[ID]=[];action=bpy.data.actions.new('Exercise_'+ID);action.use_fake_user=True;slot=None;previous={}
 for f in range(151):
  r.animation_data.action=None;s.frame_set(f+1);d,st=motion.pose(a,f,ID);p=points();offsets={side:.001-float(p[idx,2].min())for side,idx in soles.items()if side in st['grounded']};d,st=motion.pose(a,f,ID,offsets);p=points();err=max(float(np.max(abs(np.array(r.pose.bones[n].matrix)-np.array(mat))))for n,mat in d.items());assert err<2e-6,(ID,f,err);expected[ID][f]=np.array([pb.matrix for pb in r.pose.bones]);st.update(ground_offsets_m=offsets,whole_skin_floor_z_m=float(p[:,2].min()),sole_minimum_z_m={side:float(p[idx,2].min())for side,idx in soles.items()},maximum_actual_bone_matrix_error=err);witness[ID].append(st);r.animation_data.action=action
  if slot:r.animation_data.action_slot=slot
  for pb in r.pose.bones:
   if pb.name in previous and pb.rotation_quaternion.dot(previous[pb.name])<0:pb.rotation_quaternion.negate()
   previous[pb.name]=pb.rotation_quaternion.copy();pb.keyframe_insert('location',frame=f+1);pb.keyframe_insert('rotation_quaternion',frame=f+1)
  slot=r.animation_data.action_slot
 for layer in action.layers:
  for strip in layer.strips:
   for bag in strip.channelbags:
    for fc in bag.fcurves:
     for key in fc.keyframe_points:key.interpolation='LINEAR'
# Root-accepted exact component; frozen motion/binding inputs remain unchanged.
sys.path.insert(0,str(F/'shoulder-specialist'));import corrective
assert sha(F/'shoulder-specialist/corrective.py')=='e6d91655df864c8331df8c7404b11435db57e303bb5e9ec2ddc8dad26f4a849b'
assert sha(F/'shoulder-specialist/shoulder-ownership-target.npz')=='f78f91bbd0c1d64a1d944980993228952a3ec83a50386c332a2e52f02bd1a958'
corrective.install(b,r,s)
attr=b.data.attributes.get('_SOURCE_INDEX')or b.data.attributes.new('_SOURCE_INDEX','FLOAT','POINT');attr.data.foreach_set('value',np.arange(10582,dtype=np.float32));s.frame_start=1;s.frame_end=151;s.render.fps=30;s.render.engine='BLENDER_WORKBENCH';s.render.resolution_x=850;s.render.resolution_y=900;s.render.resolution_percentage=100;s.render.film_transparent=True;s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGBA';sh=s.display.shading;sh.light='STUDIO';sh.color_type='MATERIAL';sh.show_cavity=False;sh.show_shadows=False;sh.show_specular_highlight=False;s.view_settings.view_transform='Standard';s.view_settings.look='None';cd=bpy.data.cameras.new('NativeReviewCamera');cam=bpy.data.objects.new('NativeReviewCamera',cd);s.collection.objects.link(cam);s.camera=cam;cd.type='ORTHO';views=[{'label':'front_oblique_whole_body','position':[3.4,-5,2.0],'target':[0,0,1.05],'scale':3.5},{'label':'side_whole_body','position':[5,-.1,1.5],'target':[0,0,1.05],'scale':3.5}];r.animation_data.action=bpy.data.actions['Exercise_5172'];r.animation_data.action_slot=r.animation_data.action.slots[0];s.frame_set(1);bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(F/'source.blend'))
for ID in ['5172','6014']:
 P=B/'assets'/ID;corrective.select(b,r,ID);error=0
 for f,mat in expected[ID].items():s.frame_set(f+1);bpy.context.view_layer.update();error=max(error,float(np.max(abs(np.array([pb.matrix for pb in r.pose.bones])-mat))))
 assert error<2e-6;path=P/'source.blend'
 if path.exists():path.unlink()
 os.link(F/'source.blend',path);proofs=[];poses=[];states=[(0,'start-open'),(19,'mid-swing'),(37.5,'right-over-cross'),(75,'return-open'),(112.5,'left-over-cross'),(150,'loop-return')]if ID=='5172'else[(0,'start-low'),(9,'rising-step'),(18.75,'left-knee-overhead'),(37.5,'return-low'),(56.25,'right-knee-overhead'),(150,'loop-return')]
 for f,label in states:
  s.frame_set(int(f)+1,subframe=f%1);bpy.context.view_layer.update();before=points();poses.append({'id':ID,'frame':f,'joints':{pb.name:list(r.matrix_world@pb.head)for pb in r.pose.bones}})
  for view in views:
   cam.location=view['position'];cam.rotation_euler=(Vector(view['target'])-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=view['scale']/(850/900);s.render.filepath=str(P/f"early-v5-{label}-{view['label']}.png");bpy.ops.render.render(write_still=True);assert np.array_equal(before,points());proofs.append({'frame':f,'seconds':f/30,'phase':label,'view':view['label'],'file':Path(s.render.filepath).name,'pre_post_render_skin_delta_m':0})
 record=json.loads((B.parents[2]/'catalogue/exercises'/f'{ID}.json').read_text());clip={'id':ID,'name':record['name'],'action':'Exercise_'+ID,'duration':5,'duration_seconds':5,'frames':150,'fps':30,'native_frame_origin':1,'skinning':'dualQuaternion','primary':[record['target']],'secondary':record['secondaryMuscles'],'display_mode':'heat','highlight_sides':{},'source_instructions':record['instructions'],'source_record_sha256':sha(B.parents[2]/'catalogue/exercises'/f'{ID}.json'),'source_hold_recommendation_seconds':None,'source_workout_interval_seconds':[30,60]if ID=='6014'else None,'phases':[{'start':0,'end':2.5,'label':'First crossover and reopening'if ID=='5172'else'Alternating knee lifts and overhead raises'},{'start':2.5,'end':5,'label':'Other arm above and reopening'if ID=='5172'else'Continue stepping and lowering arms'}],'interpretation':'Five-second authored illustration. '+('Two crossovers alternate upper forearm, with105mm wrist elevation offsets,120degree swing and34.431645degree protraction atcross/3degree retraction atopening. Hip-width standing feet are chosen because leg placement is missing from source.'if ID=='5172'else'Four gentle alternating140mm ankle lifts with matching arm raises; one foot always supported, no flight. Shin-relative foot/forefoot transport preserves ankle shape. Lowered arms retain the original source-rest upperarm/forearm frames (28.24degree upperarm abduction); coherent joint interpolation blends into the authored overhead frame. Source30–60second workout interval remains separate; cadence and range are authored choices.')+' Open relaxed hands, no fists; current-scapula transported upperarm orientation and original upper-body weights preserved. Numerical staging is not a source tempo or measured activation.','review_status':'early_native_shape_pending','source_sha256':sha(F/'source.blend')}
 for name,value in [('clip.json',clip),('cameras.json',views),('pose-samples.json',poses),('local-binding-report.json',binding),('motion-witnesses.json',{'id':ID,'source_sha256':sha(F/'source.blend'),'samples':witness[ID]}),('early-report.json',{'id':ID,'source_sha256':sha(F/'source.blend'),'status':'Actual native shape/motion review pending; not fullQA/export acceptance.','maximum_saved_151_matrix_error':error,'maximum_reach_error_m':max(v for x in witness[ID]for v in x['reach_errors_m'].values()),'minimum_full_cycle_skin_z_m':min(x['whole_skin_floor_z_m']for x in witness[ID]),'proofs':proofs})]:(P/name).write_text(json.dumps(value,indent=2)+'\n')
 (P/'authoring-context.json').write_bytes((B/'contexts'/f'{ID}.json').read_bytes());print('EARLY',ID,sha(F/'source.blend'),error,min(x['whole_skin_floor_z_m']for x in witness[ID]))
