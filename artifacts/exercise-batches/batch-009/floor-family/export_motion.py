"""Export a single saved keyed source with exact source-ID attribute."""
import bpy,sys,hashlib,json
from pathlib import Path
from mathutils import Vector
F=Path(__file__).resolve().parent;ID=sys.argv[sys.argv.index('--')+1];P=F.parent/'assets'/ID;assert ID=='4663'
bpy.ops.wm.open_mainfile(filepath=str(P/'source.blend'));s=bpy.context.scene;b=bpy.data.objects['SK_BlenderStudioHuman'];r=bpy.data.objects['RIG_BlenderStudioHuman'];s.frame_set(1)
assert 'Exercise_'+ID in bpy.data.actions
# Give the editable scene the same first recommended camera before freezing source.
v=json.loads((P/'cameras.json').read_text())[0];cam=s.camera;cam.location=v['position'];cam.rotation_euler=(Vector(v['target'])-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=v['scale'];bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(P/'source.blend'))
bpy.ops.object.select_all(action='DESELECT');b.select_set(True);r.select_set(True);bpy.context.view_layer.objects.active=r
bpy.ops.export_scene.gltf(filepath=str(P/'motion.glb'),export_format='GLB',use_selection=True,export_yup=True,export_apply=False,export_texcoords=True,export_normals=True,export_materials='EXPORT',export_vertex_color='NONE',export_attributes=True,export_morph=True,export_morph_normal=True,export_animations=True,export_animation_mode='ACTIONS',export_merge_animation='ACTION',export_force_sampling=True,export_frame_range=False,export_frame_step=1,export_anim_slide_to_zero=True,export_skins=True,export_influence_nb=4,export_def_bones=True,export_leaf_bone=False,export_rest_position_armature=True,export_extras=True,export_cameras=False,export_lights=False)
print('FROZEN_EXPORT',json.dumps({name:hashlib.sha256((P/name).read_bytes()).hexdigest()for name in ['source.blend','motion.glb']}))
