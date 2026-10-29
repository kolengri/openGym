"""Original CC0 across-chest stretch, source-indexed linear runtime cage."""
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector

P = Path(__file__).resolve().parent
sys.path.insert(0, str(P.parents[2] / 'batch-003'))
import authoring as a
sys.path.insert(0, str(P))
import shoulder_weights

EXPECTED = '227ede3fc31d1a2b47ff40f20a4a7288fe7bb36179add23bae953993826c8b7b'
parser = argparse.ArgumentParser()
parser.add_argument('--final', action='store_true')
opts = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
assert a.initialize() == EXPECTED
body, rig, scene = a.body, a.rig, a.scene
weight_report = shoulder_weights.apply(body)
weight_report.update({'original_binding': EXPECTED, 'new_binding': a.binding_hash(body, rig)})
(P/'local-weight-report.json').write_text(json.dumps(weight_report, indent=2)+'\n')


def amount(t):
    # Source order: first place the active arm, then apply the opposite forearm.
    # On release, remove the supporting forearm before lowering the active arm.
    return a.ease(min(t, 5-t) / 1.30)


def transported(name, parent_name, parent_q, direction):
    base = parent_q @ a.rest[parent_name].to_quaternion().inverted() @ a.rest[name].to_quaternion()
    return (base @ Vector((0, 1, 0))).rotation_difference(direction.normalized()) @ base


def pose(t):
    u = amount(t)
    d = {name: matrix.copy() for name, matrix in a.rest.items()}
    # The left clavicle moves forward slightly without elevating the shoulder.
    sh = 'LeftShoulder'
    sh_q = a.rest[sh].to_quaternion().slerp(a.orient(sh, (.18, -.095, .002)), u)
    d[sh] = Matrix.Translation(a.heads[sh]) @ sh_q.to_matrix().to_4x4()
    shoulder = d[sh] @ a.rest[sh].inverted() @ a.heads['LeftArm']
    target = Vector((-.80, -.60, -.045)).normalized()
    upper_q = a.rest['LeftArm'].to_quaternion().slerp(a.orient('LeftArm', target), u)
    # Raise through anterior space before horizontal adduction, avoiding a
    # shortest-arc sweep through the pectoral surface during the middle entry.
    original_dir = upper_q @ Vector((0, 1, 0))
    anterior_arc = .60*math.sin(math.pi*u)
    clear_dir = (original_dir + Vector((0, -anterior_arc, 0))).normalized()
    upper_q = original_dir.rotation_difference(clear_dir) @ upper_q
    upper_q = Quaternion(upper_q @ Vector((0, 1, 0)), math.radians(75*u)) @ upper_q
    upper_dir = upper_q @ Vector((0, 1, 0))
    elbow = shoulder + upper_dir * a.length['LeftArm']
    d['LeftArm'] = Matrix.Translation(shoulder) @ upper_q.to_matrix().to_4x4()
    # A transported elbow frame avoids the independent forearm-roll singularity.
    base_lower = upper_q @ a.rest['LeftArm'].to_quaternion().inverted() @ a.rest['LeftForeArm'].to_quaternion()
    lower_dir = (base_lower @ Vector((0, 1, 0))).lerp(target, u).normalized()
    lower_q = transported('LeftForeArm', 'LeftArm', upper_q, lower_dir)
    wrist = elbow + lower_dir * a.length['LeftForeArm']
    d['LeftForeArm'] = Matrix.Translation(elbow) @ lower_q.to_matrix().to_4x4()
    left_hand_q = lower_q @ a.rest['LeftForeArm'].to_quaternion().inverted() @ a.rest['LeftHand'].to_quaternion()
    # Continue the palm with the forearm, retaining the original relaxed wrist frame.
    left_hand_dir = (left_hand_q @ Vector((0, 1, 0))).lerp(target, .75*u).normalized()
    left_hand_q = (left_hand_q @ Vector((0, 1, 0))).rotation_difference(left_hand_dir) @ left_hand_q
    d['LeftHand'] = Matrix.Translation(wrist) @ left_hand_q.to_matrix().to_4x4()

    v = a.ease((min(t, 5-t)-1.25)/.75)
    sh = 'RightShoulder'
    sh_q = a.rest[sh].to_quaternion().slerp(a.orient(sh, (-.18, -.08, .002)), v)
    d[sh] = Matrix.Translation(a.heads[sh]) @ sh_q.to_matrix().to_4x4()
    shoulder = d[sh] @ a.rest[sh].inverted() @ a.heads['RightArm']
    end_wrist = Vector((-.055, -.3481640625, 1.50))
    wrist = a.heads['RightHand'].lerp(end_wrist, v)
    # The hand travels medially while still below the active arm, then the
    # forearm rises in anterior space and settles back onto its contact patch.
    medial = a.ease(v*2)
    wrist.x = a.heads['RightHand'].x*(1-medial)+end_wrist.x*medial
    wrist.y -= .22 * math.sin(math.pi*v)
    pole = a.heads['RightForeArm'].lerp(Vector((-.05, -.28, 1.15)), v)
    elbow, wrist = a.two_joint(shoulder, wrist, a.length['RightArm'], a.length['RightForeArm'], pole)
    upper_q = a.orient('RightArm', elbow-shoulder)
    lower_q = transported('RightForeArm', 'RightArm', upper_q, wrist-elbow)
    d['RightArm'] = Matrix.Translation(shoulder) @ upper_q.to_matrix().to_4x4()
    d['RightForeArm'] = Matrix.Translation(elbow) @ lower_q.to_matrix().to_4x4()
    hand_q = lower_q @ a.rest['RightForeArm'].to_quaternion().inverted() @ a.rest['RightHand'].to_quaternion()
    d['RightHand'] = Matrix.Translation(wrist) @ hand_q.to_matrix().to_4x4()
    # Loose fingers; the support is the forearm, never a wrist-gripping hand.
    for name, (head, tail, parent, digit, index) in a.finger_specs.items():
        sign = 1 if name.startswith('Left') else -1
        bend_axis = (tail-head).normalized().cross(Vector((-sign, 0, 0))).normalized()
        local_axis = a.rest[name].to_3x3().inverted() @ bend_axis
        angle = [8, 12, 8][index] if digit != 'Thumb' else [2, 4, 3][index]
        d[name] = d[parent] @ a.rest[parent].inverted() @ a.rest[name] @ Quaternion(local_axis, math.radians(angle)).to_matrix().to_4x4()
    for pb in rig.pose.bones:
        parent = pb.parent.name if pb.parent else None
        pb.matrix_basis = a.rest[pb.name].inverted() @ (a.rest[parent] @ d[parent].inverted() if parent else Matrix.Identity(4)) @ d[pb.name]
    bpy.context.view_layer.update()


