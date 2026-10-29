"""Explicit peak solid/wire views and palm contact inspection; never saves scene."""
from pathlib import Path
import sys,json
import bpy,numpy as np
from mathutils import Vector
F=Path(__file__).resolve().parent;ID=sys.argv[sys.argv.index('--')+1];P=F.parent/'assets'/ID
bpy.ops.wm.open_mainfile(filepath=str(P/'source.blend'));b=bpy.data.objects['SK_BlenderStudioHuman'];r=bpy.data.objects['RIG_BlenderStudioHuman'];s=bpy.context.scene;r.animation_data.action=bpy.data.actions['Exercise_'+ID];r.animation_data.action_slot=next(x for x in r.animation_data.action.slots if x.target_id_type=='OBJECT');s.frame_set(31);bpy.context.view_layer.update()
sys.path.insert(0,str(Path.home()/'.codex/skills/blender-asset-qa/scripts'));import review_shots
for mode in ([]if '--palm-only'in sys.argv else['random','wire']):
 result=review_shots.run(objects=[b.name],out=str(P/f'qa-{mode}.png'),views=['right','top','three_quarter','bottom'],mode=mode,res=500);print(mode,result)
# close hand views with an explicit floor line, viewed from the supporting side.
cam=s.camera;s.render.resolution_x=900;s.render.resolution_y=600;s.render.film_transparent=True;s.display.shading.show_cavity=False;s.display.shading.show_shadows=False;s.display.shading.show_object_outline=False;s.display.shading.color_type='MATERIAL';cam.data.type='ORTHO';cam.data.ortho_scale=.46
for side in ['Left','Right']:
 h=r.pose.bones[side+'Hand'].head;sign=1 if side=='Left'else-1;target=h+Vector((0,-.06,0));cam.location=h+Vector((sign,-.4,.22));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();s.render.filepath=str(P/f'palm-{side}-contact.png');bpy.ops.render.render(write_still=True)
print('REVIEW_READY',ID)
