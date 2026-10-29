"""Bake the shared four-action standing source and early motion proof packet."""
import bpy,numpy as np,json,sys,hashlib,importlib.util,os
from pathlib import Path
from mathutils import Vector
sys.dont_write_bytecode=True
F=Path(__file__).resolve().parent;B=F.parent;OLD=B.parent/'batch-008/standing-dynamic';sys.path[:0]=[str(F),str(B.parent/'batch-003')];import authoring as a,motion
camera_records={ID:(B/'assets'/ID/'cameras.json').read_bytes()for ID in motion.IDS if(B/'assets'/ID/'cameras.json').exists()}
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for dependency in json.loads((F/'dependencies.json').read_text())['files']:assert sha(Path(dependency['path']))==dependency['sha256'],dependency['path']
a.initialize();bpy.ops.wm.open_mainfile(filepath=str(OLD/'source.blend'));a.body=b=bpy.data.objects['SK_BlenderStudioHuman'];a.rig=r=bpy.data.objects['RIG_BlenderStudioHuman'];a.scene=s=bpy.context.scene
spec=importlib.util.spec_from_file_location('foundation_motion',OLD/'motion.py');foundation=importlib.util.module_from_spec(spec);spec.loader.exec_module(foundation)
component=json.loads((F/'cuff-component-dependency.json').read_text());assert sha(Path(component['component_path']))==component['component_sha256'];assert sha(Path(component['importer_path']))==component['importer_sha256'];assert component['root_native_shape_accepted']
spec=importlib.util.spec_from_file_location('wrap_cuff_component',Path(component['importer_path']));cuff=importlib.util.module_from_spec(spec);spec.loader.exec_module(cuff);cuff.install(b,r,s,archive_path=component['archive_path'],expected_sha256=component['archive_sha256'])
r.animation_data_clear();keys=b.data.shape_keys;keys.animation_data_clear()
for act in list(bpy.data.actions):bpy.data.actions.remove(act)
for ob in list(bpy.data.objects):
 if ob not in[b,r]:bpy.data.objects.remove(ob,do_unlink=True)
for pb in r.pose.bones:pb.rotation_mode='QUATERNION'
for m in b.modifiers:
 m.show_viewport=m.show_render=m.type=='ARMATURE'
 if m.type=='ARMATURE':m.use_deform_preserve_volume=True
soles={side:np.array([v.index for v in b.data.vertices if v.co.z<.10 and sum(g.weight for g in v.groups if b.vertex_groups[g.group].name in[side+'Foot',side+'ToeBase'])>.5],int)for side,_ in motion.SIDES}
def points():
 bpy.context.view_layer.update();e=b.evaluated_get(bpy.context.evaluated_depsgraph_get());me=e.to_mesh();p=np.array([v.co[:]for v in me.vertices]);e.to_mesh_clear();return p
