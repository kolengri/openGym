"""Temporary checker floor for native-surface sit-up contact review; not delivery media."""
import bpy,json,sys,numpy as np
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
source=Path(args[args.index('--source')+1]) if '--source' in args else P/'trials'/'candidate.blend'
bpy.ops.wm.open_mainfile(filepath=str(source));body=bpy.data.objects['SK_BlenderStudioHuman'];rig=bpy.data.objects['RIG_BlenderStudioHuman'];scene=bpy.context.scene
rig.animation_data.action=bpy.data.actions['Exercise_0001']
material=bpy.data.materials.new('QA_Body');material.diffuse_color=(.53,.61,.66,1);body.data.materials.clear();body.data.materials.append(material)
vertices=[];faces=[]
for x in range(16):
 for y in range(22):
  x0=-.8+x*.1;y0=-.9+y*.1;i=len(vertices);vertices.extend([(x0,y0,-.001),(x0+.1,y0,-.001),(x0+.1,y0+.1,-.001),(x0,y0+.1,-.001)]);faces.append((i,i+1,i+2,i+3))
mesh=bpy.data.meshes.new('QA_Floor');mesh.from_pydata(vertices,[],faces);floor=bpy.data.objects.new('QA_Floor',mesh);scene.collection.objects.link(floor)
for name,color in [('A',(.72,.75,.78,1)),('B',(.42,.46,.50,1))]:
 mat=bpy.data.materials.new('QA_Checker'+name);mat.diffuse_color=color;mesh.materials.append(mat)
for i,p in enumerate(mesh.polygons):p.material_index=(i//22+i%22)%2
scene.render.engine='BLENDER_WORKBENCH';scene.render.resolution_x=1000;scene.render.resolution_y=700;scene.render.resolution_percentage=100;scene.render.film_transparent=False
scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA';scene.view_settings.view_transform='Standard';scene.view_settings.look='None';scene.display.shading.color_type='MATERIAL';scene.display.shading.light='STUDIO';scene.display.shading.show_shadows=True;scene.display.shading.show_cavity=True;scene.display.shading.cavity_type='BOTH';scene.display.shading.curvature_ridge_factor=1.;scene.display.shading.curvature_valley_factor=1.;scene.display.shading.show_specular_highlight=False;scene.display.shading.background_type='WORLD';scene.world.color=(.91,.93,.95)
cam=scene.camera;cam.data.type='ORTHO';cam.data.ortho_scale=1.95
rest=np.array([v.co[:] for v in body.data.vertices]);samples=[]
for f in [0,30,60]:
 scene.frame_set(f+1);bpy.context.view_layer.update();ev=body.evaluated_get(bpy.context.evaluated_depsgraph_get());m=ev.to_mesh();co=np.array([v.co[:] for v in m.vertices]);samples.append({'frame':f,'body_min_z':co[:,2].min()});ev.to_mesh_clear()
 for label,loc,target in [('side',(6,.12,.32),(0,.12,.32)),('oblique',(2.6,-2.8,2.),(0,.12,.27))]:
  cam.location=loc;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(P/f'proof-{label}-{f:03d}.png');bpy.ops.render.render(write_still=True)
print(json.dumps(samples))
