"""Capture immutable held pose and canonical channels without source mutations."""
import sys
sys.dont_write_bytecode=True
import bpy,numpy as np,json,hashlib
from pathlib import Path
F=Path(__file__).resolve().parent;sys.path.insert(0,str(F));import corrective
SOURCE=F/'inputs-contact/source.blend';SOURCE_SHA='88c2da9b30955e3793637fe5f8a086e0ca7339d395cf20997d6b3fdcac817c1e'
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==SOURCE_SHA
bpy.ops.wm.open_mainfile(filepath=str(SOURCE));b=bpy.data.objects['SK_BlenderStudioHuman'];r=bpy.data.objects['RIG_BlenderStudioHuman'];s=bpy.context.scene
for m in b.modifiers:
 m.show_viewport=m.show_render=m.type=='ARMATURE'
 if m.type=='ARMATURE':assert m.use_deform_preserve_volume
rest=np.array([v.co[:]for v in b.data.vertices],np.float32);normals=np.array([v.normal[:]for v in b.data.vertices],np.float32);names=[pb.name for pb in r.pose.bones];W=np.zeros((len(rest),len(names)))
for v in b.data.vertices:
 for g in v.groups:W[v.index,names.index(b.vertex_groups[g.group].name)]=g.weight
b.data.calc_loop_triangles();T=np.array([t.vertices[:]for t in b.data.loop_triangles],int);P=[];N=[];M=[];frames=[0.,24.,32.,37.5]
act=bpy.data.actions['Exercise_3995'];r.animation_data.action=act;r.animation_data.action_slot=next(slot for slot in act.slots if slot.target_id_type=='OBJECT');keys=b.data.shape_keys;keys.animation_data.action=act;keys.animation_data.action_slot=next(slot for slot in act.slots if slot.target_id_type=='KEY')
for f in frames:
 s.frame_set(int(f)+1,subframe=f%1);bpy.context.view_layer.update();assert all(key.value==0. for key in list(keys.key_blocks)[1:]);e=b.evaluated_get(bpy.context.evaluated_depsgraph_get());me=e.to_mesh();P.append([v.co[:]for v in me.vertices]);N.append([v.normal[:]for v in me.vertices]);e.to_mesh_clear();M.append([np.array(pb.matrix@r.data.bones[pb.name].matrix_local.inverted())for pb in r.pose.bones])
np.savez_compressed(F/'capture.npz',rest=rest,rest_normals=normals,weights=W,triangles=T,frames=frames,positions=np.array(P),normals=np.array(N),matrices=M,bone_rest=[np.array(r.data.bones[n].matrix_local)for n in names],bone_heads=[r.data.bones[n].head_local[:]for n in names],bone_tails=[r.data.bones[n].tail_local[:]for n in names])
old={key.name:hashlib.sha256(np.array([v.co[:]for v in key.data],np.float32).tobytes()).hexdigest()for key in keys.key_blocks};uv={uv.name:hashlib.sha256(np.array([x.uv[:]for x in uv.data],np.float32).tobytes()).hexdigest()for uv in b.data.uv_layers}
(F/'capture.json').write_text(json.dumps({'source_sha256':SOURCE_SHA,'capture_npz_sha256':hashlib.sha256((F/'capture.npz').read_bytes()).hexdigest(),'blender':bpy.app.version_string,'bones':names,'vertices':len(rest),'triangles':len(T),'old_shape_key_hashes':old,'uv_hashes':uv,'binding_sha256':corrective.binding_signature(b,r),'modifiers':[{'name':m.name,'type':m.type,'active':m.show_viewport}for m in b.modifiers]},indent=2)+'\n');print('CAPTURE',len(rest),len(T),len(names),old)
