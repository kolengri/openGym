"""Original above-head chest stretch; immutable CC0 mesh, binding and rest pose."""
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
sys.path.insert(0, str(P.parents[1]))
import authoring as a

EXPECTED = '227ede3fc31d1a2b47ff40f20a4a7288fe7bb36179add23bae953993826c8b7b'
args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
parser = argparse.ArgumentParser()
parser.add_argument('--final', action='store_true')
parser.add_argument('--normal-trial', action='store_true', help='Frozen experimental normal cache; not the accepted export.')
options = parser.parse_args(args)
assert a.initialize() == EXPECTED
body, rig, scene = a.body, a.rig, a.scene
REST = np.array([v.co[:] for v in body.data.vertices])
NATIVE = {m.name: (m.show_viewport, m.show_render, getattr(m, 'use_deform_preserve_volume', None)) for m in body.modifiers}
GRIP = {'wrist_halfspan': .159, 'row_offset': .014, 'normal_offset': .020,
        'finger_angles': [15, 60, 35], 'thumb_angles': [5, 25, 15]}


def amount(t):
    return a.ease(t / 2) if t < 2 else 1 if t <= 3 else a.ease((5 - t) / 2)


def pose(t):
    u = amount(t)
    # Only the upper thorax lifts. Pelvis and lumbar segment retain rest pitch.
    d = a.torso(a.heads['Hips'], [0, 0, -3.5 * u, -1.5 * u, 0])
    for side, sign in [('Left', 1), ('Right', -1)]:
        sh = side + 'Shoulder'
        sh_head = d['Spine1'] @ a.rest['Spine1'].inverted() @ a.heads[sh]
        sh_dir = a.Vector((sign * .18, -.005, .010 + .010 * u))
        d[sh] = Matrix.Translation(sh_head) @ a.orient(sh, sh_dir).to_matrix().to_4x4()
        shoulder = d[sh] @ a.rest[sh].inverted() @ a.heads[side + 'Arm']
        # Wide forward arc keeps the linked hands away from face and scalp.
        row_offset = GRIP['row_offset'] if sign == -1 else 0
        normal_offset = GRIP['normal_offset'] if sign == -1 else 0
        wrist = a.V((sign * GRIP['wrist_halfspan'],
            -.32*(1-u)+.075*u-.33*math.sin(math.pi*u)+row_offset*math.sin(u*math.pi/2)-normal_offset*math.cos(u*math.pi/2),
            1.09+.835*u+row_offset*math.cos(u*math.pi/2)+normal_offset*math.sin(u*math.pi/2)))
        pole = a.V((sign * (.56 - .12*u), -.10 + .12*u, 1.30 + .30*u))
        elbow, wrist = a.two_joint(shoulder, wrist, a.length[side+'Arm'], a.length[side+'ForeArm'], pole)
        upper, lower = side+'Arm', side+'ForeArm'
        upper_q = a.orient(upper, elbow-shoulder)
        d[upper] = Matrix.Translation(shoulder) @ upper_q.to_matrix().to_4x4()
        # Transport the forearm frame with the upper arm before applying elbow
        # flexion. This avoids an independent 180-degree shortest-arc roll.
        lower_base = upper_q @ a.rest[upper].to_quaternion().inverted() @ a.rest[lower].to_quaternion()
        lower_dir = lower_base @ a.V((0, 1, 0))
        lower_q = lower_dir.rotation_difference((wrist-elbow).normalized()) @ lower_base
        d[lower] = Matrix.Translation(elbow) @ lower_q.to_matrix().to_4x4()
        palm_normal = a.V((0, -math.cos(u*math.pi/2), math.sin(u*math.pi/2)))
        d[side+'Hand'] = Matrix.Translation(wrist) @ a.orient(side+'Hand', a.V((-sign, 0, 0)), palm_normal).to_matrix().to_4x4()
        # Feet, knees and hips retain the original grounded standing geometry.
        for suffix in ['UpLeg', 'Leg', 'Foot', 'ToeBase']:
            d[side+suffix] = a.rest[side+suffix].copy()
    # Articulated loose finger hook, with an offset between the two finger rows.
    # The linked grip is carried through the whole demonstration.
    for name, (h, tail, parent, digit, index) in a.finger_specs.items():
        sign = 1 if name.startswith('Left') else -1
        direction = (tail-h).normalized()
        palm = a.V((-sign, 0, 0))
        axis = a.rest[name].to_3x3().inverted() @ direction.cross(palm).normalized()
        angles = GRIP['finger_angles'] if digit != 'Thumb' else GRIP['thumb_angles']
        d[name] = d[parent] @ a.rest[parent].inverted() @ a.rest[name] @ Quaternion(axis, math.radians(angles[index])).to_matrix().to_4x4()
    for pb in rig.pose.bones:
        parent = pb.parent.name if pb.parent else None
        pb.matrix_basis = a.rest[pb.name].inverted() @ (a.rest[parent] @ d[parent].inverted() if parent else Matrix.Identity(4)) @ d[pb.name]
    bpy.context.view_layer.update()
    return d


