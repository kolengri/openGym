"""Export the unchanged original cage and two DQ90/90 actions, without textures."""
import argparse
import bpy
import hashlib
import json
import struct
import sys
from pathlib import Path
import numpy as np

P = Path(__file__).resolve().parent
args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
parser = argparse.ArgumentParser()
parser.add_argument('--draft', action='store_true')
parser.add_argument('--asset', choices=['ninety-repaired'], default='ninety-repaired')
options = parser.parse_args(args)
source = P / (options.asset + '.blend')
repaired = options.asset == 'ninety-repaired'
report_dir = P / 'repair-90/dq' if repaired else P
bpy.ops.wm.open_mainfile(filepath=str(source))
body = bpy.data.objects['SK_BlenderStudioHuman']
rig = bpy.data.objects['RIG_BlenderStudioHuman']
assert len(body.data.vertices) == 10582 and len(rig.data.bones) == 51
assert body.data.shape_keys is None
for modifier in body.modifiers:
    modifier.show_viewport = modifier.type == 'ARMATURE'
    modifier.show_render = modifier.type == 'ARMATURE'
attribute = body.data.attributes.get('_SOURCE_INDEX') or body.data.attributes.new(name='_SOURCE_INDEX', type='FLOAT', domain='POINT')
attribute.data.foreach_set('value', np.arange(len(body.data.vertices), dtype=np.float32))
assert len(body.data.materials) == 1
material = body.data.materials[0]
assert not any(node.type == 'TEX_IMAGE' for node in material.node_tree.nodes)
scene = bpy.context.scene
scene.render.fps = 30
scene.render.fps_base = 1
if not options.draft:
    report = json.loads((report_dir / 'pose-verification.json').read_text())
    assert report['ok'] and report['source_sha256'] == hashlib.sha256(source.read_bytes()).hexdigest()
bpy.ops.object.select_all(action='DESELECT')
body.select_set(True)
rig.select_set(True)
bpy.context.view_layer.objects.active = rig
output = P / (options.asset + '.glb')
bpy.ops.export_scene.gltf(filepath=str(output), export_format='GLB', use_selection=True,
    export_yup=True, export_apply=False, export_texcoords=True, export_normals=True,
    export_materials='EXPORT', export_vertex_color='NONE', export_attributes=True,
    export_animations=True, export_animation_mode='ACTIONS', export_force_sampling=True,
    export_frame_range=False, export_frame_step=1, export_anim_slide_to_zero=True,
    export_skins=True, export_influence_nb=4, export_def_bones=True, export_leaf_bone=False,
    export_rest_position_armature=True, export_extras=True, export_cameras=False, export_lights=False)
data = output.read_bytes()
length, kind = struct.unpack_from('<II', data, 12)
document = json.loads(data[20:20 + length])
primitives = [p for mesh in document['meshes'] for p in mesh['primitives']]
triangles = sum(document['accessors'][p['indices']]['count'] // 3 for p in primitives)
assert len(document['meshes']) == len(document['skins']) == 1
assert len(document['skins'][0]['joints']) == 51
assert triangles == 21160
assert len(document['animations']) == (2 if repaired else 5)
if repaired:
    assert {a['name'] for a in document['animations']} == {'Exercise_10565','Exercise_6560'}
    assert not any(p.get('targets') for p in primitives)
assert not document.get('images') and not document.get('textures')
assert all('_SOURCE_INDEX' in p['attributes'] for p in primitives)
summary = {'status': 'draft_visual_review_only' if options.draft else 'source_qa_passed_runtime_review_required',
           'source': str(source), 'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
           'output': str(output), 'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data),
           'meshes': len(document['meshes']), 'skins': len(document['skins']), 'bones': len(document['skins'][0]['joints']),
           'triangles': triangles, 'materials': len(document.get('materials', [])), 'color_textures': 0,
           'source_index': '_SOURCE_INDEX', 'source_vertices': 10582,
           'animations': [a['name'] for a in document['animations']],
           'modifiers': 'Original-binding DQ cage; only PreserveVolume Armature enabled. Standard GLB skin requires the explicit DQ renderer.',
           'skinning':'dualQuaternion','generic_LBS_quality_approved':False,
           'engine_verification': 'Owned by primary; source bone/surface parity references accompany final export.'}
(P / 'ninety-runtime-export.json').write_text(json.dumps(summary, indent=2) + '\n')
if not options.draft:
    identity_path=P/'ninety-source-identity.json'
    identity=json.loads(identity_path.read_text())
    assert identity['output_sha256']==summary['source_sha256']
    identity['export']={k:summary[k] for k in ['output','sha256','bytes','meshes','skins','bones','triangles','animations']}
    identity['status']='native_DQ_QA_passed_runtime_and_primary_visual_review_required'
    identity['reference_files']={name:hashlib.sha256((P/name).read_bytes()).hexdigest() for name in ['ninety-dq-reference.json.gz','ninety-runtime-surface-reference.json','ninety-pose-samples.json','ninety-pose-verification.json','ninety-asset-qa.json']}
    identity_path.write_text(json.dumps(identity,indent=2)+'\n')
print(json.dumps(summary))
