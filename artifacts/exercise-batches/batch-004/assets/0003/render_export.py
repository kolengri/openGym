"""Curated actual exported-DQ geometry views; Three normals are tested separately."""
import json,sys
from pathlib import Path
import bpy
from mathutils import Vector
P=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P/'source.blend'))
scene=bpy.context.scene;source_mode='--source' in sys.argv
if not source_mode:
    for object in list(bpy.data.objects):
        if object.type in ['MESH','ARMATURE']:bpy.data.objects.remove(object,do_unlink=True)
    for action in list(bpy.data.actions):bpy.data.actions.remove(action)
    scene.render.fps=30;bpy.ops.import_scene.gltf(filepath=str(P/'motion.glb'))
for object in bpy.data.objects:
    if object.type!='MESH':continue
    for modifier in object.modifiers:
        modifier.show_viewport=modifier.show_render=modifier.type=='ARMATURE'
        if modifier.type=='ARMATURE':modifier.use_deform_preserve_volume=True
cameras=json.loads((P/'cameras.json').read_text());camera=scene.camera
scene.display.shading.show_shadows=False;scene.display.shading.show_cavity=False;scene.display.shading.show_specular_highlight=False
phases=[(0,'start-side',1),(12.5,'blend-oblique',0),(37.5,'right-cross-oblique',0),(112.5,'left-cross-oblique',0),(150,'return-side',1)]
if '--blend-only' in sys.argv:phases=[(12.5,'blend-oblique',0)]
for frame,label,view_index in phases:
    view=cameras[view_index];camera.location=view['position'];camera.rotation_euler=(Vector(view['target'])-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.ortho_scale=view['scale']
    scene.frame_set(int(frame)+(1 if source_mode else 0),subframe=frame%1);bpy.context.view_layer.update()
    prefix='dq-cage'if source_mode else'exported-dq'
    scene.render.filepath=str(P/f'{prefix}-{label}.png')
    if frame==phases[0][0]:bpy.ops.render.render(write_still=False)
    bpy.ops.render.render(write_still=True)
print('ACTUAL_EXPORTED_DQ_GEOMETRY_PROOFS_READY')
