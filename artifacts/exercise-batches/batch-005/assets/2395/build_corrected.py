"""Bake the frozen, source-bound bicycle support recipe without pose refitting."""
import hashlib,json,sys
from pathlib import Path
import bpy,numpy as np
P=Path(__file__).resolve().parent;S=P.parents[2]/'batch-004/assets/0003';H=P.parents[1]/'posture-support'
sys.path[:0]=[str(P),str(H),str(P.parents[2]/'batch-003'),str(S)]
import authoring as a,support_sampler as sampler
contract=sampler.CONTRACT
assert contract['status']=='native_support_passed'
assert hashlib.sha256((S/'source.blend').read_bytes()).hexdigest()==contract['source_blend_sha256']
a.initialize();bpy.ops.wm.open_mainfile(filepath=str(S/'source.blend'))
a.body=bpy.data.objects['SK_BlenderStudioHuman'];a.rig=bpy.data.objects['RIG_BlenderStudioHuman'];a.scene=bpy.context.scene
body,rig,scene=a.body,a.rig,a.scene
original_binding=a.binding_hash(body,rig);assert original_binding==contract['original_binding_sha256']
action=rig.animation_data.action;slot=rig.animation_data.action_slot;action.name='Exercise_2395';rig.animation_data.action=None
assert body.data.shape_keys.animation_data.action is action
basis=np.array([v.co[:]for v in body.data.vertices]);oldkeys={k.name:np.array([v.co[:]for v in k.data])for k in body.data.shape_keys.key_blocks}
for name,digest in contract['foundation']['key_coordinate_sha256_float32'].items():assert hashlib.sha256(oldkeys[name].astype(np.float32).tobytes()).hexdigest()==digest
binding=sampler.apply_binding(body,rig);support=sampler.install_support(body,'2395')
assert a.binding_hash(body,rig)==contract['runtime_binding_sha256']
assert np.array_equal(basis,np.array([v.co[:]for v in body.data.vertices]))
assert np.array_equal(oldkeys['Basis'],np.array([v.co[:]for v in body.data.shape_keys.key_blocks['Basis'].data]))
maximum_additive=max(float(np.linalg.norm(np.array([v.co[:]for v in body.data.shape_keys.key_blocks[n].data])-oldkeys[n],axis=1).max())for n in sampler.KEY_NAMES);assert maximum_additive<=.008
foundation_binding=a.binding_hash(body,rig)
previous={};expected={};maximum_pose_error=0.;schedule=[]
for frame in range(151):
 rig.animation_data.action=None
 surface,meta=sampler.sample(a,frame,'2395');desired=meta['desired'];maximum_pose_error=max(maximum_pose_error,meta['matrix_max_error'])
 schedule.append([float(body.data.shape_keys.key_blocks[n].value)for n in sampler.KEY_NAMES])
 expected[frame]={name:np.array(matrix)for name,matrix in desired.items()}
 rig.animation_data.action=action;rig.animation_data.action_slot=slot
 for bone in rig.pose.bones:
  if bone.name in previous and bone.rotation_quaternion.dot(previous[bone.name])<0:bone.rotation_quaternion.negate()
  previous[bone.name]=bone.rotation_quaternion.copy()
  bone.keyframe_insert('location',frame=frame+1);bone.keyframe_insert('rotation_quaternion',frame=frame+1)
assert np.array_equal(np.array(schedule),np.array(contract['foundation']['original151_weight_schedule']))
# Replay accepted joint components; no corrective fitting occurs here.
import glute_binding_overlay
assert hashlib.sha256((P/'glute-binding-repair.json').read_bytes()).hexdigest()=='a7c22d67f59ffacb4e7c7b10a70db7c9d04c2af9aa430474acc17e8f897f854a'
hip=glute_binding_overlay.install(body)
shoulder=np.load(P/'shoulder-additive-component.npz');shoulder_ids=shoulder['source_ids']
assert hashlib.sha256((P/'shoulder-additive-component.npz').read_bytes()).hexdigest()=='72fbe31853f567c95216b3d2848e2df64bb8afae7fb330cd61dafd6b2c5aceda'
for index,name in enumerate(sampler.KEY_NAMES):
 current=np.array([v.co[:]for v in body.data.shape_keys.key_blocks[name].data],np.float32)
 assert np.array_equal(current,shoulder['foundation_buffers'][index])
 final=current.astype(np.float64);final[shoulder_ids]+=shoulder['deltas'][index]
 body.data.shape_keys.key_blocks[name].data.foreach_set('co',final.astype(np.float32).ravel())
