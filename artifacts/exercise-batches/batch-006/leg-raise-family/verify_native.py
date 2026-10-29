"""Saved-source all151 physical/game QA and five diagnostic DQ references.

Temporary full-skin QA streams feed exact decoded parity; they are never runtime
inputs and are removed after verification, excluded from the curated packet.
"""
import sys,json,math,gzip,hashlib,copy
from pathlib import Path
import bpy,numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
P=Path(__file__).resolve().parent;B=P.parent;sys.path[:0]=[str(P),str(Path.home()/'.codex/skills/blender-asset-qa/scripts'),str(B.parents[1]/'bodyweight-next-five')]
import family_common as c,qa_check,warning_observer
warning_observer.install(qa_check)
bpy.ops.wm.open_mainfile(filepath=str(P/'source.blend'));b=bpy.data.objects['SK_BlenderStudioHuman'];r=bpy.data.objects['RIG_BlenderStudioHuman'];s=bpy.context.scene;keys=b.data.shape_keys;sha=hashlib.sha256((P/'source.blend').read_bytes()).hexdigest();W=[{b.vertex_groups[g.group].name:float(g.weight)for g in v.groups}for v in b.data.vertices];assert W==json.loads((P/'source-build-receipt.json').read_text())['actual_weights'];assert max(map(len,W))<=4 and max(abs(sum(w.values())-1)for w in W)<2e-6
for mod in b.modifiers:
 mod.show_viewport=mod.show_render=mod.type=='ARMATURE'
 if mod.type=='ARMATURE':mod.use_deform_preserve_volume=True
R=np.array([v.co[:]for v in b.data.vertices]);b.data.calc_loop_triangles();tri=np.array([t.vertices[:]for t in b.data.loop_triangles]);names=[k.name for k in keys.key_blocks if k.name!='Basis'];sets={'arms':set(),'legs':set(),'foot_L':set(),'foot_R':set()}
for i,w in enumerate(W):
 arm=sum(v for n,v in w.items()if any(n.startswith(side+token)for side in ['Left','Right']for token in ['Shoulder','Arm','ForeArm','Hand','Index','Middle','Ring','Little','Thumb']));leg=sum(v for n,v in w.items()if any(n.startswith(side+token)for side in ['Left','Right']for token in ['UpLeg','Leg','Foot','ToeBase']))
 if arm>.5:sets['arms'].add(i)
 if leg>.5:sets['legs'].add(i)
 for side,suffix in [('Left','L'),('Right','R')]:
  if sum(v for n,v in w.items()if n in [side+'Foot',side+'ToeBase'])>.5:sets['foot_'+suffix].add(i)
faces={n:[row.tolist()for row in tri if any(int(i)in domain for i in row)]for n,domain in sets.items()};(P/'physical-domains.json').write_text(json.dumps({'source_sha256':sha,'selection':'Actual saved weights >50% regional sum; triangle domain includes any incident vertex, conservatively retaining boundary triangles.','source_domains':{n:sorted(v)for n,v in sets.items()}},indent=2)+'\n')
FRAMES=[0,12.5,30,37.5,75,112.5,120,137.5,150];native=json.loads((P/'native-action-readback.json').read_text());assert native['source_sha256']==sha
patches={'lumbar_arch':{'indices':c.MASKS['lumbar_arch'],'state':'observed','rationale':'All45 frozen original lumbar IDs, raw metrics retained; source groove offsets separately explicit.'},'lower_lumbar_profile':{'indices':c.PROFILE['lower_lumbar_ids'],'state':'observed','rationale':'Frozen lower38 source posterior-envelope profile with neutral groove retained; strict2/5mm contract in source-neutral-envelope.json.'},'pelvic_support_L':{'indices':c.MASKS['pelvic_support_L'],'state':'supported','rationale':'Original4 posterior pelvic IDs, minimum<=2mm.'},'pelvic_support_R':{'indices':c.MASKS['pelvic_support_R'],'state':'supported','rationale':'Original4 posterior pelvic IDs, minimum<=2mm.'},'upper_back_anchor':{'indices':[3303],'state':'observed','rationale':'Original pure-Spine1 diagnostic3303,4.987mm in accepted frozen pose; exact target protection.'},'upper_back_floor_anchors':{'indices':[3311,8568],'state':'supported','rationale':'Actual frozen pre-corrective upper-back floor anchors; already protected before cervical target construction.'},'occiput_anchor':{'indices':[8040],'state':'observed','rationale':'Original pure-Head posterior skull anchor; supported in flat-head clips, raised in4001.'}}
for suffix in ['L','R']:patches['foot_'+suffix]={'indices':sorted(sets['foot_'+suffix]),'state':'airborne','rationale':'Entire foot/toe weighted surface remains positively clear of floor, including low-leg phase.'}
TOL={'maximum_floor_penetration_m':.00035,'profile_median_max_m':.005,'profile_minimum_fraction_within5mm':.5,'midline_and_ridge_max_m':.002,'pelvic_patch_minimum_max_m':.002,'minimum_airborne_foot_clearance_m':.005,'minimum_whole_arm_hand_leg_clearance_m':.0005,'loop_skin_m':.0001,'actual_weight_sum_max_error':2e-6,'maximum_influences':4}
def frame(f):s.frame_set(int(f)+1,subframe=f%1);bpy.context.view_layer.update()
def points():
 ob=b.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=ob.to_mesh();v=np.array([v.co[:]for v in mesh.vertices]);ob.to_mesh_clear();return v

