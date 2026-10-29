"""Curated still QA views, never animation frames or delivery media."""
import argparse
import bpy
import json
import math
import sys
from pathlib import Path
from mathutils import Vector

P = Path(__file__).resolve().parent
args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
parser = argparse.ArgumentParser()
parser.add_argument('--draft', action='store_true')
parser.add_argument('--procedural', action='store_true')
parser.add_argument('--ids', nargs='+')
parser.add_argument('--views', nargs='+', choices=['oblique', 'side', 'rear'])
parser.add_argument('--source', type=Path, default=P / 'ninety-repaired.blend')
parser.add_argument('--output-dir', type=Path)
parser.add_argument('--prefix', default='')
parser.add_argument('--dq', action='store_true')
parser.add_argument('--ninety-sign', type=int, choices=[-1, 1], default=1)
parser.add_argument('--time', type=float)
parser.add_argument('--cage', action='store_true')
parser.add_argument('--corrective', action='store_true')
options = parser.parse_args(args)
if options.procedural:
    sys.path.insert(0, str(P))
    import ninety_pose as author
    author.initialize()
    if (P/'ninety-contact-parameters.json').exists():author.CONTACT_PARAMETERS=json.loads((P/'ninety-contact-parameters.json').read_text())['parameters']
    author.NINETY_KNEE_SIGN = options.ninety_sign
    author.metadata()
else:
    bpy.ops.wm.open_mainfile(filepath=str(options.source))
body = bpy.data.objects['SK_BlenderStudioHuman']
rig = bpy.data.objects['RIG_BlenderStudioHuman']
next(m for m in body.modifiers if m.type == 'ARMATURE').use_deform_preserve_volume = True
if options.dq:
    next(m for m in body.modifiers if m.type == 'ARMATURE').use_deform_preserve_volume = True
if options.cage:
    for m in body.modifiers:
        m.show_viewport = m.show_render = m.type == 'ARMATURE'
if options.corrective:
    sys.path.insert(0, str(P / 'repair-90'))
    import volume_corrective
scene = bpy.context.scene
scene.render.engine = 'BLENDER_WORKBENCH'
scene.render.resolution_x = 600
scene.render.resolution_y = 600
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.render.film_transparent = True
scene.view_settings.view_transform = 'Standard'
shade = scene.display.shading
shade.light = 'STUDIO'
shade.studiolight_rotate_z = .5
shade.color_type = 'MATERIAL'
shade.show_shadows = False
shade.show_cavity = False
shade.show_specular_highlight = False
shade.show_object_outline = False
camdata = bpy.data.cameras.new('QA_Camera')
camera = bpy.data.objects.new('QA_Camera', camdata)
scene.collection.objects.link(camera)
scene.camera = camera
camdata.type = 'ORTHO'
camdata.ortho_scale = 1.90
floor_mesh = bpy.data.meshes.new('QA_Checker_Floor')
vertices, faces = [], []
for y in range(-10, 11):
    for x in range(-10, 11):
        i = len(vertices)
        vertices.extend([(x * .12, y * .12, -.002), ((x + 1) * .12, y * .12, -.002),
                         ((x + 1) * .12, (y + 1) * .12, -.002), (x * .12, (y + 1) * .12, -.002)])
        faces.append((i, i + 1, i + 2, i + 3))
floor_mesh.from_pydata(vertices, [], faces)
floor = bpy.data.objects.new('QA_Temporary_Floor_Not_Exported', floor_mesh)
scene.collection.objects.link(floor)
for value in [.19, .25]:
    material = bpy.data.materials.new('QA_Checker_' + str(value))
    material.diffuse_color = (value, value, value, 1)
    floor.data.materials.append(material)
for i, polygon in enumerate(floor_mesh.polygons):
    polygon.material_index = ((i // 21) + i % 21) % 2
mat = bpy.data.materials.new('QA_Wire')
mat.diffuse_color = (.035, .045, .055, 1)
outdir = options.output_dir or (P / 'trials' if options.draft else P / 'qa/stills')
outdir.mkdir(parents=True, exist_ok=True)
metadata = json.loads((P / 'ninety-clips.json').read_text())
measurements = []
for item in metadata:
    identifier = item['id']
    if options.ids and identifier not in options.ids:
        continue
    index = 60 if identifier == '5265' else 45 if identifier in ['4007', '6428'] else 60
    if options.time is not None:
        index = round(options.time * 30)
    if options.procedural:
        author.make_pose(item, index / 30)
    else:
        rig.animation_data.action = bpy.data.actions[item['action']]
        scene.frame_set(index + 1)
    if options.corrective:
        volume_corrective.set_values(body, index / 30)
    bpy.context.view_layer.update()
    ev = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = ev.to_mesh()
    measurements.append({'id': identifier, 'frame': index, 'min_z': min(v.co.z for v in mesh.vertices),
                         'joints': {b.name: list(b.head) for b in rig.pose.bones if not any(s in b.name for s in ['Index', 'Middle', 'Ring', 'Little', 'Thumb'])}})
    ev.to_mesh_clear()
    views = [('oblique', (3.4, -5, 2.5)), ('side', (5, 0, .42)), ('rear', (-1.5, 5, 1.5))]
    if options.views:
        views = [view for view in views if view[0] in options.views]
    elif options.draft:
        views = views[:1]
    for view, position in views:
        if not options.draft and options.time is None:
            view_index = index if view == 'oblique' else 0 if view == 'side' else (75 if item['display_mode'] == 'stretch' else 3 * item['frames'] // 4)
            if options.procedural:
                author.make_pose(item, view_index / 30)
            else:
                scene.frame_set(view_index + 1)
            if options.corrective:
                volume_corrective.set_values(body, view_index / 30)
            bpy.context.view_layer.update()
        target = Vector((0, .06 if identifier == '5265' else -.01, .42))
        camera.location = position
        camera.rotation_euler = (target - camera.location).to_track_quat('-Z', 'Y').to_euler()
        scene.render.filepath = str(outdir / f'{options.prefix}{identifier}-{view}-solid.png')
        bpy.ops.render.render(write_still=True)
        if not options.draft:
            # Evaluated cage wire as a temporary QA overlay; source remains unchanged.
            saved = [(m, m.show_viewport, m.show_render) for m in body.modifiers]
            for modifier, _, _ in saved:
                modifier.show_viewport = modifier.type == 'ARMATURE'
                modifier.show_render = modifier.type == 'ARMATURE'
            bpy.context.view_layer.update()
            ev = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
            wiremesh = bpy.data.meshes.new_from_object(ev)
            wire = bpy.data.objects.new('QA_Evaluated_DQ_Wire', wiremesh)
            scene.collection.objects.link(wire)
            wire.data.materials.clear()
            wire.data.materials.append(mat)
            modifier = wire.modifiers.new('QA_Wireframe', 'WIREFRAME')
            modifier.thickness = .0008
            modifier.use_replace = True
            body.hide_render = True
            scene.render.filepath = str(outdir / f'{identifier}-{view}-wire.png')
            bpy.ops.render.render(write_still=True)
            body.hide_render = False
            bpy.data.objects.remove(wire, do_unlink=True)
            for modifier, viewport, render in saved:
                modifier.show_viewport = viewport
                modifier.show_render = render
(outdir / (options.prefix + 'pose-inspection.json')).write_text(json.dumps(measurements, indent=2) + '\n')
print(json.dumps(measurements))
