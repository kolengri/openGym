"""Bake the authoritative fixed-tabletop support foundation; no new pose fitting."""
import json,sys,hashlib
from pathlib import Path
import bpy,numpy as np
from mathutils import Vector,Quaternion
P=Path(__file__).resolve().parent;H=P.parents[1]/'posture-support';S=P.parents[2]/'batch-004/assets/0003'
sys.path[:0]=[str(P),str(H),str(P.parents[2]/'batch-003')]
import authoring as a,support_sampler as support
C=support.CONTRACT
assert C['status']=='native_support_passed'
assert hashlib.sha256((S/'source.blend').read_bytes()).hexdigest()==C['source_blend_sha256']
a.initialize();bpy.ops.wm.open_mainfile(filepath=str(S/'source.blend'))
a.body=bpy.data.objects['SK_BlenderStudioHuman'];a.rig=bpy.data.objects['RIG_BlenderStudioHuman'];a.scene=bpy.context.scene
body,rig,scene=a.body,a.rig,a.scene
original_action=body.data.shape_keys.animation_data.action
rig.animation_data_clear()
foundation={name:np.array([v.co[:]for v in body.data.shape_keys.key_blocks[name].data],np.float32)for name in support.KEY_NAMES}
for name,values in foundation.items():assert hashlib.sha256(values.tobytes()).hexdigest()==C['foundation']['key_coordinate_sha256_float32'][name]
binding=support.apply_binding(body,rig);assert a.binding_hash(body,rig)==C['runtime_binding_sha256']
composition=support.install_support(body,'5266')
import glute_binding_overlay
posterior_attachment=glute_binding_overlay.install(body)
for modifier in body.modifiers:
 modifier.show_viewport=modifier.show_render=modifier.type=='ARMATURE'
 if modifier.type=='ARMATURE':modifier.use_deform_preserve_volume=True
scene.frame_start=1;scene.frame_end=151;scene.render.fps=30
# Manual sampling has no attached rig action. The original KEY action supplies
# the exact original151 partition schedule. Only after capture is the rig baked.
captured=[];previous={};max_matrix=0
for frame in range(151):
 points,receipt=support.sample(a,frame,'5266');max_matrix=max(max_matrix,receipt['matrix_max_error'])
 values={}
 for bone in rig.pose.bones:
  q=bone.rotation_quaternion.copy()
  if bone.name in previous and q.dot(previous[bone.name])<0:q.negate()
  previous[bone.name]=q.copy();values[bone.name]=(bone.location.copy(),q)
 captured.append(values)
 observed=[body.data.shape_keys.key_blocks[name].value for name in support.KEY_NAMES]
 assert np.max(abs(np.array(observed)-C['foundation']['original151_weight_schedule'][frame]))<1e-7
original_action.name='Exercise_5266';original_action.use_fake_user=True
rig.animation_data_create();rig.animation_data.action=original_action;rig.animation_data.action_slot=next(slot for slot in original_action.slots if slot.target_id_type=='OBJECT')
for frame,values in enumerate(captured):
 scene.frame_set(frame+1)
 for bone in rig.pose.bones:
  bone.location,bone.rotation_quaternion=values[bone.name]
  bone.keyframe_insert('location',frame=frame+1);bone.keyframe_insert('rotation_quaternion',frame=frame+1)
for layer in original_action.layers:
 for strip in layer.strips:
  for bag in strip.channelbags:
   for curve in bag.fcurves:
    for key in curve.keyframe_points:key.interpolation='LINEAR'
