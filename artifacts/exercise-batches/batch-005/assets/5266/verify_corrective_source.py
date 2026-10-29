"""Independently compare final editable source with immutable original cage/rest/UV."""
import gzip,hashlib,json,sys
from pathlib import Path
import bpy,numpy as np
P=Path(__file__).resolve().parent;sys.path.insert(0,str(P.parents[2]/'batch-003'))
import authoring as a
sys.path.insert(0,str(P.parents[1]/'posture-support'));import support_sampler as support
C=support.CONTRACT

def invariant_hash(body,rig):
 h=hashlib.sha256()
 for v in body.data.vertices:h.update(np.array(v.co,np.float32).tobytes())
 for f in body.data.polygons:h.update(np.array(f.vertices,np.int32).tobytes())
 for uv in body.data.uv_layers:
  values=np.empty(len(uv.data)*2,np.float32);uv.data.foreach_get('uv',values);h.update(uv.name.encode()+values.tobytes())
 for bone in rig.data.bones:h.update(bone.name.encode()+np.array(bone.matrix_local,np.float32).tobytes())
 return h.hexdigest()

def weights(body):return[{body.vertex_groups[g.group].name:float(g.weight)for g in v.groups}for v in body.data.vertices]

bpy.ops.wm.open_mainfile(filepath=str(P/'source.blend'))
b=bpy.data.objects['SK_BlenderStudioHuman'];r=bpy.data.objects['RIG_BlenderStudioHuman'];keys=b.data.shape_keys;names=['JointNeutral','JointRightCross','JointLeftCross']
assert[key.name for key in keys.key_blocks]==['Basis']+names
points=np.array([v.co[:]for v in b.data.vertices]);basis=np.array([v.co[:]for v in keys.key_blocks['Basis'].data]);assert np.array_equal(points,basis)
assert len(points)==10582 and len(r.data.bones)==51 and sum(len(f.vertices)-2 for f in b.data.polygons)==21160
assert[action.name for action in bpy.data.actions]==['Exercise_5266'];assert r.animation_data.action==keys.animation_data.action
assert{slot.target_id_type for slot in r.animation_data.action.slots}=={'OBJECT','KEY'}
assert all(m.show_viewport==(m.type=='ARMATURE')and m.show_render==(m.type=='ARMATURE')for m in b.modifiers)
assert next(m for m in b.modifiers if m.type=='ARMATURE').use_deform_preserve_volume
ids=np.empty(10582,np.float32);b.data.attributes['_SOURCE_INDEX'].data.foreach_get('value',ids);assert np.array_equal(ids,np.arange(10582))
final_invariant=invariant_hash(b,r);final_binding=a.binding_hash(b,r);final_weights=weights(b)
# The accepted static posterior attachment is additive to the shared binding.
final_keys={name:np.array([v.co[:]for v in keys.key_blocks[name].data],np.float32)for name in names}
for frame,expected in enumerate(C['foundation']['original151_weight_schedule']):
 bpy.context.scene.frame_set(frame+1);observed=[keys.key_blocks[name].value for name in names];assert np.max(abs(np.array(observed)-expected))<1e-7
assert max(len(v)for v in final_weights)==4
assert all(abs(sum(v.values())-1)<1e-6 for v in final_weights)
source_sha=hashlib.sha256((P/'source.blend').read_bytes()).hexdigest()
normal_ref={'source_sha256':source_sha,'basis':np.array(keys.key_blocks['Basis'].normals_vertex_get()).reshape((-1,3)).tolist(),'targets':{name:np.array(keys.key_blocks[name].normals_vertex_get()).reshape((-1,3)).tolist()for name in names},'coordinate_frame':'Original Blender rest normals; Z up'}
with gzip.open(P/'joint-normal-reference.json.gz','wt',compresslevel=9)as stream:json.dump(normal_ref,stream,separators=(',',':'))
protected=np.flatnonzero(((abs(points[:,0])<.16)&(points[:,1]>.055)&(points[:,2]>.82)&(points[:,2]<1.02))|((abs(points[:,0])<.08)&(points[:,1]>.055)&(points[:,2]>1.05)&(points[:,2]<1.25)))
protected_delta=max(float(np.linalg.norm(np.array([v.co[:]for v in keys.key_blocks[name].data])[protected]-basis[protected],axis=1).max())for name in names)
 # Total includes the explicitly retained legacy11.7–15.7mm flank field.
 # The8mm cap applies only to the new additive support, checked below.
