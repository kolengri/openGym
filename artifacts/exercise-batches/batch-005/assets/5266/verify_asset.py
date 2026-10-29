"""Verify the corrective-bearing original DQ cage and separate native preview."""
import bpy,json,sys,hashlib,math,gzip
from pathlib import Path
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
P=Path(__file__).resolve().parent
FRAMES=[0,12.5,19,30,37.5,56,75,94,112.5,120,131,137.5,150]
TOL={'support_near_band_m':.012,'support_minimum_near_fraction':.20,'maximum_floor_penetration_m':.00035,'minimum_airborne_foot_clearance_m':.05,'planted_hand_maximum_drift_m':.005,'loop_translation_m':.0001}

def _frame(scene,frame):
 scene.frame_set(int(frame)+1,subframe=frame%1)
 bpy.context.view_layer.update()

def hand_separation(body,scene):
 sets={}
 for side in ['Left','Right']:
  names={group.index for group in body.vertex_groups if group.name.startswith(side)and any(token in group.name for token in ['Hand','Thumb','Index','Middle','Ring','Little'])}
  sets[side]={vertex.index for vertex in body.data.vertices if sum(group.weight for group in vertex.groups if group.group in names)>.5}
 samples=[]
 for frame in [0,37.5,112.5]:
  _frame(scene,frame);evaluated=body.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=evaluated.to_mesh();points=[vertex.co.copy()for vertex in mesh.vertices]
  trees={side:BVHTree.FromPolygons(points,[list(face.vertices)for face in mesh.polygons if all(index in sets[side]for index in face.vertices)])for side in ['Left','Right']}
  signed=[];distances=[]
  for side,other in [('Left','Right'),('Right','Left')]:
   for index in sets[side]:
    nearest,normal,face,distance=trees[other].find_nearest(points[index]);distances.append(distance);signed.append((points[index]-nearest).dot(normal))
  samples.append({'frame':frame,'minimum_unsigned_distance_m':min(distances),'minimum_nearest_normal_signed_distance_m':min(signed),'vertices_more_than4mm_inside':sum(value<-.004 for value in signed)})
  evaluated.to_mesh_clear()
 return {'source_sha256':hashlib.sha256((P/'source.blend').read_bytes()).hexdigest(),'samples':samples,'scope':'Actual original-ID hand/finger surfaces. Nearest normals diagnose overlap; hands move rigidly with head and fingertips are outside corrective masks.'}

