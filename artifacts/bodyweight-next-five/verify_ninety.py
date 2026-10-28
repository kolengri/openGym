"""Native original-binding DQ-cage surface QA with frozen original-index landmarks.

These are illustration-authoring checks, not medical/biomechanics approval.
"""
import argparse
import bpy
import hashlib
import json
import math
import sys
from pathlib import Path
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

P = Path(__file__).resolve().parent
sys.path.insert(0, str(P))
args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
parser = argparse.ArgumentParser()
parser.add_argument('--procedural', action='store_true')
parser.add_argument('--asset', choices=['ninety-repaired'], default='ninety-repaired')
parser.add_argument('--surface-only', action='store_true', help='Draft diagnostic; never produces a passing final pose-verification receipt.')
options = parser.parse_args(args)
if options.procedural:
    import ninety_pose as author
    author.initialize()
    if (P/'ninety-contact-parameters.json').exists():author.CONTACT_PARAMETERS=json.loads((P/'ninety-contact-parameters.json').read_text())['parameters']
    items = author.metadata()
else:
    bpy.ops.wm.open_mainfile(filepath=str(P / (options.asset + '.blend')))
    items = json.loads((P / 'ninety-clips.json').read_text())
    items = [i for i in items if (i['id'] in ['10565','6560']) == (options.asset == 'ninety-repaired')]
body = bpy.data.objects['SK_BlenderStudioHuman']
rig = bpy.data.objects['RIG_BlenderStudioHuman']
assert len(rig.data.bones)==51 and body.data.shape_keys is None
next(m for m in body.modifiers if m.type=='ARMATURE').use_deform_preserve_volume=True
scene = bpy.context.scene
OUT = P / 'trials' if options.procedural else P / 'repair-90/dq' if options.asset == 'ninety-repaired' else P
OUT.mkdir(parents=True,exist_ok=True)
rest = np.array([v.co[:] for v in body.data.vertices])
rest_sha = hashlib.sha256(rest.astype(np.float32).tobytes()).hexdigest()
modifiers = [(m, m.show_viewport, m.show_render) for m in body.modifiers]
group_names = {g.index: g.name for g in body.vertex_groups}
groups = {name: np.array([sum(g.weight for g in v.groups if group_names[g.group] == name) for v in body.data.vertices]) for name in group_names.values()}


def set_pose(item, frame, path):
    if options.procedural:
        author.make_pose(item, frame / 30)
    else:
        rig.animation_data.action = bpy.data.actions[item['action']]
        scene.frame_set(frame + 1)
    for modifier, viewport, _ in modifiers:
        modifier.show_viewport = viewport if path == 'native' else modifier.type == 'ARMATURE'
    bpy.context.view_layer.update()


def evaluated():
    ev = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = ev.to_mesh()
    positions = np.array([body.matrix_world @ v.co for v in mesh.vertices])
    return ev, mesh, positions


def source_positions(item, frame):
    set_pose(item, frame, 'dq_cage')
    ev, mesh, positions = evaluated()
    ev.to_mesh_clear()
    assert len(positions) == 10582
    return positions


def stats(values):
    return {'min_z': float(values.min()), 'p10_z': float(np.percentile(values, 10)),
            'median_z': float(np.median(values)), 'max_z': float(values.max())}


RAYS = [Vector(v).normalized() for v in [( .843, .371, .39), (-.237, .925, .29), (.17, -.31, .935),
                                        (-.843, -.371, -.39), (.237, -.925, -.29), (-.17, .31, -.935)]]


def inside_surface(bvh, point):
    """Majority ray parity, not the half-space of one distant nearest triangle.

    The cropped head/leg surfaces have one remote boundary. Six directions
    prevent that crop from turning outside points into fictitious penetration.
    """
    odd = 0
    for direction in RAYS:
        origin = point.copy()
        crossings = 0
        for _ in range(64):
            hit, _, _, _ = bvh.ray_cast(origin, direction, 4.0)
            if hit is None:
                break
            crossings += 1
            origin = hit + direction * .000002
        odd += crossings % 2
    return odd >= 4


