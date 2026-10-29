"""Curate only the final integrated source, verification evidence and exact inputs."""
from pathlib import Path
import json,hashlib,collections
F=Path(__file__).resolve().parent;B=F.parent;IDS=['1405','4515','3995','1404']
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text())
write=lambda p,d:p.write_text(json.dumps(d,indent=2)+'\n')
source_sha=sha(F/'source.blend');model_sha=sha(F/'motion.glb');invariants=read(F/'invariant-verification.json');assert invariants['ok']and invariants['source_sha256']==source_sha
component=read(F/'cuff-component-dependency.json');assert component['root_native_shape_accepted']
route=read(F/'route-native-parity.json');assert route['ok']and route['source_sha256']==source_sha
continuity=read(F/'continuity-wrist-detour.json');assert continuity['source_sha256']==source_sha
native_identity=read(F/'accepted-native-identity.json');decoded_identity=read(F/'accepted-decoded-identity.json')
for ID in ['1404','4515','1405']:
 assert native_identity[ID]['final_source_sha256']==source_sha and decoded_identity[ID]['final_glb_sha256']==model_sha
 assert native_identity[ID]['all151_native_POSITION_max_error_m']==native_identity[ID]['all151_native_NORMAL_max_vector_error']==native_identity[ID]['all151_51bone_matrix_max_element_error']==0
 assert decoded_identity[ID]['all151_actual_Three_DQ_POSITION_max_error_m']==decoded_identity[ID]['all151_shader_equivalent_DQ_NORMAL_max_vector_error']==decoded_identity[ID]['all151_51bone_world_matrix_max_element_error']==0

def physical_summary(report):
 allowed=set();diagnostics=[];hard=[]
 for row in report['samples']:
  for label,value in row['arm_self_clearance'].items():
   if not value['exact_triangle_crossings']:continue
   pairs=value['dominant_bone_pairs'];local_attachment=label!='left_arm_right_arm'and pairs and all(p in ['LeftArm/Spine1','RightArm/Spine1']for p in pairs)
   item={'frame':row['frame'],'skin_origin':row.get('skin_origin'),'category':label,'pairs':pairs,'crossing_source_domains':value['crossing_domains'],'first_crossing_source_faces':value['first_crossing_source_faces']}
   if local_attachment:
    diagnostics.append(item);allowed.add('frame'+str(row['frame'])+': '+label+' source-bound actual skin crossings '+str(value['exact_triangle_crossings']))
   else:hard.append(item)
 unexpected=[x for x in report['failures']if x not in allowed];assert not hard and not unexpected,{'hard_pairs':hard[:2],'other_failures':unexpected[:5]}
 return {'integer_states':report['native_integer_frames'],'additional_native_fractional_states':report['additional_fractional_frames'],'hard_crossing_or_other_failure_count':0,'raw_gate_ok':report['ok'],'raw_failure_count':len(report['failures']),'localized_Arm_Spine1_diagnostic_category_samples':len(diagnostics),'localized_attachment_unique_frames':len({x['frame']for x in diagnostics}),'localized_Arm_Spine1_exact_pair_sum':sum(sum(x['pairs'].values())for x in diagnostics),'minimum_skin_floor_z_m':report['minimum_floor_z_m'],'minimum_triangle_area_m2':report['minimum_triangle_area_m2'],'loop_skin_error_m':report['loop_skin_error_m'],'maximum_native_decoded_POSITION_error_m':report['maximum_full_cycle_native_decoded_error_m']},diagnostics

