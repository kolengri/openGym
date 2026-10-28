"""Localized hand-texture cleanup and measured nose repair for the athlete asset.

Only this module's optional CLI loads a source asset and creates a review scene.
The public repair(body, rig, out_dir) function operates on existing rest geometry.
"""
from pathlib import Path
import json
import hashlib
import math
import sys

import bpy
import numpy as np
from mathutils import Vector


def _world_points(body):
    points = np.empty(len(body.data.vertices) * 3, dtype=np.float32)
    body.data.vertices.foreach_get('co', points)
    points = points.reshape(-1, 3)
    matrix = np.asarray(body.matrix_world, dtype=np.float64)
    return points @ matrix[:3, :3].T + matrix[:3, 3]


def _setup_review(body):
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_EEVEE'
    scene.render.resolution_x = 640
    scene.render.resolution_y = 640
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.film_transparent = False
    if scene.world is None:
        scene.world = bpy.data.worlds.new('HandFace_World')
    scene.world.color = (0.16, 0.16, 0.16)
    scene.view_settings.view_transform = 'Khronos PBR Neutral'
    for name, loc, energy, size in [
        ('HandFace_Key', (-2, -3, 3), 280, 2.0),
        ('HandFace_Fill', (2, -1, 2), 120, 1.5),
        ('HandFace_Rim', (0, 2, 3), 160, 1.5),
    ]:
        light = bpy.data.lights.new(name, 'AREA')
        light.energy, light.shape, light.size = energy, 'DISK', size
        obj = bpy.data.objects.new(name, light)
        scene.collection.objects.link(obj)
        obj.location = loc
        obj.rotation_euler = (Vector((0, 0, 1.15)) - obj.location).to_track_quat('-Z', 'Y').to_euler()
    cam_data = bpy.data.cameras.new('HandFace_Camera')
    cam_data.type = 'ORTHO'
    cam = bpy.data.objects.new('HandFace_Camera', cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    return scene, cam


def _render_views(body, out_dir, prefix):
    scene, cam = _setup_review(body)
    clay = bpy.data.materials.new('HandFace_ReviewClay')
    principled = next(n for n in clay.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    principled.inputs['Base Color'].default_value = (0.46, 0.30, 0.22, 1)
    principled.inputs['Roughness'].default_value = .55
    views = [
        ('hands-front', (.00, -.6, 0), (0, 0, .895), 1.04),
        ('hand-left', (.12, -.6, .04), (.435, .015, .856), .25),
        ('hand-right', (-.12, -.6, .04), (-.43, .02, .85), .25),
        ('hand-clay', (.12, -.6, .04), (.435, .015, .856), .25),
        ('hand-back', (.1, .6, .03), (.435, .015, .856), .25),
        ('face-front', (0, -.8, .02), (.014, -.01, 1.655), .33),
        ('face-profile', (.8, 0, .02), (.014, -.01, 1.655), .33),
        ('face-threequarter', (.5, -.8, .02), (.014, -.01, 1.655), .33),
    ]
    paths = []
    for name, direction, target, scale in views:
        cam.location = Vector(target) + Vector(direction)
        cam.rotation_euler = (Vector(target) - cam.location).to_track_quat('-Z', 'Y').to_euler()
        cam.data.ortho_scale = scale
        scene.view_layers[0].material_override = clay if name in ('face-profile', 'hand-clay') else None
        filepath = out_dir / f'handface-{prefix}-{name}.png'
        scene.render.filepath = str(filepath)
        bpy.ops.render.render(write_still=True)
        paths.append(str(filepath))
    scene.view_layers[0].material_override = None
    return paths


def _diagnose(body, rig, out_dir):
    points = _world_points(body)
    mesh = body.data
    report = {'vertex_count': len(mesh.vertices), 'triangle_count': len(mesh.polygons),
              'bounds_m': [points.min(0).tolist(), points.max(0).tolist()],
              'has_custom_normals': mesh.has_custom_normals, 'materials': []}
    for material in mesh.materials:
        report['materials'].append({'name': material.name, 'nodes': [
            {'type': n.type, 'name': n.name, 'image': n.image.name if n.type == 'TEX_IMAGE' and n.image else None,
             'links': [(l.from_socket.name, l.to_node.type, l.to_socket.name) for output in n.outputs for l in output.links]}
            for n in material.node_tree.nodes]})
    for side in ['LeftHand', 'RightHand']:
        group = body.vertex_groups.get(side)
        if group:
            selected = np.array([any(g.group == group.index and g.weight > .5 for g in v.groups) for v in mesh.vertices])
            report[side] = {'verts': int(selected.sum()), 'bounds': [points[selected].min(0).tolist(), points[selected].max(0).tolist()]}
    report['front_center_profile'] = []
    for z in np.arange(1.52, 1.74, .005):
        selected = (np.abs(points[:, 0] - .015) < .006) & (np.abs(points[:, 2] - z) < .003)
        if selected.any():
            front = points[selected][np.argmin(points[selected, 1])]
            report['front_center_profile'].append(front.tolist())
    out_dir.joinpath('handface-source-diagnostics.json').write_text(json.dumps(report, indent=2))
    return report


def _smoothstep(values):
    values = np.clip(values, 0.0, 1.0)
    return values * values * (3.0 - 2.0 * values)


def _hand_mask(points, rig):
    """Rest-space wrist planes; independent of mesh vertex order and garment edits."""
    mask = np.zeros(len(points), dtype=np.float64)
    for side in ('Left', 'Right'):
        wrist = rig.matrix_world @ rig.data.bones[side + 'Hand'].head_local
        elbow = rig.matrix_world @ rig.data.bones[side + 'ForeArm'].head_local
        direction = np.array((wrist - elbow).normalized())
        distance = (points - np.array(wrist)) @ direction
        side_mask = (np.abs(points[:, 0]) > .32) & (points[:, 2] < 1.0)
        side_mask &= points[:, 0] > 0 if side == 'Left' else points[:, 0] < 0
        mask = np.maximum(mask, _smoothstep((distance + .008) / .026) * side_mask)
    return mask


def _source_image(material, socket_name):
    shader = next(n for n in material.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    socket = shader.inputs[socket_name]
    if socket.is_linked and socket.links[0].from_node.type == 'TEX_IMAGE':
        return socket.links[0].from_node.image
    if socket_name == 'Normal' and socket.is_linked:
        normal = socket.links[0].from_node
        if normal.type == 'NORMAL_MAP' and normal.inputs['Color'].is_linked:
            image_node = normal.inputs['Color'].links[0].from_node
            if image_node.type == 'TEX_IMAGE':
                return image_node.image
    return None


def _math(nodes, links, operation, a, b=None):
    node = nodes.new('ShaderNodeMath')
    node.operation = operation
    for socket, value in zip(node.inputs, (a, b)):
        if value is None:
            continue
        if isinstance(value, (float, int)):
            socket.default_value = value
        else:
            links.new(value, socket)
    return node.outputs[0]


def _bake_hand_maps(body, rig, selected_faces, source_material, out_dir, ordinal):
    """Self-bake only copied hand triangles; never paint shared source images."""
    import bmesh
    source_color = _source_image(source_material, 'Base Color')
    source_normal = _source_image(source_material, 'Normal')
    if source_color is None:
        raise ValueError('Hand repair expects a direct image Base Color on the source Principled material; run before procedural muscle shading.')
    material = source_material.copy()
    material.name = f'HandFace_CleanSkin_{ordinal}'
    target_color = source_color.copy()
    target_color.name = f'HandFace_BaseColor_{ordinal}'
    target_color.colorspace_settings.name = 'sRGB'
    target_normal = source_normal.copy() if source_normal else None
    if target_normal:
        target_normal.name = f'HandFace_Normal_{ordinal}'
        target_normal.colorspace_settings.name = 'Non-Color'

    temp = body.copy()
    temp.data = body.data.copy()
    temp.name = 'HandFace_TemporaryBake'
    bpy.context.scene.collection.objects.link(temp)
    temp.hide_render = False
    temp.modifiers.clear()
    selected_set = set(selected_faces)
    bm = bmesh.new()
    bm.from_mesh(temp.data)
    bm.faces.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[face for face in bm.faces if face.index not in selected_set], context='FACES')
    bm.to_mesh(temp.data)
    bm.free()
    temp.data.materials.clear()
    bake_material = bpy.data.materials.new('HandFace_TemporaryShader')
    temp.data.materials.append(bake_material)
    for face in temp.data.polygons:
        face.material_index = 0
    # Recompute spatial mask after bmesh reindexing; no dependence on source IDs.
    temp_mask = _hand_mask(_world_points(temp), rig)
    attr = temp.data.color_attributes.new(name='HandFace_Blend', type='FLOAT_COLOR', domain='CORNER')
    colors = np.ones((len(temp.data.loops), 4), dtype=np.float32)
    loop_vertices = np.array([loop.vertex_index for loop in temp.data.loops])
    colors[:, :3] = temp_mask[loop_vertices, None]
    attr.data.foreach_set('color', colors.ravel())

    nodes, links = bake_material.node_tree.nodes, bake_material.node_tree.links
    nodes.clear()
    output = nodes.new('ShaderNodeOutputMaterial')
    emit = nodes.new('ShaderNodeEmission')
    links.new(emit.outputs[0], output.inputs['Surface'])
    source = nodes.new('ShaderNodeTexImage')
    source.image = source_color
    hsv = nodes.new('ShaderNodeSeparateColor')
    hsv.mode = 'HSV'
    links.new(source.outputs['Color'], hsv.inputs['Color'])
    # Gray/blue cloth contamination has much less chroma than clean hand skin.
    # Smooth mask avoids threshold outlines and preserves warm creases/nails.
    low_chroma = nodes.new('ShaderNodeMapRange')
    low_chroma.clamp = True
    low_chroma.interpolation_type = 'SMOOTHSTEP'
    links.new(hsv.outputs[1], low_chroma.inputs['Value'])
    low_chroma.inputs['From Min'].default_value = .30
    low_chroma.inputs['From Max'].default_value = .50
    low_chroma.inputs['To Min'].default_value = 1.0
    low_chroma.inputs['To Max'].default_value = 0.0
    attr_node = nodes.new('ShaderNodeVertexColor')
    attr_node.layer_name = attr.name
    factor = _math(nodes, links, 'MULTIPLY', low_chroma.outputs[0], attr_node.outputs['Color'])
    # Sample a robust warm source tone from unaffected hand triangles.
    pixels = np.empty(len(source_color.pixels), dtype=np.float32)
    source_color.pixels.foreach_get(pixels)
    pixels = pixels.reshape(source_color.size[1], source_color.size[0], 4)
    uv = body.data.uv_layers.active.data
    samples = []
    for index in selected_faces:
        face = body.data.polygons[index]
        xy = np.mean([uv[i].uv[:] for i in face.loop_indices], axis=0)
        sample = pixels[min(int(xy[1] * source_color.size[1]), source_color.size[1] - 1), min(int(xy[0] * source_color.size[0]), source_color.size[0] - 1), :3]
        if sample[0] > sample[1] * 1.15 and sample[1] > sample[2] * 1.05 and sample.mean() > .2:
            samples.append(sample)
    if not samples:
        raise ValueError('No unaffected warm hand colors found for recoloring')
    # Image pixels are encoded source samples; use a native texture sample node
    # for color conversion rather than treating those samples as shader-linear.
    skin_rgb = np.median(np.array(samples), axis=0)
    skin_linear = np.where(skin_rgb <= .04045, skin_rgb / 12.92, ((skin_rgb + .055) / 1.055) ** 2.4)
    corrected = nodes.new('ShaderNodeMixRGB')
    corrected.blend_type = 'MIX'
    links.new(factor, corrected.inputs[0])
    links.new(source.outputs['Color'], corrected.inputs[1])
    corrected.inputs[2].default_value = (*skin_linear.tolist(), 1)
    links.new(corrected.outputs[0], emit.inputs[0])
    target = nodes.new('ShaderNodeTexImage')
    target.image = target_color
    nodes.active = target
    target.select = True

    scene = bpy.context.scene
    old_engine = scene.render.engine
    old_selected = list(bpy.context.selected_objects)
    old_active = bpy.context.view_layer.objects.active
    old_hide = body.hide_render
    body.hide_render = True
    scene.render.engine = 'CYCLES'
    old_samples = scene.cycles.samples
    old_bake = {key: getattr(scene.render.bake, key) for key in ('use_clear', 'margin', 'margin_type')}
    scene.cycles.samples = 1
    scene.render.bake.use_clear = False
    scene.render.bake.margin = 12
    scene.render.bake.margin_type = 'EXTEND'
    bpy.ops.object.select_all(action='DESELECT')
    temp.select_set(True)
    bpy.context.view_layer.objects.active = temp
    try:
        bpy.ops.object.bake(type='EMIT')
        target_color.filepath_raw = str(out_dir / f'handface-color-{ordinal}.png')
        target_color.file_format = 'PNG'
        target_color.save()
        target_color.pack()
        if target_normal:
            source.image = source_normal
            # Use the original COLOR map to classify contamination for both maps.
            classify = nodes.new('ShaderNodeTexImage')
            classify.image = source_color
            links.new(classify.outputs['Color'], hsv.inputs['Color'])
            corrected.inputs[2].default_value = (.5, .5, 1.0, 1.0)
            target.image = target_normal
            bpy.ops.object.bake(type='EMIT')
            target_normal.filepath_raw = str(out_dir / f'handface-normal-{ordinal}.png')
            target_normal.file_format = 'PNG'
            target_normal.save()
            target_normal.pack()
    finally:
        body.hide_render = old_hide
        scene.render.engine = old_engine
        scene.cycles.samples = old_samples
        for key, value in old_bake.items():
            setattr(scene.render.bake, key, value)
        bpy.ops.object.select_all(action='DESELECT')
        for obj in old_selected:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = old_active
        temp_mesh = temp.data
        bpy.data.objects.remove(temp, do_unlink=True)
        bpy.data.meshes.remove(temp_mesh)
        bpy.data.materials.remove(bake_material)
    # Export-ready direct image connections; all source scalar/PBR maps survive.
    for node in material.node_tree.nodes:
        if node.type == 'TEX_IMAGE' and node.image == source_color:
            node.image = target_color
        elif node.type == 'TEX_IMAGE' and node.image == source_normal and target_normal:
            node.image = target_normal
    return material, {'source_material': source_material.name, 'hand_material': material.name,
                      'faces': len(selected_faces), 'sampled_skin_srgb': skin_rgb.tolist(),
                      'source_color_preserved': source_color.name,
                      'color_image': target_color.filepath_raw,
                      'normal_image': target_normal.filepath_raw if target_normal else None}


def _nose_displacement(points):
    x, y, z = points.T
    def compact(center_z, radius_x, radius_z, amplitude):
        wx = np.maximum(0.0, 1.0 - ((x - .0107) / radius_x) ** 2) ** 2
        wz = np.maximum(0.0, 1.0 - ((z - center_z) / radius_z) ** 2) ** 2
        return wx * wz * amplitude
    front_only = _smoothstep((-.082 - y) / .014)
    return (compact(1.641, .026, .028, .014) + compact(1.662, .017, .027, .004)) * front_only


def _repair_nose(body, points):
    mesh = body.data
    offsets = _nose_displacement(points)
    affected = offsets > 1e-9
    old_normals = np.array([normal.vector[:] for normal in mesh.corner_normals], dtype=np.float64)
    encoded_attr = mesh.attributes.get('custom_normal')
    encoded_before = None
    if encoded_attr and encoded_attr.data_type == 'INT16_2D':
        encoded_before = np.empty(len(mesh.loops) * 2, dtype=np.int32)
        encoded_attr.data.foreach_get('value', encoded_before)
        encoded_before = encoded_before.reshape(-1, 2)
    # Correct custom split normals through the displacement Jacobian. Preserve
    # every unaffected corner's exact source normal, including hard UV seams.
    gradients = []
    epsilon = 1e-5
    for axis in range(3):
        delta = np.zeros_like(points)
        delta[:, axis] = epsilon
        gradients.append((_nose_displacement(points + delta) - _nose_displacement(points - delta)) / (2 * epsilon))
    gradients = np.array(gradients).T
    moved = points.copy()
    moved[:, 1] -= offsets
    inv_world = body.matrix_world.inverted()
    for index in np.flatnonzero(affected):
        mesh.vertices[int(index)].co = inv_world @ Vector(moved[index])
    mesh.update()
    matrix = np.asarray(body.matrix_world, dtype=np.float64)[:3, :3]
    normal_to_world = np.linalg.inv(matrix).T
    loop_vertices = np.array([loop.vertex_index for loop in mesh.loops])
    normals = old_normals.copy()
    for loop_index in np.flatnonzero(affected[loop_vertices]):
        index = loop_vertices[loop_index]
        n = normal_to_world @ old_normals[loop_index]
        dx, dy, dz = gradients[index]
        ny = n[1] / (1.0 - dy)
        n = np.array((n[0] + dx * ny, ny, n[2] + dz * ny))
        local = matrix.T @ n
        normals[loop_index] = local / np.linalg.norm(local)
    mesh.normals_split_custom_set(normals.tolist())
    # Blender compresses custom normals relative to each smooth fan. Re-encoding
    # unchanged fans introduces quantization drift, so restore their original
    # integer payload exactly. Only the nose and its incident one-ring fans need
    # new encoding because their geometric bases changed.
    support = affected.copy()
    for face in mesh.polygons:
        if any(affected[index] for index in face.vertices):
            support[list(face.vertices)] = True
    unaffected = ~support[loop_vertices]
    encoded_restored_exactly = False
    if encoded_before is not None:
        encoded_after = np.empty(len(mesh.loops) * 2, dtype=np.int32)
        attr = mesh.attributes['custom_normal']
        attr.data.foreach_get('value', encoded_after)
        encoded_after = encoded_after.reshape(-1, 2)
        encoded_after[unaffected] = encoded_before[unaffected]
        attr.data.foreach_set('value', encoded_after.ravel())
        mesh.update()
        encoded_restored_exactly = True
    current_normals = np.array([normal.vector[:] for normal in mesh.corner_normals], dtype=np.float64)
    max_normal_delta = float(np.linalg.norm(current_normals[unaffected] - old_normals[unaffected], axis=1).max())
    # Profile measurements use actual existing central surface vertices.
    central = (np.abs(points[:, 0] - .0107) < .008) & (points[:, 1] < -.08)
    tip = central & (points[:, 2] > 1.626) & (points[:, 2] < 1.65)
    root = central & (points[:, 2] > 1.674) & (points[:, 2] < 1.696)
    root_y = float(np.median(points[root, 1]))
    return {'moved_vertices': int(affected.sum()), 'max_forward_displacement_m': float(offsets.max()),
            'affected_bounds_m': [points[affected].min(0).tolist(), points[affected].max(0).tolist()],
            'nasal_root_y_m': root_y, 'tip_before_y_m': float(points[tip, 1].min()),
            'tip_after_y_m': float(moved[tip, 1].min()),
            'projection_from_root_before_m': float(root_y - points[tip, 1].min()),
            'projection_from_root_after_m': float(root_y - moved[tip, 1].min()),
            'preserved_unaffected_corner_normals': int(unaffected.sum()),
            'max_unaffected_normal_vector_delta': max_normal_delta,
            'encoded_normals_outside_nose_support_restored_exactly': encoded_restored_exactly,
            'nose_normal_support_vertices': int(support.sum())}


def repair(body, rig, out_dir):
    """Repair existing rest geometry in place; return a JSON-serializable report.

    Contract: body is the imported athlete mesh with original rest-space world
    coordinates, UVs, source image material and its Armature modifier. rig is
    its unchanged imported armature. Call before adding procedural muscle
    materials. Supports the raw asset or a mesh whose pelvic faces were removed.
    Only hand faces receive copied/baked materials; only existing nose vertices
    move. No rig, topology, UV, source image or other material is modified.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    if body.get('handface_repair_version'):
        raise ValueError('Hand/face repair already applied; refusing to double-displace the nose')
    bpy.context.view_layer.update()
    points = _world_points(body)
    mask = _hand_mask(points, rig)
    original_slots = np.array([face.material_index for face in body.data.polygons])
    source_images = {node.image for material in body.data.materials if material for node in material.node_tree.nodes if node.type == 'TEX_IMAGE' and node.image}
    def image_digest(image):
        pixels = np.empty(len(image.pixels), dtype=np.float32)
        image.pixels.foreach_get(pixels)
        return hashlib.sha256(pixels.tobytes()).hexdigest()
    source_digests = {image: image_digest(image) for image in source_images}
    hand_faces = [p.index for p in body.data.polygons if any(mask[i] > 0 for i in p.vertices)]
    materials = {}
    for index in hand_faces:
        materials.setdefault(body.data.polygons[index].material_index, []).append(index)
    report = {'contract_version': 1, 'hand_vertices_in_mask': int((mask > 0).sum()), 'hands': [],
              'vertex_count_before': len(body.data.vertices), 'face_count_before': len(body.data.polygons),
              'rig_bones': len(rig.data.bones)}
    for ordinal, (slot, indices) in enumerate(materials.items()):
        material, hand_report = _bake_hand_maps(body, rig, indices, body.data.materials[slot], out_dir, ordinal)
        body.data.materials.append(material)
        new_slot = len(body.data.materials) - 1
        for index in indices:
            body.data.polygons[index].material_index = new_slot
        report['hands'].append(hand_report)
    report['nose'] = _repair_nose(body, points)
    final_points = _world_points(body)
    changed = np.linalg.norm(final_points - points, axis=1) > 1e-7
    nose_expected = _nose_displacement(points) > 1e-9
    report['vertices_changed_outside_nose'] = int((changed & ~nose_expected).sum())
    report['vertex_count_after'] = len(body.data.vertices)
    report['face_count_after'] = len(body.data.polygons)
    report['custom_normals_retained'] = bool(body.data.has_custom_normals)
    nonhand = np.ones(len(body.data.polygons), dtype=bool)
    nonhand[hand_faces] = False
    final_slots = np.array([face.material_index for face in body.data.polygons])
    report['nonhand_material_assignments_changed'] = int((original_slots[nonhand] != final_slots[nonhand]).sum())
    report['source_images_unchanged'] = {image.name: image_digest(image) == digest for image, digest in source_digests.items()}
    body['handface_repair_version'] = 1
    out_dir.joinpath('handface-repair-report.json').write_text(json.dumps(report, indent=2))
    return report


def main():
    out_dir = Path(__file__).resolve().parent
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(out_dir / 'athlete-rigged.glb'))
    body = bpy.data.objects['char1']
    rig = bpy.data.objects['Armature']
    # The importer may create a visualization helper from the vendor asset.
    for obj in list(bpy.context.scene.objects):
        if obj.type == 'MESH' and obj != body:
            obj.hide_render = True
    bpy.context.view_layer.update()
    _diagnose(body, rig, out_dir)
    if '--diagnose' in sys.argv:
        _render_views(body, out_dir, 'before')
    else:
        report = repair(body, rig, out_dir)
        print('@@HAND_FACE@@' + json.dumps(report))
        if '--qa' in sys.argv:
            sys.path.insert(0, str(Path.home() / '.codex/skills/blender-asset-qa/scripts'))
            import qa_check
            import review_shots
            qa = qa_check.run(objects=[body.name], profile='game', max_tris=100000, uv=True)
            out_dir.joinpath('handface-qa.json').write_text(json.dumps(qa, indent=2))
            review_shots.run(objects=[body.name], out=str(out_dir / 'handface-review-wire.png'), views=['front', 'right'], mode='wire', res=512)
        _render_views(body, out_dir, 'after')
    bpy.ops.wm.save_as_mainfile(filepath=str(out_dir / 'handface-test.blend'))


if __name__ == '__main__':
    main()
