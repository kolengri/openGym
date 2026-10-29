"""Authoritative batch005 native sampler and additive support integration API.

Load the original0003 foundation, clear its rig action, then call apply_binding
and install_support once before baking a new action. Existing original compact
key animation stays unchanged. Additive joint fixes must avoid protected IDs.
"""
import hashlib,json,sys
from pathlib import Path
import numpy as np
P=Path(__file__).resolve().parent
CONTRACT=json.loads((P/'support-contract.json').read_text())
KEY_NAMES=[r['key']for r in CONTRACT['support_states']]

def apply_binding(body,rig):
 from profile_binding import ProfileBinding
 family=ProfileBinding(body,rig)
 amount=CONTRACT['binding_amounts']
 family.apply(amount['above_hip_thigh_removal'],amount['posterior_lower_lumbar_chest_removal'])
 return family.apply(amount['above_hip_thigh_removal'],amount['posterior_lower_lumbar_chest_removal'],details=True)

def install_support(body,family):
 family=str(family);target=P/CONTRACT['support_targets']
 assert hashlib.sha256(target.read_bytes()).hexdigest()==CONTRACT['support_targets_sha256']
 data=np.load(target);ids=data['source_ids'];basis=np.array([v.co[:]for v in body.data.vertices])
 assert basis.shape==(10582,3) and np.array_equal(basis[ids].astype(np.float32),data['source_basis'])
 changed=[]
 for state,name in enumerate(KEY_NAMES):
  key=body.data.shape_keys.key_blocks[name];current=np.array([v.co[:]for v in key.data])
  assert np.array_equal(current[ids].astype(np.float32),data['foundation_keys'][state]),'Original0003 support foundation changed or support was already installed: '+name
  original=current.astype(np.float32).copy();delta=data[family+'_deltas'][state];current[ids]+=delta
  expected=current.astype(np.float32);key.data.foreach_set('co',expected.ravel())
  actual=np.array([v.co[:]for v in key.data],dtype=np.float32)
  assert np.array_equal(actual,expected),'Additive support composition readback changed'
  changed.append({'key':name,'maximum_declared_additive_rest_delta_m':float(np.linalg.norm(delta,axis=1).max()),'maximum_actual_coordinate_difference_m':float(np.linalg.norm(actual-original,axis=1).max()),'changed_source_ids':ids[np.linalg.norm(delta,axis=1)>1e-8].tolist(),'composition':{'original_input_full_sha256_float32':hashlib.sha256(original.tobytes()).hexdigest(),'declared_sparse_support_delta_sha256_float32':hashlib.sha256(delta.tobytes()).hexdigest(),'expected_composed_full_sha256_float32':hashlib.sha256(expected.tobytes()).hexdigest(),'actual_composed_full_sha256_float32':hashlib.sha256(actual.tobytes()).hexdigest(),'actual_equals_float32_original_plus_declared_delta':True,'legacy_guards_retained_in_original_input':True}})
 assert np.array_equal(basis,np.array([v.co[:]for v in body.data.vertices]))
 return {'family':family,'targets':changed,'protected_source_ids':ids.tolist(),'added_morph_count':0}

def sample(a,frame,family):
 """Pose with a constant root; never renormalize the corrected support surface."""
 family=str(family)
 assert not a.rig.animation_data or a.rig.animation_data.action is None,'Clear inherited/new rig action before manual sampling; baking must key only after the sample.'
 source=P.parent.parent/'batch-004/assets/0003'
 for path in [P,source]:
  if str(path)not in sys.path:sys.path.insert(0,str(path))
 if family=='2395':import air_bike_pose as motion
 elif family=='5266':import tabletop_pose as motion
 else:raise ValueError('Unsupported support family: '+family)
 a.scene.frame_set(int(frame)+1,subframe=frame%1)
 desired=motion.pose(a,frame,CONTRACT['constant_root_z_m'],CONTRACT['posture'])
 import bpy
 bpy.context.view_layer.update()
 error=max(float(np.max(abs(np.array(a.rig.pose.bones[n].matrix)-np.array(desired[n]))))for n in desired)
 assert error<2e-6,('Actual native pose changed',family,frame,error)
 evaluated=a.body.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=evaluated.to_mesh()
 values=np.empty(len(mesh.vertices)*3);mesh.vertices.foreach_get('co',values);evaluated.to_mesh_clear()
 return values.reshape(-1,3),{'matrix_max_error':error,'root_z_m':CONTRACT['constant_root_z_m'],'desired':desired}
