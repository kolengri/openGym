"""Original supine air-bicycle targets on the unchanged source rig."""
import math
import numpy as np
from mathutils import Matrix, Quaternion, Vector
_palm_normals={}
POSTURE={'pelvis':-90,'spine':-100,'chest_base':-70,'chest_curl':10,
         'neck_base':-65,'neck_curl':10,'twist':30}


def source_palm_normal(a,side,sign):
    if side not in _palm_normals:
        group=a.body.vertex_groups[side+'Hand'].index
        points=np.array([v.co[:] for v in a.body.data.vertices if any(g.group==group and g.weight>.6 for g in v.groups)])
        _,axes=np.linalg.eigh(np.cov(points.T))
        normal=Vector(axes[:,0])
        if normal.x*sign>0:normal=-normal
        _palm_normals[side]=normal
    return _palm_normals[side]


def segment_rotation(a, bone, direction, source_axis, target_axis):
    original = a.tails[bone] - a.heads[bone]
    rotation = (a.frame(direction, target_axis) @
                a.frame(original, source_axis).transposed()).to_quaternion()
    return rotation @ a.rest[bone].to_quaternion()


def pose(a, runtime_frame, root_z=.12,posture=None):
    swing = math.sin(2 * math.pi * runtime_frame / 150)
    effort = swing * swing
    root = Vector((0, 0, root_z))
    # Pelvis/lower lumbar remain supine; the upper trunk curls and rotates.
    desired={}
    posture=POSTURE if posture is None else posture
    pitches=[posture['pelvis'],posture['spine'],posture['chest_base']+posture['chest_curl']*effort,
             posture['neck_base']+posture['neck_curl']*effort,posture['neck_base']+posture['neck_curl']*effort]
    for index,name in enumerate(['Hips','Spine','Spine1','Neck','Head']):
        parent=a.rig.data.bones[name].parent
        head=root if parent is None else desired[parent.name] @ a.rest[parent.name].inverted() @ a.heads[name]
        # Axial rotation starts in the upper trunk. Twisting the lower lumbar
        # frame rolled a flank onto the floor and lifted the actual pelvis.
        twist=0 if index<2 else posture['twist']*swing
        rotation=a.rx(pitches[index]) @ Quaternion(Vector((0,0,1)),math.radians(twist)) @ a.rest[name].to_quaternion()
        desired[name]=Matrix.Translation(head) @ rotation.to_matrix().to_4x4()
    for side, sign in [('Left', 1), ('Right', -1)]:
        pedal = sign * swing
        flex, extension = max(0, pedal), max(0, -pedal)
        hip = desired['Hips'] @ a.rest['Hips'].inverted() @ a.heads[side+'UpLeg']
        # Start: raised thighs and horizontal shins, exactly 90-degree knee.
        thigh = Vector((sign * .025 * flex, .80 * flex - .98 * extension,
                        1 - .40 * flex - .80 * extension)).normalized()
        calf = Vector((0, -1, -.08 * flex + .015 * extension)).normalized()
        knee = hip + thigh * a.length[side+'UpLeg']
        ankle = knee + calf * a.length[side+'Leg']
        rest_thigh = a.tails[side+'UpLeg']-a.heads[side+'UpLeg']
        rest_calf = a.tails[side+'Leg']-a.heads[side+'Leg']
        original_axis = rest_thigh.cross(rest_calf).normalized()
        target_axis = thigh.cross(calf).normalized()
        for bone, start, end in [(side+'UpLeg', hip, knee), (side+'Leg', knee, ankle)]:
            rotation = segment_rotation(a, bone, end-start, original_axis, target_axis)
            desired[bone] = Matrix.Translation(start) @ rotation.to_matrix().to_4x4()
        foot_q = a.foot_rotation(side, -18 + 5 * extension)
        desired[side+'Foot'] = Matrix.Translation(ankle) @ (foot_q @ a.rest[side+'Foot'].to_quaternion()).to_matrix().to_4x4()
        toe = desired[side+'Foot'] @ a.rest[side+'Foot'].inverted() @ a.heads[side+'ToeBase']
        desired[side+'ToeBase'] = Matrix.Translation(toe) @ (foot_q @ a.rest[side+'ToeBase'].to_quaternion()).to_matrix().to_4x4()

        shoulder = side+'Shoulder'
        sh = desired['Spine1'] @ a.rest['Spine1'].inverted() @ a.heads[shoulder]
        chest_q = desired['Spine1'].to_quaternion() @ a.rest['Spine1'].to_quaternion().inverted()
        desired[shoulder] = Matrix.Translation(sh) @ (chest_q @ a.rest[shoulder].to_quaternion()).to_matrix().to_4x4()
        arm_head = desired[shoulder] @ a.rest[shoulder].inverted() @ a.heads[side+'Arm']
        head_matrix = desired['Head'] @ a.rest['Head'].inverted()
        head_q = head_matrix.to_quaternion()
        # Separate relaxed palms cradle the occiput; fingers point toward crown.
        wrist = head_matrix @ Vector((sign*.208, .130, 1.66))
        lateral = head_q @ Vector((sign, 0, 0))
        back = head_q @ Vector((0, 1, 0))
        up = head_q @ Vector((0, 0, 1))
        open_pole = arm_head + lateral * .55 + back * .03 + up * .04
        approach=max(0,-sign*swing)
        opposite='Right' if side=='Left' else 'Left'
        cross_hip=desired['Hips'] @ a.rest['Hips'].inverted() @ a.heads[opposite+'UpLeg']
        cross_thigh=Vector((-sign*.025*approach,.80*approach,1-.40*approach)).normalized()
        cross_knee=cross_hip+cross_thigh*a.length[opposite+'UpLeg']
        # The active elbow follows the opposite knee while the hand stays at
        # the occiput; this is shoulder adduction, not neck traction.
        pole=open_pole.lerp(cross_knee,.85*approach)
        hand_name=side+'Hand'
        hand_q=(a.frame(-lateral+up*.12, -back) @
                a.frame(a.tails[hand_name]-a.heads[hand_name], source_palm_normal(a,side,sign)).transposed()).to_quaternion() @ a.rest[hand_name].to_quaternion()
        palm_direction=(hand_q @ a.rest[hand_name].to_quaternion().inverted()) @ (a.heads[side+'Middle1']-a.heads[hand_name])
        # Keep the fixed occiput hand placement while limiting the authored
        # palm/forearm deviation. This35deg staging bound is not a clinical limit.
        def elbow_at(amount):
            return a.two_joint(arm_head,wrist,a.length[side+'Arm'],a.length[side+'ForeArm'],open_pole.lerp(pole,amount))[0]
        if (wrist-elbow_at(1)).angle(palm_direction)>math.radians(35):
            lower,upper=0.,1.
            for _ in range(18):
                middle=(lower+upper)/2
                if (wrist-elbow_at(middle)).angle(palm_direction)<=math.radians(35):lower=middle
                else:upper=middle
            pole=open_pole.lerp(pole,lower)
        elbow, wrist = a.two_joint(arm_head, wrist, a.length[side+'Arm'],
                                   a.length[side+'ForeArm'], pole)
        for bone, start, end in [(side+'Arm', arm_head, elbow), (side+'ForeArm', elbow, wrist)]:
            # Minimal rotations are solved in the moving chest frame. Solving
            # against world-rest directions leaves a supine arm axially upright
            # and shears the shoulder even when joint endpoints are correct.
            rotation = chest_q @ a.orient(bone, chest_q.inverted() @ (end-start))
            desired[bone] = Matrix.Translation(start) @ rotation.to_matrix().to_4x4()
        desired[side+'Hand'] = Matrix.Translation(wrist) @ hand_q.to_matrix().to_4x4()

    for name, (head, tail, parent, digit, index) in a.finger_specs.items():
        direction = (tail-head).normalized()
        normal = Vector((-1 if name.startswith('Left') else 1, 0, 0))
        axis = a.rest[name].to_3x3().inverted() @ direction.cross(normal).normalized()
        angle = ([6, 10, 7] if digit != 'Thumb' else [5, 8, 5])[index]
        desired[name] = desired[parent] @ a.rest[parent].inverted() @ a.rest[name] @ Quaternion(axis, math.radians(angle)).to_matrix().to_4x4()
    for bone in a.rig.pose.bones:
        parent = bone.parent.name if bone.parent else None
        bone.matrix_basis = a.rest[bone.name].inverted() @ (a.rest[parent] @ desired[parent].inverted() if parent else Matrix.Identity(4)) @ desired[bone.name]
    return desired
