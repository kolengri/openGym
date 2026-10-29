"""Canonical body, isolated keys, and early native start/bilateral-peak/return proofs."""
import bpy,numpy as np,sys,json,hashlib
from pathlib import Path
from mathutils import Vector
sys.dont_write_bytecode=True
F=Path(__file__).resolve().parent;P=F.parent/'assets/3214';P.mkdir(parents=True,exist_ok=True);sys.path[:0]=[str(F),str(F.parents[1]/'batch-003'),str(F.parents[1]/'batch-007/arm-circle-family')]
import authoring as a,motion,plantar_binding
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert a.initialize()=='227ede3fc31d1a2b47ff40f20a4a7288fe7bb36179add23bae953993826c8b7b';b,r,s=a.body,a.rig,a.scene;report=plantar_binding.apply(b);report['runtime_binding_sha256']=a.binding_hash(b,r);(P/'local-binding-report.json').write_text(json.dumps(report,indent=2)+'\n')
for m in b.modifiers:
 m.show_viewport=m.show_render=m.type=='ARMATURE'
 if m.type=='ARMATURE':m.use_deform_preserve_volume=True
soles={side:np.array([v.index for v in b.data.vertices if v.co.z<.10 and sum(g.weight for g in v.groups if b.vertex_groups[g.group].name in[side+'Foot',side+'ToeBase'])>.5],int)for side in ['Left','Right']}
def points():
 bpy.context.view_layer.update();e=b.evaluated_get(bpy.context.evaluated_depsgraph_get());me=e.to_mesh();p=np.array([v.co[:]for v in me.vertices]);e.to_mesh_clear();return p
r.animation_data_create();action=bpy.data.actions.new('Exercise_3214');action.use_fake_user=True;slot=None;previous={};expected={};witness=[]
for f in range(151):
 r.animation_data.action=None;s.frame_set(f+1);desired,state=motion.pose(a,f);p=points();offsets={side:.001-float(p[idx,2].min())for side,idx in soles.items()if side in state['grounded']};desired,state=motion.pose(a,f,offsets);p=points();err=max(float(np.max(abs(np.array(r.pose.bones[n].matrix)-np.array(m))))for n,m in desired.items());assert err<2e-6,(f,err);expected[f]=np.array([pb.matrix for pb in r.pose.bones]);state.update(ground_offsets_m=offsets,sole_minimum_z_m={side:float(p[idx,2].min())for side,idx in soles.items()},whole_skin_floor_z_m=float(p[:,2].min()),maximum_actual_matrix_error=err);witness.append(state)
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
attr=b.data.attributes.get('_SOURCE_INDEX')or b.data.attributes.new('_SOURCE_INDEX','FLOAT','POINT');attr.data.foreach_set('value',np.arange(10582,dtype=np.float32));s.frame_start=1;s.frame_end=151;s.render.fps=30;s.render.engine='BLENDER_WORKBENCH';s.render.resolution_x=800;s.render.resolution_y=800;s.render.resolution_percentage=100;s.render.film_transparent=True;s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGBA';sh=s.display.shading;sh.light='STUDIO';sh.color_type='MATERIAL';sh.show_shadows=False;sh.show_cavity=False;sh.show_specular_highlight=False;s.view_settings.view_transform='Standard';s.view_settings.look='None';cd=bpy.data.cameras.new('ReviewCamera');cam=bpy.data.objects.new('ReviewCamera',cd);s.collection.objects.link(cam);s.camera=cam;cd.type='ORTHO';views=[{'label':'side_whole_body','position':[5,-.45,1.9],'target':[0,0,.95],'scale':2.5},{'label':'front_oblique_whole_body','position':[-3.6,-5,2.6],'target':[0,0,.95],'scale':2.5}];v=views[1];cam.location=v['position'];cam.rotation_euler=(Vector(v['target'])-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=v['scale'];s.frame_set(1);bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(P/'source.blend'))
bpy.ops.wm.open_mainfile(filepath=str(P/'source.blend'));b=bpy.data.objects['SK_BlenderStudioHuman'];r=bpy.data.objects['RIG_BlenderStudioHuman'];s=bpy.context.scene;cam=s.camera;err=0
for f,matrices in expected.items():
 s.frame_set(f+1);bpy.context.view_layer.update();err=max(err,float(np.max(abs(np.array([pb.matrix for pb in r.pose.bones])-matrices))))
