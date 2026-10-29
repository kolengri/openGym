"""Re-export separately from the delivered source; frozen GLB cannot be changed."""
from pathlib import Path
import argparse,sys,bpy,json,hashlib
P=Path(__file__).resolve().parent;A=P.parent/'assets/4365';parser=argparse.ArgumentParser();parser.add_argument('--output',required=True,type=Path);args=parser.parse_args(sys.argv[sys.argv.index('--')+1:]if '--'in sys.argv else [])
assert args.output.resolve()!=(A/'motion.glb').resolve(),'Frozen GLB cannot be overwritten'
bpy.ops.wm.open_mainfile(filepath=str(A/'source.blend'));b=bpy.data.objects['SK_BlenderStudioHuman'];r=bpy.data.objects['RIG_BlenderStudioHuman'];assert set(x.name for x in bpy.data.actions)=={'Exercise_4365'}
bpy.ops.object.select_all(action='DESELECT');b.select_set(True);r.select_set(True);bpy.context.view_layer.objects.active=r
result=bpy.ops.export_scene.gltf(filepath=str(args.output.resolve()),export_format='GLB',use_selection=True,export_animations=True,export_animation_mode='ACTIONS',export_force_sampling=True,export_frame_range=True,export_frame_step=1,export_skins=True,export_all_influences=False,export_apply=False,export_morph=True,export_morph_normal=True,export_merge_animation='ACTION',export_attributes=True,export_materials='EXPORT',export_vertex_color='NONE',export_anim_slide_to_zero=True,export_rest_position_armature=True,export_influence_nb=4,export_cameras=False,export_lights=False,export_yup=True)
assert result=={'FINISHED'};print(json.dumps({'output':str(args.output),'sha256':hashlib.sha256(args.output.read_bytes()).hexdigest(),'required_runtime':'Unchanged project optional DQ adapter; standard linear fallback is not native appearance.'}))
