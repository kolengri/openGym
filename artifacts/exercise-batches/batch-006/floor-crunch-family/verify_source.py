"""Independent actual-source invariant/weight/target-buffer readback."""
from pathlib import Path
import sys,json,gzip,hashlib
import bpy,numpy as np
P=Path(__file__).resolve().parent;B=P.parent;sys.path.insert(0,str(B.parent/'batch-003'))
import authoring as a

def invariant(body,rig):
 h=hashlib.sha256()
 for v in body.data.vertices:h.update(np.array(v.co,np.float32).tobytes())
 for f in body.data.polygons:h.update(np.array(f.vertices,np.int32).tobytes())
 for uv in body.data.uv_layers:
  values=np.empty(len(uv.data)*2,np.float32);uv.data.foreach_get('uv',values);h.update(uv.name.encode()+values.tobytes())
 for bone in rig.data.bones:h.update(bone.name.encode()+np.array(bone.matrix_local,np.float32).tobytes())
 return h.hexdigest()
def weights(body):return[{body.vertex_groups[g.group].name:float(g.weight)for g in v.groups}for v in body.data.vertices]
original_binding=a.initialize();original_invariant=invariant(a.body,a.rig);original_weights=weights(a.body)
bpy.ops.wm.open_mainfile(filepath=str(P/'source.blend'));b=bpy.data.objects['SK_BlenderStudioHuman'];r=bpy.data.objects['RIG_BlenderStudioHuman'];keys=b.data.shape_keys;sha=hashlib.sha256((P/'source.blend').read_bytes()).hexdigest();observed=weights(b);receipt=json.loads((P/'binding-receipt.json').read_text())
assert invariant(b,r)==original_invariant;assert observed==receipt['actual_weights'];assert max(map(len,observed))<=4;assert max(abs(sum(row.values())-1)for row in observed)<2e-6
assert np.array_equal(np.array([v.co[:]for v in b.data.vertices],np.float32),np.array([v.co[:]for v in keys.key_blocks['Basis'].data],np.float32))
assert len(b.data.vertices)==10582 and len(r.data.bones)==51 and sum(len(f.vertices)-2 for f in b.data.polygons)==21160
names=[k.name for k in keys.key_blocks if k.name!='Basis'];assert len(names)==6 and not any('Knee' in n for n in names);assert sorted(act.name for act in bpy.data.actions)==['Exercise_0006','Exercise_4354']
ids=np.empty(10582,np.float32);b.data.attributes['_SOURCE_INDEX'].data.foreach_get('value',ids);assert np.array_equal(ids,np.arange(10582))
archive=np.load(P/'joint-components.npz');R=np.array([v.co[:]for v in b.data.vertices],np.float32);mask=archive['shoulder_mask'];target_report=[]
for name in names:
 actual=np.array([v.co[:]for v in keys.key_blocks[name].data],np.float32);expected=(R.astype(np.float64)+archive[name]).astype(np.float32);assert np.array_equal(actual,expected);assert np.array_equal(actual[mask==0],R[mask==0]);maximum=float(np.linalg.norm(actual-R,axis=1).max());assert maximum<=.0400001
 target_report.append({'name':name,'coordinate_sha256_float32':hashlib.sha256(actual.tobytes()).hexdigest(),'maximum_source_delta_m':maximum,'changed_ids':np.flatnonzero(np.linalg.norm(actual-R,axis=1)>1e-8).tolist(),'outside_source_shoulder_domain_exact':True})
normal={'source_sha256':sha,'basis':np.array(keys.key_blocks['Basis'].normals_vertex_get()).reshape((-1,3)).tolist(),'targets':{n:np.array(keys.key_blocks[n].normals_vertex_get()).reshape((-1,3)).tolist()for n in names},'coordinate_frame':'Original Blender rest normals; Zup'}
for id in ['0006','4354']:
 out=B/'assets'/id
 with gzip.open(out/'joint-normal-reference.json.gz','wt',compresslevel=9)as stream:json.dump(normal,stream,separators=(',',':'))
allowed=set(row['source_id']for row in receipt['shared_causal_profile']['changes'])|set(receipt['posterior_attachment']['changed_original_vertex_ids'])|set(row['id']for row in receipt['plantar'])|set(receipt['knee_binding']['changed_ids']);changed=[i for i,(old,new)in enumerate(zip(original_weights,observed))if old!=new];assert set(changed)<=allowed
assert all(m.show_viewport==(m.type=='ARMATURE')and m.show_render==(m.type=='ARMATURE')for m in b.modifiers);assert next(m for m in b.modifiers if m.type=='ARMATURE').use_deform_preserve_volume
report={'pass':True,'source_sha256':sha,'original_geometry_rest_uv_sha256':original_invariant,'basis_rest_uv_topology_identical_to_immutable_original':True,'original_source_sha256':a.SOURCE_SHA,'source_vertices':10582,'triangles':21160,'bones':51,'source_index_ids_preserved':True,'original_binding':original_binding,'runtime_binding':a.binding_hash(b,r),'actual_saved_weights_equal_declared_field':True,'maximum_influences':max(map(len,observed)),'maximum_weight_sum_error':max(abs(sum(row.values())-1)for row in observed),'weight_changed_ids':changed,'outside_declared_weight_domain_exact':True,'actions':['Exercise_0006','Exercise_4354'],'targets':target_report,'all_non_armature_modifiers_disabled':True,'rejected_knee_morph_absent':True,'normal_reference':'joint-normal-reference.json.gz','source_resaved':False}
(P/'source-verification.json').write_text(json.dumps(report,indent=2)+'\n')
for id in ['0006','4354']:(B/'assets'/id/'source-verification.json').write_text(json.dumps(dict(report,id=id),indent=2)+'\n')
print('SOURCE_VERIFIED',sha,flush=True)
