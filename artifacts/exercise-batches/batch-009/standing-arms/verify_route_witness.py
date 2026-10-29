"""Bone-only parity between the frozen route and its saved native action."""
from pathlib import Path
import hashlib
import json
import sys

import bpy
import numpy as np
from mathutils import Matrix

sys.dont_write_bytecode = True
F = Path(__file__).resolve().parent
sys.path.insert(0, str(F))
from coherent_route import CoherentRoute
from wrap_acquisition import ClearanceRoute

sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
dependency = json.loads((F / 'route-dependency.json').read_text())
assert sha(F / 'coherent_route.py') == dependency['helper_sha256']
assert sha(F / 'coherent-hand-matrices.npz') == dependency['witness151_sha256']
baseline_route = CoherentRoute(F / 'coherent-route-coefficients.npz')
route = ClearanceRoute(F / 'coherent-route-coefficients.npz',json.loads((F/'wrist-detour.json').read_text())['amplitude_m'])
with np.load(F / 'coherent-hand-matrices.npz', allow_pickle=False) as data:
    witness = data['matrices'].copy()
reference=F/'untouched-route-reference.npz';assert sha(reference)==dependency['untouched_reference']['sha256']
with np.load(reference,allow_pickle=False)as data:
    baseline_matrices=data['matrices'].copy();reference_names=data['bone_names'].tolist();assert str(data['source_sha256'])=='934c0658daf0154a2468740845b3c33c1c5ad850e53f3f35d8e7a86451097911'
bpy.ops.wm.open_mainfile(filepath=str(F / 'source.blend'))
rig = bpy.data.objects['RIG_BlenderStudioHuman']
keys = bpy.data.objects['SK_BlenderStudioHuman'].data.shape_keys
action = bpy.data.actions['Exercise_3995']
rig.animation_data.action = action
rig.animation_data.action_slot = next(x for x in action.slots if x.target_id_type == 'OBJECT')
keys.animation_data.action = action
keys.animation_data.action_slot = next(x for x in action.slots if x.target_id_type == 'KEY')
helper_error = saved_error = rigid_error = endpoint_error = weight_error = position_error = angular_error = projection_error = untouched_error = 0.
worst = None
dynamic={side+part for side in ['Left','Right']for part in ['Shoulder','Arm','ForeArm','Hand']}|{name for name,_,_ in route.fingers}
untouched=[route.names.index(name)for name in reference_names]
for frame in range(151):
    desired, scalar = route.pose(frame)
    expected = np.array([desired[name] for name in route.names], dtype=np.float32)
    original,_=baseline_route.pose(frame)
    helper_error = max(helper_error, float(np.max(abs(np.asarray([original[name]for name in route.names],dtype=np.float32) - witness[frame]))))
    bpy.context.scene.frame_set(frame + 1)
    bpy.context.view_layer.update()
    actual = np.array([rig.pose.bones[name].matrix for name in route.names], dtype=np.float32)
    untouched_error=max(untouched_error,float(np.max(abs(actual[untouched]-baseline_matrices[frame]))))
    error = float(np.max(abs(actual - expected)))
    if error > saved_error:
        saved_error, worst = error, frame
    progress = min(1., scalar / route.peak)
    endpoint = 0 if progress <= 1e-14 else 1 if progress >= 1. - 1e-12 else None
    if endpoint is not None:
        endpoint_error = max(endpoint_error, float(np.max(abs(actual - route.data['endpoint_native_global_matrices'][endpoint]))))
    rigid=[]
    for i,name in enumerate(route.names):
        if endpoint is not None:
            target=route.data['endpoint_native_global_matrices'][endpoint,i]
        elif name not in dynamic:
            target=route.data['endpoint_native_global_matrices'][0,i]
        else:
            target=np.asarray(Matrix.Translation(desired[name].translation)@desired[name].to_quaternion().normalized().to_matrix().to_4x4(),dtype=np.float32)
        rigid.append(target)
        qa=np.asarray(rig.pose.bones[name].matrix.to_quaternion(),dtype=np.float64);qb=np.asarray(desired[name].to_quaternion(),dtype=np.float64)
        dot=abs(float(qa@qb)/(np.linalg.norm(qa)*np.linalg.norm(qb)))
        angular_error=max(angular_error,float(np.degrees(2*np.arccos(np.clip(dot,0.,1.)))))
    rigid=np.asarray(rigid,dtype=np.float32)
    rigid_error=max(rigid_error,float(np.max(abs(actual-rigid))))
    projection_error=max(projection_error,float(np.max(abs(expected-rigid))))
    position_error=max(position_error,float(np.linalg.norm(actual[:,:3,3]-expected[:,:3,3],axis=1).max()))
    weight_error = max(weight_error, abs(keys.key_blocks['WrapRightOverCuff'].value - scalar))
    assert keys.key_blocks['OwnershipRightCross'].value == keys.key_blocks['OwnershipLeftCross'].value == 0
assert helper_error == 0
assert endpoint_error == 0
assert untouched_error == 0
assert rigid_error < 2e-6
assert weight_error < 1e-7
report = {
    'source_sha256': sha(F / 'source.blend'),
    'helper_sha256': dependency['helper_sha256'],
    'archive_sha256': dependency['archive_sha256'],
    'witness151_sha256': dependency['witness151_sha256'],
    'acquisition_extension_sha256':sha(F/'wrap_acquisition.py'),
    'anterior_wrist_amplitude_m':route.amplitude,
    'all151_untouched_bones_vs_0290944c_matrix_error':untouched_error,
    'states': 151,
    'maximum_frozen_helper_witness_51bone_matrix_error': helper_error,
    'maximum_saved_native_desired_51bone_matrix_error': saved_error,
    'maximum_saved_native_rigid_reference_51bone_matrix_error': rigid_error,
    'maximum_rigid_reference_projection_51bone_matrix_change': projection_error,
    'maximum_saved_native_authoring_route_joint_position_error_m': position_error,
    'maximum_saved_native_authoring_route_rotation_error_degrees': angular_error,
    'saved_native_desired_worst_frame': worst,
    'maximum_saved_native_accepted_endpoint_51bone_matrix_error': endpoint_error,
    'maximum_original_p_held_key_scalar_error': weight_error,
    'scope': 'Bone-only. Native endpoint channels preserve the accepted saved source exactly. Intermediate dynamic frames use the existing production rigid-quaternion normalization convention to remove frozen float32 nonrigidity; static trunk/head/feet retain original native channels. Raw frozen-matrix, projected rigid-reference, position and rotation errors are reported separately. No mesh or skin QA is performed.',
    'ok': True,
}
(F / 'route-native-parity.json').write_text(json.dumps(report, indent=2) + '\n')
print('ROUTE_NATIVE_PARITY', json.dumps(report))