summaries={};failure_summary={};asset_files=[]
common=['source.blend','motion.glb','clip.json','cameras.json','authoring-context.json','motion-witnesses.json','pose-samples.json','runtime-surface-reference.json','surface-landmarks.json','dq-reference.json.gz','normal-reference.json.gz','source-verification.json','surface-contact-report.json','decoded-source-readback.json','decoded-physical-report.json','export-verification.json','raw-asset-qa.json','environment.json','local-binding-report.json','morph-weight-export.json']
for ID in IDS:
 P=B/'assets'/ID;assert sha(P/'source.blend')==source_sha and sha(P/'motion.glb')==model_sha
 native=read(P/'surface-contact-report.json');decoded=read(P/'decoded-physical-report.json');export=read(P/'export-verification.json');qa=read(P/'raw-asset-qa.json')
 for d in [native,decoded,export,qa]:assert d['source_sha256']==source_sha
 assert export['ok']and export['glb_sha256']==model_sha and export['morph_targets']==3
 assert native['native_integer_frames']==decoded['native_integer_frames']==151
 assert qa['pass']and all(not x['report']['errors']for x in qa['samples'])
 ns,nd=physical_summary(native);ds,dd=physical_summary(decoded);summaries[ID]={'native':ns,'actual_decoded':ds,'game_profile_errors':sum(len(x['report']['errors'])for x in qa['samples']),'game_profile_warnings':sum(len(x['report']['warnings'])for x in qa['samples']),'maximum_sparse_DQ_POSITION_error_m':export['maximum_full_dq_vertex_error_m'],'maximum_source_NORMAL_vector_error':export['maximum_normal_vector_error'],'maximum_morph_NORMAL_vector_error':export['maximum_morph_NORMAL_vector_error'],'maximum_51_joint_error_m':export['maximum_joint_error_m']};failure_summary[ID]={'native_localized_attachment_diagnostics':nd,'actual_decoded_localized_attachment_diagnostics':dd}
 early=read(P/'early-report.json');assert early['source_sha256']==source_sha;proofs=[{'frame':x['frame'],'phase':x['phase'],'view':x['view'],'file':x['file']}for x in early['proofs']]
 for phase,frame in ([('right-over-wrap',37.5),('repeat-right-over-wrap',112.5)]if ID=='3995'else[('peak',60)]):
  for view in ['front','rear']:proofs.append({'frame':frame,'phase':phase,'view':'hands_'+view,'file':f'early-{source_sha[:12]}-{phase}-hands-{view}.png'})
 for x in proofs:assert(P/x['file']).is_file()
 write(P/'proofs.json',{'source_sha256':source_sha,'proofs':proofs})
 (P/'README.md').write_text(f"# Exercise {ID}\n\nEditable shared source and standard GLB action `Exercise_{ID}`, five seconds at 30 fps, native frames 1–151/runtime 0–150. Two whole-body cameras use native Blender coordinates. Source instructions, authored staging and workout hold are in `clip.json`.\n\nSource SHA256: `{source_sha}`. GLB SHA256: `{model_sha}`.\n\nAll 151 native and actual Three/DQ-decoded states were checked. There are zero hard hand/finger/forearm/opposite-arm or unrelated physical failures. Raw localized Arm/Spine1 attachment diagnostics remain explicit in the two physical reports and the family `failure-summary.json`; this is not a global self-collision-free claim. Game QA reports {summaries[ID]['game_profile_errors']} errors and {summaries[ID]['game_profile_warnings']} warnings. POSITION/NORMAL transport, three-target animation/reset, support, positive areas and loop closure are recorded separately. Root owns final GPU acceptance, fields, camera fitting and publication.\n")
 files=[P/x for x in common]+([P/'verification-reuse.json']if (P/'verification-reuse.json').exists()else[])+[P/'README.md',P/'proofs.json']+[P/x['file']for x in proofs]+[P/'curated-files.json']
 for p in files:
  if p.name!='curated-files.json':assert p.is_file(),p
 write(P/'curated-files.json',{'id':ID,'source_sha256':source_sha,'glb_sha256':model_sha,'files':[str(p.relative_to(Path.cwd()))for p in files]});asset_files.extend(files)