scene.frame_start, scene.frame_end = 1, 151
rig.animation_data_create()
act = bpy.data.actions.new('Exercise_1980')
act.use_fake_user = True
rig.animation_data.action = act
for frame in range(151):
    scene.frame_set(frame+1)
    pose(frame/30)
    for pb in rig.pose.bones:
        pb.keyframe_insert('location', frame=frame+1)
        pb.keyframe_insert('rotation_quaternion', frame=frame+1)
for layer in act.layers:
    for strip in layer.strips:
        for bag in strip.channelbags:
            for fc in bag.fcurves:
                for key in fc.keyframe_points:
                    key.interpolation = 'LINEAR'
attr = body.data.attributes.get('_SOURCE_INDEX') or body.data.attributes.new('_SOURCE_INDEX', 'FLOAT', 'POINT')
attr.data.foreach_set('value', np.arange(len(body.data.vertices), dtype=np.float32))
assert a.binding_hash(body, rig) == weight_report['new_binding']
for modifier in body.modifiers:
    modifier.show_viewport = modifier.show_render = modifier.type == 'ARMATURE'
    if modifier.type == 'ARMATURE':
        modifier.use_deform_preserve_volume = False

scene.render.engine = 'BLENDER_WORKBENCH'
scene.render.resolution_x, scene.render.resolution_y = 840, 1000
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGBA'
scene.render.film_transparent = True
shade = scene.display.shading
shade.light = 'STUDIO'
shade.color_type = 'MATERIAL'
shade.show_shadows = False
shade.show_cavity = False
shade.show_specular_highlight = False
scene.view_settings.view_transform = 'Standard'
scene.view_settings.look = 'None'
camdata = bpy.data.cameras.new('ReviewCamera')
cam = bpy.data.objects.new('ReviewCamera', camdata)
scene.collection.objects.link(cam)
scene.camera = cam
camdata.type = 'ORTHO'
CAMERAS = [
    {'label': 'left_posterior_shoulder', 'position': [3.8, 5, 2.1], 'target': [0, -.05, .86], 'scale': 3.4},
    {'label': 'front_forearm_contact', 'position': [1.8, -5, 2.0], 'target': [0, -.08, .86], 'scale': 3.4},
]


