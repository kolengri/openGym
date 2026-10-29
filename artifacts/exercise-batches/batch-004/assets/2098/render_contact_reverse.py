"""Complementary actual-cage still; never changes the saved source."""
from pathlib import Path
import bpy
from mathutils import Vector
P=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P/'source.blend'))
s=bpy.context.scene;s.frame_set(76);c=s.camera;c.location=(1.8,-2.1,1.7);c.rotation_euler=(Vector((-.12,-.50,1.40))-c.location).to_track_quat('-Z','Y').to_euler();c.data.ortho_scale=.45
s.render.filepath=str(P/'hold-hands-reverse.png');bpy.ops.render.render(write_still=True)
