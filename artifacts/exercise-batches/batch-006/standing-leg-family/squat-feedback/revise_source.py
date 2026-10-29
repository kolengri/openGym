"""One chronology repair; the3480 source action and geometry remain exact."""
from pathlib import Path
import bpy,sys,json,hashlib,math,numpy as np
from mathutils import Vector
P=Path(__file__).resolve().parent;F=P.parent;B=F.parent;sys.path.insert(0,str(B.parent/'batch-003'));sys.path.insert(0,str(F));import authoring as a;a.initialize();from revised_poses import StandingLegPoses
baseline=B/'assets/3480/source.blend';assert hashlib.sha256(baseline.read_bytes()).hexdigest()=='f716265a508389e5a72a151d65234341fb3013939df66b90d532df91a1bc60ab';bpy.ops.wm.open_mainfile(filepath=str(baseline));body=bpy.data.objects['SK_BlenderStudioHuman'];rig=bpy.data.objects['RIG_BlenderStudioHuman'];scene=bpy.context.scene;a.body,a.rig,a.scene=body,rig,scene
# Rest/head/helper globals came from the immutable original; saved binding and keys
# are taken directly from the accepted source, without regenerating any geometry.
keys=body.data.shape_keys;baseline_scales={pb.name:pb.scale.copy() for pb in rig.pose.bones}

def action_hash(act):
 d={'name':act.name,'slots':[(x.identifier,x.target_id_type,x.handle) for x in act.slots],'curves':[]}
 for layer in act.layers:
  for strip in layer.strips:
   for bag in strip.channelbags:
    for fc in bag.fcurves:d['curves'].append({'slot':bag.slot_handle,'path':fc.data_path,'index':fc.array_index,'points':[(list(k.co),list(k.handle_left),list(k.handle_right),k.interpolation,k.handle_left_type,k.handle_right_type) for k in fc.keyframe_points]})
 return hashlib.sha256(json.dumps(d,separators=(',',':')).encode()).hexdigest()
def geometry_hash():
 h=hashlib.sha256()
 for v in body.data.vertices:
  h.update(np.array(v.co,np.float32).tobytes());h.update(json.dumps([(g.group,g.weight) for g in v.groups]).encode())
 for p in body.data.polygons:h.update(np.array(p.vertices,np.int32).tobytes())
 for u in body.data.uv_layers:h.update(np.array([v.uv[:] for v in u.data],np.float32).tobytes())
 for k in keys.key_blocks:h.update(k.name.encode());h.update(np.array([v.co[:] for v in k.data],np.float32).tobytes())
 for bone in rig.data.bones:h.update(bone.name.encode());h.update(np.array(bone.matrix_local,np.float32).tobytes())
 return h.hexdigest()
before_action=action_hash(bpy.data.actions['Exercise_3480']);before_geometry=geometry_hash();rig.animation_data.action=bpy.data.actions['Exercise_3480'];keys.animation_data.action=rig.animation_data.action;keys.animation_data.action_slot=next(x for x in keys.animation_data.action.slots if x.target_id_type=='KEY');bpy.data.actions.remove(bpy.data.actions['Exercise_3479']);act=bpy.data.actions.new('Exercise_3479');act.use_fake_user=True;rig.animation_data.action=act;poses=StandingLegPoses(a);intended={};states={};errors={};previous={};scene.frame_start=1;scene.frame_end=241;scene.render.fps=30
for f in range(241):
 scene.frame_set(f+1);d,st,err=poses.pose('3479',f);bpy.context.view_layer.update();intended[f]={n:np.array(m) for n,m in d.items()};errors[f]=err;states[f]={k:list(v) if isinstance(v,Vector) else v for k,v in st.items() if k!='feet'};states[f]['feet']={ss:{'ankle':list(fp['ankle']),'support':fp['support']} for ss,fp in st['feet'].items()}
 for pb in rig.pose.bones:
  if pb.name in previous and pb.rotation_quaternion.dot(previous[pb.name])<0:pb.rotation_quaternion.negate()
  previous[pb.name]=pb.rotation_quaternion.copy();pb.keyframe_insert('location',frame=f+1);pb.keyframe_insert('rotation_quaternion',frame=f+1)