def physical(p):
 verts=[Vector(v)for v in p];trees={n:BVHTree.FromPolygons(verts,faces[n])for n in ['arms','legs']};overlap=trees['arms'].overlap(trees['legs']);minimum=float('inf');witness=None
 for region,other in [('arms','legs'),('legs','arms')]:
  for i in sets[region]:
   near,normal,face,distance=trees[other].find_nearest(verts[i])
   if distance<minimum:minimum=distance;witness={'region':region,'source_id':i,'opposite_triangle':face}
 areas=np.linalg.norm(np.cross(p[tri[:,1]]-p[tri[:,0]],p[tri[:,2]]-p[tri[:,0]]),axis=1)/2;m=c.support_metrics(p)
 return {'minimum_triangle_area_m2':float(areas.min()),'nonpositive_triangles':int(np.sum(areas<=1e-12)),'arm_hand_leg_intersections':len(overlap),'minimum_arm_hand_leg_clearance_m':minimum,'clearance_witness':witness,'airborne_foot_min_z_m':{q:float(p[sorted(sets['foot_'+q]),2].min())for q in ['L','R']},**m}

shared_physical=None;shared_game=None
for eid in ['4826','4001','5106','3590']:
 out=B/'assets'/eid;act=bpy.data.actions['Exercise_'+eid];r.animation_data.action=act;r.animation_data.action_slot=next(slot for slot in act.slots if slot.target_id_type=='OBJECT');keys.animation_data.action=act;keys.animation_data.action_slot=next(slot for slot in act.slots if slot.target_id_type=='KEY');currentpatches=copy.deepcopy(patches)
 if eid!='4001':currentpatches['occiput_anchor']['state']='supported'
 failures=[];rows=[];dq=[];morph=[];poses=[];surface=[];qareports=[];initial=None;initial_hips={};hip_drift=0.;loop=0.;same_skin_max_error=0.;source_stream=None
 if eid=='3590':source_stream=np.frombuffer(gzip.decompress((P/'.native-all151-4826.f32.gz').read_bytes()),dtype='<f4').reshape((151,10582,3))
 with gzip.open(P/f'.native-all151-{eid}.f32.gz','wb',compresslevel=5)as stream:
  for f in range(151):
   frame(f);p=points();stream.write(p.astype('<f4').tobytes())
   if eid=='3590':
    err=float(np.linalg.norm(p.astype('<f4')-source_stream[f],axis=1).max());same_skin_max_error=max(same_skin_max_error,err);assert err==0.;q=copy.deepcopy(shared_physical[f])
   else:q=physical(p)
   q['frame']=f;heads={pb.name:list(r.matrix_world@pb.head)for pb in r.pose.bones};expected=native['actions'][eid]['all151_joints'][f]['joints'];joint_error=max(float(np.linalg.norm(np.array(heads[n])-expected[n]))for n in heads);assert joint_error<1e-7;q['native_joint_readback_error_m']=joint_error
   for side in ['Left','Right']:
    hip=np.array(heads[side+'UpLeg']);initial_hips.setdefault(side,hip);hip_drift=max(hip_drift,float(np.linalg.norm(hip-initial_hips[side])));u=np.array(heads[side+'UpLeg'])-heads[side+'Leg'];v=np.array(heads[side+'Foot'])-heads[side+'Leg'];angle=math.degrees(math.acos(np.clip(u@v/(np.linalg.norm(u)*np.linalg.norm(v)),-1,1)));q.setdefault('knee_internal_degrees',{})[side]=angle
    if angle<179.99:failures.append(f'frame{f}:{side} nonstraight leg')
   if q['whole_body_min_z_m']<-.00035 or q['profile_median_m']>.005 or q['profile_fraction_within5mm']<.5 or q['midline_profile_max_m']>.002 or q['ridge_max_z_m']>.002 or max(q['pelvic_min_m'].values())>.002:failures.append(f'frame{f}:frozen posterior support/floor contract')
   if q['nonpositive_triangles']or q['arm_hand_leg_intersections']or q['minimum_arm_hand_leg_clearance_m']<.0005:failures.append(f'frame{f}:triangle/whole arm-hand versus leg clearance')
   if min(q['airborne_foot_min_z_m'].values())<.005:failures.append(f'frame{f}:airborne foot touches floor')
   if eid!='4001'and p[8040,2]>.002:failures.append(f'frame{f}:flat head not supported')
   if eid=='4001'and p[8040,2]<.020:failures.append(f'frame{f}:head not raised')
   if initial is None:initial=p.copy()
   if f==150:loop=float(np.linalg.norm(p-initial,axis=1).max())
   rows.append(q);morph.append({'frame':f,'weights':{n:float(keys.key_blocks[n].value)for n in names}})
   if f in [0,30,75,120,150]:dq.append({'id':eid,'frame':f,'positions':p.tolist()})
   if f%50==0:print('NATIVE_FRAME',eid,f,flush=True)
 for f in FRAMES:
  frame(f);p=points();poses.append({'id':eid,'frame':f,'joints':{pb.name:list(r.matrix_world@pb.head)for pb in r.pose.bones}});surface.append({'id':eid,'frame':f,'floor_plane_z':0,'global_floor_z':float(p[:,2].min()),'patches':{n:{**v,'positions':p[v['indices']].tolist(),'min_z':float(p[v['indices'],2].min()),'max_z':float(p[v['indices'],2].max())}for n,v in currentpatches.items()}})
  if f in [0,37.5,75,112.5]and eid!='3590':
   qa=qa_check.run(objects=[b.name],profile='game');qareports.append({'id':eid,'frame':f,'qa':qa,'warning_locations':qa_check.QA_WARNING_DETAILS})
   if not qa['pass']:failures.append(f'frame{f}:game QA errors')
 if eid=='3590':qareports=copy.deepcopy(shared_game)
 if loop>.0001 or hip_drift>1e-6:failures.append('loop/pelvis joint drift')
 if eid=='4826':shared_physical=copy.deepcopy(rows);shared_game=copy.deepcopy(qareports)
 with gzip.open(out/'dq-reference.json.gz','wt',compresslevel=9)as stream:json.dump({'source_sha256':sha,'source_vertices':10582,'samples':dq},stream,separators=(',',':'))
 (out/'pose-samples.json').write_text(json.dumps(poses,indent=2)+'\n');(out/'source-morph-samples.json').write_text(json.dumps({'source_sha256':sha,'samples':morph},indent=2)+'\n');(out/'landmarks.json').write_text(json.dumps({'id':eid,'source_sha256':sha,'source_vertices':10582,'coordinate_frame':'Blender Zup metres','floor':{'point':[0,0,0],'normal':[0,0,1]},'patches':currentpatches,'tolerances':TOL,'profile_contract':'../../leg-raise-family/source-neutral-envelope.json','basis':'Frozen original source anatomy with neutral centerline groove retained. Strict illustration2/5mm contact QC, not clinical validation.'},indent=2)+'\n');(out/'runtime-surface-reference.json').write_text(json.dumps({'id':eid,'source_sha256':sha,'source_vertices':10582,'coordinate_frame':'Blender Zup metres','source_index_attribute':'_SOURCE_INDEX','skinning':'dualQuaternion','reference_kind':'native-armature-only-original-cage-with-explicit-position-normal-targets','samples':surface},separators=(',',':'))+'\n')
 report={'id':eid,'ok':not failures,'failures':failures,'source_sha256':sha,'sampled_frames':151,'loop_skin_error_m':loop,'maximum_fixed_pelvis_hip_joint_drift_m':hip_drift,'tolerances':TOL,'samples':rows,'minimum_arm_hand_leg_clearance_m':min(q['minimum_arm_hand_leg_clearance_m']for q in rows),'minimum_triangle_area_m2':min(q['minimum_triangle_area_m2']for q in rows),'worst_floor_min_z_m':min(q['whole_body_min_z_m']for q in rows),'maximum_ridge_z_m':max(q['ridge_max_z_m']for q in rows),'maximum_midline_profile_residual_m':max(q['midline_profile_max_m']for q in rows),'minimum_airborne_foot_z_m':min(z for q in rows for z in q['airborne_foot_min_z_m'].values()),'shared_physical_check_reuse':({'from':'4826','all151_actual_float32_skin_max_difference_m':same_skin_max_error,'separate_action_and_morph_readback':True}if eid=='3590'else None),'limits':'Discrete all151 native DQ cages, conservative whole arm/hand and lower-limb triangle overlap plus two-way vertex/triangle witnesses. No continuous-time/global self-collision or clinical claim.'}
 (out/'surface-contact-report.json').write_text(json.dumps(report,indent=2)+'\n');(out/'mechanics-verification.json').write_text(json.dumps(report,indent=2)+'\n');(out/'asset-qa.json').write_text(json.dumps({'id':eid,'source_sha256':sha,'pass':all(q['qa']['pass']for q in qareports),'blender':bpy.app.version_string,'samples':qareports,'warning_disposition':'Original canonical cage/body, extreme straight-limb poses and tiny authorized≤.35mm floor intersections may retain generic topology/ground warnings. Mandatory game QA errors remain zero. Full source-bound floor/areas/clearance checks are separately strict.','identical_action_physics_reused_from':'4826'if eid=='3590'else None},indent=2)+'\n');print('NATIVE_RESULT',eid,json.dumps({'ok':not failures,'failures':failures,'clearance_m':report['minimum_arm_hand_leg_clearance_m'],'floor_m':report['worst_floor_min_z_m'],'loop_m':loop}),flush=True);assert not failures,failures
