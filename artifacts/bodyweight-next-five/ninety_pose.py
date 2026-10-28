"""Author the two repaired90/90 actions on the unchanged CC0 rig.

Run with Blender 5.2.3. Only this directory is written. No restricted media used.
"""
import ast
import bpy
import hashlib
import json
import math
import re
import struct
import sys
from pathlib import Path

import numpy as np
from mathutils import Matrix, Quaternion, Vector

P = Path(__file__).resolve().parent
SOURCE = P.parent / 'bodyweight-five/bodyweight-five.blend'
SOURCE_SHA = 'fbf635733118dc190fdb3cefabcde7fe4367bbccfa40aa3495a2ab2e7537d070'
IDS = ['10565', '6560']
NINETY_KNEE_SIGN = 1
CONTACT_PARAMETERS = None


def contact_parameters(hinge):
    if not CONTACT_PARAMETERS:
        return {'root_z': .1225-.007*hinge}
    rows=CONTACT_PARAMETERS
    lo=next((i for i in range(len(rows)-1) if rows[i]['hinge']<=hinge<=rows[i+1]['hinge']),len(rows)-2)
    a,b=rows[lo],rows[lo+1]
    u=(hinge-a['hinge'])/(b['hinge']-a['hinge'])
    return {k:a[k]*(1-u)+b[k]*u for k in a if k!='hinge'}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def binding_hash(body, rig):
    digest = hashlib.sha256()
    for vertex in body.data.vertices:
        digest.update(np.array(vertex.co, np.float32).tobytes())
        for group in vertex.groups:
            digest.update(struct.pack('<If', group.group, group.weight))
    for polygon in body.data.polygons:
        digest.update(np.array(polygon.vertices, np.int32).tobytes())
    for uv in body.data.uv_layers:
        a = np.empty(len(uv.data) * 2, np.float32)
        uv.data.foreach_get('uv', a)
        digest.update(uv.name.encode() + a.tobytes())
    for bone in rig.data.bones:
        digest.update(bone.name.encode() + np.array(bone.matrix_local, np.float32).tobytes())
    return digest.hexdigest()


