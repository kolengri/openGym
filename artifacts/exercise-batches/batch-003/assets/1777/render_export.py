"""Render decoded GLB positions with the exact Three.js shader normals.

Blender 5.2's importer ignores morph NORMAL; this readback avoids that limitation.
"""
import hashlib
import json
import sys
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector
P = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(P))
import verify_export as e
sys.path.insert(0, str(P.parent/'4348'))
from glb_normals import decode, to_blender, unit

doc, payload = e.D, e.BIN
primitive = doc['meshes'][0]['primitives'][0]
base_normal = e.accessor(primitive['attributes']['NORMAL'])
deltas = np.array([decode(doc, payload, t['NORMAL']) for t in primitive.get('targets', [])])
triangles = e.accessor(primitive['indices']).astype(int).ravel().reshape(-1, 3)
weight_channel = next((ch for ch in doc['animations'][0]['channels'] if ch['target']['path'] == 'weights'), None)
if weight_channel:
    sampler = doc['animations'][0]['samplers'][weight_channel['sampler']]
    times = e.accessor(sampler['input']).ravel()
    values = e.accessor(sampler['output']).reshape(len(times), -1)
else:
    times, values = np.array([0., 5.]), np.zeros((2, 0))


def decoded_pose(t):
    matrices = e.evaluate(t)
    transform = np.array([matrices[i] for i in e.skin['joints']]) @ e.ibm
    xyz = np.zeros((len(e.pos), 4))
    rotation = np.zeros((len(e.pos), 3, 3))
    for k in range(4):
        xyz += e.weights[:, k, None]*np.einsum('nij,nj->ni', transform[e.joints[:, k]], e.homo)
        rotation += e.weights[:, k, None, None]*transform[e.joints[:, k], :3, :3]
    i = max(0, min(len(times)-1, np.searchsorted(times, t, side='right')-1))
    j = min(i+1, len(times)-1)
    u = (t-times[i])/(times[j]-times[i]) if j != i else 0
    weights = values[i]*(1-u)+values[j]*u
    normal = base_normal+np.einsum('k,knj->nj', weights, deltas) if len(deltas) else base_normal
    normal = unit(np.einsum('nij,nj->ni', rotation, normal))
    return to_blender(xyz[:, :3]), to_blender(normal)


bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = 'BLENDER_WORKBENCH'
scene.render.resolution_x, scene.render.resolution_y = 900, 1000
scene.render.resolution_percentage = 100
scene.render.film_transparent = True
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGBA'
shade = scene.display.shading
shade.light, shade.color_type = 'STUDIO', 'MATERIAL'
shade.show_shadows = shade.show_cavity = shade.show_specular_highlight = False
scene.view_settings.view_transform, scene.view_settings.look = 'Standard', 'None'
material = bpy.data.materials.new('Actual_GLB_Neutral')
material.diffuse_color = doc['materials'][0]['pbrMetallicRoughness']['baseColorFactor']
camera_data = bpy.data.cameras.new('DecodedGLBReview')
camera = bpy.data.objects.new('DecodedGLBReview', camera_data)
scene.collection.objects.link(camera)
scene.camera = camera
camera_data.type = 'ORTHO'
cameras = json.loads((P/'cameras.json').read_text())


def render(name, frame, c):
    xyz, normals = decoded_pose(frame/30)
    mesh = bpy.data.meshes.new('Actual_Decoded_GLB')
    mesh.from_pydata(xyz.tolist(), [], triangles.tolist())
    for polygon in mesh.polygons:
        polygon.use_smooth = True
    mesh.normals_split_custom_set_from_vertices(normals.tolist())
    mesh.materials.append(material)
    body = bpy.data.objects.new('Actual_Decoded_GLB', mesh)
    scene.collection.objects.link(body)
    camera.location = c['position']
    camera.rotation_euler = (Vector(c['target'])-camera.location).to_track_quat('-Z', 'Y').to_euler()
    camera_data.ortho_scale = c['scale']
    scene.render.filepath = str(P/name)
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(body, do_unlink=True)
    bpy.data.meshes.remove(mesh)


for label, frame in [('start', 0), ('peak', 75), ('return', 150)]:
    render(f'export-{label}-oblique.png', frame, cameras[0])
render('export-entry-oblique.png', 45, cameras[0])
render('export-peak-side.png', 75, cameras[1])
render('export-peak-hands.png', 75, {'position': [1.2, -1.8, 2.7], 'target': [0, .07, 1.93], 'scale': .58})
report = {'ok': True, 'glb_sha256': hashlib.sha256((P/'motion.glb').read_bytes()).hexdigest(),
          'source_sha256': hashlib.sha256((P/'source.blend').read_bytes()).hexdigest(),
          'curated_stills': 6, 'actual_animation': doc['animations'][0]['name'],
          'position_and_normal_basis': 'Decoded actual GLB TRS, inverse bind matrices, zero POSITION morphs and animated NORMAL targets; exact Three.js weighted skin-normal equation. Render-only posed mesh, no source positional or material substitution.',
          'style': 'Heat off, original neutral material, real alpha, no shadows/cavity/AO/specular.',
          'scope': 'Faithful shader-normal stills; primary owns actual live Three.js acceptance.'}
(P/'export-render-report.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report))
