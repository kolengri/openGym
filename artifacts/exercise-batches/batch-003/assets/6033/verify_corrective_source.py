"""Read-only source invariants and original-index rest-normal reference."""
import gzip
import hashlib
import json
import sys
from pathlib import Path

import bpy
import numpy as np

P = Path(__file__).resolve().parent
sys.path.insert(0, str(P.parents[1]))
import authoring as a

bpy.ops.wm.open_mainfile(filepath=str(P / 'source.blend'))
body = next(o for o in bpy.data.objects if o.type == 'MESH')
rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
keys = body.data.shape_keys
assert [k.name for k in keys.key_blocks] == ['Basis', 'KneeCapRound']
assert np.array_equal(np.array([v.co[:] for v in body.data.vertices]),
                      np.array([v.co[:] for v in keys.key_blocks['Basis'].data]))
assert a.binding_hash(body, rig) == '227ede3fc31d1a2b47ff40f20a4a7288fe7bb36179add23bae953993826c8b7b'
assert len(rig.data.bones) == 51
assert [action.name for action in bpy.data.actions] == ['Exercise_6033']
assert rig.animation_data.action == keys.animation_data.action
assert {slot.target_id_type for slot in rig.animation_data.action.slots} == {'OBJECT', 'KEY'}
assert all(m.show_viewport == (m.type == 'ARMATURE') and
           m.show_render == (m.type == 'ARMATURE') for m in body.modifiers)
assert next(m for m in body.modifiers if m.type == 'ARMATURE').use_deform_preserve_volume
source_sha = hashlib.sha256((P / 'source.blend').read_bytes()).hexdigest()
base = np.array(keys.key_blocks['Basis'].normals_vertex_get()).reshape((-1, 3))
target = np.array(keys.key_blocks['KneeCapRound'].normals_vertex_get()).reshape((-1, 3))
assert len(base) == len(target) == 10582 and np.isfinite(target).all()
reference = {'source_sha256': source_sha, 'coordinate_frame': 'Original Blender mesh rest normals; Z up',
             'basis': base.tolist(), 'target': target.tolist()}
with gzip.open(P / 'knee-normal-reference.json.gz', 'wt', compresslevel=9) as stream:
    json.dump(reference, stream, separators=(',', ':'))
report = {'pass': True, 'source_sha256': source_sha, 'basis_identical_to_original_mesh': True,
          'binding_rest_uv_unchanged': True, 'bones': 51, 'actions': ['Exercise_6033'],
          'action_slots': ['OBJECT', 'KEY'], 'morphs': ['KneeCapRound'],
          'global_corrective_smooth_disabled': True, 'all_non_armature_modifiers_disabled': True,
          'normal_reference': 'knee-normal-reference.json.gz', 'source_saved': False}
(P / 'knee-source-verification.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
