from pathlib import Path
import bpy
from mathutils import Vector
P=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P/'source.blend'));s=bpy.context.scene;s.frame_set(76)
target=(bpy.data.objects['RIG_BlenderStudioHuman'].pose.bones['LeftFoot'].head+Vector((.05,-.04,-.025)))
cam=s.camera;cam.location=target+Vector((2,1,.6));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=.45
s.render.filepath=str(P/'hold-grip-detail.png');bpy.ops.render.render(write_still=True)
