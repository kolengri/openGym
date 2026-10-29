"""Actual saved weight and immutable source/rest/UV/ID readback."""
from pathlib import Path
import sys,json,hashlib,gzip
import bpy,numpy as np
P=Path(__file__).resolve().parent;B=P.parent;sys.path.insert(0,str(B.parent/'batch-003'));import authoring as a
bpy.ops.wm.open_mainfile(filepath=str(P/'source.blend'));b=bpy.data.objects['SK_BlenderStudioHuman'];r=bpy.data.objects['RIG_BlenderStudioHuman'];sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
def signature(body,rig):
 h=hashlib.sha256();h.update(np.array([v.co[:]for v in body.data.vertices],np.float32).tobytes())
 for p in body.data.polygons:h.update(np.array(p.vertices,np.int32).tobytes())
 for uv in body.data.uv_layers:
  values=np.empty(2*len(uv.data),np.float32);uv.data.foreach_get('uv',values);h.update(uv.name.encode()+values.tobytes())
 for bone in rig.data.bones:h.update(bone.name.encode()+np.array(bone.matrix_local,np.float32).tobytes())
 return h.hexdigest()
def weights(body):return[{body.vertex_groups[g.group].name:float(g.weight)for g in v.groups}for v in body.data.vertices]
current=weights(b);receipt=json.loads((P/'binding-receipt.json').read_text());assert current==receipt['actual_weights'];sums=[sum(row.values())for row in current];assert max(map(len,current))<=4 and max(abs(v-1)for v in sums)<2e-6
assert len(b.data.vertices)==10582 and len(r.data.bones)==51 and sum(len(f.vertices)-2 for f in b.data.polygons)==21160
assert np.array_equal(np.array([v.co[:]for v in b.data.vertices]),np.array([v.co[:]for v in b.data.shape_keys.key_blocks['Basis'].data]));assert len(b.data.shape_keys.key_blocks)==1
assert sorted(x.name for x in bpy.data.actions)==['Exercise_1368','Exercise_2761','Exercise_2762'];assert [round(x.value)for x in b.data.attributes['_SOURCE_INDEX'].data]==list(range(10582));assert all(m.show_viewport==(m.type=='ARMATURE')and m.show_render==(m.type=='ARMATURE')for m in b.modifiers)
normal=np.array(b.data.shape_keys.key_blocks['Basis'].normals_vertex_get()).reshape(-1,3)
with gzip.open(P/'basis-normal-reference.json.gz','wt')as handle:json.dump({'source_sha256':sha(P/'source.blend'),'normals':normal.tolist()},handle,separators=(',',':'))
sig=signature(b,r);binding=a.binding_hash(b,r);source_sha=sha(P/'source.blend')
r.animation_data.action=bpy.data.actions['Exercise_2761'];bpy.context.scene.frame_set(1);bpy.context.view_layer.update();deform={name:r.pose.bones[name].matrix@r.data.bones[name].matrix_local.inverted()for name in ['Hips','Spine','Spine1']};common=max(abs(float(x-y))for name in ['Spine','Spine1']for rowa,rowb in zip(deform['Hips'],deform[name])for x,y in zip(rowa,rowb));assert common<2e-6
bpy.ops.wm.open_mainfile(filepath=str(a.SOURCE));original=bpy.data.objects['SK_BlenderStudioHuman'];original_rig=bpy.data.objects['RIG_BlenderStudioHuman'];assert signature(original,original_rig)==sig;original_weights=weights(original);changed=set(receipt['changed_original_ids']);assert all(current[i]==original_weights[i]for i in range(10582)if i not in changed)
report={'pass':True,'source_sha256':source_sha,'accepted_source_sha256':a.SOURCE_SHA,'basis_rest_uv_topology_signature':sig,'basis_rest_uv_topology_exact':True,'source_vertices':10582,'triangles':21160,'bones':51,'original_source_binding':receipt['source_binding'],'runtime_binding':binding,'changed_original_ids':sorted(changed),'outside_binding_domain_exact':True,'maximum_actual_influences':max(map(len,current)),'maximum_actual_weight_sum_error':max(abs(v-1)for v in sums),'actions':['Exercise_1368','Exercise_2761','Exercise_2762'],'corrective_keys':[],'all_non_armature_modifiers_disabled':True,'shared_profile_lumbar_effect':'Full frozen recipe is required by its proximal-glute input contract; torso Hips/Spine/Spine1 share an identical rigid deformation here, so the lumbar weight transfer has no pose-space shape effect.','maximum_common_torso_deformation_difference':common,'source_index_exact':True}
(P/'source-verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items()if k!='changed_original_ids'}))
