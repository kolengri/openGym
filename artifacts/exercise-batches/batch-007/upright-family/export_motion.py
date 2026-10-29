"""One physical GLB with two independently selectable five-second actions."""
import bpy,json,hashlib,os
from pathlib import Path
F=Path(__file__).resolve().parent;bpy.ops.wm.open_mainfile(filepath=str(F/'source.blend'));b=bpy.data.objects['SK_BlenderStudioHuman'];r=bpy.data.objects['RIG_BlenderStudioHuman'];bpy.context.scene.frame_set(1)
assert sorted(a.name for a in bpy.data.actions)==['Exercise_4436','Exercise_4437']
bpy.ops.object.select_all(action='DESELECT');b.select_set(True);r.select_set(True);bpy.context.view_layer.objects.active=r
bpy.ops.export_scene.gltf(filepath=str(F/'motion.glb'),export_format='GLB',use_selection=True,export_yup=True,export_apply=False,export_texcoords=True,export_normals=True,export_materials='EXPORT',export_vertex_color='NONE',export_attributes=True,export_morph=True,export_morph_normal=True,export_animations=True,export_animation_mode='ACTIONS',export_merge_animation='ACTION',export_force_sampling=True,export_frame_range=False,export_frame_step=1,export_anim_slide_to_zero=True,export_skins=True,export_influence_nb=4,export_def_bones=True,export_leaf_bone=False,export_rest_position_armature=True,export_extras=True,export_cameras=False,export_lights=False)
import sys;sys.path.insert(0,str(F));import fix_fist_weights
weight_report=fix_fist_weights.run(F/'motion.glb',['Exercise_4437'])
for ID in ['4437','4436']:
 (F.parent/'assets'/ID/'fist-weight-export.json').write_text(json.dumps(weight_report,indent=2)+'\n')
 p=F.parent/'assets'/ID/'motion.glb'
 if p.exists():p.unlink()
 os.link(F/'motion.glb',p)
print('EXPORTED',hashlib.sha256((F/'motion.glb').read_bytes()).hexdigest())
