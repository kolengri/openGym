"""Reproducible canonical source setup, native proofs and sampled actions."""
import bpy,numpy as np,sys,json,hashlib,argparse,shutil
from pathlib import Path
from mathutils import Vector
sys.dont_write_bytecode=True
F=Path(__file__).resolve().parent;B=F.parent;sys.path[:0]=[str(F),str(B.parent/'batch-003'),str(B.parent/'batch-007/arm-circle-family')]
import authoring as a,plantar_binding
parser=argparse.ArgumentParser();parser.add_argument('--final',action='store_true');opts=parser.parse_args(sys.argv[sys.argv.index('--')+1:]if'--'in sys.argv else[])
assert a.initialize()=='227ede3fc31d1a2b47ff40f20a4a7288fe7bb36179add23bae953993826c8b7b';b,r,s=a.body,a.rig,a.scene
import motion,shoulder_binding
shoulder_report=shoulder_binding.apply(b);(F/'shoulder-binding-report.json').write_text(json.dumps(shoulder_report,indent=2)+'\n')
report=plantar_binding.apply(b);report['upper_body_original']=False;report['upper_body_preserved_outside_shoulder_domain']=True;report['shoulder_component']='shoulder-binding-report.json';report['runtime_binding_sha256']=a.binding_hash(b,r);(F/'local-binding-report.json').write_text(json.dumps(report,indent=2)+'\n')
for m in b.modifiers:
 m.show_viewport=m.show_render=m.type=='ARMATURE'
 if m.type=='ARMATURE':m.use_deform_preserve_volume=True
soles={side:np.array([v.index for v in b.data.vertices if v.co.z<.10 and sum(g.weight for g in v.groups if b.vertex_groups[g.group].name in[side+'Foot',side+'ToeBase'])>.5],int)for side in ['Left','Right']}
def points():
 bpy.context.view_layer.update();e=b.evaluated_get(bpy.context.evaluated_depsgraph_get());me=e.to_mesh();p=np.array([v.co[:]for v in me.vertices]);e.to_mesh_clear();return p
r.animation_data_create();witness={};expected_all={};bpy.context.preferences.filepaths.save_version=0
for ID in ['1987','1986']:
 action=bpy.data.actions.new('Exercise_'+ID);action.use_fake_user=True;slot=None;previous={};witness[ID]=[];expected={}
 for f in (range(151)if opts.final else[0,15,30,45,60,75,90,105,120,135,150]):
  r.animation_data.action=None;s.frame_set(f+1);desired,state=motion.pose(a,ID,f);p=points();offsets={side:.001-float(p[idx,2].min())for side,idx in soles.items()};desired,state=motion.pose(a,ID,f,offsets);p=points();err=max(float(np.max(abs(np.array(r.pose.bones[n].matrix)-np.array(m))))for n,m in desired.items());assert err<2e-6,(ID,f,err);expected[f]=np.array([pb.matrix for pb in r.pose.bones]);state.update(ground_offsets_m=offsets,sole_minimum_z_m={side:float(p[idx,2].min())for side,idx in soles.items()},whole_skin_floor_z_m=float(p[:,2].min()),maximum_actual_matrix_error=err);witness[ID].append(state)
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
 expected_all[ID]=expected
 for f,target in expected.items():
  s.frame_set(f+1);bpy.context.view_layer.update();assert np.max(abs(np.array([pb.matrix for pb in r.pose.bones])-target))<3e-6
(F/'native-keying-receipt.json').write_text(json.dumps(witness,indent=2)+'\n')
attr=b.data.attributes.get('_SOURCE_INDEX')or b.data.attributes.new('_SOURCE_INDEX','FLOAT','POINT');attr.data.foreach_set('value',np.arange(10582,dtype=np.float32));s.frame_start=1;s.frame_end=151;s.render.fps=30;s.render.engine='BLENDER_WORKBENCH';s.render.resolution_x=700;s.render.resolution_y=840;s.render.resolution_percentage=100;s.render.film_transparent=True;s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGBA';sh=s.display.shading;sh.light='STUDIO';sh.color_type='MATERIAL';sh.show_shadows=False;sh.show_cavity=False;sh.show_specular_highlight=False;s.view_settings.view_transform='Standard';s.view_settings.look='None';cd=bpy.data.cameras.new('ReviewCamera');cam=bpy.data.objects.new('ReviewCamera',cd);s.collection.objects.link(cam);s.camera=cam;cd.type='ORTHO'
def render(P,name,f,pos,target,width):
 s.frame_set(f+1);bpy.context.view_layer.update();before=points();bones=np.array([pb.matrix for pb in r.pose.bones]);cam.location=pos;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();cd.ortho_scale=width/(s.render.resolution_x/s.render.resolution_y);s.render.filepath=str(P/name);bpy.ops.render.render(write_still=True);after=points();assert np.array_equal(before,after);assert np.array_equal(bones,np.array([pb.matrix for pb in r.pose.bones]))
for ID in ['1987','1986']:
 P=B/'assets'/ID;action=bpy.data.actions['Exercise_'+ID];r.animation_data.action=action;r.animation_data.action_slot=action.slots[0];views=[{'label':'posterior_contact_oblique','position':[3.8,5,2.1],'target':[0,.03,.98],'scale':2.2},{'label':'side_whole_body','position':[5,.8,2.1],'target':[0,.03,.98],'scale':2.2}]
 for label,f in [('start',0),('peak',75),('release',120)]:
  for c in views:render(P,'early-'+label+'-'+c['label']+'.png',f,c['position'],c['target'],c['scale'])
 render(P,'early-peak-contact.png',75,(1.2,4,1.9),(0,.17,1.10 if ID=='1987'else 1.61),.58)
 (P/'cameras.json').write_text(json.dumps(views,indent=2)+'\n')
 s.frame_set(1);bpy.ops.wm.save_as_mainfile(filepath=str(P/'source.blend'))
print('EARLY_PROOFS_READY',str(F))

# One physical canonical source with both actions; per-ID copies remain byte-identical.
r.animation_data.action=bpy.data.actions['Exercise_1987'];r.animation_data.action_slot=r.animation_data.action.slots[0];s.frame_set(1);bpy.ops.wm.save_as_mainfile(filepath=str(B/'assets/1987/source.blend'));shutil.copyfile(B/'assets/1987/source.blend',B/'assets/1986/source.blend')
bpy.ops.wm.open_mainfile(filepath=str(B/'assets/1987/source.blend'));b=bpy.data.objects['SK_BlenderStudioHuman'];r=bpy.data.objects['RIG_BlenderStudioHuman'];s=bpy.context.scene;maximum=0
for ID,expected in expected_all.items():
 r.animation_data.action=bpy.data.actions['Exercise_'+ID];r.animation_data.action_slot=r.animation_data.action.slots[0]
 for f,target in expected.items():
  s.frame_set(f+1);bpy.context.view_layer.update();maximum=max(maximum,float(np.max(abs(np.array([pb.matrix for pb in r.pose.bones])-target))))
assert maximum<3e-6
(F/'saved-keying-receipt.json').write_text(json.dumps({'maximum_saved_matrix_error':maximum,'actions':sorted(expected_all),'native_frames_per_action':151 if opts.final else 11,'source_sha256':hashlib.sha256((B/'assets/1987/source.blend').read_bytes()).hexdigest()},indent=2)+'\n')
