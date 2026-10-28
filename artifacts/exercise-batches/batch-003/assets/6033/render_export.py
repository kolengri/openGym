"""View the actual imported exported skin at curated start/peak/return phases."""
import bpy,json,sys
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P/'source.blend'))
s=bpy.context.scene
source_mode='--source' in sys.argv
if not source_mode:
 for ob in list(bpy.data.objects):
  if ob.type in ['MESH','ARMATURE']:bpy.data.objects.remove(ob,do_unlink=True)
 for a in list(bpy.data.actions):bpy.data.actions.remove(a)
 s.render.fps=30
 bpy.ops.import_scene.gltf(filepath=str(P/'motion.glb'))
for ob in bpy.data.objects:
 if ob.type=='MESH':
  for modifier in ob.modifiers:
   modifier.show_viewport=modifier.show_render=modifier.type=='ARMATURE'
   if modifier.type=='ARMATURE':modifier.use_deform_preserve_volume=True
cam=s.camera
for frame,label,view in [(0,'start','side'),(75,'peak','oblique'),(150,'return','side')]:
 if view=='oblique':cam.location=(3.8,-4,2.2);target=Vector((0,-.23,.42));cam.data.ortho_scale=1.9
 else:cam.location=(5,-.15,.65);target=Vector((0,-.15,.42));cam.data.ortho_scale=1.85
 cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()
 s.frame_set(frame+(1 if source_mode else 0));bpy.context.view_layer.update()
 s.display.shading.type='SOLID';s.display.shading.light='STUDIO';s.display.shading.show_shadows=False;s.display.shading.show_cavity=False;s.display.shading.show_specular_highlight=False
 prefix='dq-cage' if source_mode else 'exported-dq'
 s.render.filepath=str(P/f'{prefix}-{label}-{view}.png')
 # Background Workbench can retain a pre-import draw cache on its first draw.
 if label=='start':bpy.ops.render.render(write_still=False)
 bpy.ops.render.render(write_still=True)
print('EXPORTED_SKIN_PROOFS_READY')
