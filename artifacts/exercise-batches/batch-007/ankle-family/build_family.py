"""Original-body seated ankle family: early actual-source proofs first."""
from pathlib import Path
import sys,json,hashlib,math,os
import bpy,numpy as np
from mathutils import Vector
P=Path(__file__).resolve().parent;B=P.parent;F=B.parent/'batch-006/floor-crunch-family'
sys.dont_write_bytecode=True;sys.path[:0]=[str(P),str(B.parent/'batch-003'),str(F)]
import authoring as a,profile_binding,glute_binding_overlay,ankle_pose as motion
original=a.initialize();body,rig,scene=a.body,a.rig,a.scene
original_weights=[{body.vertex_groups[g.group].name:float(g.weight)for g in v.groups}for v in body.data.vertices]
profile=profile_binding.ProfileBinding(body,rig).apply(.8815200062877445,.9794368639602231,details=True)
body.shape_key_add(name='Basis');glute=glute_binding_overlay.install(body)
coords=np.array([v.co[:]for v in body.data.vertices]);plantar=[]
def smooth(t):t=np.clip(t,0,1);return t*t*(3-2*t)
for side,sign in [('Left',1),('Right',-1)]:
 for i,v in enumerate(body.data.vertices):
  blend=float((1-smooth((coords[i,2]-.035)/.045))*smooth((sign*coords[i,0]-.08)/.04))
  if blend<1e-8:continue
  before={body.vertex_groups[g.group].name:float(g.weight)for g in v.groups};after={n:w*(1-blend)for n,w in before.items()};after[side+'Foot']=after.get(side+'Foot',0)+blend;after={n:w for n,w in after.items()if w>1e-8};after=dict(sorted(after.items(),key=lambda row:row[1],reverse=True)[:4]);total=sum(after.values());after={n:w/total for n,w in after.items()}
  for name in before:body.vertex_groups[name].remove([i])
  for name,w in after.items():body.vertex_groups[name].add([i],w,'REPLACE')
  plantar.append({'id':i,'before':before,'after':after})
for mod in body.modifiers:
 mod.show_viewport=mod.show_render=mod.type=='ARMATURE'
 if mod.type=='ARMATURE':mod.use_deform_preserve_volume=True
for side,sign in [('Left',1),('Right',-1)]:
 motion.HEEL_IDS[side]=[v.index for v in body.data.vertices if v.co.x*sign>.12 and v.co.y>.025 and v.co.z<.035 and sum(g.weight for g in v.groups if body.vertex_groups[g.group].name==side+'Foot')>.999]
 motion.PALMS[side]=[v.index for v in body.data.vertices if sum(g.weight for g in v.groups if body.vertex_groups[g.group].name==side+'Hand')>.8]
 motion.HEEL_SKIN_IDS[side]=[v.index for v in body.data.vertices if v.co.x*sign>.08 and v.co.y>0 and v.co.z<.18 and sum(g.weight for g in v.groups if body.vertex_groups[g.group].name in [side+'Foot',side+'Leg'])>.8]
 motion.CALF_IDS[side]=[v.index for v in body.data.vertices if .15<v.co.z<.48 and sum(g.weight for g in v.groups if body.vertex_groups[g.group].name==side+'Leg')>.8]
 thigh=[v for v in body.data.vertices if .65<v.co.z<.84 and v.co.y<-.04 and sum(g.weight for g in v.groups if body.vertex_groups[g.group].name==side+'UpLeg')>.99]
 motion.THIGH_TARGET[side]=min(thigh,key=lambda v:(v.co-Vector((sign*.17,-.09,.75))).length).index
 handlong=(a.tails[side+'Hand']-a.heads[side+'Hand']).normalized();desired=a.heads[side+'Hand']+handlong*.075+Vector((-sign*.02,0,0));motion.PALM_ANCHOR[side]=min((body.data.vertices[i]for i in motion.PALMS[side]),key=lambda v:(v.co-desired).length).co.copy()
 assert motion.HEEL_IDS[side]and motion.PALMS[side]
