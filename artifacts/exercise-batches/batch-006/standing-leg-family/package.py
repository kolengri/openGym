"""One physical standard-linear GLB, two distinct frozen authored actions."""
from pathlib import Path
import bpy,shutil,json,hashlib
P=Path(__file__).resolve().parent;bpy.ops.wm.open_mainfile(filepath=str(P/'joint-source.blend'));body=bpy.data.objects['SK_BlenderStudioHuman'];rig=bpy.data.objects['RIG_BlenderStudioHuman'];s=bpy.context.scene
assert set(x.name for x in bpy.data.actions)=={'Exercise_3479','Exercise_3480'}
keys=body.data.shape_keys
# Blender5.2 ACTIONS discovers nonactive OBJECT slots on the only rig, but
# discovers nonactive KEY slots only through NLA. Muting preserves authoring
# evaluation while retaining the explicit standard-export association.
track=keys.animation_data.nla_tracks.new();track.name='Exercise_3480';strip=track.strips.new('Exercise_3480',1,bpy.data.actions['Exercise_3480']);strip.action_slot=next(x for x in bpy.data.actions['Exercise_3480'].slots if x.target_id_type=='KEY');track.mute=True;keys.animation_data.use_nla=False
a=bpy.data.actions['Exercise_3479'];rig.animation_data.action=a;body.data.shape_keys.animation_data.action=a;body.data.shape_keys.animation_data.action_slot=next(x for x in a.slots if x.target_id_type=='KEY');s.frame_set(1);s['shared_standing_leg_family']='One source geometry, linear rig and four compact POSITION/NORMAL targets; distinct five-second bilateral trajectories3479 and3480.'
bpy.ops.wm.save_as_mainfile(filepath=str(P/'source.blend'));bpy.ops.object.select_all(action='DESELECT');body.select_set(True);rig.select_set(True);bpy.context.view_layer.objects.active=rig
result=bpy.ops.export_scene.gltf(filepath=str(P/'motion.glb'),export_format='GLB',use_selection=True,export_animations=True,export_animation_mode='ACTIONS',export_force_sampling=True,export_frame_range=True,export_frame_step=1,export_skins=True,export_all_influences=False,export_apply=False,export_morph=True,export_morph_normal=True,export_merge_animation='ACTION',export_attributes=True,export_materials='EXPORT',export_vertex_color='NONE',export_anim_slide_to_zero=True,export_rest_position_armature=True,export_influence_nb=4,export_cameras=False,export_lights=False,export_yup=True);assert result=={'FINISHED'}
for id in ['3479','3480']:
 out=P.parent/'assets'/id
 for name in ['source.blend','motion.glb']:shutil.copyfile(P/name,out/name)
(P/'export-manifest.json').write_text(json.dumps({'physical_geometry':1,'actions':['Exercise_3479','Exercise_3480'],'skin':'standard linear','morphs':4,'same_bytes_in_both_assets':True,'source_sha256':hashlib.sha256((P/'source.blend').read_bytes()).hexdigest(),'glb_sha256':hashlib.sha256((P/'motion.glb').read_bytes()).hexdigest(),'glb_bytes':(P/'motion.glb').stat().st_size},indent=2)+'\n');print((P/'export-manifest.json').read_text())
