"""Read back original invariants and every declared binding/additive component."""
import gzip,hashlib,json,sys
from pathlib import Path
import bpy,numpy as np
P=Path(__file__).resolve().parent;S=P.parents[2]/'batch-004/assets/0003';H=P.parents[1]/'posture-support'
sys.path.insert(0,str(P.parents[2]/'batch-003'));import authoring as a
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def invariant(body,rig):
 h=hashlib.sha256()
 for v in body.data.vertices:h.update(np.array(v.co,np.float32).tobytes())
 for p in body.data.polygons:h.update(np.array(p.vertices,np.int32).tobytes())
 for uv in body.data.uv_layers:
  data=np.empty(len(uv.data)*2,np.float32);uv.data.foreach_get('uv',data);h.update(uv.name.encode()+data.tobytes())
 for b in rig.data.bones:h.update(b.name.encode()+np.array(b.matrix_local,np.float32).tobytes())
 return h.hexdigest()
def weights(body):
 return [{body.vertex_groups[g.group].name:float(g.weight)for g in v.groups}for v in body.data.vertices]
bpy.ops.wm.open_mainfile(filepath=str(S/'source.blend'));b=bpy.data.objects['SK_BlenderStudioHuman'];r=bpy.data.objects['RIG_BlenderStudioHuman'];original=invariant(b,r);expected_weights=weights(b)
original_keys={k.name:np.array([v.co[:]for v in k.data],np.float32)for k in b.data.shape_keys.key_blocks};contract=json.loads((P/'support-contract.json').read_text());data=np.load(H/contract['support_targets']);ids=data['source_ids'];shoulder=np.load(P/'shoulder-additive-component.npz');shoulder_ids=shoulder['source_ids'];integration=json.loads((P/'joint-repair-integration.json').read_text());assert integration['pass']
# Replay declarative before/after fields rather than trusting a stored hash.
for changes in [json.loads((P/'profile-binding-overlay.json').read_text())['changes'],json.loads((P/'glute-binding-repair.json').read_text())['changes']]:
 for change in changes:
  i=change.get('source_id',change.get('id'));assert expected_weights[i]==change['before'],('Binding foundation differs',i)
  expected_weights[i]={n:float(np.float32(v))for n,v in change['after'].items()}
bpy.ops.wm.open_mainfile(filepath=str(P/'source.blend'));b=bpy.data.objects['SK_BlenderStudioHuman'];r=bpy.data.objects['RIG_BlenderStudioHuman'];keys=b.data.shape_keys;names=['JointNeutral','JointRightCross','JointLeftCross']
assert invariant(b,r)==original
assert weights(b)==expected_weights,'Actual source weights differ from declared normalized overlays'
assert max(len(v.groups)for v in b.data.vertices)<=4
assert max(abs(sum(g.weight for g in v.groups)-1)for v in b.data.vertices)<2e-6
assert a.binding_hash(b,r)==integration['runtime_binding_sha256']
assert sha(P/'source.blend')==integration['source_sha256']
assert [k.name for k in keys.key_blocks]==['Basis']+names
assert np.array_equal(np.array([v.co[:]for v in keys.key_blocks['Basis'].data],np.float32),original_keys['Basis'])
assert np.array_equal(np.array([v.co[:]for v in b.data.vertices],np.float32),original_keys['Basis'])
protected=json.loads((P/'support-protected-domain.json').read_text())['protected_source_ids'];composition=[]
for index,name in enumerate(names):
 foundation=original_keys[name].astype(np.float64);foundation[ids]+=data['2395_deltas'][index];foundation=foundation.astype(np.float32)
 assert np.array_equal(foundation,shoulder['foundation_buffers'][index])
 expected=foundation.astype(np.float64);expected[shoulder_ids]+=shoulder['deltas'][index]
 actual=np.array([v.co[:]for v in keys.key_blocks[name].data],np.float32);assert np.array_equal(actual,expected.astype(np.float32)),name
 assert np.array_equal(actual[protected],foundation[protected])
 composition.append({'key':name,'final_coordinate_sha256_float32':hashlib.sha256(actual.tobytes()).hexdigest(),'original_foundation_coordinate_sha256_float32':hashlib.sha256(original_keys[name].tobytes()).hexdigest(),'maximum_new_support_delta_m':float(np.linalg.norm(data['2395_deltas'][index],axis=1).max()),'maximum_additive_shoulder_delta_m':float(np.linalg.norm(shoulder['deltas'][index],axis=1).max()),'all97_shared_support_positions_exact':True,'exact_original_plus_support_plus_shoulder':True})
assert len(r.data.bones)==51 and [x.name for x in bpy.data.actions]==['Exercise_2395']
assert r.animation_data.action is keys.animation_data.action
assert {x.target_id_type for x in r.animation_data.action.slots}=={'OBJECT','KEY'}
assert all(m.show_viewport==(m.type=='ARMATURE')and m.show_render==(m.type=='ARMATURE')for m in b.modifiers)
assert next(m for m in b.modifiers if m.type=='ARMATURE').use_deform_preserve_volume
source_sha=sha(P/'source.blend');normals={'source_sha256':source_sha,'basis':np.array(keys.key_blocks['Basis'].normals_vertex_get()).reshape(-1,3).tolist(),'targets':{name:np.array(keys.key_blocks[name].normals_vertex_get()).reshape(-1,3).tolist()for name in names},'coordinate_frame':'Original Blender rest normals; Z up'}
with gzip.open(P/'joint-normal-reference.json.gz','wt',compresslevel=9)as out:json.dump(normals,out,separators=(',',':'))
report={'pass':True,'source_sha256':source_sha,'original_source_sha256':a.SOURCE_SHA,'binding_rest_uv_sha256':a.binding_hash(b,r),'original_basis_topology_uv_bone_rest_sha256':original,'basis_topology_uv_bone_rest_unchanged':True,'runtime_weights_changed_by_declared_local_overlays':True,'all_actual_weights_equal_declarative_recipe':True,'maximum_influences':max(len(v.groups)for v in b.data.vertices),'maximum_weight_partition_error':max(abs(sum(g.weight for g in v.groups)-1)for v in b.data.vertices),'binding_overlay_receipts':['profile-binding-overlay.json','glute-binding-repair.json','joint-repair-integration.json'],'bones':51,'vertices':len(b.data.vertices),'triangles':sum(len(p.vertices)-2 for p in b.data.polygons),'materials':len(b.data.materials),'dimensions_m':list(b.dimensions),'actions':['Exercise_2395'],'action_slots':['OBJECT','KEY'],'morphs':names,'composition':composition,'global_corrective_smooth_disabled':True,'all_non_armature_modifiers_disabled':True,'normal_reference':'joint-normal-reference.json.gz','source_saved':False}
(P/'source-verification.json').write_text(json.dumps(report,indent=2)+'\n')
bpy.context.scene.frame_set(1);bpy.context.view_layer.update();sys.path.insert(0,str(Path.home()/'.codex/skills/blender-asset-qa/scripts'));import qa_check
raw=qa_check.run(objects=[b.name],profile='game');(P/'raw-asset-qa.json').write_text(json.dumps(raw,indent=2)+'\n');assert raw['pass'],raw['errors']
print('SOURCE_READBACK_PASS',json.dumps(report));print('RAW_QA',raw['pass'],raw['warnings'])
