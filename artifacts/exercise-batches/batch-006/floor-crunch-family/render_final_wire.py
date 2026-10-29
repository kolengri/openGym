"""Two final solid-plus-wire original-cage proofs; never save review helpers."""
from pathlib import Path
import json,hashlib,bpy,numpy as np
from mathutils import Vector
P=Path(__file__).resolve().parent;B=P.parent
bpy.ops.wm.open_mainfile(filepath=str(P/'source.blend'));b=bpy.data.objects['SK_BlenderStudioHuman'];r=bpy.data.objects['RIG_BlenderStudioHuman'];s=bpy.context.scene;cam=s.camera
rows=[]
def points():
 e=b.evaluated_get(bpy.context.evaluated_depsgraph_get());m=e.to_mesh();p=np.array([v.co[:]for v in m.vertices]);e.to_mesh_clear();return p
for id,f,label,view in [('0006',37.5,'wire-left-oblique',1),('4354',0,'wire-start-side',0)]:
 action=bpy.data.actions['Exercise_'+id];r.animation_data.action=action;b.data.shape_keys.animation_data.action=action;b.data.shape_keys.animation_data.action_slot=next(t for t in action.slots if t.target_id_type=='KEY');s.frame_set(int(f)+1,subframe=f%1);bpy.context.view_layer.update();before=points();matrices=np.array([pb.matrix[:]for pb in r.pose.bones]);v=json.loads((B/'assets'/id/'cameras.json').read_text())[view];cam.location=v['position'];cam.rotation_euler=(Vector(v['target'])-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=v['scale']
 wiremesh=bpy.data.meshes.new_from_object(b.evaluated_get(bpy.context.evaluated_depsgraph_get()));wire=bpy.data.objects.new('FinalCageWire',wiremesh);s.collection.objects.link(wire);mat=bpy.data.materials.new('FinalCageWireMaterial');mat.diffuse_color=(.015,.015,.015,1);wiremesh.materials.clear();wiremesh.materials.append(mat);mod=wire.modifiers.new('FinalCageWire','WIREFRAME');mod.thickness=.00045;mod.offset=1
 s.render.filepath=str(B/'assets'/id/(label+'.png'));bpy.ops.render.render(write_still=True);after=points();assert np.linalg.norm(after-before,axis=1).max()==0;assert np.array_equal(matrices,np.array([pb.matrix[:]for pb in r.pose.bones]));bpy.data.objects.remove(wire,do_unlink=True);bpy.data.meshes.remove(wiremesh);bpy.data.materials.remove(mat);rows.append({'id':id,'frame':f,'file':label+'.png','full_skin_pre_post_render_delta_m':0,'all51_matrices_unchanged':True})
(P/'final-wire-readback.json').write_text(json.dumps({'source_sha256':hashlib.sha256((P/'source.blend').read_bytes()).hexdigest(),'samples':rows,'source_saved':False},indent=2)+'\n')