for layer in action.layers:
 for strip in layer.strips:
  for bag in strip.channelbags:
   for curve in bag.fcurves:
    for key in curve.keyframe_points:key.interpolation='LINEAR'
scene.frame_set(1);bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(P/'source.blend'))
bpy.ops.wm.open_mainfile(filepath=str(P/'source.blend'))
body=bpy.data.objects['SK_BlenderStudioHuman'];rig=bpy.data.objects['RIG_BlenderStudioHuman'];scene=bpy.context.scene
maximum_saved_error=0.;saved_schedule=[]
for frame,matrices in expected.items():
 scene.frame_set(frame+1);bpy.context.view_layer.update()
 maximum_saved_error=max(maximum_saved_error,max(float(np.max(abs(np.array(rig.pose.bones[name].matrix)-matrix)))for name,matrix in matrices.items()))
 saved_schedule.append([float(body.data.shape_keys.key_blocks[n].value)for n in sampler.KEY_NAMES])
assert maximum_saved_error<2e-6,maximum_saved_error
assert np.array_equal(np.array(saved_schedule),np.array(contract['foundation']['original151_weight_schedule']))
scene.frame_set(1)
bpy.ops.object.select_all(action='DESELECT');body.select_set(True);rig.select_set(True);bpy.context.view_layer.objects.active=rig
bpy.ops.export_scene.gltf(filepath=str(P/'motion.glb'),export_format='GLB',use_selection=True,export_yup=True,export_apply=False,export_texcoords=True,export_normals=True,export_materials='EXPORT',export_vertex_color='NONE',export_attributes=True,export_morph=True,export_morph_normal=True,export_animations=True,export_animation_mode='ACTIONS',export_merge_animation='ACTION',export_force_sampling=True,export_frame_range=False,export_frame_step=1,export_anim_slide_to_zero=True,export_skins=True,export_influence_nb=4,export_def_bones=True,export_leaf_bone=False,export_rest_position_armature=True,export_extras=True,export_cameras=False,export_lights=False)
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
receipt={'source_asset':'batch-004/assets/0003','source_blend_sha256':sha(S/'source.blend'),'original_source_sha256':a.SOURCE_SHA,'support_contract':'../../posture-support/support-contract.json','support_contract_sha256':sha(H/'support-contract.json'),'helper_hashes':{n:sha(H/n)for n in ['support_sampler.py','profile_binding.py','support-targets.npz','frozen-neutral-envelope.json','support-protected-domain.json']},'posture':contract['posture'],'constant_root_z_m':contract['constant_root_z_m'],'basis_uv_rest_original_ids_unchanged':True,'original_binding_sha256':original_binding,'binding_rest_uv_sha256':foundation_binding,'runtime_binding_after_joint_repair_sha256':a.binding_hash(body,rig),'original_three_targets_preserved_as_additive_foundation':True,'composition':'Each final key equals the exact original0003 key plus the declared sparse2395supportdelta. This equals six additive targets sharing threeweights; no legacy guard is subtracted.','original151_weight_schedule_exact':True,'maximum_new_additive_rest_delta_m':maximum_additive,'legacy_maximum_rest_delta_m':.05276146819288466,'maximum_pose_matrix_error':maximum_pose_error,'maximum_saved_matrix_error':maximum_saved_error,'motion_equivalence':False,'motion_change':'Frozen coupled pelvis/lumbar posture and constant supportheight; original bicycle controls and transported head/hand mechanics.','actions':[x.name for x in bpy.data.actions],'support':support,'joint_repair_integration':'joint-repair-integration.json','joint_repair_source_sha256':sha(P/'source.blend'),'shoulder_component':'shoulder-additive-component.npz'}
(P/'profile-binding-overlay.json').write_text(json.dumps(binding,indent=2)+'\n');(P/'family-reuse-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
for name in ['support-contract.json','frozen-neutral-envelope.json','support-protected-domain.json']:(P/name).write_bytes((H/name).read_bytes())
if (P/'joint-repair-integration.json').exists():
 integration=json.loads((P/'joint-repair-integration.json').read_text());integration['source_sha256']=sha(P/'source.blend');integration['runtime_binding_sha256']=a.binding_hash(body,rig);integration['hip_overlay']=hip;(P/'joint-repair-integration.json').write_text(json.dumps(integration,indent=2)+'\n')
print('CORRECTED_ASSET_READY',json.dumps({k:v for k,v in receipt.items()if k not in ['support']}))