assert err<2e-6;assert a.binding_hash(b,r)==report['runtime_binding_sha256'];assert max(len(v.groups)for v in b.data.vertices)<=4;assert max(abs(sum(g.weight for g in v.groups)-1)for v in b.data.vertices)<2e-6
proofs=[]
for f,label in [(0,'start'),(33,'right-reach'),(65,'right-return'),(108,'left-reach'),(140,'left-return'),(150,'loop-return')]:
 for vi,v in enumerate(views):
  s.frame_set(f+1);bpy.context.view_layer.update();cam.location=v['position'];cam.rotation_euler=(Vector(v['target'])-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=v['scale'];before=points();s.render.filepath=str(P/f'early-{label}-{vi}.png');bpy.ops.render.render(write_still=True);assert np.array_equal(before,points());proofs.append({'frame':f,'seconds':f/30,'phase':motion.state(f)['phase'],'file':Path(s.render.filepath).name,'view':v['label'],'pre_post_render_skin_delta_m':0})
record=json.loads((F.parents[3]/'catalogue/exercises/3214.json').read_text());clip={'id':'3214','name':record['name'],'action':'Exercise_3214','duration':5,'duration_seconds':5,'frames':150,'fps':30,'native_frame_origin':1,'skinning':'dualQuaternion','primary':[record['target']],'secondary':record['secondaryMuscles'],'display_mode':'heat','highlight_sides':{},'source_instructions':record['instructions'],'source_record_sha256':sha(F.parents[3]/'catalogue/exercises/3214.json'),'source_hold_recommendation_seconds':None,'phases':[{'start':0,'end':.25,'label':'Transfer right'},{'start':.25,'end':1.2,'label':'Right hand down / left leg back'},{'start':1.2,'end':2.5,'label':'Return and reset'},{'start':2.5,'end':2.75,'label':'Transfer left'},{'start':2.75,'end':3.7,'label':'Left hand down / right leg back'},{'start':3.7,'end':5,'label':'Return and reset'}],'interpretation':'Five-second authored bilateral demonstration. Same-side hand circles down towards stance toes while the opposite near-straight leg rises behind; full upright reset precedes the mirror. Source says towards, so no toe grasp or floor hand contact is imposed. Reach extent follows the actual unchanged body proportions. The rounded arm arc, timing,80-degree pelvic hinge, modest distributed upper-spine rounding and70-degree rear-leg angle are authored interpretations, not exact source facts. Relaxed open fingers and soft knees. Only proven distal plantar binding is reused; torso/arm weights remain original. No measured muscle activation or clinical claim.','review_status':'early_native_shape_pending'}
for name,data in [('clip.json',clip),('cameras.json',views),('motion-witnesses.json',{'id':'3214','source_sha256':sha(P/'source.blend'),'samples':witness}),('early-report.json',{'id':'3214','source_sha256':sha(P/'source.blend'),'runtime_binding_sha256':report['runtime_binding_sha256'],'maximum_saved_151_matrix_error':err,'maximum_reach_error_m':max(v for x in witness for v in x['reach_errors_m'].values()),'proofs':proofs})]:
 (P/name).write_text(json.dumps(data,indent=2)+'\n')
(P/'authoring-context.json').write_bytes((F.parent/'contexts/3214.json').read_bytes());print('EARLY',json.dumps({'source':sha(P/'source.blend'),'maximum_saved_error':err,'proofs':proofs}))