def patch_from_low_quads(item, candidates, frames, rationale):
    """Author local skin quads from actual posed source skin, never atlas masks."""
    polygons = [p for p in body.data.polygons if all(candidates[i] for i in p.vertices)]
    assert polygons, rationale
    chosen = set()
    for frame in frames:
        positions = source_positions(item, frame)
        # Freeze an actual lowest skin point and its local face, rather than a
        # low median elsewhere that may miss the true contact pad entirely.
        face = min(polygons, key=lambda p: (float(positions[list(p.vertices), 2].min()), float(np.median(positions[list(p.vertices), 2]))))
        chosen.add(face.index)
    indices = sorted({i for n in chosen for i in body.data.polygons[n].vertices})
    return {'indices': indices, 'polygons': sorted(chosen), 'rationale': rationale,
            'selection': 'Local original skin quads containing the actual lowest floor-facing source skin point in the declared search region at representative phases; frozen original IDs, not a glute atlas or clinical ischial landmark.'}


def make_landmarks(item):
    n = item['frames']
    patches = {}
    pelvic = (rest[:, 2] > .80) & (rest[:, 2] < 1.03) & (rest[:, 1] > .025) & (abs(rest[:, 0]) < .23)
    phases = [0, n // 4, 3 * n // 4] if item['display_mode'] != 'stretch' else [0, 60]
    patches['pelvic_support'] = patch_from_low_quads(item, pelvic, phases,
        'Actual posterior pelvic/upper-thigh junction skin supporting the seated/supine body. Search is bounded to the original posterior pelvic skin and manually reviewed in solid/side views. Not a clinically localized load-bearing landmark.')
    patches['pelvic_support']['state'] = 'supported'
    for side, suffix, sign in [('Left', 'L', 1), ('Right', 'R', -1)]:
        foot = (rest[:, 0] * sign > .15) & (rest[:, 2] < .05)
        if item['display_mode'] == 'stretch':
            candidates = groups[side + 'Foot'] > .7
            patches['foot_edge_' + suffix] = patch_from_low_quads(item, candidates, [0, 60],
                'Actual lateral/medial foot-edge skin on the shared floor in the seated90/90 pose; not a falsely flat plantar sole.')
            patches['foot_edge_' + suffix]['state'] = 'supported'
            for part, label in [('UpLeg', 'thigh_'), ('Leg', 'shin_')]:
                patches[label + suffix] = patch_from_low_quads(item, groups[side + part] > .7, [0, 60],
                    'Local outer seated leg skin; floor clearance distribution is reported. Curved shin need not lie flat along its entire length.')
                patches[label + suffix]['state'] = 'supported' if part == 'UpLeg' else 'observed'
        else:
            for label, mask in [('heel_', foot & (rest[:, 1] > .105) & (rest[:, 2] < .025)),
                                ('sole_', foot & (rest[:, 1] < .025) & (rest[:, 1] > -.075) & (rest[:, 2] < .012))]:
                patches[label + suffix] = {'indices': np.flatnonzero(mask).tolist(), 'rationale': 'Original plantar posterior heel / forefoot skin, separately sampled rather than whole-foot extrema.',
                                          'state': 'supported' if item['id'] == '6428' else 'lifted'}
        hand = np.zeros(len(rest), bool)
        for name, weight in groups.items():
            if name.startswith(side) and any(s in name for s in ['Hand', 'Thumb', 'Index', 'Middle', 'Ring', 'Little']):
                hand |= weight > .5
        patches['hand_' + suffix] = {'indices': np.flatnonzero(hand).tolist(), 'state': 'observed', 'rationale': 'All strongly hand/finger-bound source skin; signed head and lower-body surface clearance is measured.'}
        patches['forearm_'+suffix]={'indices':np.flatnonzero(groups[side+'ForeArm']>.7).tolist(),'state':'observed','rationale':'Strongly forearm-bound original skin; separate signed clearance against the lower-body skin, beyond hand-only or joint checks.'}
        tips = []
        for digit in ['Index', 'Middle', 'Ring', 'Little']:
            ids = np.flatnonzero(groups[side + digit + '3'] > .5)
            tips.extend(int(i) for i in ids if rest[i, 2] < rest[ids, 2].min() + .007)
        patches['fingertips_' + suffix] = {'indices': sorted(tips), 'state': 'observed', 'rationale': 'Distal four-finger skin, independent of wrist/head joint proxies.'}
        if item['id'] == '6560':
            candidates = sum(groups[side+d+str(j)] for d in ['Index','Middle','Ring','Little'] for j in [1,2,3])>.5
            patches['finger_floor_' + suffix] = patch_from_low_quads(item, candidates, [0, 15, 30, 45, 60],
                'Actual floor-facing extended finger pads. Separate palm-core patches verify palm support rather than accepting only curled fingertips.')
            patches['finger_floor_' + suffix]['state'] = 'supported'
            patches['palm_floor_' + suffix] = patch_from_low_quads(item, groups[side+'Hand']>.8, [0,30,60],
                'Actual palm/heel-of-hand skin, measured separately from the extended fingers and visually reviewed on the shared floor. Illustration contact, not a pressure/load claim.')
            patches['palm_floor_' + suffix]['state'] = 'supported'
    return patches


frames_by_id = {x['id']: ([0, 15, 30, 45, 60, 75, 90, 105, 120, 135, 150] if x['display_mode'] == 'stretch'
                                 else [round(x['frames'] * f / 8) for f in range(9)]) for x in items}
tolerances = {'support_maximum_closest_gap_m': .012, 'support_near_band_m': .012,
              'support_minimum_near_fraction': .20, 'maximum_floor_penetration_m': .004,
              'minimum_airborne_foot_clearance_m': .05, 'maximum_hand_skin_penetration_m': .003,
              'planted_foot_maximum_centroid_drift_m': .005,
              'loop_joint_translation_error_m': .0001, 'loop_quaternion_angle_degrees': .01}
landmarks = {'schema_version': '1.0.0', 'source_index_attribute': '_SOURCE_INDEX', 'source_vertices': 10582,
             'rest_coordinates_sha256': rest_sha, 'coordinate_frame': 'Blender world metres; Three.js conversion[x,z,-y].',
             'floor': {'point': [0, 0, 0], 'normal': [0, 0, 1]}, 'tolerances': tolerances,
             'tolerance_basis': 'Authored illustration-QA bands at1.8m character scale. Reuses the accepted first-batch12mm curved-support band,20% near fraction and4mm maximum skin-floor penetration. Not medical landmarks, safe joint limits, clinical technique or physical contact certification.',
             'exercises': {item['id']: {'sample_frames': frames_by_id[item['id']], 'patches': make_landmarks(item)} for item in items}}
(OUT / 'landmarks.json').write_text(json.dumps(landmarks, indent=2) + '\n')

# Separate scalar fields propagate the frozen source patches through native subdivision.
attributes = []
for identifier, exercise in landmarks['exercises'].items():
    for name, patch in exercise['patches'].items():
        key = 'QA_Next_' + identifier + '_' + name
        attribute = body.data.attributes.new(name=key, type='FLOAT', domain='POINT')
        values = np.zeros(len(rest), np.float32)
        values[patch['indices']] = 1
        attribute.data.foreach_set('value', values)
        attributes.append(attribute.name)
lower_weights = sum(groups[name] for name in ['Hips', 'LeftUpLeg', 'LeftLeg', 'LeftFoot', 'LeftToeBase',
                                             'RightUpLeg', 'RightLeg', 'RightFoot', 'RightToeBase'])
for name, mask in [('head', rest[:, 2] > 1.59), ('lower_body', (rest[:, 2] < 1.025) & (lower_weights > .5))]:
    attribute = body.data.attributes.new(name='QA_Next_' + name, type='FLOAT', domain='POINT')
    attribute.data.foreach_set('value', mask.astype(np.float32))
    attributes.append(attribute.name)

samples, bone_samples, references, failures = [], [], [], []
full_references=[]
timing_report=[]
loop_report = []
try:
    for item in items:
        identifier = item['id']
        patches = landmarks['exercises'][identifier]['patches']
        endpoints = {}
        phase_positions={}
        for path in ['dq_cage']:
            first_centroids = {}
            for frame in frames_by_id[identifier]:
                set_pose(item, frame, path)
                ev, mesh, positions = evaluated()
                try:
                    masks = {}
                    for name in [*patches, 'head', 'lower_body']:
                        key = 'QA_Next_' + (identifier + '_' if name in patches else '') + name
                        values = np.empty(len(mesh.vertices), np.float32)
                        mesh.attributes[key].data.foreach_get('value', values)
                        masks[name] = values > .35
                    # Vertex area gives a useful curved-patch near-contact area estimate.
                    areas = np.zeros(len(mesh.vertices), np.float64)
                    for polygon in mesh.polygons:
                        areas[list(polygon.vertices)] += polygon.area / len(polygon.vertices)
                    contacts = {}
                    for name, patch in patches.items():
                        points = positions[masks[name]]
                        z = points[:, 2]
                        near = abs(z) <= tolerances['support_near_band_m']
                        weight = areas[masks[name]]
                        centroid = points[:, :2].mean(0)
                        first_centroids.setdefault(name, centroid.copy())
                        contacts[name] = {**stats(z), 'vertices': len(points),
                                          'fraction_near_floor': float(near.mean()),
                                          'near_floor_area_m2': float(weight[near].sum()),
                                          'patch_area_m2': float(weight.sum()),
                                          'tangential_centroid_drift_m': float(np.linalg.norm(centroid - first_centroids[name]))}
                        if patch['state'] == 'supported':
                            if z.min() > tolerances['support_maximum_closest_gap_m'] or near.mean() < tolerances['support_minimum_near_fraction']:
                                failures.append(f'{identifier} {path} frame{frame} {name} support gap/fraction')
                        elif patch['state'] == 'lifted' and z.min() < tolerances['minimum_airborne_foot_clearance_m']:
                            failures.append(f'{identifier} {path} frame{frame} {name} airborne clearance')
                        if patch['state'] == 'supported' and (name.startswith('heel_') or name.startswith('sole_') or name.startswith('foot_edge_')) and contacts[name]['tangential_centroid_drift_m'] > tolerances['planted_foot_maximum_centroid_drift_m']:
                            failures.append(f'{identifier} {path} frame{frame} {name} planted drift')
                    clearances = {}
                    for region in ['head', 'lower_body']:
                        faces = [tuple(p.vertices) for p in mesh.polygons if all(masks[region][i] for i in p.vertices)]
                        bvh = BVHTree.FromPolygons([Vector(p) for p in positions], faces, all_triangles=False)
                        for part,suffix in [(part,suffix) for part in (['hand','forearm'] if region=='lower_body' else ['hand']) for suffix in ['L','R']]:
                            values = []
                            for point in positions[masks[part+'_' + suffix]]:
                                closest, normal, _, distance = bvh.find_nearest(Vector(point))
                                candidate_inside = (Vector(point) - closest).dot(normal) < 0
                                is_inside = candidate_inside and inside_surface(bvh, Vector(point))
                                values.append(-distance if is_inside else distance)
                            v = np.array(values)
                            points = positions[masks[part+'_' + suffix]]
                            clearances[part+'_' + suffix + '_vs_' + region] = {'signed_min_m': float(v.min()), 'deepest_penetration_m': max(0., float(-v.min())),
                                'worst_point_world_m': points[int(v.argmin())].tolist()}
                            if v.min() < -tolerances['maximum_hand_skin_penetration_m']:
                                failures.append(f'{identifier} {path} frame{frame} {part}_{suffix} {region} penetration')
                    angles = {}
                    for side in ['Left', 'Right']:
                        hip = rig.pose.bones[side + 'UpLeg'].head
                        knee = rig.pose.bones[side + 'Leg'].head
                        ankle = rig.pose.bones[side + 'Foot'].head
                        shoulder = rig.pose.bones[side + 'Arm'].head
                        elbow = rig.pose.bones[side + 'ForeArm'].head
                        wrist = rig.pose.bones[side + 'Hand'].head
                        angles[side + '_knee_internal_degrees'] = math.degrees((hip - knee).angle(ankle - knee))
                        angles[side + '_elbow_internal_degrees'] = math.degrees((shoulder - elbow).angle(wrist - elbow))
                    axis = rig.pose.bones['Neck'].head - rig.pose.bones['Hips'].head
                    angles['hip_to_neck_floor_inclination_degrees'] = math.degrees(math.atan2(axis.z, math.hypot(axis.x, axis.y)))
                    if identifier == '5265' and frame in [item['frames'] // 4, 3 * item['frames'] // 4]:
                        near, opposite = ('Left', 'Right') if frame == item['frames'] // 4 else ('Right', 'Left')
                        knee = rig.pose.bones[near + 'Leg'].head
                        same_distance = (knee - rig.pose.bones[near + 'ForeArm'].head).length
                        cross_distance = (knee - rig.pose.bones[opposite + 'ForeArm'].head).length
                        forward = rig.pose.bones[opposite + 'Arm'].head.y < rig.pose.bones[near + 'Arm'].head.y
                        angles['opposite_elbow_to_raised_knee_m'] = cross_distance
                        angles['same_elbow_to_raised_knee_m'] = same_distance
                        if not (forward and cross_distance + .03 < same_distance):
                            failures.append(f'{identifier} {path} frame{frame} opposite elbow/knee twist direction')
                    row = {'id': identifier, 'frame': frame, 'seconds': frame / 30, 'path': path,
                           'global_floor_z': float(positions[:, 2].min()), 'patches': contacts,
                           'hand_surface_clearances': clearances, 'angles': angles}
                    samples.append(row)
                    if row['global_floor_z'] < -tolerances['maximum_floor_penetration_m']:
                        failures.append(f'{identifier} {path} frame{frame} body-floor penetration')
                    if path == 'dq_cage':
                        phase_positions[frame]=positions.copy()
                        if frame in [0,30,75,120,150]:full_references.append({'id':identifier,'frame':frame,'positions':np.round(positions,8).tolist()})
                        joints = {pb.name: list((rig.matrix_world @ pb.matrix).translation) for pb in rig.pose.bones}
                        bone_samples.append({'id': identifier, 'frame': frame, 'joints': joints})
                        references.append({'id': identifier, 'frame': frame, 'global_floor_z': row['global_floor_z'],
                                           'patches': {name: {'indices': patch['indices'], 'min_z': contacts[name]['min_z'], 'max_z': contacts[name]['max_z']} for name, patch in patches.items()}})
                        if frame in [0, item['frames']]:
                            endpoints[frame] = {pb.name: (pb.matrix.copy(), pb.matrix.to_quaternion()) for pb in rig.pose.bones}
                finally:
                    ev.to_mesh_clear()
        hold=max(float(np.max(abs(phase_positions[f]-phase_positions[60]))) for f in [75,90])
        loop_skin=float(np.max(abs(phase_positions[0]-phase_positions[150])))
        movement=float(np.max(np.linalg.norm(phase_positions[0]-phase_positions[60],axis=1)))
        action=bpy.data.actions[item['action']]
        duration=(action.frame_range[1]-action.frame_range[0])/30
        timing_report.append({'id':identifier,'duration_seconds':duration,'hold_interval_seconds':[2,3],'hold_max_skin_drift_m':hold,'loop_max_skin_drift_m':loop_skin,'hinge_max_vertex_travel_m':movement})
        if duration!=5 or hold>0.000002 or loop_skin>0.000002 or movement<.05:failures.append(identifier+' compressed-demo timing/hold/loop surface witness')
        first, last = endpoints[0], endpoints[item['frames']]
        error = max((first[k][0].translation - last[k][0].translation).length for k in first)
        angles = [math.degrees(first[k][1].rotation_difference(last[k][1]).angle) for k in first]
        # Quaternion sign equivalence is a closed loop, not a360degree discontinuity.
        angle = max(min(value, abs(360 - value)) for value in angles)
        loop_report.append({'id': identifier, 'joint_translation_error_m': error, 'quaternion_angle_degrees': angle})
        if error > tolerances['loop_joint_translation_error_m'] or angle > tolerances['loop_quaternion_angle_degrees']:
            failures.append(identifier + ' loop closure')
finally:
    for name in attributes:
        body.data.attributes.remove(body.data.attributes[name])
    for modifier, viewport, render in modifiers:
        modifier.show_viewport, modifier.show_render = viewport, render

source_sha = hashlib.sha256((P / (options.asset + '.blend')).read_bytes()).hexdigest() if not options.procedural else None
report = {'ok': not failures, 'source_sha256': source_sha, 'rest_coordinates_sha256': rest_sha,
          'checks': f'{sum(len(frames_by_id[i["id"]]) for i in items)} phase poses per skin path; local source-index support skin, signed hand/head/lower-body distances, surface areas/fractions, drift, loop endpoints.',
          'platform': bpy.app.version_string, 'tolerances': tolerances, 'failures': failures,
          'loops': loop_report, 'timing':timing_report,'samples': samples, 'review_status': 'measured_prototype_requires_visual_and_runtime_review',
          'limitations': 'Sampled illustration QA. No clinical/medical certification or continuous collision proof. Native source and runtime reference use original-binding PreserveVolume DQ cage. CorrectiveSmooth and Multires are disabled; optional subdivision is separate review, not contact truth.'}
(OUT / 'surface-contact-report.json').write_text(json.dumps(report, indent=2) + '\n')
(OUT / 'pose-samples.json').write_text(json.dumps(bone_samples, indent=2) + '\n')
(OUT / 'runtime-surface-reference.json').write_text(json.dumps({'source_sha256': source_sha, 'coordinate_frame': 'Blender world metres', 'source_index_attribute': '_SOURCE_INDEX', 'source_vertices': 10582, 'samples': references}, separators=(',', ':')) + '\n')

if not options.procedural and not options.surface_only:
    sys.path.insert(0, str(Path.home() / '.codex/skills/blender-asset-qa/scripts'))
    import qa_check
    import ninety_qa_observer as warning_observer
    warning_observer.install(qa_check)
    qa_rows = []
    for item in items:
        for frame in ([0, 30, 75, 150] if item['display_mode'] == 'stretch' else [0, item['frames'] // 4, 3 * item['frames'] // 4]):
            for path in ['dq_cage']:
                set_pose(item, frame, path)
                qa = qa_check.run(objects=[body.name], profile='game')
                qa_rows.append({'id': item['id'], 'frame': frame, 'path': path, 'qa': qa, 'warning_locations': qa_check.QA_WARNING_DETAILS,'error_locations':qa_check.QA_ERROR_DETAILS})
                if not qa['pass']:
                    failures.append(f"{item['id']} {path} frame{frame} asset-QA errors: {qa['errors']}")
    (OUT / 'asset-qa.json').write_text(json.dumps({'source_sha256': source_sha, 'pass': all(r['qa']['pass'] for r in qa_rows), 'samples': qa_rows}, indent=2) + '\n')
    (OUT / 'pose-verification.json').write_text(json.dumps({'ok': not failures, 'source_sha256': source_sha, 'failures': failures, 'surface_samples': len(samples), 'geometry_checks': len(qa_rows), 'loops': loop_report, 'review_status': 'requires_primary_and_user_review'}, indent=2) + '\n')
print(json.dumps({'ok': not failures, 'failures': failures, 'surface_samples': len(samples), 'loops': loop_report}), flush=True)
if not options.procedural and not options.surface_only:
    assert not failures, failures
    import gzip, shutil
    with gzip.open(P/'ninety-dq-reference.json.gz','wt',encoding='utf-8') as handle:
        json.dump({'source_sha256':source_sha,'source_vertices':10582,'skinning':'dualQuaternion','coordinate_frame':'Blender world metres, original vertex-ID order, all non-Armature modifiers disabled','samples':full_references},handle,separators=(',',':'))
    for name in ['landmarks','surface-contact-report','pose-samples','runtime-surface-reference','asset-qa','pose-verification']:
        shutil.copy2(OUT/(name+'.json'),P/('ninety-'+name+'.json'))