corrective=json.loads((P/'joint-corrective-report.json').read_text())
for entry in corrective['keys']:
 delta=np.array([v.co[:]for v in keys.key_blocks[entry['name']].data])-basis;entry['changed_original_vertex_ids']=np.flatnonzero(np.linalg.norm(delta,axis=1)>1e-8).tolist();entry['total_maximum_rest_delta_m']=float(np.linalg.norm(delta,axis=1).max());entry['final_changed_vertex_count']=len(entry['changed_original_vertex_ids'])
assert a.initialize()=='227ede3fc31d1a2b47ff40f20a4a7288fe7bb36179add23bae953993826c8b7b'
assert invariant_hash(a.body,a.rig)==final_invariant
original_weights=weights(a.body)
bpy.ops.wm.open_mainfile(filepath=C['source_blend']);a.body=bpy.data.objects['SK_BlenderStudioHuman'];a.rig=bpy.data.objects['RIG_BlenderStudioHuman']
support.apply_binding(a.body,a.rig);assert a.binding_hash(a.body,a.rig)==C['runtime_binding_sha256']
sys.path.insert(0,str(P));import glute_binding_overlay
attachment=glute_binding_overlay.install(a.body);assert a.binding_hash(a.body,a.rig)==final_binding
expected_weights=weights(a.body)
assert final_weights==expected_weights
changed=[];maximum=0
for i,(old,new)in enumerate(zip(original_weights,final_weights)):
 delta=max(abs(old.get(name,0)-new.get(name,0))for name in old.keys()|new.keys())
 if delta>1e-7:changed.append(i);maximum=max(maximum,delta)
report={'pass':True,'source_sha256':source_sha,'original_binding_rest_uv_sha256':'227ede3fc31d1a2b47ff40f20a4a7288fe7bb36179add23bae953993826c8b7b','final_binding_rest_uv_sha256':final_binding,'original_geometry_rest_uv_sha256':final_invariant,'basis_rest_uv_topology_identical_to_immutable_original':True,'source_index_ids_preserved':True,'source_vertices':10582,'triangles':21160,'bones':51,'actions':['Exercise_5266'],'action_slots':['OBJECT','KEY'],'maximum_influences':4,'weight_changed_original_vertex_ids':changed,'weight_changed_vertices':len(changed),'maximum_single_weight_delta':maximum,'morphs':names,'maximum_pelvic_lumbar_rest_corrective_delta_m':protected_delta,'binding_matches_exact_shared_plus_frozen_posterior_attachment':True,'posterior_attachment':attachment,'all_non_armature_modifiers_disabled':True,'normal_reference':'joint-normal-reference.json.gz','source_saved':False}
bpy.ops.wm.open_mainfile(filepath=C['source_blend'])
foundation_body=bpy.data.objects['SK_BlenderStudioHuman'];data=np.load(P/'support-targets.npz');support_ids=data['source_ids'];composition=[]
for state,name in enumerate(names):
 old=np.array([v.co[:]for v in foundation_body.data.shape_keys.key_blocks[name].data],np.float32)
 assert hashlib.sha256(old.tobytes()).hexdigest()==C['foundation']['key_coordinate_sha256_float32'][name]
 assert np.linalg.norm(data['5266_deltas'][state],axis=1).max()<.008
 expected=old.copy();expected[support_ids]=(old[support_ids].astype(np.float64)+data['5266_deltas'][state]).astype(np.float32)
 assert np.array_equal(final_keys[name],expected),('Final target not exact original+declaredsupport',name)
 composition.append({'name':name,'original_foundation_sha256_float32':hashlib.sha256(old.tobytes()).hexdigest(),'final_sha256_float32':hashlib.sha256(final_keys[name].tobytes()).hexdigest(),'maximum_additive_rest_delta_m':float(np.linalg.norm(data['5266_deltas'][state],axis=1).max()),'exact_composition':True})
report['foundation_plus_sparse_support_composition']=composition;report['original151_morph_schedule_preserved']=True;report['additional_joint_residuals']=[]
(P/'joint-corrective-report.json').write_text(json.dumps(corrective,indent=2)+'\n');(P/'source-verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items()if k!='weight_changed_original_vertex_ids'}))