slot=act.slots.new(id_type='KEY',name='Preserved bounded joint targets');keys.animation_data.action=act;keys.animation_data.action_slot=slot
for f in range(241):
 scene.frame_set(f+1)
 for k in keys.key_blocks:
  if k.name=='Basis':continue
  k.value=states[f]['kick'] if k.name=='HeelTouch'+states[f]['side']+'Shoulder' else 0;k.keyframe_insert('value',frame=f+1)
for layer in act.layers:
 for strip in layer.strips:
  for bag in strip.channelbags:
   for fc in bag.fcurves:
    for k in fc.keyframe_points:k.interpolation='LINEAR'
# Scale is not an animated channel in the accepted source. Matrix decomposition
# may perturb it by float ULPs, so preserve those shared defaults exactly.
for pb in rig.pose.bones:pb.scale=baseline_scales[pb.name]
mx=0
for f in range(241):
 scene.frame_set(f+1);bpy.context.view_layer.update();mx=max(mx,max(float(abs(np.array(pb.matrix)-intended[f][pb.name]).max()) for pb in rig.pose.bones))
assert mx<2e-5;assert before_action==action_hash(bpy.data.actions['Exercise_3480']);assert before_geometry==geometry_hash();assert max(max(x.values()) for x in errors.values())<1e-6
# A small proof set closes the choreography concern before full native/export QA.
scene.render.resolution_x=600;scene.render.resolution_y=720;scene.render.resolution_percentage=100;proof=[]
def xyz():
 bpy.context.view_layer.update();ev=body.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh();X=np.array([ev.matrix_world@v.co for v in me.vertices]);ev.to_mesh_clear();return X
for label,f in [('start',0),('deep-squat',27),('rise',39),('full-stand',51),('support-transfer',58.5),('kick',74),('heel-touch',80),('return',111)]:
 scene.frame_set(int(f)+1,subframe=f%1);bpy.context.view_layer.update();X=xyz();bones={pb.name:np.array(pb.matrix) for pb in rig.pose.bones}
 for view,pos in [('oblique',(3.8,-5,2.3)),('side',(5,0,1))] if label in ['deep-squat','rise','support-transfer'] else [('oblique',(3.8,-5,2.3))]:
  cam=scene.camera;cam.location=pos;cam.rotation_euler=(Vector((0,0,.9))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=2.35;file=P/f'after-native-{label}-{view}.png';scene.render.filepath=str(file);bpy.ops.render.render(write_still=True);assert np.max(abs(xyz()-X))==0;assert max(np.max(abs(np.array(pb.matrix)-bones[pb.name])) for pb in rig.pose.bones)==0;proof.append({'time':f/30,'frame':f,'label':label,'file':file.name,'sha256':hashlib.sha256(file.read_bytes()).hexdigest(),'render_surface_delta_m':0,'render_bone_delta':0,'key_values':{k.name:k.value for k in keys.key_blocks if k.name!='Basis'}})
scene.frame_set(1);scene['3479_choreography_revision']='User rejected rushed overlap: now full squat and stand, weight transfer, then the existing side kick/touch, return and mirror;8seconds.';outfile=B/'assets/3479/source.blend';bpy.ops.wm.save_as_mainfile(filepath=str(outfile));statebank=json.loads((F/'kinematic-state.json').read_text());statebank['3479']=states;(F/'kinematic-state.json').write_text(json.dumps(statebank,indent=2)+'\n');target=json.loads((F/'target-errors.json').read_text());target['maximum_native_matrix_errors']['3479']=mx;target['target_errors_by_frame']['3479']=errors;(F/'target-errors.json').write_text(json.dumps(target,indent=2)+'\n');(P/'source-revision-report.json').write_text(json.dumps({'source_sha256':hashlib.sha256(outfile.read_bytes()).hexdigest(),'baseline_source_sha256':hashlib.sha256(baseline.read_bytes()).hexdigest(),'duration_seconds':8,'fps':30,'frame_count':240,'native_frame_origin':1,'maximum_native_matrix_error':mx,'maximum_target_reach_error_m':max(max(x.values()) for x in errors.values()),'3480_action_hash_before':before_action,'3480_action_hash_after':action_hash(bpy.data.actions['Exercise_3480']),'geometry_binding_uv_targets_rest_hash_before':before_geometry,'geometry_binding_uv_targets_rest_hash_after':geometry_hash(),'all_3480_source_curves_exact':True,'all_geometry_weights_targets_rest_exact':True,'proofs':proof},indent=2)+'\n');print('REVISED_SOURCE_READY',mx,before_action,before_geometry)