assert list(keys.key_blocks)[1:] and [k.name for k in list(keys.key_blocks)[1:]]==motion.MORPH_NAMES
r.animation_data_create();keys.animation_data_create();witness={};expected={}
for ID in motion.IDS:
 act=bpy.data.actions.new('Exercise_'+ID);act.use_fake_user=True;slot=None;previous={};witness[ID]=[];expected[ID]={}
 for f in range(151):
  r.animation_data.action=None;keys.animation_data.action=None;s.frame_set(f+1)
  values=motion.morph_values(f,ID);assert len(values)==len(keys.key_blocks)-1
  for k,val in zip(list(keys.key_blocks)[1:],values):k.value=val
  d,st=motion.pose(a,f,ID,foundation.pose);p=points();offset={side:.001-float(p[idx,2].min())for side,idx in soles.items()};d,st=motion.pose(a,f,ID,foundation.pose,offset);p=points();err=max(float(np.max(abs(np.array(r.pose.bones[n].matrix)-np.array(mat))))for n,mat in d.items());assert err<2e-6,(ID,f,err);expected[ID][f]=np.array([pb.matrix for pb in r.pose.bones]);st.update(ground_offsets_m=offset,whole_skin_floor_z_m=float(p[:,2].min()),sole_minimum_z_m={side:float(p[idx,2].min())for side,idx in soles.items()});witness[ID].append(st);r.animation_data.action=act
  if slot:r.animation_data.action_slot=slot
  for pb in r.pose.bones:
   if pb.name in previous and pb.rotation_quaternion.dot(previous[pb.name])<0:pb.rotation_quaternion.negate()
   previous[pb.name]=pb.rotation_quaternion.copy();pb.keyframe_insert('location',frame=f+1);pb.keyframe_insert('rotation_quaternion',frame=f+1)
  slot=r.animation_data.action_slot
 slot=act.slots.new(id_type='KEY',name='Explicit component animation and reset');keys.animation_data.action=act;keys.animation_data.action_slot=slot
 for f in range(151):
  for k,val in zip(list(keys.key_blocks)[1:],motion.morph_values(f,ID)):k.value=val;k.keyframe_insert('value',frame=f+1)
 for l in act.layers:
  for strip in l.strips:
   for bag in strip.channelbags:
    for fc in bag.fcurves:
     for pt in fc.keyframe_points:pt.interpolation='LINEAR'
def select(ID):
 act=bpy.data.actions['Exercise_'+ID];r.animation_data.action=act;r.animation_data.action_slot=next(x for x in act.slots if x.target_id_type=='OBJECT');keys.animation_data.action=act;keys.animation_data.action_slot=next(x for x in act.slots if x.target_id_type=='KEY')
