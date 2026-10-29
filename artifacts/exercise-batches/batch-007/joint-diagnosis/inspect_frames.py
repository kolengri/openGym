"""Read-only matrix evidence for the inherited kneeling collar binding."""
from pathlib import Path
import hashlib
import json
import math
import sys

import bpy
import numpy as np
from mathutils import Matrix, Vector

P = Path(__file__).resolve().parent
F = P.parent / "kneeling-family"
source = F / "joint5-source.blend"
expected = "99b2084976b01f73ec126f88cb7f5616cca7f63264781df0fbeeb076ca936d3c"
assert hashlib.sha256(source.read_bytes()).hexdigest() == expected
bpy.ops.wm.open_mainfile(filepath=str(source))
sys.path.insert(0, "/Users/kolengri/.codex/skills/blender-core/scripts")
import env_report

environment = env_report.run()
body = bpy.data.objects["SK_BlenderStudioHuman"]
rig = bpy.data.objects["RIG_BlenderStudioHuman"]
scene = bpy.context.scene
rig.animation_data.action = bpy.data.actions["Exercise_4365"]
scene.frame_set(76)
bpy.context.view_layer.update()
names = [g.name for g in body.vertex_groups]
W = np.zeros((len(body.data.vertices), len(names)))
for vertex in body.data.vertices:
    for group in vertex.groups:
        W[vertex.index, group.group] = group.weight
original = W.copy()
binding4 = json.loads((F / "binding4-report.json").read_text())
binding3 = json.loads((F / "fold3-binding-report.json").read_text())
for row in binding4["vertices"]:
    original[row["id"]] = 0
    for name, value in row["before"].items():
        original[row["id"], names.index(name)] = value
for row in binding3["edits"]:
    original[row["source_index"]] = 0
    for name, value in row["original"].items():
        original[row["source_index"], names.index(name)] = value
R = np.array([v.co[:] for v in body.data.vertices])
D = np.array([
    rig.pose.bones[name].matrix @ rig.data.bones[name].matrix_local.inverted()
    for name in names
])
A = np.einsum("vb,bij->vij", W, D[:, :3, :3])
AO = np.einsum("vb,bij->vij", original, D[:, :3, :3])
X = np.einsum("vij,vj->vi", A, R) + W @ D[:, :3, 3]
XO = np.einsum("vij,vj->vi", AO, R) + original @ D[:, :3, 3]

def row_weights(weights, i):
    return {names[k]: float(weights[i, k]) for k in np.flatnonzero(weights[i] > 1e-8)}

def degrees(q):
    angle = math.degrees(q.angle)
    return min(angle, 360 - angle)

frames = []
virtual_pose = {pb.name: pb.matrix.copy() for pb in rig.pose.bones}
for name, parent in [
    ("LeftArm", "LeftShoulder"),
    ("RightArm", "RightShoulder"),
    ("LeftUpLeg", "Hips"),
    ("RightUpLeg", "Hips"),
]:
    pb = rig.pose.bones[name]
    base = (rig.pose.bones[parent].matrix.to_quaternion()
            @ rig.data.bones[parent].matrix_local.to_quaternion().inverted()
            @ rig.data.bones[name].matrix_local.to_quaternion())
    direction = (pb.tail - pb.head).normalized()
    carried = ((base @ Vector((0, 1, 0))).rotation_difference(direction) @ base)
    actual = pb.matrix.to_quaternion()
    virtual_pose[name] = Matrix.Translation(pb.head) @ carried.to_matrix().to_4x4()
    frames.append({
        "bone": name,
        "parent": parent,
        "actual_vs_parent_carried_minimum_swing_twist_degrees": degrees(actual.rotation_difference(carried)),
        "same_bone_axis_error": float(((actual @ Vector((0, 1, 0))) - direction).length),
        "minimum_swing_axis_error": float(((carried @ Vector((0, 1, 0))) - direction).length),
        "parent_deform_angle_degrees": degrees(
            (rig.pose.bones[parent].matrix @ rig.data.bones[parent].matrix_local.inverted()).to_quaternion()),
        "actual_relative_parent_deform_angle_degrees": degrees(
            ((rig.pose.bones[parent].matrix @ rig.data.bones[parent].matrix_local.inverted()).to_quaternion().inverted()
             @ (pb.matrix @ rig.data.bones[name].matrix_local.inverted()).to_quaternion())),
        "carried_relative_parent_deform_angle_degrees": degrees(
            ((rig.pose.bones[parent].matrix @ rig.data.bones[parent].matrix_local.inverted()).to_quaternion().inverted()
             @ (virtual_pose[name] @ rig.data.bones[name].matrix_local.inverted()).to_quaternion())),
    })

