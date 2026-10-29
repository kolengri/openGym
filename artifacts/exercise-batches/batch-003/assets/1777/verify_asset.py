"""Independent native/LBS topology, support, hand and pose measurements."""
import hashlib
import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils.bvhtree import BVHTree

P = Path(__file__).resolve().parent
sys.path.insert(0, str(P.parents[1]))
import authoring as a
bpy.ops.wm.open_mainfile(filepath=str(P/'source.blend'))
body = bpy.data.objects['SK_BlenderStudioHuman']
rig = bpy.data.objects['RIG_BlenderStudioHuman']
scene = bpy.context.scene
EXPECTED = '227ede3fc31d1a2b47ff40f20a4a7288fe7bb36179add23bae953993826c8b7b'
assert a.binding_hash(body, rig) == EXPECTED
R = np.array([v.co[:] for v in body.data.vertices])
attr = body.data.attributes.new('_QA_REST', 'FLOAT_VECTOR', 'POINT')
attr.data.foreach_set('vector', R.astype(np.float32).ravel())
mods = [(m, m.show_viewport, m.show_render, getattr(m, 'use_deform_preserve_volume', None)) for m in body.modifiers]


def skin(frame, path):
    for m, v, r, preserve in mods:
        m.show_viewport = v if path == 'native' else m.type == 'ARMATURE'
        if m.type == 'ARMATURE':
            m.use_deform_preserve_volume = preserve if path == 'native' else False
    scene.frame_set(frame+1)
    bpy.context.view_layer.update()
    ev = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = ev.to_mesh()
    xyz = np.array([ev.matrix_world@v.co for v in mesh.vertices])
    rest = np.empty(len(mesh.vertices)*3, np.float32)
    mesh.attributes['_QA_REST'].data.foreach_get('vector', rest)
    mesh.calc_loop_triangles()
    triangles = np.array([tri.vertices for tri in mesh.loop_triangles])
    ev.to_mesh_clear()
    return xyz, rest.reshape(-1, 3), triangles


def supports(rest):
    result = {}
    for side, sign in [('L', 1), ('R', -1)]:
        sole = (sign*rest[:, 0] > .13) & (rest[:, 2] < .012)
        result['heel_'+side] = sole & (rest[:, 1] > .025)
        result['forefoot_'+side] = sole & (rest[:, 1] < -.035)
    return result


def hand_mask(rest, sign):
    return (sign*rest[:, 0] > .375) & (rest[:, 2] < .965)


def surface_tree(xyz, tri, mask):
    selected = tri[np.all(mask[tri], axis=1)]
    return BVHTree.FromPolygons(xyz.tolist(), selected.tolist(), all_triangles=True)


tolerance = {'floor_penetration_m': .004, 'support_gap_m': .015,
             'near_distance_m': .015, 'minimum_near_fraction': .50,
             'static_patch_drift_m': .002}
rows, references, linear_refs, poses, failures, loop = [], [], [], [], [], {}
initial_centroids = {}
for frame in [0, 15, 30, 45, 60, 75, 90, 105, 120, 135, 150]:
    ref = {'id': '1777', 'frame': frame, 'patches': {}}
    for path in ['native', 'linear']:
        xyz, rest, tri = skin(frame, path)
        contact = {}
        for name, mask in supports(rest).items():
            ids = np.where(mask)[0]
            assert len(ids) > 0, name
            z = xyz[ids, 2]
            centroid = xyz[ids].mean(axis=0)
            key = (path, name)
            initial_centroids.setdefault(key, centroid)
            drift = float(np.linalg.norm((centroid-initial_centroids[key])[:2]))
            faces = tri[np.all(mask[tri], axis=1)]
            area = np.linalg.norm(np.cross(xyz[faces[:, 1]]-xyz[faces[:, 0]], xyz[faces[:, 2]]-xyz[faces[:, 0]]), axis=1)*.5
            near_faces = np.all(np.abs(xyz[faces, 2]) <= tolerance['near_distance_m'], axis=1)
            near_fraction = float(((z >= -.004) & (z <= .015)).mean())
            contact[name] = {'count': len(ids), 'min_z': float(z.min()), 'max_z': float(z.max()),
                             'near_fraction': near_fraction, 'surface_area_m2': float(area.sum()),
                             'near_area_m2': float(area[near_faces].sum()), 'tangential_drift_m': drift}
            if z.min() > .015 or near_fraction < .50 or drift > .002:
                failures.append(f'{path} frame {frame} {name} support')
            if path == 'linear':
                ref['patches'][name] = {'indices': ids.tolist(), 'min_z': float(z.min()), 'max_z': float(z.max())}
        left, right = hand_mask(rest, 1), hand_mask(rest, -1)
        head = (rest[:, 2] > 1.56) & (np.abs(rest[:, 0]) < .16)
        head_tree = surface_tree(xyz, tri, head)
        clearance = min(head_tree.find_nearest(tuple(p))[3] for p in xyz[left|right])
        overlaps = surface_tree(xyz, tri, left).overlap(surface_tree(xyz, tri, right))
        rows.append({'path': path, 'frame': frame, 'global_floor_z': float(xyz[:, 2].min()),
                     'supports': contact, 'hand_head_clearance_m': float(clearance),
                     'cross_hand_triangle_intersections': len(overlaps),
                     'bounds': [xyz.min(axis=0).tolist(), xyz.max(axis=0).tolist()]})
        if xyz[:, 2].min() < -.004:
            failures.append(f'{path} frame {frame} floor penetration')
        if clearance < .025:
            failures.append(f'{path} frame {frame} hand-head clearance')
        if overlaps:
            failures.append(f'{path} frame {frame} cross-hand surface intersections')
        if path == 'linear':
            ref['global_floor_z'] = float(xyz[:, 2].min())
            linear_refs.append({'frame': frame, 'vertices': xyz.tolist()})
            if frame in [0, 150]:
                loop[frame] = xyz
    references.append(ref)
    p = {'frame': frame, 'pelvis_head': list(rig.pose.bones['Hips'].head), 'lumbar_quaternion': list(rig.pose.bones['Spine'].matrix.to_quaternion())}
    for side in ['Left', 'Right']:
        shoulder, elbow, wrist = [rig.pose.bones[side+s].head for s in ['Arm', 'ForeArm', 'Hand']]
        p[side+'_elbow_internal_degrees'] = math.degrees((shoulder-elbow).angle(wrist-elbow))
    poses.append(p)
