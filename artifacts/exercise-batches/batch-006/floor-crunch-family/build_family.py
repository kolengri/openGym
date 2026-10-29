"""Grounded floor-crunch native candidate and source-safe early proofs."""
from pathlib import Path
import sys,json,hashlib,math
import bpy,numpy as np
from mathutils import Vector
P=Path(__file__).resolve().parent;B=P.parent
sys.path[:0]=[str(P),str(B.parent/'batch-003')]
import authoring as a,profile_binding
import floor_crunch_pose as motion
original=a.initialize();body,rig,scene=a.body,a.rig,a.scene
# Reuse only the accepted causal source-anatomy binding field, not old poses or
# pose-space correctives. Actual source readback is retained, by stable names.
binding=profile_binding.ProfileBinding(body,rig)
receipt=binding.apply(.8815200062877445,.9794368639602231,details=True)
body.shape_key_add(name='Basis')
import glute_binding_overlay
posterior=glute_binding_overlay.install(body)
# Plantar field from accepted3948: rigid sole core below35mm, C1 collar to80mm.
coords=np.array([v.co[:]for v in body.data.vertices]);plantar=[]
def smooth(t):t=np.clip(t,0,1);return t*t*(3-2*t)
for side,sign in [('Left',1),('Right',-1)]:
 for i,v in enumerate(body.data.vertices):
  blend=float((1-smooth((coords[i,2]-.035)/.045))*smooth((sign*coords[i,0]-.08)/.04))
  if blend<1e-8:continue
  before={body.vertex_groups[g.group].name:float(g.weight)for g in v.groups}
  after={n:w*(1-blend)for n,w in before.items()};after[side+'Foot']=after.get(side+'Foot',0)+blend
  after={n:w for n,w in after.items()if w>1e-8};after=dict(sorted(after.items(),key=lambda x:x[1],reverse=True)[:4]);total=sum(after.values());after={n:w/total for n,w in after.items()}
  for name in before:body.vertex_groups[name].remove([i])
  for name,value in after.items():body.vertex_groups[name].add([i],value,'REPLACE')
  plantar.append({'id':i,'before':before,'after':after})
import knee_binding
knee_receipt=knee_binding.apply(body)
weights=[{body.vertex_groups[g.group].name:float(g.weight)for g in v.groups}for v in body.data.vertices]
assert max(map(len,weights))<=4 and max(abs(sum(w.values())-1)for w in weights)<2e-6
for m in body.modifiers:
 m.show_viewport=m.show_render=m.type=='ARMATURE'
 if m.type=='ARMATURE':m.use_deform_preserve_volume=True
# The constant support root is one scalar contact solve on a source-frozen
# bilateral pelvic patch. Ankles stay at their exact grounded targets.
pelvis=[8533,8585,8646,8648,3276,3328,3388,3390]
def points():
 bpy.context.view_layer.update();e=body.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=e.to_mesh();p=np.array([v.co[:]for v in mesh.vertices]);e.to_mesh_clear();return p
root=.13
for _ in range(4):
 motion.pose(a,0,'0006',root);p=points();res=float(p[pelvis,2].min()-.0015)
 root-=res
motion.ROOT_Z=root
(P/'pose-contract.json').write_text(json.dumps({'root_z_m':root,'ankle_y_m':motion.ANKLE_Y,'heel_wrist_lateral_m':motion.HEEL_WRIST_LATERAL,'grounded_feet':True,'old_pose_targets_imported':False,'source_floor_pelvic_ids':pelvis,'pelvic_start_min_m':float(p[pelvis,2].min()),'actions':['Exercise_0006','Exercise_4354'],'source_original_binding':original,'runtime_binding':a.binding_hash(body,rig)},indent=2)+'\n')
(P/'binding-receipt.json').write_text(json.dumps({'original_binding':original,'runtime_binding':a.binding_hash(body,rig),'shared_causal_profile':receipt,'posterior_attachment':posterior,'plantar':plantar,'knee_binding':knee_receipt,'actual_weights':weights,'maximum_influences':max(map(len,weights)),'maximum_sum_error':max(abs(sum(w.values())-1)for w in weights),'basis_rest_uv_ids_preserved':True},indent=2)+'\n')
scene.frame_start=1;scene.frame_end=151;scene.render.fps=30
captured={};desired={}
for id in ['0006','4354']:
 rig.animation_data_clear();captured[id]=[];desired[id]={};previous={}
 for f in range(151):
  scene.frame_set(f+1);target=motion.pose(a,f,id);bpy.context.view_layer.update()
  assert max(abs(rig.pose.bones[n].matrix[i][j]-m[i][j])for n,m in target.items()for i in range(4)for j in range(4))<2e-6
  row={}
  for pb in rig.pose.bones:
   q=pb.rotation_quaternion.copy()
   if pb.name in previous and q.dot(previous[pb.name])<0:q.negate()
   previous[pb.name]=q.copy();row[pb.name]=(pb.location.copy(),q)
  captured[id].append(row)
  if f in [0,37,38,75,112,113,150]:desired[id][f]=np.array([target[pb.name]for pb in rig.pose.bones])
