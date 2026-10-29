"""Saved-action native DQ verification against the frozen anatomical profile."""
import hashlib,json
from pathlib import Path
import bpy,numpy as np
P=Path(__file__).resolve().parent;S=P.parents[2]/'batch-004/assets/0003';H=P.parents[1]/'posture-support'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
contract=json.loads((P/'support-contract.json').read_text());profile=json.loads((P/'frozen-neutral-envelope.json').read_text());old=json.loads((H/'frozen-support-masks.json').read_text())
assert sha(P/'frozen-neutral-envelope.json')==contract['profile_sha256']
assert sha(P/'support-contract.json')==sha(H/'support-contract.json')
lower=profile['lower_lumbar_ids'];mid=profile['lower_midline_ids'];ridges=profile['direct_ridge_ids'];raw45=old['patches']['lumbar_arch'];raw19=old['patches']['lumbar_midline'];depth=np.array([profile['expected_neutral_groove_depth_m'][str(i)]for i in lower]);middepth=np.array([profile['expected_neutral_groove_depth_m'][str(i)]for i in mid]);qc=profile['qc']
bpy.ops.wm.open_mainfile(filepath=str(P/'source.blend'));body=bpy.data.objects['SK_BlenderStudioHuman'];scene=bpy.context.scene
assert [a.name for a in bpy.data.actions]==['Exercise_2395']
for m in body.modifiers:
 m.show_viewport=m.show_render=m.type=='ARMATURE'
 if m.type=='ARMATURE':m.use_deform_preserve_volume=True
rows=[];failures=[]
for frame in range(151):
 scene.frame_set(frame+1);bpy.context.view_layer.update();e=body.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=e.to_mesh();p=np.array([body.matrix_world@v.co for v in mesh.vertices]);e.to_mesh_clear();assert p.shape==(10582,3)
 adjusted=p[lower,2]-depth;adjustedmid=p[mid,2]-middepth
 pelvic={n:float(p[old['patches'][n],2].min())for n in ['pelvic_support_L','pelvic_support_R']}
 checks={'whole_skin_floor':p[:,2].min()>=qc['whole_body_min_z_m'],'both_original_pelvic_supports':all(v<=qc['both_original_pelvic_patch_min_max_m']for v in pelvic.values()),'profile_adjusted_median':np.median(adjusted)<=qc['lower_profile_adjusted_median_max_m'],'profile_adjusted_contact_fraction':np.mean(abs(adjusted)<=.005)>=qc['lower_profile_adjusted_fraction_abs_within_5mm_min'],'every_profile_adjusted_midline_point':adjustedmid.max()<=qc['every_lower_midline_adjusted_residual_max_m'],'direct_ridge':p[ridges,2].max()<=qc['direct_ridge_max_z_m']}
 row={'frame':frame,'pass':all(checks.values()),'failed_checks':[n for n,v in checks.items()if not v],'whole_skin_minimum_z_m':float(p[:,2].min()),'whole_skin_lowest_original_id':int(p[:,2].argmin()),'pelvic_patch_minimum_z_m':pelvic,'raw_original45_z_m':p[raw45,2].tolist(),'raw_failed_flat_midline19_z_m':p[raw19,2].tolist(),'raw_original45_median_z_m':float(np.median(p[raw45,2])),'profile_adjusted_lower38_z_m':adjusted.tolist(),'profile_adjusted_median_z_m':float(np.median(adjusted)),'profile_adjusted_fraction_within_5mm':float(np.mean(abs(adjusted)<=.005)),'profile_adjusted_midline18_z_m':adjustedmid.tolist(),'maximum_profile_adjusted_midline_z_m':float(adjustedmid.max()),'direct_ridge12_z_m':p[ridges,2].tolist()}
 if not row['pass']:failures.append({'frame':frame,'failed_checks':row['failed_checks']})
 rows.append(row)
report={'id':'2395','pass':not failures,'source_sha256':sha(P/'source.blend'),'support_contract_sha256':sha(P/'support-contract.json'),'profile_sha256':sha(P/'frozen-neutral-envelope.json'),'source_cue':{'path':'catalogue/exercises/2395.json','pointer':'/instructions/4','text':'Keep your lower back pressed down.'},'criterion_authority':'Root-selected physical illustration QC. Frozen neutral source-groove depth is subtracted only for the named lower-lumbar profile metric; raw45/19 heights are retained. No flat-groove, clinical or globalcollisionfree claim.','prior_failed_flat_test':'lower-back-flat-history.json','trusted_baseline_receipt':'../../posture-support/baseline-native-report.json','trusted_baseline_receipt_sha256':sha(H/'baseline-native-report.json'),'raw_original45_ids':raw45,'raw_failed_flat_midline19_ids':raw19,'lower_lumbar_ids':lower,'lower_midline_ids':mid,'direct_ridge_ids':ridges,'profile_neutral_groove_depth_m':profile['expected_neutral_groove_depth_m'],'tolerances':qc,'source_vertices':10582,'skinning':'dualQuaternion','reference_kind':'native saved keyed action, only Armature enabled; composed support targets included','samples':rows,'failures':failures}
(P/'lower-back-cue-verification.json').write_text(json.dumps(report,indent=2)+'\n')
print('LOWER_BACK_CUE',json.dumps({'pass':not failures,'failed_frames':len(failures),'minimum_skin_z_m':min(r['whole_skin_minimum_z_m']for r in rows),'maximum_profile_median_z_m':max(r['profile_adjusted_median_z_m']for r in rows),'maximum_profile_midline_z_m':max(r['maximum_profile_adjusted_midline_z_m']for r in rows)}));assert not failures,failures[:3]
