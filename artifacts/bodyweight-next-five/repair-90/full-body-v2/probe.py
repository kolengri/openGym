import bpy,json,sys,math
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P.parents[1]/'ninety-repaired.blend'))
body=bpy.data.objects['SK_BlenderStudioHuman'];rig=bpy.data.objects['RIG_BlenderStudioHuman'];scene=bpy.context.scene
rig.animation_data.action=bpy.data.actions['Exercise_6560'];scene.frame_set(76);bpy.context.view_layer.update()
report={'weights':{},'rotations':{},'rest_regions':{}}
names={g.index:g.name for g in body.vertex_groups}
for b in rig.pose.bones:
 q=b.matrix.to_quaternion()@b.bone.matrix_local.to_quaternion().inverted()
 report['rotations'][b.name]={'delta_angle':math.degrees(q.angle),'delta_axis':list(q.axis)}
for side in ['Left','Right']:
 for suffix in ['Shoulder','Arm','ForeArm','Hand','UpLeg','Leg','Hips']:
  n=side+suffix if suffix!='Hips' else 'Hips';g=body.vertex_groups.get(n)
  ids=[v for v in body.data.vertices if any(x.group==g.index and x.weight>.02 for x in v.groups)]
  report['weights'][n]={'count':len(ids),'bbox':[[min(v.co[i] for v in ids),max(v.co[i] for v in ids)] for i in range(3)]}
for label,p in [('back_glute',(0.12,.13,.9)),('front_hip',(.18,-.07,.88)),('deltoid',(.21,.02,1.41)),('inside_arm',(.17,-.02,1.32))]:
 ids=sorted(body.data.vertices,key=lambda v:(v.co-Vector(p)).length)[:12]
 report['rest_regions'][label]=[{'i':v.index,'co':list(v.co),'w':{names[g.group]:g.weight for g in v.groups}} for v in ids]
(P/'diagnosis/weights-frames.json').write_text(json.dumps(report,indent=2)+'\n')
arm=next(m for m in body.modifiers if m.type=='ARMATURE')
for m in body.modifiers:m.show_viewport=m.show_render=m.type=='ARMATURE'
scene.render.engine='BLENDER_WORKBENCH';scene.render.resolution_x=720;scene.render.resolution_y=720;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.render.film_transparent=True;scene.view_settings.view_transform='Standard'
s=scene.display.shading;s.light='STUDIO';s.color_type='SINGLE';s.single_color=(.60,.62,.64);s.show_shadows=False;s.show_cavity=False;s.show_specular_highlight=False
cd=bpy.data.cameras.new('Probe');cam=bpy.data.objects.new('Probe',cd);scene.collection.objects.link(cam);scene.camera=cam;cd.type='ORTHO';cd.ortho_scale=1.65
for dq in [False,True]:
 arm.use_deform_preserve_volume=dq
 for view,pos in [('front',(0,-5,1.25)),('rear',(-1.5,5,1.5)),('oblique',(3.4,-5,2.5))]:
  cam.location=pos;cam.rotation_euler=(Vector((0,0,.46))-cam.location).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(P/'diagnosis'/(f'hinge-{view}-'+('dq' if dq else 'lbs')+'.png'))
  bpy.ops.render.render(write_still=True)
print(json.dumps(report['rotations']))
