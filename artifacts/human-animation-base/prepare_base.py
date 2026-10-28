import bpy,json,numpy as np
from pathlib import Path
from mathutils import Vector,Matrix
P=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P/'human_base_meshes_bundle.blend'))
body=bpy.data.objects['GEO-body_male_realistic']
# Keep the original, professionally authored human geometry and topology.
for ob in list(bpy.data.objects):
 if ob!=body:bpy.data.objects.remove(ob,do_unlink=True)
body.hide_set(False);body.hide_render=False
for c in list(body.users_collection):c.objects.unlink(body)
bpy.context.scene.collection.objects.link(body)
# Normalize existing placement, world scale and floor before rigging.
coords=np.asarray([tuple(body.matrix_world@v.co) for v in body.data.vertices]);lo=coords.min(0);hi=coords.max(0);factor=1.8/(hi[2]-lo[2]);center=(lo+hi)/2
for v,p in zip(body.data.vertices,coords):v.co=Vector(((p[0]-center[0])*factor,(p[1]-center[1])*factor,(p[2]-lo[2])*factor))
body.matrix_world=Matrix.Identity(4);body.name='SK_BlenderStudioHuman'
for m in body.modifiers:
 if m.type=='MULTIRES':m.levels=min(2,m.total_levels);m.render_levels=min(2,m.total_levels)
for face in body.data.polygons:face.use_smooth=True
face_sets=body.data.attributes.get('.sculpt_face_set');buckets={}
if face_sets:
 for face,val in zip(body.data.polygons,face_sets.data):
  entry=buckets.setdefault(int(val.value),[])
  entry.extend([body.data.vertices[i].co[:] for i in face.vertices])
report={'source':'Blender Studio Human Base Meshes v1.4.1 / CC0','vertices':len(body.data.vertices),'faces':len(body.data.polygons),'bounds':[list(body.dimensions)],'face_sets':{str(k):{'count':len(v),'lo':np.min(v,axis=0).tolist(),'hi':np.max(v,axis=0).tolist(),'center':np.mean(v,axis=0).tolist()} for k,v in buckets.items()}}
(P/'prepared-report.json').write_text(json.dumps(report,indent=2))
scene=bpy.context.scene;scene.render.engine='BLENDER_WORKBENCH';scene.display.shading.light='STUDIO';scene.display.shading.studiolight_rotate_z=.4;scene.display.shading.color_type='SINGLE';scene.display.shading.single_color=(.62,.69,.75);scene.display.shading.show_shadows=True;scene.display.shading.show_cavity=True;scene.display.shading.cavity_type='BOTH';scene.display.shading.curvature_ridge_factor=1.3;scene.display.shading.curvature_valley_factor=1.1;scene.display.shading.show_specular_highlight=False;scene.display.shading.background_type='WORLD';scene.world.color=(.92,.94,.96)
scene.render.resolution_x=640;scene.render.resolution_y=800;scene.render.resolution_percentage=100
bpy.ops.object.camera_add(location=(2.5,-6,1.3));camera=bpy.context.object;camera.data.type='ORTHO';camera.data.ortho_scale=2.12;camera.rotation_euler=(Vector((0,0,.92))-camera.location).to_track_quat('-Z','Y').to_euler();scene.camera=camera
scene.render.image_settings.file_format='PNG';scene.render.filepath=str(P/'professional-base.png')
bpy.ops.wm.save_as_mainfile(filepath=str(P/'professional-base.blend'));bpy.ops.render.render(write_still=True)
print(json.dumps({'vertices':report['vertices'],'faces':report['faces'],'face_sets':len(buckets)}))
