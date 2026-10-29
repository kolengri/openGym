"""Verify the shipped default importer against the root-accepted native file."""
import sys
sys.dont_write_bytecode=True
import bpy,numpy as np,json,hashlib
from pathlib import Path
F=Path(__file__).resolve().parent;sys.path.insert(0,str(F));import corrective
META=json.loads((F/'component.json').read_text());source=F/'inputs-contact/source.blend';assert corrective.sha(source)==META['source_sha256']
bpy.ops.wm.open_mainfile(filepath=str(source));body=bpy.data.objects['SK_BlenderStudioHuman'];rig=bpy.data.objects['RIG_BlenderStudioHuman'];scene=bpy.context.scene

def select():
 action=bpy.data.actions['Exercise_3995'];rig.animation_data.action=action;rig.animation_data.action_slot=next(x for x in action.slots if x.target_id_type=='OBJECT');keys=body.data.shape_keys;keys.animation_data.action=action;keys.animation_data.action_slot=next(x for x in action.slots if x.target_id_type=='KEY');scene.frame_set(38,subframe=.5)

def sample():
 bpy.context.view_layer.update();evaluated=body.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=evaluated.to_mesh();p=np.array([v.co[:]for v in mesh.vertices],np.float32);n=np.array([v.normal[:]for v in mesh.vertices],np.float32);evaluated.to_mesh_clear();return p,n,np.array([b.matrix for b in rig.pose.bones],np.float32)
select();base=sample();action_count=len(bpy.data.actions);data=corrective.install(body,rig,scene);assert all(np.array_equal(a,b)for a,b in zip(base,sample()));key_count=len(body.data.shape_keys.key_blocks);corrective.install(body,rig,scene);assert len(body.data.shape_keys.key_blocks)==key_count;assert len(bpy.data.actions)==action_count;body.data.shape_keys.key_blocks[corrective.KEY].value=1.;installed=sample()
keys=body.data.shape_keys;normal=np.array(keys.key_blocks[corrective.KEY].normals_vertex_get(),np.float32).reshape(-1,3)-np.array(keys.key_blocks['Basis'].normals_vertex_get(),np.float32).reshape(-1,3);assert np.array_equal(normal,data['rest_normal_deltas'])
reference=F/'accepted-held-reference.npz'
if reference.exists():
 stored=np.load(reference);accepted=(stored['positions'],stored['geometric_normals'],stored['bone_matrices'])
else:
 bpy.ops.wm.open_mainfile(filepath=str(F/'candidate-a50d65d6c27e.blend'));body=bpy.data.objects['SK_BlenderStudioHuman'];rig=bpy.data.objects['RIG_BlenderStudioHuman'];scene=bpy.context.scene;select();body.data.shape_keys.key_blocks[corrective.KEY].value=1.;accepted=sample();np.savez_compressed(reference,positions=accepted[0],geometric_normals=accepted[1],bone_matrices=accepted[2])
assert all(np.array_equal(a,b)for a,b in zip(installed,accepted))
receipt={'ok':True,'archive_sha256':META['archive_sha256'],'importer_sha256':corrective.sha(F/'corrective.py'),'accepted_native_reference_sha256':corrective.sha(reference),'default_import_path_verified':True,'idempotent_install':True,'new_key_default_zero_skin_NORMAL_bones_bit_exact':True,'existing_action_count_unchanged':True,'shipped_NORMAL_archive_matches_shape_key_geometry_bit_exact':True,'installed_held_POSITION_geometric_NORMAL_all51_matrices_match_root_accepted_candidate_bit_exact':True,'native_held_skin_sha256':hashlib.sha256(installed[0].tobytes()).hexdigest()};(F/'import-verification.json').write_text(json.dumps(receipt,indent=2)+'\n');print('DEFAULT_IMPORT_PASS',receipt['archive_sha256'])
