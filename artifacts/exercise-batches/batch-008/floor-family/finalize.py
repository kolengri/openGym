"""Freeze accepted local evidence and explicit, self-inclusive curated manifests."""
from pathlib import Path
import hashlib,json,gzip
F=Path(__file__).resolve().parent;ROOT=F.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def write(path,data):path.write_text(json.dumps(data,indent=2)+'\n')
def manifest(path,data):
    data['included_files'].append({'path':'curated-files.json','self':True,'integrity':'self_integrity.sha256 canonical JSON rule'})
    digest=hashlib.sha256(json.dumps(data,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    data['self_integrity']={'algorithm':'SHA256','canonicalization':'UTF-8 JSON; sorted keys; compact separators; omit self_integrity; no trailing newline','sha256':digest}
    write(path,data)
def rows(base,names):
    result=[]
    for name in names:
        p=base/name;assert p.is_file(),p
        result.append({'path':name,'sha256':sha(p),'bytes':p.stat().st_size})
    return result
inputs=['artifacts/bodyweight-five/bodyweight-five.blend','artifacts/bodyweight-five/build_motion.py','artifacts/bodyweight-five/inspect_situp_contacts.py','artifacts/exercise-batches/batch-003/authoring.py','artifacts/exercise-batches/batch-005/findings.md','artifacts/exercise-batches/batch-006/upright-cardio-family/binding.py','artifacts/exercise-batches/batch-007/prone-family/motion.py','artifacts/exercise-batches/batch-007/prone-family/palm_frame.py','artifacts/exercise-batches/dual-quaternion.js','artifacts/exercise-batches/batch-008/asset-interface.json','artifacts/exercise-batches/batch-008/authoring-handoff.md']
inputs += [f'catalogue/exercises/{id}.json'for id in ['3204','4935','3483']]+[f'artifacts/exercise-batches/batch-008/contexts/{id}.json'for id in ['3204','4935','3483']]
deps=[{'path':p,'sha256':sha(ROOT/p)}for p in inputs]
asset_files=['source.blend','motion.glb','clip.json','cameras.json','pose-samples.json','runtime-surface-reference.json','surface-landmarks.json','dq-reference.json.gz','normal-reference.json.gz','source-verification.json','surface-contact-report.json','decoded-source-readback.json','decoded-physical-report.json','export-verification.json','raw-asset-qa.json','local-binding-report.json','early-proof-readback.json','qa-random.png','qa-wire.png']
reports=[]
for id in ['3204','4935','3483']:
    p=F.parent/'assets'/id
    native=json.loads((p/'surface-contact-report.json').read_text());decoded=json.loads((p/'decoded-physical-report.json').read_text());export=json.loads((p/'export-verification.json').read_text());qa=json.loads((p/'raw-asset-qa.json').read_text())
    assert native['ok']and decoded['ok']and export['ok']and qa['pass']
    assert all(not q['report']['errors']for q in qa['samples'])
    normals=json.loads(gzip.decompress((p/'normal-reference.json.gz').read_bytes()));assert len(normals['samples'])==5 and all(len(s['normals'])==10582 for s in normals['samples'])
    ref=json.loads(gzip.decompress((p/'dq-reference.json.gz').read_bytes()));assert len(ref['samples'])==5
    xyz=list(zip(*(v for s in ref['samples']for v in s['positions'])));lo=list(map(min,xyz));hi=list(map(max,xyz))
    warnings=[{'frame':q['frame'],'warnings':q['report']['warnings']}for q in qa['samples']if q['report']['warnings']]
    report={'id':id,'local_acceptance_pass':True,'source_sha256':sha(p/'source.blend'),'glb_sha256':sha(p/'motion.glb'),'vertices':10582,'triangles':21160,'bones':51,'exported_objects':2,'materials':1,'native_diagnostic_bounds_m':{'minimum':lo,'maximum':hi,'dimensions':[b-a for a,b in zip(lo,hi)],'basis':'Five complete native diagnostic poses, Blender Z-up meters'},'blender_version':'5.2.3 LTS','native_samples':151,'actual_decoded_samples':151,'full_source_DQ_position_reference_samples':5,'full_source_DQ_normal_reference_samples':5,'joint_reference_bones':51,'joint_reference_samples':13,'maximum_full151_native_decoded_error_m':decoded['maximum_full151_native_decoded_error_m'],'maximum_fiveframe_DQ_position_error_m':export['maximum_full_dq_vertex_error_m'],'maximum_fiveframe_DQ_normal_vector_error':export['maximum_full_fiveframe_DQ_normal_error'],'maximum_joint_error_m':export['maximum_joint_error_m'],'minimum_floor_z_m':decoded['minimum_floor_z_m'],'minimum_triangle_area_m2':decoded['minimum_triangle_area_m2'],'loop_native_skin_error_m':native['loop_skin_error_m'],'loop_decoded_skin_error_m':decoded['loop_skin_error_m'],'game_qa_errors':0,'retained_raw_warnings':warnings,'game_qa_reuse':{'from':'4935','reason':'Byte-identical source and model, identical action transform tracks; native/decoded151 action-specific gates run independently.'}if id=='3483'else None,'warning_disposition':'No game-profile errors or warnings at the diagnostic poses. The original out-of-tile UV metric is preserved under the exact UV invariant; the neutral material contains no image texture. Original low-poly hip and shoulder/armpit facets remain visible and were accepted in root native review.','source_binding_corrective':'Read-only causal waist/plantar helper; no geometry, Basis, UV, topology or rest skeleton changes. Actual saved <=4 influence normalized weights read back.','shape_keys':0,'native_visual_acceptance':'Root accepted3204 start/peak side/oblique and refreshed4935 lift/sweep/hips proofs; root actualGPU acceptance remains pending.','integration_pending':['Root actual GPU playback/surface acceptance','Root source-label soft muscle fields','Root camera-width fitting including3204 oblique foot edge'],'not_a_global_collision_or_clinical_certificate':True}
    if id!='3204':
        peak=decoded['samples'][72]['skin_patch_minima_m'];report['sweep_skin_support_and_lift_m']={k:peak[k]for k in ['pelvis','lowertrunk','foot_Left','foot_Right','upperchest']}
    write(p/'delivery-report.json',report);reports.append(report)
    names=asset_files+['delivery-report.json']+[q.name for q in sorted(p.glob('early-*.png'))]
    if id=='3204':names+=['support-plane-start.png','support-plane-peak.png']
    manifest(p/'curated-files.json',{'id':id,'source_sha256':sha(p/'source.blend'),'glb_sha256':sha(p/'motion.glb'),'included_files':rows(p,names),'read_only_dependencies':deps,'excluded':['*.log','__pycache__','*.blend1','trial reports','raw-diagnostics','verification-exchange-path.txt','temporary decoded151 vertex buffers','environments'],'root_integration_may_update':['clip.json','cameras.json'],'source_and_motion_frozen':True})
assert reports[1]['source_sha256']==reports[2]['source_sha256']and reports[1]['glb_sha256']==reports[2]['glb_sha256']
write(F/'delivery-report.json',{'family':'floor-family','status':'local_native_decoded_and_game_QA_pass;root_integration_pending','assets':reports,'shared_model':{'4935':'4935','3483':'4935','identical_source_and_GLB_hashes':True,'distinct_actions':['Exercise_4935','Exercise_3483']},'read_only_dependencies':deps,'remaining_limits':['Actual GPU playback, artistic muscle fields and camera-width integration remain root-owned.','Original low-poly hip and overhead shoulder/armpit facets remain visible.','Local nearest-normal whole-arm/hand-versus-leg diagnostic is not a global collision-free certificate.'],'no_runtime_vertex_caches':True,'source_geometry_rest_UV_sourceIDs_invariant':True})
owned=['build.py','motion.py','export_motion.py','verify_native.py','verify_export.mjs','review.py','write_metadata.py','finalize.py','README.md','superseded-diagnostics.json','delivery-report.json']
included=rows(F,owned)
included += [{'path':'../assets/'+id+'/curated-files.json','sha256':sha(F.parent/'assets'/id/'curated-files.json'),'bytes':(F.parent/'assets'/id/'curated-files.json').stat().st_size}for id in ['3204','4935','3483']]
manifest(F/'curated-files.json',{'family':'floor-family','included_files':included,'read_only_dependencies':deps,'excluded':['logs','__pycache__','raw-diagnostics','trial reports','temporary decoded buffers','backups','environments']})
print(json.dumps({'ok':True,'assets':[{'id':r['id'],'source_sha256':r['source_sha256'],'glb_sha256':r['glb_sha256'],'max151error_m':r['maximum_full151_native_decoded_error_m']}for r in reports]},indent=2))
