"""Export the exact primary-accepted static attachment candidate without resaving."""
import bpy,json
from mathutils import Vector
from pathlib import Path
P=Path(__file__).resolve().parent;bpy.ops.wm.open_mainfile(filepath=str(P/'source.blend'))
b=bpy.data.objects['SK_BlenderStudioHuman'];r=bpy.data.objects['RIG_BlenderStudioHuman'];bpy.context.scene.frame_set(1)
assert[action.name for action in bpy.data.actions]==['Exercise_5266']
assert len(b.data.shape_keys.key_blocks)==4
for modifier in b.modifiers:
 modifier.show_viewport=modifier.show_render=modifier.type=='ARMATURE'
 if modifier.type=='ARMATURE':modifier.use_deform_preserve_volume=True
bpy.ops.object.select_all(action='DESELECT');b.select_set(True);r.select_set(True);bpy.context.view_layer.objects.active=r
bpy.ops.export_scene.gltf(filepath=str(P/'motion.glb'),export_format='GLB',use_selection=True,export_yup=True,export_apply=False,export_texcoords=True,export_normals=True,export_materials='EXPORT',export_vertex_color='NONE',export_attributes=True,export_morph=True,export_morph_normal=True,export_animations=True,export_animation_mode='ACTIONS',export_merge_animation='ACTION',export_force_sampling=True,export_frame_range=False,export_frame_step=1,export_anim_slide_to_zero=True,export_skins=True,export_influence_nb=4,export_def_bones=True,export_leaf_bone=False,export_rest_position_armature=True,export_extras=True,export_cameras=False,export_lights=False)

# Final native proof uses the canonical saved action and unchanged runtime views.
s=bpy.context.scene;cam=s.camera;views=json.loads((P/'cameras.json').read_text())
for frame,label in [(0,'start'),(19,'entry'),(37.5,'right-twist'),(112.5,'left-twist')]:
 s.frame_set(int(frame)+1,subframe=frame%1)
 for view in views+[{'label':'rear','position':[3.5,3.5,2.4],'target':[0,.05,.3],'scale':2.35}]:
  cam.location=view['position'];cam.rotation_euler=(Vector(view['target'])-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=view['scale'];s.render.filepath=str(P/f'early-{label}-{view["label"]}.png');bpy.ops.render.render(write_still=True)
