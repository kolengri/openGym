"""Actual native all151 acceptance plus faithful neutral support proof."""
import json,sys,hashlib
from pathlib import Path
import bpy,numpy as np
from mathutils import Vector
P=Path(__file__).resolve().parent;B=P.parent;S=B.parent/'batch-004/assets/0003'
sys.path[:0]=[str(P),str(B.parent/'batch-003'),str(S)]
import authoring as a,support_sampler as sampler
profile=json.loads((P/'frozen-neutral-envelope.json').read_text());old=json.loads((P/'frozen-support-masks.json').read_text());contract=sampler.CONTRACT
lower=profile['lower_lumbar_ids'];mid=profile['lower_midline_ids'];ridges=profile['direct_ridge_ids'];depth=np.array([profile['expected_neutral_groove_depth_m'][str(i)]for i in lower]);middepth=np.array([profile['expected_neutral_groove_depth_m'][str(i)]for i in mid]);lm=json.loads((S/'landmarks.json').read_text())
def invariant_hash(body,rig):
 d=hashlib.sha256()
 for v in body.data.vertices:d.update(np.array(v.co,np.float32).tobytes())
 for p in body.data.polygons:d.update(np.array(p.vertices,np.int32).tobytes())
 for layer in body.data.uv_layers:
  v=np.empty(len(layer.data)*2,np.float32);layer.data.foreach_get('uv',v);d.update(layer.name.encode()+v.tobytes())
 for b in rig.data.bones:d.update(b.name.encode()+np.array(b.matrix_local,np.float32).tobytes())
 return d.hexdigest()
def points():
 bpy.context.view_layer.update();e=a.body.evaluated_get(bpy.context.evaluated_depsgraph_get());m=e.to_mesh();v=np.empty(len(m.vertices)*3);m.vertices.foreach_get('co',v);e.to_mesh_clear();return v.reshape(-1,3)
def stats(z):return {'min_m':float(z.min()),'median_m':float(np.median(z)),'max_m':float(z.max()),'fraction_within_2mm':float(np.mean(abs(z)<=.002)),'fraction_within_5mm':float(np.mean(abs(z)<=.005)),'fraction_within_12mm':float(np.mean(abs(z)<=.012))}
def metrics(p):
 adjusted=p[lower,2]-depth
 return {'whole_body_min_z_m':float(p[:,2].min()),'whole_body_min_source_id':int(p[:,2].argmin()),'raw_original45':stats(p[old['patches']['lumbar_arch'],2]),'raw_failed_flat_midline19':stats(p[old['patches']['lumbar_midline'],2]),'raw_lower38':stats(p[lower,2]),'profile_adjusted_lower38':stats(adjusted),'profile_adjusted_midline18':stats(p[mid,2]-middepth),'direct_ridge12':stats(p[ridges,2]),'pelvic_L':stats(p[old['patches']['pelvic_support_L'],2]),'pelvic_R':stats(p[old['patches']['pelvic_support_R'],2]),'feet_min_z_m':{s:float(p[lm['patches']['foot_'+s]['indices'],2].min())for s in ['L','R']}}
def failures(m):
 f=[]
 if m['whole_body_min_z_m']<-.00035:f.append('whole-body floor')
 for side in ['L','R']:
  if m['pelvic_'+side]['min_m']>.002:f.append('pelvic '+side)
 if m['profile_adjusted_lower38']['median_m']>.005:f.append('profile median')
 if m['profile_adjusted_lower38']['fraction_within_5mm']<.5:f.append('profile contact fraction')
 if m['profile_adjusted_midline18']['max_m']>.002:f.append('profile midline')
 if m['direct_ridge12']['max_m']>.002:f.append('direct ridge')
 return f
