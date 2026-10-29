"""Export the accepted keyed source after native/source QA without rebaking."""
import bpy
from pathlib import Path
P=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P/'source.blend'));body=bpy.data.objects['SK_BlenderStudioHuman'];rig=bpy.data.objects['RIG_BlenderStudioHuman'];bpy.context.scene.frame_set(1)
assert [a.name for a in bpy.data.actions]==['Exercise_2395']
bpy.ops.object.select_all(action='DESELECT');body.select_set(True);rig.select_set(True);bpy.context.view_layer.objects.active=rig
bpy.ops.export_scene.gltf(filepath=str(P/'motion.glb'),export_format='GLB',use_selection=True,export_yup=True,export_apply=False,export_texcoords=True,export_normals=True,export_materials='EXPORT',export_vertex_color='NONE',export_attributes=True,export_morph=True,export_morph_normal=True,export_animations=True,export_animation_mode='ACTIONS',export_merge_animation='ACTION',export_force_sampling=True,export_frame_range=False,export_frame_step=1,export_anim_slide_to_zero=True,export_skins=True,export_influence_nb=4,export_def_bones=True,export_leaf_bone=False,export_rest_position_armature=True,export_extras=True,export_cameras=False,export_lights=False)