s.frame_start=1;s.frame_end=151;s.render.fps=30;s.render.engine='BLENDER_WORKBENCH';s.render.resolution_x=780;s.render.resolution_y=900;s.render.resolution_percentage=100;s.render.film_transparent=True;s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGBA';sh=s.display.shading;sh.light='STUDIO';sh.color_type='MATERIAL';sh.show_cavity=False;sh.show_shadows=False;sh.show_specular_highlight=False;s.view_settings.view_transform='Standard';s.view_settings.look='None';cd=bpy.data.cameras.new('NativeReviewCamera');cam=bpy.data.objects.new('NativeReviewCamera',cd);s.collection.objects.link(cam);s.camera=cam;cd.type='ORTHO';views=[{'label':'front_oblique_whole_body','position':[3.4,-5,2.0],'target':[0,0,1.05],'scale':3.0},{'label':'rear_oblique_whole_body','position':[-3.4,5,2.0],'target':[0,0,1.05],'scale':3.0}];select('1404');s.frame_set(1);bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(F/'source.blend'))
np.savez_compressed(F/'authored-route-reference.npz',bone_names=np.array([pb.name for pb in r.pose.bones]),matrices=np.array([expected['3995'][f]for f in range(151)]),source_sha256=np.array(sha(F/'source.blend')))
for ID in motion.IDS:
 P=B/'assets'/ID;select(ID);error=0
 for f,mat in expected[ID].items():s.frame_set(f+1);bpy.context.view_layer.update();error=max(error,float(np.max(abs(np.array([pb.matrix for pb in r.pose.bones])-mat))))
 assert error<2e-6
 path=P/'source.blend'
 if path.exists():path.unlink()
 os.link(F/'source.blend',path);proofs=[];poses=[];states=[(0,'start'),(24,'intermediate'),(60,'peak'),(105,'return'),(150,'loop-return')]if ID!='3995'else[(0,'open'),(18,'wrap-intermediate'),(28,'mid-to-held-transition'),(37.5,'right-over-wrap'),(75,'open-return'),(112.5,'repeat-right-over-wrap'),(150,'loop-return')]
 for f,label in states:
  s.frame_set(int(f)+1,subframe=f%1);bpy.context.view_layer.update();before=points();poses.append({'id':ID,'frame':f,'joints':{pb.name:list(r.matrix_world@pb.head)for pb in r.pose.bones}})
  for view in views:
   cam.location=view['position'];cam.rotation_euler=(Vector(view['target'])-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=view['scale']/(780/900);s.render.filepath=str(P/f"early-{sha(F/'source.blend')[:12]}-{label}-{view['label']}.png");bpy.ops.render.render(write_still=True);assert np.array_equal(before,points());proofs.append({'frame':f,'phase':label,'view':view['label'],'file':Path(s.render.filepath).name})
  if label in['peak','right-over-wrap','repeat-right-over-wrap']:
   for side,pos in [('front',(2.8,-4,1.8)),('rear',(-2.8,4,1.8))]:
    cam.location=pos;target=Vector((0,-.4,1.55)if ID=='1405'else(0,-.58,1.28)if ID=='1404'else(0,.32,1.0)if ID=='4515'else(0,.03,1.43));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=.8;s.render.filepath=str(P/f'early-{sha(F/"source.blend")[:12]}-{label}-hands-{side}.png');bpy.ops.render.render(write_still=True)
 record=json.loads((B.parents[2]/'catalogue/exercises'/f'{ID}.json').read_text());clip={'id':ID,'name':record['name'],'action':'Exercise_'+ID,'duration':5,'duration_seconds':5,'frames':150,'fps':30,'native_frame_origin':1,'skinning':'dualQuaternion','primary':[record['target']],'secondary':record['secondaryMuscles'],'display_mode':'heat'if ID=='3995'else'stretch','highlight_sides':{},'source_instructions':record['instructions'],'source_record_sha256':sha(B.parents[2]/'catalogue/exercises'/f'{ID}.json'),'source_hold_recommendation_seconds':[15,30]if ID=='1405'else None if ID=='3995'else[20,30],'phases':[{'start':0,'end':2.5,'label':'Right arm above wrap and reopen'},{'start':2.5,'end':5,'label':'Right arm above wrap and reopen'}]if ID=='3995'else[{'start':0,'end':2,'label':'Enter'},{'start':2,'end':3,'label':'Hold'},{'start':3,'end':5,'label':'Return'}],'interpretation':('Root-authorized staging amendment: two identical right-over wrap and reopen repetitions in five seconds. Hands approach opposite posterolateral upper-back patches outside the shoulders; the right arm stays above the left in both repetitions.' if ID=='3995' else json.loads((B/'source-resolutions.json').read_text())[ID])+' Exact reach, elbow poles and cadence are authored. Grip acquisition follows reachable arm placement; reverse path releases fingers before unwinding. Preserved shoulder correctives have explicit zero tracks. The separately authored WrapRightOverCuff POSITION/NORMAL component follows the3995 shoulder-protraction fraction and resets explicitly in all other actions.','review_status':'early_native_motion_pending','source_sha256':sha(F/'source.blend')}
 for name,value in [('clip.json',clip),('cameras.json',views),('pose-samples.json',poses),('motion-witnesses.json',{'id':ID,'source_sha256':sha(F/'source.blend'),'samples':witness[ID]}),('early-report.json',{'id':ID,'source_sha256':sha(F/'source.blend'),'status':'Early native proof, full QA pending.','maximum_saved_151_matrix_error':error,'maximum_reach_error_m':max(v for x in witness[ID]for v in x['reach_errors_m'].values()),'minimum_full_cycle_skin_z_m':min(x['whole_skin_floor_z_m']for x in witness[ID]),'proofs':proofs})]:
  if name=='cameras.json'and ID in camera_records:(P/name).write_bytes(camera_records[ID])
  else:(P/name).write_text(json.dumps(value,indent=2)+'\n')
 (P/'authoring-context.json').write_bytes((B/'contexts'/f'{ID}.json').read_bytes())
 print('EARLY',ID,error,max(v for x in witness[ID]for v in x['reach_errors_m'].values()))
