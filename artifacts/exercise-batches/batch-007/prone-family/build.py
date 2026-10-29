"""Bake original source-safe DQ actions and render neutral early evidence."""
import hashlib,json,sys,math
from pathlib import Path
import bpy,numpy as np
from mathutils import Vector
F=Path(__file__).resolve().parent;ID=sys.argv[sys.argv.index('--')+1];P=F.parent/'assets'/ID;P.mkdir(exist_ok=True,parents=True)
sys.path[:0]=[str(F),str(F.parent.parent/'batch-003')];import authoring as a,motion
original=a.initialize();body,rig,scene=a.body,a.rig,a.scene
for m in body.modifiers:
 m.show_viewport=m.show_render=m.type=='ARMATURE'
 if m.type=='ARMATURE':m.use_deform_preserve_volume=True
# Source-independent causal waist and plantar repairs only; no posed binding.
sys.path.insert(0,str(F.parent.parent/'batch-006/upright-cardio-family'));import binding
receipt=binding.apply(body);motion.configure(a);receipt['original_binding_sha256']=original;receipt['runtime_binding_sha256']=a.binding_hash(body,rig)
(P/'local-binding-report.json').write_text(json.dumps(receipt,indent=2)+'\n')
rest=np.array([v.co[:]for v in body.data.vertices]);names={g.index:g.name for g in body.vertex_groups}
patches={}
for side,sign in [('Left',1),('Right',-1)]:
 patches[side+'_foot']=np.array([v.index for v in body.data.vertices if v.co.z<.10 and sign*v.co.x>.10 and sum(g.weight for g in v.groups if names[g.group]in[side+'Foot',side+'ToeBase'])>.5],int)
 patches[side+'_hand']=np.array([v.index for v in body.data.vertices if sum(g.weight for g in v.groups if names[g.group].startswith(side)and any(x in names[g.group]for x in ['Hand','Index','Middle','Ring','Little','Thumb']))>.5],int)
def points():
 bpy.context.view_layer.update();ev=body.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh();p=np.array([v.co[:]for v in me.vertices]);ev.to_mesh_clear();return p
root=None;offset={}
if ID in ['4702','4715']:
 motion.pose(a,0,ID);p=points();idx=np.where((rest[:,2]>.86)&(rest[:,2]<1.03)&(abs(rest[:,0])<.18))[0];root=.15+.001-float(p[idx,2].min())
motion.pose(a,0,ID,root);p=points()
for k,idx in patches.items():
 if ID=='3294'or k.endswith('_hand'):offset[k]=.001-float(p[idx,2].min())
expected={};witness=[];captured=[];previous={}
for frame in range(151):
 scene.frame_set(frame+1);desired,state=motion.pose(a,frame,ID,root,offset);p=points();error=max(float(np.max(abs(np.array(rig.pose.bones[n].matrix)-np.array(m))))for n,m in desired.items());assert error<2e-6
 row={}
 for bone in rig.pose.bones:
  q=bone.rotation_quaternion.copy()
  if bone.name in previous and q.dot(previous[bone.name])<0:q.negate()
  previous[bone.name]=q.copy();row[bone.name]=(bone.location.copy(),q)
 captured.append(row);expected[frame]={n:np.array(m)for n,m in desired.items()};witness.append({**state,'frame':frame,'floor_min_z_m':float(p[:,2].min())})
rig.animation_data_create();act=bpy.data.actions.new('Exercise_'+ID);act.use_fake_user=True;rig.animation_data.action=act
for frame,row in enumerate(captured):
 scene.frame_set(frame+1)
 for bone in rig.pose.bones:bone.location,bone.rotation_quaternion=row[bone.name];bone.keyframe_insert('location',frame=frame+1);bone.keyframe_insert('rotation_quaternion',frame=frame+1)
for layer in act.layers:
 for strip in layer.strips:
  for bag in strip.channelbags:
   for curve in bag.fcurves:
    for key in curve.keyframe_points:key.interpolation='LINEAR'
