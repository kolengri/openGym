"""Shared original-rig authoring helpers for independent batch003 assets.

Reuse the accepted rig math without executing historical guarded entrypoints.
Call initialize() in each isolated Blender process, then access module globals.
"""
import ast
import bpy
import hashlib
import json
import math
import re
import struct
from pathlib import Path
import numpy as np
from mathutils import Matrix, Quaternion, Vector

P = Path(__file__).resolve().parent
SOURCE = P.parents[1] / 'bodyweight-five/bodyweight-five.blend'
SOURCE_SHA = 'fbf635733118dc190fdb3cefabcde7fe4367bbccfa40aa3495a2ab2e7537d070'

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

def initialize():
    global body, rig, scene, rest, heads, tails, length, coords, finger_specs
    assert sha(SOURCE) == SOURCE_SHA, 'Accepted source changed'
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
        match = re.fullmatch('(Left|Right)(Little|Ring|Middle|Index|Thumb)([123])', bone.name)
        if match:
            finger_specs[bone.name] = (bone.head_local.copy(), bone.tail_local.copy(), bone.parent.name, match[2], int(match[3]) - 1)
    helper = SOURCE.parent / 'build_motion.py'
    names = ['V', 'rx', 'rz', 'ease', 'cycle', 'frame', 'orient', 'two_joint', 'foot_rotation', 'sole_height', 'palm_rotation', 'palm_height']
    tree = ast.parse(helper.read_text())
    exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names], type_ignores=[]), str(helper), 'exec'), globals())
    for pb in rig.pose.bones:
        pb.rotation_mode = 'QUATERNION'
        pb.matrix_basis = Matrix.Identity(4)
    scene.render.fps = 30
    scene.render.fps_base = 1
    mat = bpy.data.materials.new('Neutral_Untextured_CC0')
    mat.diffuse_color = (0.6, 0.62, 0.64, 1)
    bsdf = next((n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'))
    bsdf.inputs['Base Color'].default_value = (0.6, 0.62, 0.64, 1)
    bsdf.inputs['Roughness'].default_value = 1
    bsdf.inputs['Specular IOR Level'].default_value = 0
    body.data.materials.clear()
    body.data.materials.append(mat)
    return binding_hash(body, rig)

def torso(root, pitches, bend=0, twist=0):
    desired = {}
    for (i, bone) in enumerate(['Hips', 'Spine', 'Spine1', 'Neck', 'Head']):
        parent = rig.data.bones[bone].parent
        h = root if parent is None else desired[parent.name] @ rest[parent.name].inverted() @ heads[bone]
        factor = [0, 0.55, 1, 1, 1][i]
        q = rx(pitches[i]) @ Quaternion(V((0, 1, 0)), math.radians(bend * factor)) @ Quaternion(V((0, 0, 1)), math.radians(twist * factor))
        desired[bone] = Matrix.Translation(h) @ (q @ rest[bone].to_quaternion()).to_matrix().to_4x4()
    return desired