for id,frames in captured.items():
 rig.animation_data_create();act=bpy.data.actions.new('Exercise_'+id);act.use_fake_user=True;rig.animation_data.action=act
 for f,row in enumerate(frames):
  scene.frame_set(f+1)
  for pb in rig.pose.bones:
   pb.location,pb.rotation_quaternion=row[pb.name];pb.keyframe_insert('location',frame=f+1);pb.keyframe_insert('rotation_quaternion',frame=f+1)
 for layer in act.layers:
  for strip in layer.strips:
   for bag in strip.channelbags:
    for curve in bag.fcurves:
     for key in curve.keyframe_points:key.interpolation='LINEAR'
import joint_components
joint_components.install(body,rig,scene)
attr=body.data.attributes.get('_SOURCE_INDEX')or body.data.attributes.new(name='_SOURCE_INDEX',type='FLOAT',domain='POINT');attr.data.foreach_set('value',np.arange(10582,dtype=np.float32))
scene.render.engine='BLENDER_WORKBENCH';scene.render.resolution_x=900;scene.render.resolution_y=700;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA';scene.render.film_transparent=True
shade=scene.display.shading;shade.light='STUDIO';shade.color_type='MATERIAL';shade.show_shadows=False;shade.show_cavity=False;shade.show_specular_highlight=False
scene.view_settings.view_transform='Standard';scene.view_settings.look='None'
cd=bpy.data.cameras.new('ReviewCamera');cam=bpy.data.objects.new('ReviewCamera',cd);scene.collection.objects.link(cam);scene.camera=cam;cd.type='ORTHO'
CAMERAS=[{'label':'side','position':[4,0,1.2],'target':[0,.18,.30],'scale':2.45},{'label':'oblique','position':[3.4,-4.5,3],'target':[0,.18,.30],'scale':2.45}]
def view(p):
 cam.location=p['position'];cam.rotation_euler=(Vector(p['target'])-cam.location).to_track_quat('-Z','Y').to_euler();cd.ortho_scale=p['scale']
rig.animation_data.action=bpy.data.actions['Exercise_0006'];body.data.shape_keys.animation_data.action=bpy.data.actions['Exercise_0006'];body.data.shape_keys.animation_data.action_slot=next(slot for slot in bpy.data.actions['Exercise_0006'].slots if slot.target_id_type=='KEY');scene.frame_set(1);view(CAMERAS[1]);bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(P/'source.blend'))
# Reopen and compare actual action matrices plus full evaluated skin before and
# after every render. No manual-pose proof can override the saved action.
bpy.ops.wm.open_mainfile(filepath=str(P/'source.blend'));body=bpy.data.objects['SK_BlenderStudioHuman'];rig=bpy.data.objects['RIG_BlenderStudioHuman'];scene=bpy.context.scene;cam=scene.camera;cd=cam.data
assert weights==[{body.vertex_groups[g.group].name:float(g.weight)for g in v.groups}for v in body.data.vertices]
proof=[]
for id in ['0006','4354']:
 out=B/'assets'/id;rig.animation_data.action=bpy.data.actions['Exercise_'+id];body.data.shape_keys.animation_data.action=bpy.data.actions['Exercise_'+id];body.data.shape_keys.animation_data.action_slot=next(slot for slot in bpy.data.actions['Exercise_'+id].slots if slot.target_id_type=='KEY')
 for f,label in ([(0,'start'),(37,'left'),(112,'right')]if id=='0006'else[(0,'start'),(37,'right'),(112,'left')]):
  scene.frame_set(f+1);bpy.context.view_layer.update();actual=np.array([pb.matrix[:]for pb in rig.pose.bones]);err=float(abs(actual-desired[id][f]).max());assert err<2e-6
  for camera in CAMERAS:
   view(camera);before=points();scene.render.filepath=str(out/f'early-{label}-{camera["label"]}.png');bpy.ops.render.render(write_still=True);after=points();delta=float(np.linalg.norm(after-before,axis=1).max());assert delta<1e-8
   proof.append({'id':id,'frame':f,'view':camera['label'],'actual_saved_matrix_max_error':err,'pre_post_render_skin_delta_m':delta,'floor_min_z_m':float(after[:,2].min()),'pelvic_min_z_m':float(after[pelvis,2].min())})
 # Contact view is deliberately different from the normal oblique camera.
 scene.frame_set(1);view({'position':[3.8,-1.5,.8],'target':[0,.1,.18],'scale':2.1});before=points();scene.render.filepath=str(out/'early-contact.png');bpy.ops.render.render(write_still=True);assert np.linalg.norm(points()-before,axis=1).max()<1e-8
 (out/'cameras.json').write_text(json.dumps(CAMERAS,indent=2)+'\n')
(P/'early-proof-readback.json').write_text(json.dumps({'source_sha256':hashlib.sha256((P/'source.blend').read_bytes()).hexdigest(),'samples':proof,'actual_weights_normalized':True,'skinning':'dualQuaternion','no_old_correctives':True,'declared_local_components':'joint-components.json'},indent=2)+'\n')
print('EARLY_NATIVE_READY',root,flush=True)