def metadata():
    items = []
    for identifier in IDS:
        record = json.loads((P.parent.parent / 'catalogue/exercises' / f'{identifier}.json').read_text())
        stretch = identifier in ['10565', '6560']
        duration = 5.0 if stretch else 6.0 if identifier != '5265' else 8.0
        phases = ([{'start': 0, 'end': 2, 'label': 'Hinge forward over the front shin'},
                   {'start': 2, 'end': 3, 'label': 'Hold the hip stretch for 1 second'},
                   {'start': 3, 'end': 5, 'label': 'Return upright'}] if stretch else
                  [{'start': 0, 'end': duration / 4, 'label': 'Reach left heel' if identifier != '5265' else 'Left knee / right elbow'},
                   {'start': duration / 4, 'end': duration / 2, 'label': 'Return through center'},
                   {'start': duration / 2, 'end': 3 * duration / 4, 'label': 'Reach right heel' if identifier != '5265' else 'Right knee / left elbow'},
                   {'start': 3 * duration / 4, 'end': duration, 'label': 'Return through center'}])
        item = {'id': identifier, 'name': record['name'], 'duration': duration,
                'duration_seconds': duration, 'frames': round(duration * 30),
                'duration_frames': round(duration * 30), 'fps': 30,
                'action': 'Exercise_' + identifier, 'primary': [record['target']],
                'secondary': record['secondaryMuscles'], 'stretch': ([record['target']] + record['secondaryMuscles']) if stretch else [],
                'display_mode': 'stretch' if stretch else 'heat', 'camera': 'oblique', 'phases': phases,
                'source_roles': {'primary': [record['target']], 'secondary': record['secondaryMuscles']},
                'muscle_display_roles': {'primary': 'stretch_main' if stretch else 'main',
                                         'secondary': 'stretch_context' if stretch else 'additional'},
                'highlight_sides': {'glutes': ['L'], 'hip flexors': ['R']} if stretch else {},
                'side_note': 'Front leg is anatomical left; repeat on the mirrored side.' if stretch else 'Both sides alternate; both oblique sides are combined training-emphasis proxies.',
                'muscle_notice': 'Illustrative smooth surface emphasis; not EMG, physiological recruitment or true segmentation. Deep hip flexors/adductors/lumbar labels use surface proxies.' if stretch else 'Illustrative training emphasis; not measured phase recruitment. Both oblique sides represent the combined superficial/deep group.',
                'interpretation': '', 'review_status': 'authored_prototype_requires_user_review',
                'source_path': f'catalogue/exercises/{identifier}.json',
                'source_sha256': sha(P.parent.parent / 'catalogue/exercises' / f'{identifier}.json')}
        if identifier == '5265':
            item['interpretation'] = 'Authored seated balance on pelvic skin, torso about45degrees, feet airborne, alternating pedal/twist. Explicit prototype resolution of retained initial_body_support_unresolved source classifier flag.'
            item['arms'] = 'Open elbows, light fingers behind the occiput, hands do not pull the neck.'
        elif identifier == '4007':
            item['interpretation'] = 'Supine shoulder lift with fixed airborne approximately90degree hips/knees; alternating ipsilateral reach toward each heel.'
            item['arms'] = 'Open hands extend toward the raised heel; opposite hand remains alongside torso.'
        elif identifier == '6428':
            item['interpretation'] = 'Supine with both feet planted; shoulders stay slightly lifted while the trunk bends laterally to alternate near-heel reaches.'
            item['arms'] = 'Open hands reach beside the corresponding heel; palms face inward/down without a grip.'
        else:
            item['arms'] = 'Hands rest separately on the front knee and shin; an authored relaxed placement because the source does not specify it.' if identifier == '10565' else 'Both palms and extended fingers rest on the floor in front of the hips; elbows remain unlocked.'
            item['interpretation'] = 'One representative seated90/90 side;5second compressed demonstration with a1second preview hold. The source workout hold remains20–30seconds. The two sources describe substantially the same hip stretch.'
            item['preview_timing'] = {'compressed_demo': True, 'duration_seconds': 5, 'hold_seconds': 1, 'source_workout_hold_seconds': [20, 30]}
            item['asset'] = 'ninety-repaired'
            item['skinning'] = 'dualQuaternion'
        items.append(item)
    (P / 'ninety-clips.json').write_text(json.dumps(items, indent=2) + '\n')
    cameras = {}
    for item in items:
        stretch = item['display_mode'] == 'stretch'
        fitted_scale = {'5265': 2.84, '4007': 2.32, '6428': 2.57}.get(item['id'], 2.0)
        cameras[item['id']] = [
            {'label': 'Hip position and forward hinge' if stretch else 'Torso, hands and foot position',
             'position': [3.4, -5.0, 2.7] if stretch else [2, -3.5, 5],
             'target': [0, -.03, .42] if stretch else [0, 0, .35], 'scale': fitted_scale},
            {'label': 'Rear hip and floor supports' if stretch else 'Side profile and support plane',
             'position': [-4.5, 2.0 if stretch else .3, 1.65], 'target': [0, .0, .40], 'scale': 2.05}]
    # Retain primary-owned view refinements; pose repair must not undo them.
    if (P / 'ninety-camera-presets.json').exists():
        cameras.update(json.loads((P / 'ninety-camera-presets.json').read_text()))
    (P / 'ninety-camera-presets.json').write_text(json.dumps(cameras, indent=2) + '\n')
    return items


