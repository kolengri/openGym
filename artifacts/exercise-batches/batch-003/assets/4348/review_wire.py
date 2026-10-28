"""Curated neutral original-cage topology still; no source/GLB mutation."""
import sys
from pathlib import Path
sys.dont_write_bytecode = True
import bpy
from mathutils import Vector
P=Path(__file__).resolve().parent;bpy.ops.wm.open_mainfile(filepath=str(P/'source.blend'))
scene=bpy.context.scene;body=bpy.data.objects['SK_BlenderStudioHuman']
for mod in body.modifiers:mod.show_render=mod.show_viewport=mod.type=='ARMATURE'
wire=body.copy();wire.data=body.data.copy();wire.name='QA_Original_Cage_Wire';scene.collection.objects.link(wire)
w=wire.modifiers.new('QA_Wire','WIREFRAME');w.thickness=.00065;w.offset=1
scene.display.shading.color_type='OBJECT';body.color=(.62,.65,.68,1);wire.color=(.015,.015,.015,1)
scene.display.shading.show_shadows=False;scene.display.shading.show_cavity=False;scene.display.shading.show_specular_highlight=False
sys.path.insert(0,str(P));from build_motion import CAMERAS
c=CAMERAS['oblique'];scene.camera.location=c['position'];scene.camera.rotation_euler=(Vector(c['target'])-scene.camera.location).to_track_quat('-Z','Y').to_euler();scene.camera.data.ortho_scale=c['scale']
scene.frame_set(76);scene.render.filepath=str(P/'review-wire.png');bpy.ops.render.render(write_still=True)
