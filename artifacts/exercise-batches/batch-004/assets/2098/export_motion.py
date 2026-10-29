"""Export exactly the frozen linear source cage and one baked action."""
from pathlib import Path
import bpy,json,hashlib
P=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P/'source.blend'))
q=json.loads((P/'surface-contact-report.json').read_text());source=hashlib.sha256((P/'source.blend').read_bytes()).hexdigest()
assert q['ok'] and q['source_sha256']==source
body=bpy.data.objects['SK_BlenderStudioHuman'];rig=bpy.data.objects['RIG_BlenderStudioHuman']
for m in body.modifiers:
 m.show_viewport=m.show_render=m.type=='ARMATURE'
 if m.type=='ARMATURE':m.use_deform_preserve_volume=False
bpy.context.scene.frame_set(1);bpy.ops.object.select_all(action='DESELECT');body.select_set(True);rig.select_set(True);bpy.context.view_layer.objects.active=rig
result=bpy.ops.export_scene.gltf(filepath=str(P/'motion.glb'),export_format='GLB',use_selection=True,export_animations=True,export_animation_mode='ACTIONS',export_force_sampling=True,export_frame_range=True,export_frame_step=1,export_skins=True,export_all_influences=False,export_apply=False,export_attributes=True,export_materials='EXPORT',export_vertex_color='NONE',export_anim_slide_to_zero=True,export_rest_position_armature=True,export_influence_nb=4,export_cameras=False,export_lights=False,export_yup=True)
assert result=={'FINISHED'}
print('EXPORTED',P/'motion.glb')