result={'profile_sha256':contract['profile_sha256'],'support_targets_sha256':contract['support_targets_sha256'],'families':[],'physics_limit':'No global collision-free or clinical claim. This report verifies stated source-bound native support, loop, fixed-joint and rendering invariants.'};proof=[]
for family in ['2395','5266']:
 a.initialize();bpy.ops.wm.open_mainfile(filepath=str(S/'source.blend'));a.body=bpy.data.objects['SK_BlenderStudioHuman'];a.rig=bpy.data.objects['RIG_BlenderStudioHuman'];a.scene=bpy.context.scene;a.rig.animation_data_clear()
 original=invariant_hash(a.body,a.rig);original_binding=a.binding_hash(a.body,a.rig);overlay=sampler.apply_binding(a.body,a.rig);installed=sampler.install_support(a.body,family);after=invariant_hash(a.body,a.rig)
 assert original==after and original_binding==contract['original_binding_sha256']
 rows=[];first=None;fixed_ref=None;fixed_error=0.;loop_error=0.;max_matrix=0.
 for frame in range(151):
  p,meta=sampler.sample(a,frame,family);m=metrics(p);issues=failures(m)
  if first is None:first=p.copy()
  if frame==150:loop_error=float(np.max(np.linalg.norm(p-first,axis=1)))
  if family=='5266':
   fixed=np.array([a.rig.pose.bones[n].head[:]for n in ['Hips','LeftUpLeg','LeftLeg','LeftFoot','LeftToeBase','RightUpLeg','RightLeg','RightFoot','RightToeBase']])
   if fixed_ref is None:fixed_ref=fixed.copy()
   fixed_error=max(fixed_error,float(np.max(np.linalg.norm(fixed-fixed_ref,axis=1))))
  max_matrix=max(max_matrix,meta['matrix_max_error']);rows.append({'frame':frame,'failures':issues,**m})
 family_report={'exercise_id':family,'ok':all(not r['failures']for r in rows),'constant_root_z_m':contract['constant_root_z_m'],'basis_topology_uv_rest_exact':original==after,'invariant_hash_without_weights':after,'runtime_binding_sha256':a.binding_hash(a.body,a.rig),'max_influences':max(len([g for g in v.groups if g.weight>1e-8])for v in a.body.data.vertices),'maximum_weight_sum_error':max(abs(sum(g.weight for g in v.groups)-1)for v in a.body.data.vertices),'bones':len(a.rig.data.bones),'matrix_max_error':max_matrix,'skin_loop_max_error_m':loop_error,'fixed_tabletop_joint_max_drift_m':fixed_error if family=='5266'else None,'samples':rows,'install':installed}
 result['families'].append(family_report)
 scene=a.scene;cam=scene.camera;scene.render.engine='BLENDER_WORKBENCH';scene.render.resolution_x=1100;scene.render.resolution_y=800;scene.render.resolution_percentage=100;scene.render.film_transparent=False;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA';scene.display.shading.color_type='SINGLE';scene.display.shading.single_color=(.56,.59,.62);scene.display.shading.show_shadows=False;scene.display.shading.show_cavity=True
 views=[{'label':'side','position':[5,0,.28],'target':[0,0,.28],'scale':2.1},{'label':'oblique','position':[3,-3,2.5],'target':[0,.02,.25],'scale':2.25}]
 # Reference guide is QA-only and remains absent from both asset folders.
 mesh=bpy.data.meshes.new('QA_FloorGuide');mesh.from_pydata([[-.20,-1.2,-.002],[-.20,1.2,-.002],[-.20,1.2,0],[-.20,-1.2,0]],[],[[0,1,2,3]]);guide=bpy.data.objects.new('QA_FloorGuide',mesh);scene.collection.objects.link(guide)
 for frame,label in [(0.,'start'),(37.5,'right-peak'),(112.5,'left-peak')]:
  p,meta=sampler.sample(a,frame,family)
  for view in views:
   cam.location=view['position'];cam.rotation_euler=(Vector(view['target'])-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=view['scale'];scene.render.filepath=str(P/f'support-{family}-{label}-{view["label"]}.png');bpy.ops.render.render(write_still=True)
   err=float(np.max(np.linalg.norm(points()-p,axis=1)));assert err<2e-6;proof.append({'family':family,'frame':frame,'view':view['label'],'native_render_surface_max_error_m':err})
 # Existing project game-profile checker; topology and original cage stay exact.
 sys.path.insert(0,'/Users/kolengri/.codex/skills/blender-asset-qa/scripts')
 import qa_check
 qa=qa_check.run(objects=[a.body.name],profile='game');(P/f'support-{family}-asset-qa.json').write_text(json.dumps(qa,indent=2)+'\n')
 family_report['game_profile_qa']=qa
 # One wire proof with an ephemeral thin evaluated wire overlay.
 p,meta=sampler.sample(a,37.5,family);e=a.body.evaluated_get(bpy.context.evaluated_depsgraph_get());m=e.to_mesh();wiremesh=bpy.data.meshes.new_from_object(e);e.to_mesh_clear();wire=bpy.data.objects.new('QA_EvaluatedWire',wiremesh);scene.collection.objects.link(wire);mod=wire.modifiers.new('QA_Wire','WIREFRAME');mod.thickness=.0004;wire.color=(.02,.02,.02,1);scene.display.shading.color_type='OBJECT';a.body.color=(.65,.67,.69,1)
 cam.location=views[0]['position'];cam.rotation_euler=(Vector(views[0]['target'])-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=views[0]['scale'];scene.render.filepath=str(P/f'support-{family}-right-peak-wire.png');bpy.ops.render.render(write_still=True)
result['native_render_readback']=proof;result['ok']=all(f['ok']and f['game_profile_qa'].get('pass',False)for f in result['families'])
(P/'support-native-verification.json').write_text(json.dumps(result,indent=2)+'\n')
contract['status']='native_support_passed'if result['ok']else'native_support_failed';contract['native_verification']='support-native-verification.json';contract['native_verification_sha256']=hashlib.sha256((P/'support-native-verification.json').read_bytes()).hexdigest();(P/'support-contract.json').write_text(json.dumps(contract,indent=2)+'\n')
print('SUPPORT_NATIVE_RESULT',json.dumps({'ok':result['ok'],'families':[{'id':f['exercise_id'],'ok':f['ok'],'failed_frames':[r['frame']for r in f['samples']if r['failures']],'matrix_max_error':f['matrix_max_error'],'loop':f['skin_loop_max_error_m'],'fixed_drift':f['fixed_tabletop_joint_max_drift_m'],'qa_pass':f['game_profile_qa'].get('pass')}for f in result['families']]}),flush=True)
