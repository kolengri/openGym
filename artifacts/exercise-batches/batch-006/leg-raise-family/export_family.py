"""Frozen four-action standard GLB; no native source resave."""
from pathlib import Path
import sys,bpy
P=Path(__file__).resolve().parent;sys.path.insert(0,str(P));bpy.ops.wm.open_mainfile(filepath=str(P/'source.blend'));b=bpy.data.objects['SK_BlenderStudioHuman'];r=bpy.data.objects['RIG_BlenderStudioHuman'];s=bpy.context.scene
assert sorted(a.name for a in bpy.data.actions)==sorted('Exercise_'+i for i in ['4826','4001','3590','5106']);assert len(b.data.shape_keys.key_blocks)==8
for m in b.modifiers:
 m.show_viewport=m.show_render=m.type=='ARMATURE'
 if m.type=='ARMATURE':m.use_deform_preserve_volume=True
s.frame_set(1);bpy.ops.object.select_all(action='DESELECT');b.select_set(True);r.select_set(True);bpy.context.view_layer.objects.active=r
result=bpy.ops.export_scene.gltf(filepath=str(P/'motion.glb'),export_format='GLB',use_selection=True,export_yup=True,export_apply=False,export_texcoords=True,export_normals=True,export_materials='EXPORT',export_vertex_color='NONE',export_attributes=True,export_morph=True,export_morph_normal=True,export_animations=True,export_animation_mode='ACTIONS',export_merge_animation='ACTION',export_force_sampling=True,export_frame_range=False,export_frame_step=1,export_anim_slide_to_zero=True,export_skins=True,export_influence_nb=4,export_all_influences=False,export_def_bones=True,export_leaf_bone=False,export_rest_position_armature=True,export_extras=True,export_cameras=False,export_lights=False);assert result=={'FINISHED'}
from complete_morph_channels import complete
print(complete(P),flush=True)
