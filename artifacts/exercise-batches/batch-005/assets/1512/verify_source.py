"""Read-only immutable Basis/rest/UV/ID and bounded binding/key evidence."""
import bpy,json,hashlib,gzip,sys
sys.dont_write_bytecode=True
from pathlib import Path
import numpy as np
P=Path(__file__).resolve().parent
sys.path.insert(0,str(P.parents[2]/'batch-003'));import authoring as a
bpy.ops.wm.open_mainfile(filepath=str(P/'source.blend'))
b=bpy.data.objects['SK_BlenderStudioHuman'];r=bpy.data.objects['RIG_BlenderStudioHuman'];keys=b.data.shape_keys
sha=hashlib.sha256((P/'source.blend').read_bytes()).hexdigest()
def geometry_digest(body,rig):
 h=hashlib.sha256();h.update(np.array([v.co[:]for v in body.data.vertices],np.float32).tobytes())
 for p in body.data.polygons:h.update(np.array(p.vertices,np.int32).tobytes())
 for uv in body.data.uv_layers:
  values=np.empty(len(uv.data)*2,np.float32);uv.data.foreach_get('uv',values);h.update(uv.name.encode()+values.tobytes())
 for bone in rig.data.bones:h.update(bone.name.encode()+np.array(bone.matrix_local,np.float32).tobytes())
 return h.hexdigest()
def binding(body):return [{body.vertex_groups[g.group].name:float(g.weight)for g in v.groups}for v in body.data.vertices]
original=np.array([v.co[:]for v in b.data.vertices]);basis=np.array([v.co[:]for v in keys.key_blocks['Basis'].data])
assert np.array_equal(original,basis)
assert len(r.data.bones)==51 and len(b.data.vertices)==10582 and sum(len(p.vertices)-2 for p in b.data.polygons)==21160
assert [x.name for x in bpy.data.actions]==['Exercise_1512']
assert keys.animation_data.action==r.animation_data.action
assert all(m.show_viewport==(m.type=='ARMATURE')and m.show_render==(m.type=='ARMATURE')for m in b.modifiers)
assert next(m for m in b.modifiers if m.type=='ARMATURE').use_deform_preserve_volume
assert [round(x.value)for x in b.data.attributes['_SOURCE_INDEX'].data]==list(range(10582))
normal_ref={'source_sha256':sha,'basis':np.array(keys.key_blocks['Basis'].normals_vertex_get()).reshape(-1,3).tolist(),'targets':{key.name:np.array(key.normals_vertex_get()).reshape(-1,3).tolist()for key in keys.key_blocks if key.name!='Basis'},'coordinate_frame':'Original Blender Z-up rest normals'}
with gzip.open(P/'morph-normal-reference.json.gz','wt')as handle:json.dump(normal_ref,handle,separators=(',',':'))
corrective=json.loads((P/'local-corrective-report.json').read_text());domain=set(corrective['mask_original_ids']);outside=[i for i in range(10582)if i not in domain]
max_outside=max(float(np.linalg.norm(np.array([v.co[:]for v in key.data])[outside]-basis[outside],axis=1).max())for key in keys.key_blocks if key.name!='Basis')
assert max_outside==0
protected=np.flatnonzero((original[:,1]>.13)&(original[:,2]>.84)&(original[:,2]<1.20)&(abs(original[:,0])<.25))
protected_max=0
def evaluated_points():
 obj=b.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=obj.to_mesh();pp=np.array([v.co[:]for v in mesh.vertices]);obj.to_mesh_clear();return pp
for entry in corrective['keys']:
 key=keys.key_blocks[entry['name']];delta=np.array([v.co[:]for v in key.data])-basis;lengths=np.linalg.norm(delta,axis=1);changed=np.flatnonzero(lengths>1e-8)
 bpy.context.scene.frame_set(entry['frame']+1)
 for k in keys.key_blocks:
  if k.name!='Basis':k.value=0
 bpy.context.view_layer.update();base_points=evaluated_points();key.value=1;bpy.context.view_layer.update();target_points=evaluated_points()
 target_lengths=np.linalg.norm(target_points-base_points,axis=1)
 local_protected=float(np.linalg.norm(delta[protected],axis=1).max());protected_max=max(protected_max,local_protected)
 entry['actual_source_key_statistics']={'changed_vertices_over1e_minus8_m':len(changed),'maximum_rest_delta_m':float(lengths.max()),'p95_rest_delta_among_changed_m':float(np.percentile(lengths[changed],95)),'maximum_evaluated_target_delta_m':float(target_lengths.max()),'p95_evaluated_target_delta_among_changed_m':float(np.percentile(target_lengths[changed],95)),'maximum_outside_declared_mask_delta_m':float(lengths[outside].max()),'maximum_protected_posterior_waist_delta_m':local_protected,'source_coordinate_bounds_of_changed_vertices':{'min':original[changed].min(axis=0).tolist(),'max':original[changed].max(axis=0).tolist()}}
assert protected_max==0
corrective['protected_posterior_waist']={'source_bounds':'sourceY>0.13m,sourceZ0.84..1.20m,|sourceX|<0.25m; excludes shoulder/knee target domains','original_ids':protected.tolist(),'maximum_key_delta_m':protected_max}
(P/'local-corrective-report.json').write_text(json.dumps(corrective,indent=2)+'\n')
current_digest=geometry_digest(b,r);current_binding=a.binding_hash(b,r);current_weights=binding(b);max_influences=max(len(v.groups)for v in b.data.vertices)
assert max_influences<=4
local=json.loads((P/'local-binding-report.json').read_text());changed={row['id']for row in local['vertices']}
assert current_binding==local['binding_sha256']
bpy.ops.wm.open_mainfile(filepath=str(a.SOURCE));base=bpy.data.objects['SK_BlenderStudioHuman'];base_rig=bpy.data.objects['RIG_BlenderStudioHuman']
assert a.binding_hash(base,base_rig)=='227ede3fc31d1a2b47ff40f20a4a7288fe7bb36179add23bae953993826c8b7b'
assert geometry_digest(base,base_rig)==current_digest
original_weights=binding(base)
assert all(original_weights[i]==current_weights[i]for i in range(10582)if i not in changed)
assert all(max(abs(v-current_weights[row['id']].get(k,0))for k,v in row['after'].items())<1e-7 for row in local['vertices'])
data={'pass':True,'source_sha256':sha,'accepted_source_sha256':a.SOURCE_SHA,'geometry_rest_uv_sha256':current_digest,'basis_rest_uv_topology_identical_to_accepted_source':True,'original_source_binding_sha256':local['source_binding_sha256'],'local_binding_sha256':current_binding,'binding_changed_original_ids':sorted(changed),'binding_outside_declared_domain_exact':True,'source_vertices':10582,'triangles':21160,'bones':51,'maximum_influences':max_influences,'actions':['Exercise_1512'],'all_non_armature_modifiers_disabled':True,'skinning':'dualQuaternion','morphs':list(normal_ref['targets']),'outside_corrective_domain_maximum_delta_m':max_outside,'protected_posterior_waist_maximum_key_delta_m':protected_max,'normal_reference':'morph-normal-reference.json.gz','scope':'Read-only source-bound invariants, no save; DQ adapter required and native Smooth/Multires disabled.'}
(P/'source-verification.json').write_text(json.dumps(data,indent=2)+'\n');print(json.dumps({k:v for k,v in data.items()if k!='binding_changed_original_ids'}))