write(F/'failure-summary.json',{'source_sha256':source_sha,'glb_sha256':model_sha,'status':'Hard categories zero; localized attachment diagnostics retained for visible review. No crossings are removed from raw reports.','coordinates':'Original source and posed native Blender Z-up meters','actions':failure_summary})
report={'status':'LOCAL_VERIFICATION_COMPLETE_ROOT_FINAL_INTEGRATION_OWNED_SEPARATELY','source_sha256':source_sha,'glb_sha256':model_sha,'vertices':10582,'bones':51,'triangles':21160,'actions':['Exercise_'+x for x in IDS],'all_integer_states_per_action':151,'morph_targets':['OwnershipRightCross','OwnershipLeftCross','WrapRightOverCuff'],'canonical_invariants_exact':True,'existing_components_exact':True,'new_component_archive_sha256':component['archive_sha256'],'new_component_driver':'Held cuff follows original sin-squared p. The coherent transported acquisition route has a C1 anterior193.194mm Leftwrist detour with fixed arm lengths and unchanged forearm-local hand interpolation. All3components explicitly zero in the other actions.','root_actual_GPU_acceptance':{'model_sha256':model_sha,'receipt':'artifacts/exercise-batches/batch-009/logs/self-hug-detour-5c960475/capture-peaks.json','scope':'20poses including formerhandcrossingf21/f22/f23/f53; wholebody andcuffdetail'},'bone_continuity':continuity['summary'],'route_native_parity':route,'accepted_three_action_POSITION_NORMAL_and_51bone_identity':True,'3995_endpoint_sampling':decoded_identity['3995'],'no_runtime_vertex_cache':True,'verification':summaries,'limitation':'Raw localized Arm/Spine1 attachment intersections remain explicit. They are not game-QA errors/warnings and do not imply global self-collision freedom. Root owns final metadata/camera integration.'};write(F/'delivery-report.json',report)
helpers=['README.md','source.blend','motion.glb','motion.py','build.py','export_motion.py','fix_morph_weights.py','clearance_checks.py','verify_native.py','verify_export.mjs','verify_invariants.py','verify_conventional_identity.py','verify_accepted_identity.mjs','write_packet.py','reuse_accepted_verification.py','dependencies.json','cuff-component-dependency.json','invariant-verification.json','accepted-native-identity.json','accepted-decoded-identity.json','failure-summary.json','delivery-report.json']
helpers+=['coherent_route.py','coherent-route-coefficients.npz','coherent-hand-matrices.npz','frozen-route-parity.json','coherent-hand-report.json','route-integration-handoff.md','coherent_hand_mid-front.png','coherent_hand_mid-side.png','coherent_hand_mid-rear.png','route-accepted-dependencies.json','route-dependency.json','wrap_acquisition.py','wrist-detour.json','derive_wrist_detour.py','wrist-detour-derivation.json','witness_wrist_detour.py','wrist-detour-witness.json','verify_route_witness.py','route-native-parity.json','authored-route-reference.npz','inspect_joint_continuity.py','continuity-before-2c7213.json','continuity-wrist-detour.json','continuity-accepted-1404.json','continuity-accepted-4515.json','continuity-accepted-1405.json']
helpers+=['untouched-route-reference.npz']
identity_inputs=['checkpoints/25b5af549368/motion.glb','checkpoints/f87959934283/motion.glb','held-wrap-right-over/source.blend','held-wrap-tangent-88c2da9b3095/source.blend']
reuse=F/'checkpoints/2c7213de9cff'
identity_inputs+=['checkpoints/2c7213de9cff/'+x for x in ['accepted-native-identity.json','accepted-decoded-identity.json']]
for ID in ['1404','4515','1405']:
 identity_inputs+=['checkpoints/2c7213de9cff/'+ID+'/'+name for name in ['surface-contact-report.json','decoded-physical-report.json','source-verification.json','decoded-source-readback.json','runtime-surface-reference.json','surface-landmarks.json','pose-samples.json','dq-reference.json.gz','normal-reference.json.gz','raw-asset-qa.json']]
files=[F/x for x in helpers+identity_inputs]+asset_files+[F/'curated-files.json']
for p in files:
 if p.name!='curated-files.json':assert p.is_file(),p
write(F/'curated-files.json',{'source_sha256':source_sha,'glb_sha256':model_sha,'files':sorted(set(str(p.relative_to(Path.cwd()))for p in files)),'read_only_dependencies':read(F/'dependencies.json')['files'],'excluded':'All trials, rejected candidates, old proofs, logs, caches, environments, backups and temporary decoded verification exchanges.'})
print('FROZEN_PACKET',source_sha,model_sha,'files',len(files))
