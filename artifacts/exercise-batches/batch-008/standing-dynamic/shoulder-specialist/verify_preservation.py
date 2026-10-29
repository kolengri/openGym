"""Exact 6014 preservation and explicit normal component for diagnostic target."""
import sys
sys.dont_write_bytecode=True
import bpy,numpy as np,json,hashlib
from pathlib import Path
F=Path(__file__).resolve().parent;sys.path.insert(0,str(F));import corrective
bpy.ops.wm.open_mainfile(filepath=str(F/'foundation.blend'));b=bpy.data.objects['SK_BlenderStudioHuman'];r=bpy.data.objects['RIG_BlenderStudioHuman'];s=bpy.context.scene
for m in b.modifiers:
    m.show_viewport=m.show_render=m.type=='ARMATURE'
    if m.type=='ARMATURE':m.use_deform_preserve_volume=True
def signature():
    h=hashlib.sha256();h.update(np.array([v.co[:]for v in b.data.vertices],np.float32).tobytes())
    for p in b.data.polygons:h.update(np.array(p.vertices,np.int32).tobytes())
    for uv in b.data.uv_layers:h.update(uv.name.encode()+np.array([x.uv[:]for x in uv.data],np.float32).tobytes())
    for pb in r.data.bones:h.update(pb.name.encode()+np.array(pb.matrix_local,np.float32).tobytes())
    for v in b.data.vertices:
        for g in v.groups:h.update(b.vertex_groups[g.group].name.encode()+np.array(g.weight,np.float32).tobytes())
    return h.hexdigest()
def sample():
    bpy.context.view_layer.update();e=b.evaluated_get(bpy.context.evaluated_depsgraph_get());me=e.to_mesh();p=np.array([v.co[:]for v in me.vertices],np.float32);e.to_mesh_clear();m=np.array([pb.matrix for pb in r.pose.bones],np.float32);return p,m
before=signature();basis=np.array([v.co[:]for v in b.data.vertices],np.float32);skin=[];matrices=[]
for f in range(151):
    corrective.select(b,r,'6014');s.frame_set(f+1);p,m=sample();skin.append(p);matrices.append(m)
data=corrective.install(b,r,s,archive_path=F/'target.npz');rows=[]
for f in range(151):
    corrective.select(b,r,'6014');s.frame_set(f+1);p,m=sample();assert np.array_equal(skin[f],p),f;assert np.array_equal(matrices[f],m),f
    assert all(b.data.shape_keys.key_blocks[name].value==0 for name,_ in corrective.STATES)
    rows.append({'frame':f,'skin_sha256':hashlib.sha256(p.tobytes()).hexdigest(),'all51_bone_matrices_sha256':hashlib.sha256(m.tobytes()).hexdigest(),'maximum_skin_difference_m':0.,'maximum_bone_matrix_difference':0.,'component_weights':[0.,0.]})
assert before==signature()
keys=b.data.shape_keys.key_blocks;normal0=np.array(keys['Basis'].normals_vertex_get()).reshape(-1,3);normal=[]
for name,_ in corrective.STATES:normal.append(np.array(keys[name].normals_vertex_get()).reshape(-1,3)-normal0)
payload={k:data[k]for k in data.files};payload['normal_source_ids']=np.arange(len(basis),dtype=np.int32);payload['rest_normal_deltas']=np.array(normal,np.float32);payload['rest_basis_normals']=normal0.astype(np.float32)
np.savez_compressed(F/corrective.ARCHIVE,**payload)
changed_normal=np.flatnonzero(np.linalg.norm(payload['rest_normal_deltas'],axis=2).max(0)>0);union=np.union1d(data['source_ids'],changed_normal);exterior=np.setdiff1d(np.arange(len(basis)),union)
report={'status':'native_shape_accepted_for_integration;full151_5172_decoded_and_GPU_pending','source_foundation_sha256':hashlib.sha256((F/'foundation.blend').read_bytes()).hexdigest(),'source_Basis_topology_UV_rest_binding_signature':before,'source_geometry_binding_signature_unchanged':True,'all151_6014_skin_bit_exact':True,'all151_6014_all51_bone_matrices_bit_exact':True,'maximum_6014_skin_difference_m':0.,'maximum_6014_matrix_difference':0.,'vertices':len(basis),'bones':len(r.pose.bones),'full_source_NORMAL_component_samples':2,'POSITION_and_NORMAL_archive':corrective.ARCHIVE,'archive_sha256':hashlib.sha256((F/corrective.ARCHIVE).read_bytes()).hexdigest(),'normal_provenance':'Blender shape-key normals_vertex_get, full source domain; native geometric target normals, distinct from actual GPU transport acceptance.','position_source_ids':data['source_ids'].tolist(),'normal_changed_source_ids':changed_normal.tolist(),'position_normal_union_source_ids':union.tolist(),'position_source_count':len(data['source_ids']),'normal_source_count':len(changed_normal),'position_normal_union_source_count':len(union),'normal_only_boundary_source_ids':np.setdiff1d(changed_normal,data['source_ids']).tolist(),'maximum_normal_delta_outside_union':float(np.abs(payload['rest_normal_deltas'][:,exterior]).max()),'protected_position_source_ids':data['protected_source_ids'].tolist(),'protected_position_component_delta_m':0.,'maximum_normal_vector_change_at_protected_position_vertices':float(np.linalg.norm(payload['rest_normal_deltas'][:,data['protected_source_ids']],axis=2).max()),'normal_boundary_note':'Protected-position vertices can have geometric normal changes from adjacent corrected faces. Keep these true one-ring NORMAL deltas;6014 zero weights preserves both channels.','samples':rows}
(F/'preservation-report.json').write_text(json.dumps(report,indent=2)+'\n');print('PRESERVATION_PASS',len(rows))
