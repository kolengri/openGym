"""Export a separate standard-linear half-kneel from the delivered editable source.

An explicit --output is required; frozen source/GLB files cannot be overwritten.
"""
from pathlib import Path
import argparse,sys,bpy,json,hashlib
P=Path(__file__).resolve().parent;out=P.parent/'assets/10058'
parser=argparse.ArgumentParser();parser.add_argument('--output',required=True,type=Path)
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:]if '--'in sys.argv else [])
assert args.output.resolve()!=(out/'motion.glb').resolve(),'Frozen GLB cannot be overwritten'
bpy.ops.wm.open_mainfile(filepath=str(out/'source.blend'))
body=bpy.data.objects['SK_BlenderStudioHuman'];rig=bpy.data.objects['RIG_BlenderStudioHuman']
assert set(a.name for a in bpy.data.actions)=={'Exercise_10058'}
assert body.data.shape_keys is None
bpy.ops.object.select_all(action='DESELECT');body.select_set(True);rig.select_set(True);bpy.context.view_layer.objects.active=rig
result=bpy.ops.export_scene.gltf(filepath=str(args.output.resolve()),export_format='GLB',use_selection=True,export_animations=True,export_animation_mode='ACTIONS',export_force_sampling=True,export_frame_range=True,export_frame_step=1,export_skins=True,export_all_influences=False,export_apply=False,export_morph=False,export_morph_normal=False,export_merge_animation='ACTION',export_attributes=True,export_materials='EXPORT',export_vertex_color='NONE',export_anim_slide_to_zero=True,export_rest_position_armature=True,export_influence_nb=4,export_cameras=False,export_lights=False,export_yup=True)
assert result=={'FINISHED'}
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
print(json.dumps({'output':str(args.output),'actions':['Exercise_10058'],'physical_geometry':1,'skinning':'linear','morphs':0,'source_sha256':sha(out/'source.blend'),'glb_sha256':sha(args.output),'glb_bytes':args.output.stat().st_size}))
