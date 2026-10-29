"""Source-bound, full-cycle lower-back cue check using frozen original IDs."""
import hashlib,json
from pathlib import Path
import bpy,numpy as np
P=Path(__file__).resolve().parent;S=P.parents[2]/'batch-004/assets/0003'
bpy.ops.wm.open_mainfile(filepath=str(P/'source.blend'))
body=bpy.data.objects['SK_BlenderStudioHuman'];scene=bpy.context.scene
for modifier in body.modifiers:
 modifier.show_viewport=modifier.show_render=modifier.type=='ARMATURE'
 if modifier.type=='ARMATURE':modifier.use_deform_preserve_volume=True
original=json.loads((S/'landmarks.json').read_text());lumbar=original['patches']['lumbar_arch']['indices']
midline=[i for i in lumbar if abs(body.data.vertices[i].co.x)<=.03]
assert len(lumbar)==45 and midline
supports={n:original['patches'][n]['indices']for n in ['pelvic_support_L','pelvic_support_R']}
tolerances={'minimum_whole_skin_z_m':-.00035,'maximum_each_original_pelvic_patch_minimum_z_m':.002,'maximum_original_lumbar_patch_median_z_m':.005,'minimum_original_lumbar_fraction_within_5mm':.5,'minimum_each_midline_point_z_m':-.00035,'maximum_each_midline_point_z_m':.002}
failures=[];rows=[]
for frame in range(151):
 scene.frame_set(frame+1);bpy.context.view_layer.update();ev=body.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=ev.to_mesh();points=np.array([body.matrix_world@v.co for v in mesh.vertices]);ev.to_mesh_clear()
 assert len(points)==10582
 z=points[:,2];lz=z[lumbar];mz=z[midline]
 row={'frame':frame,'whole_skin_minimum_z_m':float(z.min()),'whole_skin_lowest_original_id':int(z.argmin()),'pelvic_patch_minimum_z_m':{n:float(z[ids].min())for n,ids in supports.items()},'lumbar_positions_z_m':lz.tolist(),'lumbar_patch_median_z_m':float(np.median(lz)),'lumbar_patch_minimum_z_m':float(lz.min()),'lumbar_patch_maximum_z_m':float(lz.max()),'lumbar_fraction_within_5mm':float(np.mean(abs(lz)<=.005)),'midline_minimum_z_m':float(mz.min()),'midline_maximum_z_m':float(mz.max()),'midline_positions_z_m':mz.tolist()}
 checks={'whole_skin_floor':z.min()>=-.00035,'both_original_pelvic_supports':all(z[ids].min()<=.002 for ids in supports.values()),'lumbar_median':np.median(lz)<=.005,'lumbar_near_fraction':np.mean(abs(lz)<=.005)>=.5,'every_midline_point':mz.min()>=-.00035 and mz.max()<=.002}
 row['pass']=all(checks.values());row['failed_checks']=[n for n,v in checks.items()if not v]
 if not row['pass']:failures.append({'frame':frame,'failed_checks':row['failed_checks']})
 rows.append(row)
report={'id':'2395','pass':not failures,'source_sha256':hashlib.sha256((P/'source.blend').read_bytes()).hexdigest(),'source_cue':{'path':'catalogue/exercises/2395.json','pointer':'/instructions/4','text':'Keep your lower back pressed down.'},'criterion_authority':'Primary-selected illustration QC tolerances, not clinical source facts. Frozen before accepted fitting; no posthoc patch or tolerance changes.','frozen_patch_source':'batch-004/assets/0003/landmarks.json','frozen_patch_source_sha256':hashlib.sha256((S/'landmarks.json').read_bytes()).hexdigest(),'original_lumbar_ids':lumbar,'midline_ids':midline,'midline_subset_definition':'Only original45-ID lumbar_arch entries whose original neutral Basis abs(x)<=0.03m','pelvic_patch_ids':supports,'tolerances':tolerances,'source_vertices':10582,'skinning':'dualQuaternion','modifier_scope':'Only Armature enabled, preserve volume; all three current compact POSITION correctives included.','samples':rows,'failures':failures,'limits':'Actual native DQ skin and the separate floor plane; final GLB parity and neutral visual anatomy require their own receipts.'}
(P/'lower-back-flat-history.json').write_text(json.dumps(report,indent=2)+'\n')
print('LOWER_BACK_CUE',json.dumps({'pass':report['pass'],'failed_frames':len(failures),'midline_ids':midline,'maximum_lumbar_median_m':max(r['lumbar_patch_median_z_m']for r in rows),'minimum_skin_z_m':min(r['whole_skin_minimum_z_m']for r in rows)}))
assert report['pass'],failures[:3]