for name, parent in [(side + child, side + root)
                     for side in ["Left", "Right"]
                     for child, root in [("ForeArm", "Arm"), ("Leg", "UpLeg")]]:
    pb = rig.pose.bones[name]
    base = (virtual_pose[parent].to_quaternion()
            @ rig.data.bones[parent].matrix_local.to_quaternion().inverted()
            @ rig.data.bones[name].matrix_local.to_quaternion())
    direction = (pb.tail - pb.head).normalized()
    carried = (base @ Vector((0, 1, 0))).rotation_difference(direction) @ base
    virtual_pose[name] = Matrix.Translation(pb.head) @ carried.to_matrix().to_4x4()
DV = np.array([virtual_pose[name] @ rig.data.bones[name].matrix_local.inverted()
               for name in names])
AV = np.einsum("vb,bij->vij", W, DV[:, :3, :3])
AVO = np.einsum("vb,bij->vij", original, DV[:, :3, :3])

witnesses = []
for i in [4287, 9583, 3141, 8398, 3323, 8580, 8690, 3432]:
    current_s = np.linalg.svd(A[i])[1]
    original_s = np.linalg.svd(AO[i])[1]
    carried_s = np.linalg.svd(AV[i])[1]
    carried_original_s = np.linalg.svd(AVO[i])[1]
    witnesses.append({
        "id": i,
        "basis": R[i].tolist(),
        "current_weights": row_weights(W, i),
        "original_weights": row_weights(original, i),
        "current_singular_values": current_s.tolist(),
        "original_singular_values": original_s.tolist(),
        "current_condition": float(current_s.max() / current_s.min()),
        "original_condition": float(original_s.max() / original_s.min()),
        "parent_carried_current_weights_singular_values": carried_s.tolist(),
        "parent_carried_current_weights_condition": float(carried_s.max() / carried_s.min()),
        "parent_carried_original_weights_singular_values": carried_original_s.tolist(),
        "parent_carried_original_weights_condition": float(carried_original_s.max() / carried_original_s.min()),
        "virtual_original_minus_current_posed_m": (XO[i] - X[i]).tolist(),
        "virtual_original_minus_current_length_m": float(np.linalg.norm(XO[i] - X[i])),
    })

report = {
    "source_sha256": expected,
    "environment": environment,
    "scope": "No saved mesh, bone, action, binding or modifier edits; original weights reconstructed in NumPy from existing receipts.",
    "actual_frame": 76,
    "frames": frames,
    "witnesses": witnesses,
}
raw_source = P.parents[2] / "bodyweight-five" / "bodyweight-five.blend"
report["original_source_sha256"] = hashlib.sha256(raw_source.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(raw_source))
raw_body = bpy.data.objects["SK_BlenderStudioHuman"]
actual_original = np.zeros_like(original)
for vertex in raw_body.data.vertices:
    for group in vertex.groups:
        actual_original[vertex.index, names.index(raw_body.vertex_groups[group.group].name)] = group.weight
report["reconstructed_original_weight_max_error_against_original_blend"] = float(abs(actual_original - original).max())
report["basis_max_error_against_original_blend"] = float(abs(np.array([v.co[:] for v in raw_body.data.vertices]) - R).max())
assert report["reconstructed_original_weight_max_error_against_original_blend"] < 1e-7
assert report["basis_max_error_against_original_blend"] == 0
(P / "frame-binding-evidence.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps({"frames": frames, "weight_reference_error": report["reconstructed_original_weight_max_error_against_original_blend"],
                  "witness_conditions": [{"id": w["id"], "current": w["current_condition"],
                  "parent_carried": w["parent_carried_current_weights_condition"], "original": w["original_condition"]} for w in witnesses]}, indent=2))