def run():
 bpy.ops.wm.open_mainfile(filepath=str(P/'source.blend'))
 b=bpy.data.objects['SK_BlenderStudioHuman'];r=bpy.data.objects['RIG_BlenderStudioHuman'];s=bpy.context.scene
 for mod in b.modifiers:
  mod.show_viewport=mod.show_render=mod.type=='ARMATURE'
  if mod.type=='ARMATURE':mod.use_deform_preserve_volume=True
 rest=np.array([v.co[:] for v in b.data.vertices]);groups={g.name:np.array([next((p.weight for p in v.groups if p.group==g.index),0) for v in b.data.vertices]) for g in b.vertex_groups}
 patches={}
 frozen=json.loads((P/'frozen-support-masks.json').read_text())
 profile=json.loads((P/'frozen-neutral-envelope.json').read_text());acceptance=profile['qc']
 for suffix in ['L','R']:
  name='pelvic_support_'+suffix
  patches[name]={'indices':frozen['patches'][name],'state':'supported','rationale':'Unchanged original0003 posterior pelvic four-ID support patch, frozen before fitting. No post-hoc reselection.'}
 for side,sign,suffix in [('Left',1,'L'),('Right',-1,'R')]:
  hand=np.flatnonzero(sum(v for k,v in groups.items() if k.startswith(side) and any(x in k for x in ['Hand','Thumb','Index','Middle','Ring','Little']))>.5)
  patches['whole_hand_'+suffix]={'indices':hand.tolist(),'state':'observed','rationale':'Actual hand/finger skin held behind head; signed head clearance checked separately, no floor-contact claim.'}
  foot=np.flatnonzero((groups[side+'Foot']+groups[side+'ToeBase'])>.5)
  patches['foot_'+suffix]={'indices':foot.tolist(),'state':'lifted','rationale':'Actual foot/toe skin remains airborne through the complete alternating cycle.'}
 patches['lumbar_arch']={'indices':frozen['patches']['lumbar_arch'],'state':'observed','rationale':'Original raw45 domain retained diagnostically; source-profile lower38 criteria are authoritative.'}
 patches['lumbar_midline']={'indices':frozen['patches']['lumbar_midline'],'state':'observed','rationale':'Original raw19 domain retained diagnostically; final lower18 profile residual preserves the neutral groove.'}
 patches['lower_lumbar_profile']={'indices':profile['lower_lumbar_ids'],'state':'observed','rationale':'Frozen original-source lower38 profile domain at/below neutralSpine1head. Neutral groove depth is retained; adjusted arch gap checked separately.'}
 patches['direct_paraspinal_ridges']={'indices':profile['direct_ridge_ids'],'state':'supported','rationale':'Frozen12 source-derived bilateral posterior envelope ridge points, direct actual skin2mm support requirement.'}
 patches['lower_midline_profile']={'indices':profile['lower_midline_ids'],'state':'observed','rationale':'Frozen18 source-derived lower midline points; expected neutral groove depth retained, adjusted residual<=2mm.'}
 def profile_metrics(points):
  ids=profile['lower_lumbar_ids'];mid=profile['lower_midline_ids'];depth=profile['expected_neutral_groove_depth_m']
  adjusted=np.array([points[i,2]-depth[str(i)]for i in ids]);residual=np.array([points[i,2]-depth[str(i)]for i in mid])
  return {'lower_profile_adjusted_median_m':float(np.median(adjusted)),'lower_profile_adjusted_fraction_abs_within_5mm':float(np.mean(abs(adjusted)<=.005)),'lower_profile_adjusted_max_m':float(adjusted.max()),'every_lower_midline_adjusted_residual_max_m':float(residual.max()),'direct_ridge_max_z_m':float(points[profile['direct_ridge_ids'],2].max()),'raw_original45_median_m':float(np.median(points[profile['original45_ids'],2])),'raw_original45_max_m':float(points[profile['original45_ids'],2].max()),'raw_original19_max_m':float(points[patches['lumbar_midline']['indices'],2].max())}
 def support_errors(points):
  errors=[];q=profile_metrics(points)
  if points[:,2].min()<acceptance['whole_body_min_z_m']:errors.append('Full skin exceeds declared floor penetration')
  for name in ['pelvic_support_L','pelvic_support_R']:
   if points[patches[name]['indices'],2].min()>acceptance['both_original_pelvic_patch_min_max_m']:errors.append(name+' not supported within2mm')
  if q['lower_profile_adjusted_median_m']>acceptance['lower_profile_adjusted_median_max_m']or q['lower_profile_adjusted_fraction_abs_within_5mm']<acceptance['lower_profile_adjusted_fraction_abs_within_5mm_min']:errors.append('Frozen lower38 profile-adjusted arch gap fails')
  if q['every_lower_midline_adjusted_residual_max_m']>acceptance['every_lower_midline_adjusted_residual_max_m']:errors.append('Frozen lower18 profile-adjusted midline residual fails')
  if q['direct_ridge_max_z_m']>acceptance['direct_ridge_max_z_m']:errors.append('Frozen direct paraspinal ridge actual skin support fails')
  return errors

 for name,p in patches.items():
  attr=b.data.attributes.new(name='QA5266_'+name,type='FLOAT',domain='POINT');v=np.zeros(len(rest),np.float32);v[p['indices']]=1;attr.data.foreach_set('value',v)
 landmarks={'schema_version':'1.0.0','id':'5266','source_sha256':hashlib.sha256((P/'source.blend').read_bytes()).hexdigest(),'source_vertices':10582,'source_index_attribute':'_SOURCE_INDEX','coordinate_frame':'Blender world metres; Three.js[x,z,-y]','floor':{'point':[0,0,0],'normal':[0,0,1]},'patches':patches,'tolerances':TOL,'basis':'Illustration approximation at1.8m scale.12mm curved-support band,20%near fraction,4mm floor penetration reused from accepted project checks. Not exact collision, medical landmarks or clinical technique certification.'}
 (P/'landmarks.json').write_text(json.dumps(landmarks,indent=2)+'\n')
 failures=[];native_contact_differences=[];samples=[];references=[];dq_references=[];joints=[];native_qa=[];morph_samples=[]
 sys.path.insert(0,str(Path.home()/'.codex/skills/blender-asset-qa/scripts'))
 import qa_check
 sys.path.insert(0,str(P.parents[3]/'bodyweight-next-five'))
 import warning_observer
 warning_observer.install(qa_check)
 for path in ['dq_cage']:
  for mod in b.modifiers:
   mod.show_viewport=mod.show_render=(mod.type=='ARMATURE' or (path=='native' and mod.type=='MULTIRES'))
  first={};last=None
  for f in FRAMES:
   _frame(s,f);bpy.context.view_layer.update();e=b.evaluated_get(bpy.context.evaluated_depsgraph_get());m=e.to_mesh()
   pos=np.array([b.matrix_world@v.co for v in m.vertices]);areas=np.zeros(len(pos),np.float64)
   for p in m.polygons:areas[list(p.vertices)]+=p.area/len(p.vertices)
   metrics={};masks={}
   for name,p in patches.items():
    v=np.empty(len(m.vertices),np.float32);m.attributes['QA5266_'+name].data.foreach_get('value',v);mask=v>.35;masks[name]=mask
    points=pos[mask];z=points[:,2];near=abs(z)<=TOL['support_near_band_m'];cent=points[:,:2].mean(0);first.setdefault(name,cent)
    normals=np.array([v.normal[:] for v in m.vertices])[mask]
    row={'min_z':float(z.min()),'max_z':float(z.max()),'median_z':float(np.median(z)),'fraction_within_5mm':float(np.mean(abs(z)<=.005)),'p10_z':float(np.quantile(z,.1)),'p90_z':float(np.quantile(z,.9)),'fraction_near_floor':float(near.mean()),'near_floor_area_m2':float(areas[mask][near].sum()),'patch_area_m2':float(areas[mask].sum()),'tangential_drift_m':float(np.linalg.norm(cent-first[name])),'mean_floor_facing_normal':float((-normals[:,2]).mean())}
    metrics[name]=row
    if p['state']=='supported' and (z.min()>.012 or near.mean()<.2):
     (failures if path=='dq_cage' else native_contact_differences).append(f'{path} frame{f} {name}: unsupported')
    if p['state']=='supported' and name.startswith('palm') and row['tangential_drift_m']>.005:failures.append(f'{path} frame{f} {name}: hand drift')
    if path=='dq_cage' and p['state']=='lifted' and z.min()<.05:failures.append(f'{path} frame{f} {name}: foot clearance')
   if path=='dq_cage':failures.extend(f'{path} frame{f}: '+error for error in support_errors(pos))
   if path=='dq_cage' and pos[:,2].min()<-.004:failures.append(f'{path} frame{f}: floor penetration{pos[:,2].min()}')
   if path=='dq_cage':
    head_ids=set(np.flatnonzero(groups['Head']>.5).tolist())
    faces=[list(p.vertices) for p in m.polygons if all(i in head_ids for i in p.vertices)]
    bvh=BVHTree.FromPolygons([Vector(p) for p in pos],faces)
    for side,suffix in [('Left','L'),('Right','R')]:
     signed=[]
     for point in pos[masks['whole_hand_'+suffix]]:
      nearest,normal,face,distance=bvh.find_nearest(Vector(point));signed.append((Vector(point)-nearest).dot(normal))
     wrist=r.pose.bones[side+'Hand'].head;elbow=r.pose.bones[side+'ForeArm'].head;palm=r.pose.bones[side+'Middle1'].head
     angle=math.degrees((wrist-elbow).angle(palm-wrist))
     metrics['hand_head_'+suffix]={'minimum_signed_distance_m':min(signed),'vertices_more_than_4mm_inside':sum(value<-.004 for value in signed),'wrist_direction_deviation_degrees':angle,'basis':'Actual nearest Head-weighted surface normal;35degree wrist staging bound is authored, not clinical.'}
     if min(signed)<-.004:failures.append(f'{path} frame{f} hand{suffix}: head intersection')
     if angle>35.01:failures.append(f'{path} frame{f} hand{suffix}: wrist staging bound')
    joints.append({'id':'5266','frame':f,'joints':{pb.name:list(r.matrix_world@pb.head) for pb in r.pose.bones}})
    morph_samples.append({'frame':f,'weights':{key.name:float(key.value)for key in b.data.shape_keys.key_blocks if key.name!='Basis'}})
    refs={name:{'indices':p['indices'],'positions':[pos[i].tolist() for i in p['indices']],'min_z':metrics[name]['min_z'],'max_z':metrics[name]['max_z'],'state':p['state']} for name,p in patches.items()}
    if f in [0,30,75,120,150]:dq_references.append({'id':'5266','frame':f,'positions':pos.tolist()})
    references.append({'id':'5266','frame':f,'global_floor_z':float(pos[:,2].min()),'floor_plane_z':0,'patches':refs,'contacts':metrics,'pressed_back_profile':profile_metrics(pos)})
   samples.append({'id':'5266','path':path,'frame':f,'vertices':len(pos),'floor_min_z':float(pos[:,2].min()),'contacts':metrics,'pressed_back_profile':profile_metrics(pos)})
   e.to_mesh_clear()
   if (path=='dq_cage' and f in [0,19,37.5,112.5]) or (path=='native' and f in [0,37.5]):
    qa=qa_check.run(objects=[b.name],profile='game');native_qa.append({'path':path,'frame':f,'qa':qa,'warning_locations':qa_check.QA_WARNING_DETAILS})
    failures.extend(f'{path} frame{f}: '+msg for msg in qa['errors'])
  if path=='dq_cage':
   s.frame_set(1);bpy.context.view_layer.update();first_mats={p.name:p.matrix.copy() for p in r.pose.bones}
   s.frame_set(151);bpy.context.view_layer.update();loop=max(max(abs(float(x-y)) for rowa,rowb in zip(p.matrix,first_mats[p.name]) for x,y in zip(rowa,rowb)) for p in r.pose.bones)
   if loop>.0001:failures.append('Loop mismatch')
 # Check actual floor, frozen supports and airborne feet throughout the full
 # entry path. These data checks are not rendered frames or new shape keys.
 for mod in b.modifiers:mod.show_viewport=mod.show_render=mod.type=='ARMATURE'
 full_cycle=[];first_positions=None;last_positions=None
 for frame in range(151):
  _frame(s,frame);evaluated=b.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=evaluated.to_mesh()
  points=np.array([v.co[:]for v in mesh.vertices]);row={'frame':frame,'global_floor_z':float(points[:,2].min()),'patches':{},'pressed_back_profile':profile_metrics(points)}
  if frame==0:first_positions=points.copy()
  if frame==150:last_positions=points.copy()
  failures.extend(f'full cycle frame{frame}: '+error for error in support_errors(points))
  if row['global_floor_z']<-.004:failures.append(f'full cycle frame{frame}: floor penetration')
  for name,patch in patches.items():
   if patch['state']not in ['supported','lifted']:continue
   z=points[patch['indices'],2];near=float(np.mean(abs(z)<=.012))
   row['patches'][name]={'min_z':float(z.min()),'fraction_near_floor':near}
   if patch['state']=='supported'and(z.min()>.012 or near<.2):failures.append(f'full cycle frame{frame}: {name} unsupported')
   if patch['state']=='lifted'and z.min()<.05:failures.append(f'full cycle frame{frame}: {name} clearance')
  full_cycle.append(row);evaluated.to_mesh_clear()
 skin_loop=float(np.linalg.norm(first_positions-last_positions,axis=1).max())
 if skin_loop>.0001:failures.append('Actual cage vertex loop mismatch')
 hand_check=hand_separation(b,s)
 if any(row['minimum_nearest_normal_signed_distance_m']<-.0001 for row in hand_check['samples']):failures.append('Hand/finger surfaces intersect')
 (P/'hand-separation-report.json').write_text(json.dumps(hand_check,indent=2)+'\n')
 # Curated native proofs plus topology views of the actual DQ cage.
 cam=s.camera
 for path,f,filename,wire in [('dq_cage',0,'native-start-side.png',False),('dq_cage',37.5,'native-peak-oblique.png',False),('dq_cage',0,'wire-start-side.png',True),('dq_cage',37.5,'wire-peak-oblique.png',True)]:
  for mod in b.modifiers:mod.show_viewport=mod.show_render=(mod.type=='ARMATURE' or (path=='native' and mod.type=='MULTIRES'))
  _frame(s,f)
  if 'oblique' in filename:view=json.loads((P/'cameras.json').read_text())[0]
  else:view=json.loads((P/'cameras.json').read_text())[1]
  cam.location=view['position'];target=Vector(view['target']);cam.data.ortho_scale=view['scale']
  cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()
  s.display.shading.type='SOLID';s.display.shading.show_xray_wireframe=False
  wire_object=None
  if wire:
   wire_mesh=bpy.data.meshes.new_from_object(b.evaluated_get(bpy.context.evaluated_depsgraph_get()))
   wire_object=bpy.data.objects.new('QA5266_Wire',wire_mesh);s.collection.objects.link(wire_object)
   black=bpy.data.materials.new('QA5266_WireBlack');black.diffuse_color=(.015,.015,.015,1);wire_mesh.materials.clear();wire_mesh.materials.append(black)
   wm=wire_object.modifiers.new('QA5266_Wireframe','WIREFRAME');wm.thickness=.0007;wm.offset=1
  s.render.filepath=str(P/filename);bpy.ops.render.render(write_still=True)
  if wire_object:
   wm_data=wire_object.data;bpy.data.objects.remove(wire_object,do_unlink=True);bpy.data.meshes.remove(wm_data);bpy.data.materials.remove(black)
 for attr in [v.name for v in b.data.attributes if v.name.startswith('QA5266_')]:b.data.attributes.remove(b.data.attributes[attr])
 for mod in b.modifiers:mod.show_viewport=mod.show_render=mod.type=='ARMATURE'
 s.frame_set(1)
 source_sha=hashlib.sha256((P/'source.blend').read_bytes()).hexdigest()
 (P/'pose-samples.json').write_text(json.dumps(joints,indent=2)+'\n')
 (P/'source-morph-samples.json').write_text(json.dumps({'source_sha256':source_sha,'samples':morph_samples},indent=2)+'\n')
 (P/'runtime-surface-reference.json').write_text(json.dumps({'source_sha256':source_sha,'coordinate_frame':'Blender world metres','source_index_attribute':'_SOURCE_INDEX','source_vertices':10582,'skinning':'dualQuaternion','reference_kind':'native-armature-only-dual-quaternion-original-cage-with-explicit-local-position-normal-targets','pressed_back_profile':profile,'samples':references},separators=(',',':'))+'\n')
 report={'ok':not failures,'failures':failures,'source_sha256':source_sha,'correctives':['JointNeutral','JointRightCross','JointLeftCross'],'sample_frames':FRAMES,'tolerances':TOL,'loop_max_matrix_element_error':loop,'loop_max_skin_position_error_m':skin_loop,'samples':samples,'full_cycle_floor_support_checks':full_cycle,'geometry_checks':native_qa,'native_smooth_contact_differences':native_contact_differences,'contact_gate_basis':'Original raw45/midline19 retained diagnostically, including rejected flat criterion. Frozen neutral-source envelope lower38/midline18/ridges12 profile preserves source groove and excludes7 above-neutralSpine1head points from lower-back contact. Exact shared2/5mm profile criteria and actual pelvic/paraspinal/floor skin support all151. No Smooth/Multires proof.', 'pressed_back_acceptance':acceptance,'skinning':'dualQuaternion','limits':'Actual DQ cage floor/support checked at151frames; detailed contact/head/wrist checks at13phases. No Smooth or Multires enabled. Standard GLB requires optional runtime DQ adapter; primary owns GPU/browser review. No LBS quality claim.'}
 with gzip.open(P/'dq-reference.json.gz','wt',encoding='utf-8') as output:json.dump({'source_sha256':source_sha,'source_vertices':10582,'samples':dq_references},output,separators=(',',':'))
 (P/'surface-contact-report.json').write_text(json.dumps(report,indent=2)+'\n')
 (P/'asset-qa.json').write_text(json.dumps({'source_sha256':source_sha,'correctives':['JointNeutral','JointRightCross','JointLeftCross'],'blender':bpy.app.version_string,'pass':all(x['qa']['pass'] for x in native_qa),'samples':native_qa},indent=2)+'\n')
 print('QA_RESULT',json.dumps({'ok':not failures,'failures':failures,'loop':loop}),flush=True)
 return report
if __name__=='__main__':
 result=run()
 assert result['ok'],result['failures']
