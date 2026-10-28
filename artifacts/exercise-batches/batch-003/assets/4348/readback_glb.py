"""Reimport the delivered GLB and compare actual skin by original vertex ID."""
import hashlib,json,sys
from pathlib import Path
sys.dont_write_bytecode = True
import bpy
import numpy as np
from mathutils import Vector
P=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P/'source.blend'))
body=bpy.data.objects['SK_BlenderStudioHuman'];rig=bpy.data.objects['RIG_BlenderStudioHuman'];scene=bpy.context.scene
for modifier in body.modifiers:modifier.show_viewport=modifier.type=='ARMATURE'
def positions(obj):
 ob=obj.evaluated_get(bpy.context.evaluated_depsgraph_get());m=ob.to_mesh();xyz=np.array([obj.matrix_world@v.co for v in m.vertices]);ob.to_mesh_clear();return xyz
expected={}
for frame in [0,75,150]:
 scene.frame_set(frame+1);bpy.context.view_layer.update();expected[frame]=positions(body)
# Capture the unchanged rig's actual LBS matrices for the static shader-normal
# equation. All source object transforms are identity in this accepted rig.
names={g.index:g.name for g in body.vertex_groups}
matrices={b.name:np.array(rig.pose.bones[b.name].matrix @ b.matrix_local.inverted())[:3,:3] for b in rig.data.bones}
source_rotations=np.array([sum((matrices[names[g.group]]*g.weight for g in v.groups),np.zeros((3,3)))/sum(g.weight for g in v.groups) for v in body.data.vertices])
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene;scene.render.fps=30;scene.render.fps_base=1
bpy.ops.import_scene.gltf(filepath=str(P/'motion.glb'))
body=next(o for o in scene.objects if o.type=='MESH');rig=next(o for o in scene.objects if o.type=='ARMATURE')
print('ATTRS',[(x.name,x.data_type,x.domain) for x in body.data.attributes])
print('ACTIONS',[(x.name, list(x.frame_range)) for x in bpy.data.actions])
assert [x.name for x in bpy.data.actions]==['Exercise_4348']
assert len(body.data.shape_keys.key_blocks)==2
assert abs(body.data.shape_keys.key_blocks[1].value-1)<.000001
attr=body.data.attributes.get('_SOURCE_INDEX')
assert attr is not None
source_index=np.empty(len(body.data.vertices),np.float32);attr.data.foreach_get('value',source_index);source_index=np.rint(source_index).astype(int)
# Blender importer drops morph NORMAL. Apply the actual transmitted default
# morph normals before rendering; do not replace them with geometric normals.
sys.path.insert(0,str(P));from glb_normals import default_normals
normal_ids,normal_values=default_normals(P/'motion.glb')
normal_by_source=np.zeros((10582,3));counts=np.zeros(10582)
np.add.at(normal_by_source,normal_ids,normal_values);np.add.at(counts,normal_ids,1)
normal_by_source/=counts[:,None]
assert np.max(np.linalg.norm(normal_values-normal_by_source[normal_ids],axis=1))<.0001
body.data.normals_split_custom_set_from_vertices(normal_by_source[source_index].tolist())
bpy.context.view_layer.update()
results=[]
for frame in [0,75,150]:
 scene.frame_set(frame);bpy.context.view_layer.update();xyz=positions(body)
 err=np.linalg.norm(xyz-expected[frame][source_index],axis=1)
 results.append({'frame':frame,'maximum_skin_error_m':float(err.max()),'rms_skin_error_m':float(np.sqrt(np.mean(err**2))),'global_min_z':float(xyz[:,2].min())})
assert max(x['maximum_skin_error_m'] for x in results)<.0001,results
# Blender import ignores morph normals, and its Armature custom-normal transport
# differs from Three.js. For the still, use the actual decoded GLB posed skin
# with the actual Three.js R_blend*(N_basis+w*N_delta) normals explicitly.
# This render-only mesh is not saved or exported and has no altered positions.
scene.frame_set(75);bpy.context.view_layer.update()
render_mesh=bpy.data.meshes.new_from_object(body.evaluated_get(bpy.context.evaluated_depsgraph_get()))
shader_normals=np.einsum('nij,nj->ni',source_rotations[source_index],normal_by_source[source_index])
shader_normals/=np.linalg.norm(shader_normals,axis=1)[:,None]
for polygon in render_mesh.polygons:polygon.use_smooth=True
render_mesh.normals_split_custom_set_from_vertices(shader_normals.tolist())
render_body=bpy.data.objects.new('QA_Decoded_GLB_With_Actual_Shader_Normals',render_mesh)
scene.collection.objects.link(render_body);render_body.matrix_world=body.matrix_world.copy()
body.hide_render=True

scene.render.engine='BLENDER_WORKBENCH';scene.render.resolution_x=1000;scene.render.resolution_y=850;scene.render.resolution_percentage=100
scene.render.film_transparent=True;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
shade=scene.display.shading;shade.light='STUDIO';shade.color_type='MATERIAL';shade.show_shadows=False;shade.show_cavity=False;shade.show_specular_highlight=False
scene.view_settings.view_transform='Standard';scene.view_settings.look='None'
data=bpy.data.cameras.new('ReadbackReviewCamera');cam=bpy.data.objects.new('ReadbackReviewCamera',data);scene.collection.objects.link(cam);scene.camera=cam
sys.path.insert(0,str(P));from build_motion import CAMERAS, add_datum
add_datum(scene)
for name in ['oblique','hands']:
 c=CAMERAS[name];cam.location=c['position'];cam.rotation_euler=(Vector(c['target'])-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=c['scale']
 scene.frame_set(76);scene.render.filepath=str(P/('glb-readback-'+name+'.png'));bpy.ops.render.render(write_still=True)
report={'ok':True,'glb_sha256':hashlib.sha256((P/'motion.glb').read_bytes()).hexdigest(),'source_sha256':hashlib.sha256((P/'source.blend').read_bytes()).hexdigest(),'source_vertices':int(len(set(source_index))),'imported_uv_split_vertices':len(source_index),'bones':len(rig.data.bones),'animation_duration_seconds':5,'morphs':1,'morph_default_weights':[1],'samples':results,'normal_readback':'Render-only copy of independently decoded GLB posed positions with actual transmitted morph normals transported by the exact Three.js Rblend equation; avoids Blender5.2 importer/Armature normal limitations. No positional or material substitution.','scope':'Actual GLB reimport linear skin, independently decoded by Blender importer. Three.js live interaction, alpha and parity remain primary integration checks.'}
(P/'glb-readback.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
