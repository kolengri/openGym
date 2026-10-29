"""Export the provisional single eight-second arm-circle action."""
import bpy,json,hashlib,os
from pathlib import Path
F=Path(__file__).resolve().parent;bpy.ops.wm.open_mainfile(filepath=str(F.parent/'assets/3905/source.blend'));b=bpy.data.objects['SK_BlenderStudioHuman'];r=bpy.data.objects['RIG_BlenderStudioHuman'];bpy.context.scene.frame_set(1)
assert [a.name for a in bpy.data.actions]==['Exercise_3905']
bpy.ops.object.select_all(action='DESELECT');b.select_set(True);r.select_set(True);bpy.context.view_layer.objects.active=r
bpy.ops.export_scene.gltf(filepath=str(F.parent/'assets/3905/motion.glb'),export_format='GLB',use_selection=True,export_yup=True,export_apply=False,export_texcoords=True,export_normals=True,export_materials='EXPORT',export_vertex_color='NONE',export_attributes=True,export_morph=True,export_morph_normal=True,export_animations=True,export_animation_mode='ACTIONS',export_merge_animation='ACTION',export_force_sampling=True,export_frame_range=False,export_frame_step=1,export_anim_slide_to_zero=True,export_skins=True,export_influence_nb=4,export_def_bones=True,export_leaf_bone=False,export_rest_position_armature=True,export_extras=True,export_cameras=False,export_lights=False)
print('EXPORTED',hashlib.sha256((F.parent/'assets/3905/motion.glb').read_bytes()).hexdigest())
