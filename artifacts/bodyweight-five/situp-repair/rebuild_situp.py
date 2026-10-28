"""Replace only 0001 action, retaining the exact other four actions and binding."""
import ast,bpy,hashlib,json,re,sys,struct
from pathlib import Path
import numpy as np
from mathutils import Vector,Matrix,Quaternion
import math
P=Path(__file__).resolve().parent;B=P.parent
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
output=Path(args[args.index('--output')+1]) if '--output' in args else P/'trials'/'candidate.blend'
baseline=P/'trials'/'accepted-before.blend'
bpy.ops.wm.open_mainfile(filepath=str(baseline))
body=bpy.data.objects['SK_BlenderStudioHuman'];rig=bpy.data.objects['RIG_BlenderStudioHuman'];scene=bpy.context.scene

def action_hash(action):
 digest=hashlib.sha256()
 for layer in action.layers:
  for strip in layer.strips:
   for bag in strip.channelbags:
    for curve in bag.fcurves:
     digest.update(curve.data_path.encode());digest.update(struct.pack('<I',curve.array_index))
     for point in curve.keyframe_points:
      digest.update(np.array([*point.co,*point.handle_left,*point.handle_right],np.float32).tobytes())
      digest.update((point.interpolation+point.handle_left_type+point.handle_right_type+point.easing).encode())
 return digest.hexdigest()
def binding_hash():
 digest=hashlib.sha256()
 for vertex in body.data.vertices:
  digest.update(np.array(vertex.co,np.float32).tobytes())
  for group in vertex.groups:digest.update(struct.pack('<If',group.group,group.weight))
 for polygon in body.data.polygons:digest.update(np.array(polygon.vertices,np.int32).tobytes())
 for uv in body.data.uv_layers:
  a=np.empty(len(uv.data)*2,np.float32);uv.data.foreach_get('uv',a);digest.update(uv.name.encode()+a.tobytes())
 for bone in rig.data.bones:digest.update(bone.name.encode()+np.array(bone.matrix_local,np.float32).tobytes())
 return digest.hexdigest()
other_ids=['5965','5915','5887','9066'];before={i:action_hash(bpy.data.actions['Exercise_'+i]) for i in other_ids};binding_before=binding_hash()
rest={b.name:b.matrix_local.copy() for b in rig.data.bones};heads={b.name:b.head_local.copy() for b in rig.data.bones};tails={b.name:b.tail_local.copy() for b in rig.data.bones};length={b.name:b.length for b in rig.data.bones};coords=[v.co.copy() for v in body.data.vertices]
finger_specs={}
for bone in rig.data.bones:
 match=re.fullmatch(r'(Left|Right)(Little|Ring|Middle|Index|Thumb)([123])',bone.name)
 if match:finger_specs[bone.name]=(bone.head_local.copy(),bone.tail_local.copy(),bone.parent.name,match[2],int(match[3])-1)
source=(B/'build_motion.py').read_text();tree=ast.parse(source)
functions=[node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name in ['V','rx','rz','ease','cycle','frame','orient','two_joint','foot_rotation','sole_height','palm_rotation','palm_height','make_pose']]
exec(compile(ast.Module(body=functions,type_ignores=[]),str(B/'build_motion.py'),'exec'),globals())
item=next(x for x in json.loads((B/'clips.json').read_text()) if x['id']=='0001');target_errors={'0001':{'hands':0.,'feet':0.}}
rig.animation_data.action=None
old=bpy.data.actions.get('Exercise_0001')
if old:bpy.data.actions.remove(old)
action=bpy.data.actions.new('Exercise_0001');action.use_fake_user=True;rig.animation_data.action=action
for pb in rig.pose.bones:pb.rotation_mode='QUATERNION'
for frame_index in range(item['frames']+1):
 scene.frame_set(frame_index+1);make_pose(item,frame_index/item['frames'])
 for pb in rig.pose.bones:
  pb.keyframe_insert('location',frame=frame_index+1);pb.keyframe_insert('rotation_quaternion',frame=frame_index+1)
after={i:action_hash(bpy.data.actions['Exercise_'+i]) for i in other_ids}
assert before==after
assert binding_before==binding_hash()
scene.frame_set(1)
output.parent.mkdir(parents=True,exist_ok=True);bpy.ops.wm.save_as_mainfile(filepath=str(output))
report={'output':str(output),'source_blend_sha256':hashlib.sha256(baseline.read_bytes()).hexdigest(),'authoring_script_sha256':hashlib.sha256((B/'build_motion.py').read_bytes()).hexdigest(),'vertices':len(body.data.vertices),'polygons':len(body.data.polygons),'bones':len(rig.data.bones),'binding_and_rest_geometry_sha256':binding_before,'binding_and_rest_geometry_unchanged':True,'retained_other_action_payloads':after,'other_four_action_payloads_byte_identical':before==after,'situp_target_error_m':target_errors['0001'],'new_correctives':False,'issue_closure':'Primary review required; known issues are not closed by this draft.'}
(P/'source-identity.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