scene.render.fps = 30
scene.frame_start, scene.frame_end = 1, 151
rig.animation_data_create()
act = bpy.data.actions.new('Exercise_1777')
act.use_fake_user = True
rig.animation_data.action = act
for f in range(151):
    scene.frame_set(f+1)
    pose(f/30)
    for pb in rig.pose.bones:
        pb.keyframe_insert('location', frame=f+1)
        pb.keyframe_insert('rotation_quaternion', frame=f+1)
for layer in act.layers:
    for strip in layer.strips:
        for bag in strip.channelbags:
            for fc in bag.fcurves:
                for key in fc.keyframe_points:
                    key.interpolation = 'LINEAR'
attr = body.data.attributes.get('_SOURCE_INDEX') or body.data.attributes.new('_SOURCE_INDEX', 'FLOAT', 'POINT')
attr.data.foreach_set('value', np.arange(len(body.data.vertices), dtype=np.float32))
assert a.binding_hash(body, rig) == EXPECTED

scene.render.engine = 'BLENDER_WORKBENCH'
scene.render.resolution_x, scene.render.resolution_y = 900, 1000
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
    {'label': 'chest_hands_oblique', 'position': [3.2, -5, 2.6], 'target': [0, 0, 1.04], 'scale': 3.8},
    {'label': 'overhead_reach_side', 'position': [4.8, .8, 2.3], 'target': [0, -.02, 1.04], 'scale': 3.8},
]


def camera(c):
    cam.location = c['position']
    cam.rotation_euler = (a.V(c['target'])-cam.location).to_track_quat('-Z', 'Y').to_euler()
    # Curated portrait proofs use the runtime panel's 1.65 height allowance.
    camdata.ortho_scale = c['scale']/1.65


def modifiers(linear):
    for m in body.modifiers:
        viewport, rendering, preserve = NATIVE[m.name]
        m.show_viewport = viewport if not linear else m.type == 'ARMATURE'
        m.show_render = rendering if not linear else m.type == 'ARMATURE'
        if m.type == 'ARMATURE':
            m.use_deform_preserve_volume = preserve if not linear else False


def render(name, f, c=0, linear=False, wire=False, close=False):
    scene.frame_set(f+1)
    modifiers(linear)
    camera(CAMERAS[c])
    if close:
        target = a.V((0, .07, 1.93))
        cam.location = (1.2, -1.8, 2.7)
        cam.rotation_euler = (target-cam.location).to_track_quat('-Z', 'Y').to_euler()
        camdata.ortho_scale = .58
    wire_ob = None
    if wire:
        wire_ob = body.copy()
        wire_ob.data = body.data.copy()
        scene.collection.objects.link(wire_ob)
        dark = bpy.data.materials.new('ReviewWire')
        dark.diffuse_color = (.025, .025, .025, 1)
        wire_ob.data.materials.clear()
        wire_ob.data.materials.append(dark)
        wm = wire_ob.modifiers.new('ReviewWire', 'WIREFRAME')
        wm.thickness, wm.offset = .0006, 1
    scene.render.filepath = str(P/name)
    bpy.ops.render.render(write_still=True)
    if wire_ob:
        mesh = wire_ob.data
        bpy.data.objects.remove(wire_ob, do_unlink=True)
        bpy.data.meshes.remove(mesh)
    modifiers(False)


for label, f in [('start', 0), ('peak', 75), ('return', 150)]:
    render(f'early-{label}-oblique.png', f)
render('early-peak-side.png', 75, 1)
render('early-peak-hands.png', 75, close=True)
render('early-entry-oblique.png', 45)
scene.frame_set(1)
camera(CAMERAS[0])
bpy.ops.wm.save_as_mainfile(filepath=str(P/'source.blend'))
(P/'cameras.json').write_text(json.dumps(CAMERAS, indent=2)+'\n')
samples = []
for f in [0, 15, 30, 45, 60, 75, 90, 105, 120, 135, 150]:
    scene.frame_set(f+1)
    bpy.context.view_layer.update()
    samples.append({'id': '1777', 'frame': f, 'joints': {pb.name: list(rig.matrix_world@pb.head) for pb in rig.pose.bones}})
(P/'pose-samples.json').write_text(json.dumps(samples, indent=2)+'\n')
print('EARLY_PROOF_READY', str(P))
if not options.final:
    sys.exit(0)
for label, f in [('start', 0), ('peak', 75), ('return', 150)]:
    render(f'linear-{label}-oblique.png', f, linear=True)
render('linear-peak-side.png', 75, 1, linear=True)
render('native-peak-wire.png', 75, wire=True)
render('linear-peak-wire.png', 75, linear=True, wire=True)
render('linear-peak-hands.png', 75, linear=True, close=True)
modifiers(True)
scene.frame_set(1)
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
if options.normal_trial:
    import runpy
    runpy.run_path(str(P/'patch_normals.py'), run_name='__main__')