def initialize():
    global body, rig, scene, rest, heads, tails, length, coords, finger_specs
    assert sha(SOURCE) == SOURCE_SHA, 'Accepted source changed'
    for identifier in IDS:
        packet = json.loads((P.parent / 'exercise-batches/batch-002/contexts' / f'{identifier}.json').read_text())
        assert len(packet['baseline_requirements']) == 21
        assert not packet['readiness']['unresolved_source_blockers']
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
    body = bpy.data.objects['SK_BlenderStudioHuman']
    rig = bpy.data.objects['RIG_BlenderStudioHuman']
    scene = bpy.context.scene
    rig.animation_data_clear()
    for action in list(bpy.data.actions):
        bpy.data.actions.remove(action)
    for ob in list(bpy.data.objects):
        if ob not in [body, rig]:
            bpy.data.objects.remove(ob, do_unlink=True)
    rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
    heads = {b.name: b.head_local.copy() for b in rig.data.bones}
    tails = {b.name: b.tail_local.copy() for b in rig.data.bones}
    length = {b.name: b.length for b in rig.data.bones}
    coords = [v.co.copy() for v in body.data.vertices]
    finger_specs = {}
    for bone in rig.data.bones:
        match = re.fullmatch(r'(Left|Right)(Little|Ring|Middle|Index|Thumb)([123])', bone.name)
        if match:
            finger_specs[bone.name] = (bone.head_local.copy(), bone.tail_local.copy(), bone.parent.name, match[2], int(match[3]) - 1)
    # Import only established math helpers. Never execute the old guarded authoring entrypoint.
    helper = P.parent / 'bodyweight-five/build_motion.py'
    names = ['V', 'rx', 'rz', 'ease', 'cycle', 'frame', 'orient', 'two_joint', 'foot_rotation', 'sole_height', 'palm_rotation', 'palm_height']
    tree = ast.parse(helper.read_text())
    exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names], type_ignores=[]), str(helper), 'exec'), globals())
    for pb in rig.pose.bones:
        pb.rotation_mode = 'QUATERNION'
        pb.matrix_basis = Matrix.Identity(4)
    scene.render.fps = 30
    scene.render.fps_base = 1
    mat = bpy.data.materials.new('Neutral_Untextured_CC0')
    mat.diffuse_color = (.60, .62, .64, 1)
    bsdf = next(n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    bsdf.inputs['Base Color'].default_value = (.60, .62, .64, 1)
    bsdf.inputs['Roughness'].default_value = 1
    bsdf.inputs['Specular IOR Level'].default_value = 0
    body.data.materials.clear()
    body.data.materials.append(mat)
    return binding_hash(body, rig)


def torso(root, pitches, bend=0, twist=0, roll=0):
    desired = {}
    for i, bone in enumerate(['Hips', 'Spine', 'Spine1', 'Neck', 'Head']):
        parent = rig.data.bones[bone].parent
        h = root if parent is None else desired[parent.name] @ rest[parent.name].inverted() @ heads[bone]
        factor = [0, .55, 1, 1, 1][i]
        q = rx(pitches[i]) @ Quaternion(V((0, 1, 0)), math.radians(bend * factor)) @ Quaternion(V((0, 0, 1)), math.radians(twist * factor))
        if roll:
            q=Quaternion(V((0,1,0)),math.radians(roll))@q
        desired[bone] = Matrix.Translation(h) @ (q @ rest[bone].to_quaternion()).to_matrix().to_4x4()
    return desired


def seated_hand(side, direction):
    """Map the source palm's measured thin plane onto the floor plane.

    The hand bone points diagonally through the source sculpt. Its global-X
    proxy normal is not the actual palm plane, especially for the mirrored hand.
    """
    normal = V((-.895485, -.004443, -.445070)) if side == 'Left' else V((.896018, -.003273, -.444006))
    axis = (tails[side+'Hand']-heads[side+'Hand']).normalized()
    axis = (axis-normal*axis.dot(normal)).normalized()
    delta = (frame(direction, (0, 0, -1)) @ frame(axis, normal).transposed()).to_quaternion()
    return delta @ rest[side+'Hand'].to_quaternion(), normal


def make_pose(item, seconds):
    identifier = item['id']
    u = seconds / item['duration']
    swing = math.sin(2 * math.pi * u)
    stretch = item['display_mode'] == 'stretch'
    hinge = ease(seconds / 2) if seconds < 2 else 1.0 if seconds <= 3 else ease((5 - seconds) / 2)
    parameters=contact_parameters(hinge)
    if identifier == '5265':
        # Small support-height compensation follows the deformed pelvic skin,
        # rather than lifting the seated support off the plane during pedalling.
        desired = torso(V((0, .05, .090 + .012 * swing * swing)), [-80, -45, -30, -30, -30], twist=27 * swing)
    elif not stretch:
        desired = torso(V((0, .05, .0805 if identifier == '4007' else .104)), [-90, -77, -64, -63, -63], bend=26 * swing)
    else:
        pitch = 8 + 30 * hinge
        desired = torso(V((0, .04, parameters['root_z'])), [pitch, pitch, pitch, 3 + 26 * hinge, 25 * hinge],roll=parameters.get('pelvis_roll',0))
    for side, sign in [('Left', 1), ('Right', -1)]:
        hip = desired['Hips'] @ rest['Hips'].inverted() @ heads[side + 'UpLeg']
        if identifier == '5265':
            pedal = sign * swing
            q = foot_rotation(side, -5 + 10 * pedal)
            ankle_target = V((sign * .17, -.47 + .24 * pedal, .34 + .10 * pedal))
            knee, ankle = two_joint(hip, ankle_target, length[side + 'UpLeg'], length[side + 'Leg'], hip + V((sign * .05, -.25, .9)))
            normal = -(knee - hip).cross(ankle - knee).normalized() * sign
        elif identifier == '4007':
            knee = hip + V((sign * .025, -.025, 1)).normalized() * length[side + 'UpLeg']
            ankle = knee + V((0, -1, -.025)).normalized() * length[side + 'Leg']
            q = foot_rotation(side, -15)
            normal = -(knee - hip).cross(ankle - knee).normalized() * sign
        elif identifier == '6428':
            q = foot_rotation(side)
            ankle_target = V((sign * .16, -.44, sole_height(side, q) - .0015))
            knee, ankle = two_joint(hip, ankle_target, length[side + 'UpLeg'], length[side + 'Leg'], hip + V((0, -.2, .8)))
            normal = -(knee - hip).cross(ankle - knee).normalized() * sign
        else:
            thigh = V((.7071, -.7071, -.070)) if side == 'Left' else V((-1, 0, .005))
            calf = V((-.7071, -.7071, .015)) if side == 'Left' else V((0, 1, -.12))
            support_hip = V((sign * .105, .04, .095))
            support_knee = support_hip + thigh.normalized() * length[side + 'UpLeg']
            ankle_target = support_knee + calf.normalized() * length[side + 'Leg']
            ankle_target.z+=parameters.get('ankle_z_'+side,0)
            ankle_target.x+=parameters.get('ankle_x_'+side,0)
            ankle_target.y+=parameters.get('ankle_y_'+side,0)
            support_knee.z+=parameters.get('knee_pole_z_'+side,0)
            knee, ankle = two_joint(hip, ankle_target, length[side + 'UpLeg'], length[side + 'Leg'], support_knee)
            normal = -(knee - hip).cross(ankle - knee).normalized() * sign
            support_normal = -thigh.cross(calf).normalized() * sign
            q = orient(side + 'Foot', calf, support_normal) @ rest[side + 'Foot'].to_quaternion().inverted()
            if parameters.get('foot_roll_'+side,0):
                q=Quaternion(calf.normalized(),math.radians(parameters['foot_roll_'+side]))@q
        for bone, a, b in [(side + 'UpLeg', hip, knee), (side + 'Leg', knee, ankle)]:
            if stretch:
                # Map the actual source knee-flexion axis consistently on both
                # segments. A global-X proxy can inject avoidable axial roll.
                original_axis = (tails[side + 'UpLeg'] - heads[side + 'UpLeg']).cross(tails[side + 'Leg'] - heads[side + 'Leg']).normalized()
                target_axis = (knee - hip).cross(ankle - knee).normalized() * NINETY_KNEE_SIGN
                leg_q = (frame(b - a, target_axis) @ frame(tails[bone] - heads[bone], original_axis).transposed()).to_quaternion() @ rest[bone].to_quaternion()
            else:
                leg_q = orient(bone, b - a, normal)
            desired[bone] = Matrix.Translation(a) @ leg_q.to_matrix().to_4x4()
        desired[side + 'Foot'] = Matrix.Translation(ankle) @ (q @ rest[side + 'Foot'].to_quaternion()).to_matrix().to_4x4()
        toe = desired[side + 'Foot'] @ rest[side + 'Foot'].inverted() @ heads[side + 'ToeBase']
        desired[side + 'ToeBase'] = Matrix.Translation(toe) @ (q @ rest[side + 'ToeBase'].to_quaternion()).to_matrix().to_4x4()
        parent = 'Spine1'
        shoulder = side + 'Shoulder'
        sh = desired[parent] @ rest[parent].inverted() @ heads[shoulder]
        parent_q = desired[parent].to_quaternion() @ rest[parent].to_quaternion().inverted()
        depression = Quaternion(V((0, 1, 0)), math.radians(sign * 18)) if identifier == '6560' else Quaternion()
        desired[shoulder] = Matrix.Translation(sh) @ (parent_q @ depression @ rest[shoulder].to_quaternion()).to_matrix().to_4x4()
        armhead = desired[shoulder] @ rest[shoulder].inverted() @ heads[side + 'Arm']
        if identifier == '5265':
            hq = desired['Head'].to_quaternion() @ rest['Head'].to_quaternion().inverted()
            center = desired['Head'] @ rest['Head'].inverted() @ V((0, .01, 1.68))
            back = hq @ V((0, 1, 0))
            up = hq @ V((0, 0, 1))
            lateral = hq @ V((sign, 0, 0))
            wrist = center + lateral * .220 + back * .114 + up * .025
            hdir, hnormal = -lateral + up * .05, -back
            pole = armhead + lateral * .65 + back * .025 + up * .025
        elif identifier in ['4007', '6428']:
            reach = max(0, sign * swing)
            heel = ankle + q @ V((0, .075, -.065)) + V((sign * .12, 0, 0))
            # Fingers extend toward the heel; the wrist remains proximal to it.
            direction = (heel - armhead).normalized()
            near = heel - direction * .135
            relaxed = V((sign * .35, armhead.y - .34, armhead.z - (.09 if identifier == '4007' else .14)))
            wrist = relaxed.lerp(near, reach)
            if identifier == '6428':
                wrist.z += .01
            hdir = V((0, -1, .02)).lerp(direction, reach).normalized()
            hnormal = V((-sign, 0, -.15))
            pole = armhead + V((sign * .30, -.30, .14))
        elif identifier == '6560':
            hdir, hnormal = V((0, -1, -.15)), V((0, 0, -1))
            palm_q, _ = seated_hand(side, hdir)
            delta = palm_q @ rest[side+'Hand'].to_quaternion().inverted()
            palm_ids = [v.index for v in body.data.vertices if any(g.group == body.vertex_groups[side+'Hand'].index and g.weight > .8 for g in v.groups)]
            z = -min((delta @ (coords[i]-heads[side+'Hand'])).z for i in palm_ids)+.002
            wrist = V((.05 if side == 'Left' else -.22, -.25, z))
            pole = armhead + V((-.28 if side == 'Left' else sign * .12, -.35 if side == 'Left' else -.25, -.28))
        else:
            wrist = V((.40 if side == 'Left' else .09, -.24 if side == 'Left' else -.18, .18 if side == 'Left' else .20))
            target = V((.30 if side == 'Left' else .19, -.37 if side == 'Left' else -.29, .17 if side == 'Left' else .18))
            hdir, hnormal = (target - wrist).normalized(), V((0, 0, -1))
            pole = armhead + V((sign * .10, -.10, -.35))
        elbow, wrist = two_joint(armhead, wrist, length[side + 'Arm'], length[side + 'ForeArm'], pole)
        arm_q = orient(side + 'Arm', elbow - armhead)
        if identifier == '6560':
            source_axis=(tails[side+'Arm']-heads[side+'Arm']).cross(tails[side+'ForeArm']-heads[side+'ForeArm']).normalized()
            target_axis=(elbow-armhead).cross(wrist-elbow).normalized()
            elbow_frame_q=(frame(elbow-armhead,target_axis)@frame(tails[side+'Arm']-heads[side+'Arm'],source_axis).transposed()).to_quaternion()@rest[side+'Arm'].to_quaternion()
            # Retain the source shoulder volume while carrying a small part of
            # the true elbow-plane roll up the humerus. Full roll squares the
            # original DQ shoulder skin at this near-extended support pose.
            arm_q=arm_q.slerp(elbow_frame_q,.25)
        desired[side + 'Arm'] = Matrix.Translation(armhead) @ arm_q.to_matrix().to_4x4()
        hand_q = seated_hand(side, hdir)[0] if stretch else orient(side + 'Hand', hdir, hnormal)
        # Carry the palm's pronation through the forearm, rather than forcing
        # the entire twist into the wrist skin. Bone endpoints remain unchanged.
        hand_delta=hand_q@rest[side+'Hand'].to_quaternion().inverted()
        original_forearm=(tails[side+'ForeArm']-heads[side+'ForeArm']).normalized()
        hint=hand_delta@original_forearm
        forearm_q=hint.rotation_difference((wrist-elbow).normalized())@hand_delta@rest[side+'ForeArm'].to_quaternion()
        desired[side + 'ForeArm'] = Matrix.Translation(elbow) @ forearm_q.to_matrix().to_4x4()
        desired[side + 'Hand'] = Matrix.Translation(wrist) @ hand_q.to_matrix().to_4x4()
    for bone, (a, b, parent, digit, index) in finger_specs.items():
        parent_matrix = desired[parent] @ rest[parent].inverted()
        long = (b - a).normalized()
        normal = V((-1 if bone.startswith('Left') else 1, 0, 0))
        axis = rest[bone].to_3x3().inverted() @ long.cross(normal).normalized()
        angle = (-12 if digit=='Thumb' else 0) if identifier == '6560' else [3, 8, 5][index] if identifier == '5265' else [2, 4, 3][index]
        if identifier == '6560':
            # The source relaxed hand has bent distal axes even at zero curl.
            # Align the four finger segments to their proximal axis for a flat
            # resting palm; keep the thumb's authored opposition unchanged.
            proximal = bone[:-1] + '1'
            side = 'Left' if bone.startswith('Left') else 'Right'
            normal = seated_hand(side, (1, 0, 0))[1]
            flat = (tails[proximal]-heads[proximal]).normalized()
            flat = (flat-normal*flat.dot(normal)).normalized()
            # A flat palm has its knuckle centres above the floor-facing pads.
            # Lower the proximal phalanx toward the pad plane, then extend the
            # distal joints, rather than leaving all four fingertips floating.
            proximal_slope={'Index':.45,'Middle':.40,'Ring':.20,'Little':.20,'Thumb':0}[digit]
            flat = (flat + normal * ([proximal_slope, .10, 0][index] if digit!='Thumb' else 0)).normalized()
            straight = long.rotation_difference(flat)
            hdelta = desired[side+'Hand'] @ rest[side+'Hand'].inverted()
            a_world = parent_matrix @ a
            desired[bone] = Matrix.Translation(a_world) @ (hdelta.to_quaternion() @ straight @ rest[bone].to_quaternion()).to_matrix().to_4x4()
        else:
            desired[bone] = parent_matrix @ rest[bone] @ Quaternion(axis, math.radians(angle)).to_matrix().to_4x4()
    if 'LeftHipVolume' in rest:
        import hip_volume
        hip_volume.pose_helpers(sys.modules[__name__], desired)
    for pb in rig.pose.bones:
        parent = pb.parent.name if pb.parent else None
        pb.matrix_basis = rest[pb.name].inverted() @ (rest[parent] @ desired[parent].inverted() if parent else Matrix.Identity(4)) @ desired[pb.name]
    return desired


def main():
    # The original batch source/GLB are frozen for the three accepted motions.
    # All current90/90 authoring goes to the separate explicitly experimental asset.
    import runpy
    runpy.run_path(str(P / 'build_ninety_repaired.py'), run_name='__main__')


if __name__ == '__main__':
    main()