pelvis=[v.index for v in body.data.vertices if abs(v.co.x)<.23 and v.co.y>.035 and .78<v.co.z<1.02]
root=.18
for _ in range(5):
 d=motion.pose(a,'2761',0,root);motion.apply(a,d);p=motion.points(a);root-=float(p[pelvis,2].min()-.0015)
motion.ROOT_Z=root
lower,upper=.1,30.
for _ in range(12):
 motion.KNEE_FLEX=(lower+upper)/2;minimum=1.
 for t in [1.25,3.75]:
  d=motion.pose(a,'2761',t);motion.apply(a,d);pp=motion.points(a);minimum=min(minimum,*(float(pp[motion.CALF_IDS[side],2].min())for side in ['Left','Right']))
 if minimum<.0015:lower=motion.KNEE_FLEX
 else:upper=motion.KNEE_FLEX
motion.KNEE_FLEX=upper
for _ in range(3):
 d=motion.pose(a,'2761',0,root);motion.apply(a,d);p=motion.points(a);root-=float(p[pelvis,2].min()-.0015)
motion.ROOT_Z=root
(P/'pose-contract.json').write_text(json.dumps({'root_z_m':root,'authored_knee_flexion_degrees':motion.KNEE_FLEX,'pelvic_original_ids':pelvis,'heel_original_ids':motion.HEEL_IDS,'heel_skin_original_ids':motion.HEEL_SKIN_IDS,'calf_original_ids':motion.CALF_IDS,'palm_original_ids':motion.PALMS,'thigh_hand_target_original_ids':motion.THIGH_TARGET,'duration_seconds':{'1368':12,'2761':5,'2762':5},'native_frame_origin':1,'source_original_binding':original,'runtime_binding':a.binding_hash(body,rig)},indent=2)+'\n')
weights=[{body.vertex_groups[g.group].name:float(g.weight)for g in v.groups}for v in body.data.vertices];assert max(map(len,weights))<=4 and max(abs(sum(row.values())-1)for row in weights)<2e-6
changed=[i for i in range(10582)if original_weights[i]!=weights[i]]
(P/'binding-receipt.json').write_text(json.dumps({'source_binding':original,'runtime_binding':a.binding_hash(body,rig),'accepted_anatomical_profile':profile,'proximal_glute':glute,'plantar':plantar,'actual_weights':weights,'changed_original_ids':changed,'maximum_influences':max(map(len,weights)),'maximum_sum_error':max(abs(sum(row.values())-1)for row in weights),'old_pose_or_corrective_imported':False,'dependencies':{str(path):hashlib.sha256(path.read_bytes()).hexdigest()for path in [F/'profile_binding.py',F/'glute_binding_overlay.py',F/'glute-binding-repair.json',F/'support-protected-domain.json']}},indent=2)+'\n')
captured={};desired={}
for id,frames in [('1368',360),('2761',150),('2762',150)]:
 rig.animation_data_clear();captured[id]=[];desired[id]={}
 for f in range(frames+1):
  scene.frame_set(f+1);d=motion.pose(a,id,f/30);motion.apply(a,d);captured[id].append({pb.name:(pb.location.copy(),pb.rotation_quaternion.copy())for pb in rig.pose.bones});desired[id][f]=np.array([d[pb.name]for pb in rig.pose.bones])
for id,rows in captured.items():
 rig.animation_data_create();action=bpy.data.actions.new('Exercise_'+id);action.use_fake_user=True;rig.animation_data.action=action;previous={}
 for f,row in enumerate(rows):
  scene.frame_set(f+1)
  for pb in rig.pose.bones:
   loc,q=row[pb.name]
   if pb.name in previous and q.dot(previous[pb.name])<0:q.negate()
   previous[pb.name]=q.copy();pb.location=loc;pb.rotation_quaternion=q;pb.keyframe_insert('location',frame=f+1);pb.keyframe_insert('rotation_quaternion',frame=f+1)
 for layer in action.layers:
  for strip in layer.strips:
   for bag in strip.channelbags:
    for curve in bag.fcurves:
     for key in curve.keyframe_points:key.interpolation='LINEAR'