if ID in ['4702','4715']:
 copy=act.copy();copy.name='Exercise_'+('4715'if ID=='4702'else'4702');copy.use_fake_user=True
attr=body.data.attributes.get('_SOURCE_INDEX')or body.data.attributes.new('_SOURCE_INDEX','FLOAT','POINT');attr.data.foreach_set('value',np.arange(10582,dtype=np.float32))
scene.frame_start=1;scene.frame_end=151;scene.render.fps=30;scene.render.engine='BLENDER_WORKBENCH';scene.render.resolution_x=1100;scene.render.resolution_y=650;scene.render.resolution_percentage=100;scene.render.film_transparent=True;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
shade=scene.display.shading;shade.light='STUDIO';shade.color_type='MATERIAL';shade.show_shadows=False;shade.show_cavity=False;shade.show_specular_highlight=False;scene.view_settings.view_transform='Standard';scene.view_settings.look='None'
cd=bpy.data.cameras.new('ReviewCamera');cam=bpy.data.objects.new('ReviewCamera',cd);scene.collection.objects.link(cam);scene.camera=cam;cd.type='ORTHO'
cameras=[{'label':'side_whole_body','position':[4,-.2,1.8],'target':[0,-.15,.20],'scale':2.55},{'label':'oblique_whole_body','position':[3,-4,3.6],'target':[0,-.15,.20],'scale':2.55}]
(P/'cameras.json').write_text(json.dumps(cameras,indent=2)+'\n');scene.frame_set(1);bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(P/'source.blend'))
bpy.ops.wm.open_mainfile(filepath=str(P/'source.blend'));body=bpy.data.objects['SK_BlenderStudioHuman'];rig=bpy.data.objects['RIG_BlenderStudioHuman'];scene=bpy.context.scene;cam=scene.camera
saved_error=0
for frame in range(151):
 scene.frame_set(frame+1);bpy.context.view_layer.update();saved_error=max(saved_error,max(float(np.max(abs(np.array(rig.pose.bones[n].matrix)-m)))for n,m in expected[frame].items()))
assert saved_error<2e-6
proofs=[]
for f,label in [(0,'start'),(30,'right-load'),(105,'left-load'),(150,'return')]:
 scene.frame_set(f+1)
 for v in cameras:
  cam.location=v['position'];cam.rotation_euler=(Vector(v['target'])-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=v['scale'];before=points();scene.render.filepath=str(P/f'early-{label}-{v["label"]}.png');bpy.ops.render.render(write_still=True);after=points();assert np.array_equal(before,after)
  proofs.append({'frame':f,'view':v['label'],'file':Path(scene.render.filepath).name,'pre_post_render_skin_delta_m':0})
# A neutral contact diagnostic includes only a sparse reference grid at z=0;
# this reference is never saved into the editable source or GLB.
for f,label in [(0,'start'),(30,'right-load')]:
 scene.frame_set(f+1);cam.location=(4,-.15,.35);cam.rotation_euler=(Vector((0,-.15,.13))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=2.65
 grid=[]
 for y in [-1.2,-.9,-.6,-.3,0,.3,.6,.9,1.2]:
  c=bpy.data.curves.new('ReferenceFloor','CURVE');c.dimensions='3D';c.bevel_depth=.001;c.bevel_resolution=0;sp=c.splines.new('POLY');sp.points.add(1);sp.points[0].co=(-.7,y,0,1);sp.points[1].co=(.7,y,0,1);ob=bpy.data.objects.new('ReferenceFloor',c);scene.collection.objects.link(ob);grid.append(ob)
 scene.render.filepath=str(P/f'early-{label}-support-plane.png');before=points();bpy.ops.render.render(write_still=True);assert np.array_equal(points(),before)
 for ob in grid:bpy.data.objects.remove(ob,do_unlink=True)
(P/'early-proof-readback.json').write_text(json.dumps({'actual_saved_matrix_max_error':saved_error,'root_z_m':root,'contact_offsets_m':offset,'proofs':proofs,'witness':witness},indent=2)+'\n')
print('EARLY_READY',ID,root,offset,flush=True)