def render(name, frame, position, target=(0, -.05, .86), width=2.0, wire=False):
    scene.frame_set(frame+1)
    cam.location = position
    cam.rotation_euler = (Vector(target)-cam.location).to_track_quat('-Z', 'Y').to_euler()
    camdata.ortho_scale = width
    wire_ob = None
    if wire:
        wire_ob = body.copy()
        wire_ob.data = body.data.copy()
        scene.collection.objects.link(wire_ob)
        material = bpy.data.materials.new('ReviewWire')
        material.diffuse_color = (.025, .025, .025, 1)
        wire_ob.data.materials.clear()
        wire_ob.data.materials.append(material)
        wm = wire_ob.modifiers.new('ReviewWire', 'WIREFRAME')
        wm.thickness, wm.offset = .00045, 1
    scene.render.filepath = str(P/name)
    bpy.ops.render.render(write_still=True)
    if wire_ob:
        mesh = wire_ob.data
        bpy.data.objects.remove(wire_ob, do_unlink=True)
        bpy.data.meshes.remove(mesh)


for label, frame in [('start', 0), ('entry', 45), ('hold', 75)]:
    for view, position in [('side', (5, 0, 1.4)), ('oblique', (3.8, -5, 2.0)), ('rear', (2.5, 5, 1.8))]:
        render(f'early-{label}-{view}.png', frame, position)
render('early-hold-contact.png', 75, (1.6, -5, 1.8), (0, -.16, 1.40), .77)
scene.frame_set(1)
cam.location = CAMERAS[0]['position']
cam.rotation_euler = (Vector(CAMERAS[0]['target'])-cam.location).to_track_quat('-Z', 'Y').to_euler()
camdata.ortho_scale = CAMERAS[0]['scale']/1.65
bpy.ops.wm.save_as_mainfile(filepath=str(P/'source.blend'))
(P/'cameras.json').write_text(json.dumps(CAMERAS, indent=2)+'\n')
samples = []
for frame in [0, 15, 30, 45, 60, 75, 90, 105, 120, 135, 150]:
    scene.frame_set(frame+1)
    bpy.context.view_layer.update()
    samples.append({'id': '1980', 'frame': frame, 'joints': {pb.name: list(rig.matrix_world@pb.head) for pb in rig.pose.bones}})
(P/'pose-samples.json').write_text(json.dumps(samples, indent=2)+'\n')
print('EARLY_PROOF_READY', str(P))
if not opts.final:
    sys.exit(0)
render('hold-wire.png', 75, (3.8, -5, 2.0), wire=True)
scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(P/'source.blend'))
bpy.ops.object.select_all(action='DESELECT')
body.select_set(True)
rig.select_set(True)
bpy.context.view_layer.objects.active = rig
result = bpy.ops.export_scene.gltf(filepath=str(P/'motion.glb'), export_format='GLB', use_selection=True,
    export_animations=True, export_animation_mode='ACTIONS', export_force_sampling=True,
    export_frame_range=True, export_frame_step=1, export_skins=True, export_all_influences=False,
    export_apply=False, export_attributes=True, export_materials='EXPORT', export_vertex_color='NONE',
    export_anim_slide_to_zero=True, export_rest_position_armature=True, export_influence_nb=4,
    export_cameras=False, export_lights=False, export_yup=True)
assert result == {'FINISHED'}
print('EXPORTED', str(P/'motion.glb'))