assert len(bpy.data.actions)==1
attribute=body.data.attributes.get('_SOURCE_INDEX')or body.data.attributes.new(name='_SOURCE_INDEX',type='FLOAT',domain='POINT');attribute.data.foreach_set('value',np.arange(10582,dtype=np.float32))
scene.render.engine='BLENDER_WORKBENCH';scene.render.resolution_x=800;scene.render.resolution_y=650;scene.render.resolution_percentage=100
scene.render.film_transparent=True;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
shading=scene.display.shading;shading.light='STUDIO';shading.color_type='MATERIAL';shading.show_shadows=False;shading.show_cavity=False;shading.show_specular_highlight=False
scene.view_settings.view_transform='Standard';scene.view_settings.look='None'
camera=scene.camera;camera.name='Camera_5266';camera.data.type='ORTHO'
cameras=json.loads((P/'cameras.json').read_text())
def view(preset):
 camera.location=preset['position'];camera.rotation_euler=(Vector(preset['target'])-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.ortho_scale=preset['scale']
view(cameras[0]);scene.frame_set(1);bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(P/'source.blend'))
# Reopen the baked deliverable: every proof is the canonical action evaluation.
bpy.ops.wm.open_mainfile(filepath=str(P/'source.blend'));body=bpy.data.objects['SK_BlenderStudioHuman'];rig=bpy.data.objects['RIG_BlenderStudioHuman'];scene=bpy.context.scene;camera=scene.camera
for frame,label in [(0,'start'),(19,'entry'),(37.5,'right-twist'),(112.5,'left-twist')]:
 scene.frame_set(int(frame)+1,subframe=frame%1);bpy.context.view_layer.update()
 for preset in cameras:
  view(preset);scene.render.filepath=str(P/f'early-{label}-{preset["label"]}.png');bpy.ops.render.render(write_still=True)
 view({'position':[3.5,3.5,2.4],'target':[0,.05,.3],'scale':2.35});scene.render.filepath=str(P/f'early-{label}-rear.png');bpy.ops.render.render(write_still=True)
scene.frame_set(1);view(cameras[0]);bpy.ops.object.select_all(action='DESELECT');body.select_set(True);rig.select_set(True);bpy.context.view_layer.objects.active=rig
bpy.ops.export_scene.gltf(filepath=str(P/'motion.glb'),export_format='GLB',use_selection=True,export_yup=True,export_apply=False,export_texcoords=True,export_normals=True,export_materials='EXPORT',export_vertex_color='NONE',export_attributes=True,export_morph=True,export_morph_normal=True,export_animations=True,export_animation_mode='ACTIONS',export_merge_animation='ACTION',export_force_sampling=True,export_frame_range=False,export_frame_step=1,export_anim_slide_to_zero=True,export_skins=True,export_influence_nb=4,export_def_bones=True,export_leaf_bone=False,export_rest_position_armature=True,export_extras=True,export_cameras=False,export_lights=False)
report=json.loads((S/'joint-corrective-report.json').read_text());report['method']='Exact original0003 three compact joint/flank target buffers plus declared sparse5266support deltas, preserving exact original151weight schedule. No extra joint residual installed.';report['foundation']=C['foundation'];report['support_composition']=composition;report['support_contract_sha256']=hashlib.sha256((H/'support-contract.json').read_bytes()).hexdigest();report['runtime_binding_sha256']=C['runtime_binding_sha256'];report['additional_joint_residuals']=[];report['posterior_attachment_binding']=posterior_attachment
basis=np.array([v.co[:]for v in body.data.vertices])
for entry in report['keys']:
 values=np.array([v.co[:]for v in body.data.shape_keys.key_blocks[entry['name']].data]);delta=values-basis;entry['changed_original_vertex_ids']=np.flatnonzero(np.linalg.norm(delta,axis=1)>1e-8).tolist();entry['total_maximum_rest_delta_m']=float(np.linalg.norm(delta,axis=1).max())
(P/'joint-corrective-report.json').write_text(json.dumps(report,indent=2)+'\n');(P/'binding-report.json').write_text(json.dumps(binding,indent=2)+'\n')
(P/'build-report.json').write_text(json.dumps({'source_sha256':hashlib.sha256((P/'source.blend').read_bytes()).hexdigest(),'motion_sha256':hashlib.sha256((P/'motion.glb').read_bytes()).hexdigest(),'action':'Exercise_5266','source_frames':[1,151],'constant_root_z_m':C['constant_root_z_m'],'maximum_requested_native_matrix_error':max_matrix,'runtime_binding_sha256':a.binding_hash(body,rig),'support_composition':composition,'additional_joint_residuals':[]},indent=2)+'\n')
print('FINAL_FIXED_TABLETOP_BAKED',flush=True)