attr=body.data.attributes.get('_SOURCE_INDEX')or body.data.attributes.new('_SOURCE_INDEX','FLOAT','POINT');attr.data.foreach_set('value',np.arange(10582,dtype=np.float32))
scene.frame_start=1;scene.frame_end=361;scene.render.fps=30;scene.render.engine='BLENDER_WORKBENCH';scene.render.resolution_x=1000;scene.render.resolution_y=800;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA';scene.render.film_transparent=True
shade=scene.display.shading;shade.light='STUDIO';shade.color_type='MATERIAL';shade.show_shadows=False;shade.show_cavity=False;shade.show_specular_highlight=False;scene.view_settings.view_transform='Standard';scene.view_settings.look='None'
cd=bpy.data.cameras.new('AnkleReviewCamera');camera=bpy.data.objects.new('AnkleReviewCamera',cd);scene.collection.objects.link(camera);scene.camera=camera;cd.type='ORTHO'
views=[{'label':'Whole-body seated oblique','position':[3.3,-4.5,2.0],'target':[0,-.34,.4],'scale':2.05},{'label':'Whole-body seated side','position':[3.8,-.20,1.0],'target':[0,-.35,.4],'scale':2.05}]
rig.animation_data.action=bpy.data.actions['Exercise_2761'];scene.frame_set(1);bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(P/'source.blend'))
bpy.ops.wm.open_mainfile(filepath=str(P/'source.blend'));a.body=body=bpy.data.objects['SK_BlenderStudioHuman'];a.rig=rig=bpy.data.objects['RIG_BlenderStudioHuman'];a.scene=scene=bpy.context.scene;camera=scene.camera
assert weights==[{body.vertex_groups[g.group].name:float(g.weight)for g in v.groups}for v in body.data.vertices]
proof=[]
for id,phases in [('1368',[(0,'start'),(60,'circle'),(360,'return')]),('2761',[(0,'start'),(37,'dorsal'),(150,'return')]),('2762',[(0,'start'),(37,'point'),(150,'return')])]:
 out=B/'assets'/id;out.mkdir(parents=True,exist_ok=True);rig.animation_data.action=bpy.data.actions['Exercise_'+id]
 for f,label in phases:
  scene.frame_set(f+1);bpy.context.view_layer.update();error=float(abs(np.array([pb.matrix[:]for pb in rig.pose.bones])-desired[id][f]).max());assert error<2e-6
  for vi,view in enumerate(views):
   camera.location=view['position'];camera.rotation_euler=(Vector(view['target'])-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.ortho_scale=view['scale'];before=motion.points(a);scene.render.filepath=str(out/f'early-{label}-view{vi+1}.png');bpy.ops.render.render(write_still=True);after=motion.points(a);drift=float(np.linalg.norm(after-before,axis=1).max());assert drift<1e-8
   proof.append({'id':id,'frame':f,'view':vi+1,'actual_saved_matrix_error':error,'pre_post_render_skin_delta_m':drift,'global_min_z_m':float(after[:,2].min()),'pelvic_min_z_m':float(after[pelvis,2].min())})
 (out/'cameras.json').write_text(json.dumps(views,indent=2)+'\n')
(P/'early-proof-readback.json').write_text(json.dumps({'source_sha256':hashlib.sha256((P/'source.blend').read_bytes()).hexdigest(),'samples':proof,'root_z_m':root,'actual_weights_normalized_max4':True,'source_actions':['Exercise_1368','Exercise_2761','Exercise_2762']},indent=2)+'\n');print('EARLY_ANKLE_READY',root,flush=True)
