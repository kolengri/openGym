"""Frozen 3995 authoring route; importing this module does not touch bpy or files.

Only NumPy and Blender's mathutils are required. Coefficients contain the
accepted source endpoints and deterministic parallel-transport tables. This
module creates no objects, actions, shape keys, materials, files or processes.
"""
from pathlib import Path
import hashlib
import math
import numpy as np
from mathutils import Matrix, Quaternion, Vector

ARCHIVE_SHA256 = 'c0417c262db584c2e0f54844c7e7f683ffdfd02db2407f5330cf94ef8537202b'


def smooth(value):
    value = max(0., min(1., value))
    return value ** 3 * (value * (value * 6. - 15.) + 10.)


def polynomial(knots, coefficients, value):
    index = min(len(knots) - 2, max(0, int(np.searchsorted(knots, value, side='right')) - 1))
    delta = value - knots[index]
    c = coefficients[:, index]
    return ((c[0] * delta + c[1]) * delta + c[2]) * delta + c[3]


class CoherentRoute:
    """Evaluate desired armature-space matrices and the original held-key scalar.

    Quaternions in the archive use mathutils WXYZ order. Matrices are ordinary
    row-major 4x4 arrays acting on column vectors, in the source Z-up rig space.
    `pose(frame)` accepts fractional zero-based runtime frames and returns
    `(dict[bone_name, Matrix], original_p)`. The original scalar is sin² phase;
    geometry progress is normalized by the actual saved peak p*=.999561415….
    No interpolation, rebinding or alternate action is installed by this class.
    """

    def __init__(self, archive):
        archive = Path(archive)
        if hashlib.sha256(archive.read_bytes()).hexdigest() != ARCHIVE_SHA256:
            raise ValueError('Coherent 3995 route archive hash mismatch')
        with np.load(archive, allow_pickle=False) as data:
            self.data = {name: data[name].copy() for name in data.files}
        d = self.data
        self.names = d['bone_names'].tolist()
        self.ends = [{name: Matrix(values[i].tolist()) for i, name in enumerate(self.names)}
                     for values in d['endpoint_global_matrices']]
        self.peak = float(d['p_peak'])
        self.grid_count = len(d['transport_grid'])
        self.rest = {name: Matrix(d['bone_rest'][i].tolist()) for i, name in enumerate(self.names)}
        self.fingers = [(name, parent, Matrix(local.tolist()))
                        for name, parent, local in zip(d['finger_names'].tolist(),
                                                     d['finger_parents'].tolist(),
                                                     d['finger_local_matrices'])]
        self.tables = {}
        for side in ['Left', 'Right']:
            self.tables[side] = {
                'axis': [Vector(v) for v in d[side + '_wrist_axes']],
                'bend': [Vector(v) for v in d[side + '_wrist_bends']],
            }
            for part in ['Arm', 'ForeArm']:
                self.tables[side][part + '_axes'] = [Vector(v) for v in d[side + '_' + part + '_axes']]
                self.tables[side][part + '_frames'] = [Quaternion(v) for v in d[side + '_' + part + '_frames']]

    def transported(self, p, axes, values, axis):
        index = min(self.grid_count - 2, max(0, int(p * (self.grid_count - 1))))
        return axes[index].rotation_difference(axis) @ values[index]

    def pose(self, frame):
        original_p = math.sin(math.pi * (frame % 75.) / 75.) ** 2
        p = min(1., original_p / self.peak)
        if p <= 1e-14:
            return {name: matrix.copy() for name, matrix in self.ends[0].items()}, original_p
        if p >= 1. - 1e-12:
            return {name: matrix.copy() for name, matrix in self.ends[1].items()}, original_p
        d = {name: matrix.copy() for name, matrix in self.ends[0].items()}
        for side in ['Left', 'Right']:
            tables = self.tables[side]
            start, held = [endpoint[side + 'Shoulder'] for endpoint in self.ends]
            q = start.to_quaternion().slerp(held.to_quaternion(), p)
            location = start.translation.lerp(held.translation, smooth(p / .65))
            shoulder_matrix = Matrix.Translation(location) @ q.to_matrix().to_4x4()
            d[side + 'Shoulder'] = shoulder_matrix
            shoulder = shoulder_matrix @ self.rest[side + 'Shoulder'].inverted() @ Vector(self.data[side + '_arm_head'])
            t = float(polynomial(self.data[side + '_inverse_x'], self.data[side + '_inverse_c'], p))
            wrist = Vector(polynomial(self.data[side + '_spline_x'], self.data[side + '_spline_c'], t))
            axis = (wrist - shoulder).normalized()
            distance = (wrist - shoulder).length
            l1, l2 = self.data[side + '_lengths']
            if not abs(l1 - l2) < distance < l1 + l2 + 1e-5:
                raise ValueError('Coherent 3995 route left its frozen reachable domain')
            along = (l1 * l1 - l2 * l2 + distance * distance) / (2. * distance)
            bend = self.transported(p, tables['axis'], tables['bend'], axis)
            bend = Quaternion(axis, float(self.data[side + '_bend_twist']) * smooth(p)) @ bend
            bend -= axis * bend.dot(axis)
            bend.normalize()
            elbow = shoulder + axis * along + bend * math.sqrt(max(0., l1 * l1 - along * along))
            for part, head, tail in [('Arm', shoulder, elbow), ('ForeArm', elbow, wrist)]:
                direction = (tail - head).normalized()
                rotation = self.transported(p, tables[part + '_axes'], tables[part + '_frames'], direction)
                rotation = Quaternion(direction, float(self.data[side + '_' + part + '_twist']) * smooth(p)) @ rotation
                d[side + part] = Matrix.Translation(head) @ rotation.to_matrix().to_4x4()
            local = [endpoint[side + 'ForeArm'].to_quaternion().inverted() @
                     endpoint[side + 'Hand'].to_quaternion() for endpoint in self.ends]
            hand_rotation = d[side + 'ForeArm'].to_quaternion() @ local[0].slerp(local[1], smooth(p))
            d[side + 'Hand'] = Matrix.Translation(wrist) @ hand_rotation.to_matrix().to_4x4()
        for name, parent, local in self.fingers:
            d[name] = d[parent] @ local
        return d, original_p