loop_error = float(np.linalg.norm(loop[0]-loop[150], axis=1).max())
if loop_error > 1e-6:
    failures.append('linear endpoint mismatch')
previous = None
continuity = {'max_world_rotation_step_degrees': 0, 'bone': None, 'frame': None,
              'max_world_joint_step_m': 0, 'sampled_every_native_frame': True}
for frame in range(151):
    scene.frame_set(frame+1)
    bpy.context.view_layer.update()
    current = {p.name: (p.matrix.to_quaternion(), p.head.copy()) for p in rig.pose.bones}
    if previous:
        for name, (q, head) in current.items():
            old_q, old_head = previous[name]
            angle = math.degrees(2*math.acos(min(1, abs(q.dot(old_q)))))
            if angle > continuity['max_world_rotation_step_degrees']:
                continuity.update(max_world_rotation_step_degrees=angle, bone=name, frame=frame)
            continuity['max_world_joint_step_m'] = max(continuity['max_world_joint_step_m'], (head-old_head).length)
    previous = current
if continuity['max_world_rotation_step_degrees'] > 20:
    failures.append('world rotation discontinuity guard (>20 degrees per 1/30s illustration frame)')
assert [action.name for action in bpy.data.actions] == ['Exercise_1777']
sys.path.insert(0, str(Path.home()/'.codex/skills/blender-asset-qa/scripts'))
import qa_check
checks = []
for path in ['native', 'linear']:
    for frame in [0, 75]:
        skin(frame, path)
        result = qa_check.run(objects=[body.name], profile='game')
        checks.append({'path': path, 'frame': frame, 'qa': result})
        if not result['pass']:
            failures.append(f'{path} frame {frame} asset QA: {result["errors"]}')
source_sha = hashlib.sha256((P/'source.blend').read_bytes()).hexdigest()
(P/'asset-qa.json').write_text(json.dumps({'source_sha256': source_sha, 'pass': all(c['qa']['pass'] for c in checks), 'checks': checks}, indent=2)+'\n')
(P/'runtime-surface-reference.json').write_text(json.dumps({'source_sha256': source_sha, 'source_vertices': 10582,
    'coordinate_frame': 'Blender world metres, actual original cage indices', 'samples': references}, separators=(',', ':'))+'\n')
(P/'linear-vertex-reference.json').write_text(json.dumps(linear_refs, separators=(',', ':'))+'\n')
report = {'ok': not failures, 'source_sha256': source_sha, 'binding_hash': a.binding_hash(body, rig),
          'tolerances': tolerance, 'tolerance_basis': 'Authored illustration bands at 1.8 m character scale; no clinical or collision guarantee.',
          'patch_definition': 'Bilateral original-skin heel/forefoot underside patches (rest z<12 mm), evaluated together. Native smooth skin is selected by interpolated rest coordinates.',
          'native_path': 'Original armature preserve-volume plus CorrectiveSmooth and Multires1',
          'linear_path': 'Original armature only, preserve-volume disabled, identical target to GLB LBS',
          'loop_max_vertex_error_m': loop_error, 'rotation_continuity': continuity,
          'failures': failures, 'pose_samples': poses, 'samples': rows}
(P/'surface-contact-report.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps({'ok': not failures, 'failures': failures, 'cross_hand_intersections': [(r['path'], r['frame'], r['cross_hand_triangle_intersections']) for r in rows]}))
