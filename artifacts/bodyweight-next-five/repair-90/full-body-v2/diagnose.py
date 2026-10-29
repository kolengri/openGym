"""Source-bound full-body diagnostic stills; no canonical file writes."""
import bpy, json, math, sys
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent
ROOT=P.parents[1]
SOURCE=ROOT/'ninety-repaired.blend'
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
body=bpy.data.objects['SK_BlenderStudioHuman'];rig=bpy.data.objects['RIG_BlenderStudioHuman'];scene=bpy.context.scene
for m in body.modifiers:m.show_viewport=m.show_render=m.type=='ARMATURE'
scene.render.engine='BLENDER_WORKBENCH';scene.render.resolution_x=720;scene.render.resolution_y=720;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.film_transparent=True
scene.view_settings.view_transform='Standard'
s=scene.display.shading;s.light='STUDIO';s.color_type='SINGLE';s.single_color=(.60,.62,.64);s.show_shadows=False;s.show_cavity=False;s.show_specular_highlight=False
camdata=bpy.data.cameras.new('FullBodyDiagnostic');cam=bpy.data.objects.new('FullBodyDiagnostic',camdata);scene.collection.objects.link(cam);scene.camera=cam;camdata.type='ORTHO'
views={'front':(0,-5,1.25),'oblique':(3.4,-5,2.5),'side':(5,0,.75),'rear':(-1.5,5,1.5)}
out=P/'diagnosis';out.mkdir(exist_ok=True)
report={'source':str(SOURCE),'rest_bones':{},'poses':{}}
for b in rig.data.bones:
 report['rest_bones'][b.name]={'head':list(b.head_local),'tail':list(b.tail_local),'matrix':[list(r) for r in b.matrix_local]}
for label,action,frame in [('rest',None,1),('start','Exercise_6560',1),('hinge','Exercise_6560',76),('press','Exercise_10565',76)]:
 rig.animation_data.action=bpy.data.actions[action] if action else None
 if action:scene.frame_set(frame)
 else:
  from mathutils import Matrix
  for pb in rig.pose.bones:pb.matrix_basis=Matrix.Identity(4)
 bpy.context.view_layer.update()
 ev=body.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh()
 report['poses'][label]={'min_z':min(v.co.z for v in me.vertices),'bones':{b.name:{'head':list(b.head),'tail':list(b.tail),'matrix':[list(r) for r in b.matrix]} for b in rig.pose.bones}}
 ev.to_mesh_clear()
 for view,position in views.items():
  target=Vector((0,0,.87 if label=='rest' else .46));camdata.ortho_scale=2.05 if label=='rest' else 1.65
  cam.location=Vector(position)+(Vector((0,0,.45)) if label=='rest' else Vector((0,0,0)))
  cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()
  scene.render.filepath=str(out/f'{label}-{view}.png');bpy.ops.render.render(write_still=True)
(out/'frames.json').write_text(json.dumps(report,indent=2)+'\n')
