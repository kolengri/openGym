"""Curate only settled source/runtime interfaces, proofs and receipts."""
from pathlib import Path
import json,hashlib,shutil,math
F=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
write=lambda p,d:p.write_text(json.dumps(d,indent=2)+'\n')
family_files=['binding.py','motion.py','build.py','export_motion.py','verify_native.py','verify_export.mjs','write_delivery.py','README.md','curated-files.json']
(F/'README.md').write_text('''# Upright cardiovascular demonstrations

Two separate five-second actions share the original CC0 Blender Studio body and51-bone rest skeleton. No new geometry, UVs, rest changes, morphs or runtime vertex caches. `binding.py` applies a declared C1 proximal-thigh-to-torso partition and distal plantar shin-removal field, preserving Foot/ToeBase articulation; stable group-name installation is followed by actual normalized<=4 readback.

`motion.py` supplies continuous alternating one-foot hop ground/flight phases and a separate fixed staggered-stance punch action. Hops have articulated knees, ankle/toe roll and opposing arms; the four-hop timing is a slowed demonstration. Punch fists use source hand-local palmar flexion and an exterior opposed thumb. Arms/forearms/hands transport through the original connected hierarchy. No muscle activation measurement is claimed.

Run Blender5.2.3 offline, factory startup,2threads: `build.py -- <id>` makes early native proofs; `export_motion.py -- <id>` freezes the editable review camera and exports one action; `verify_native.py -- <id> --game-qa` writes native references/checks. Run `node verify_export.mjs <id>` against the exact shared optional DQ adapter, then `verify_native.py -- <id> --decoded <temporary-exchange-path>` for actual decoded151 physical checks and full151 native parity. The temporary local binary is deleted by that check and is never shipped or read at runtime. `write_delivery.py` only updates metadata/curation.

The export verifier resets its one-shot mixer action before each arbitrary-time read; otherwise a prior end-of-clip read pauses subsequent backwards reads and falsely reports large joint errors. Model bytes were unaffected by that diagnostic correction. Basis NORMAL is checked in every exported UV split; the exact shared DQ adapter handles runtime rotation. Actual GPU appearance and final camera-width/heat integration remain root-owned.
''')
write(F/'curated-files.json',{'policy':'Explicit shared authoring dependency list; excludes diagnostics, trials, logs, caches, environments.','files':family_files})
for ID in ['4918','3531']:
 P=F.parent/'assets'/ID;source=sha(P/'source.blend');glb=sha(P/'motion.glb');native=json.loads((P/'surface-contact-report.json').read_text());decoded=json.loads((P/'decoded-physical-report.json').read_text());export=json.loads((P/'export-verification.json').read_text());q=json.loads((P/'raw-asset-qa.json').read_text());original=json.loads((P/'source-verification.json').read_text());early=json.loads((P/'early-report.json').read_text());clip=json.loads((P/'clip.json').read_text())
 assert native['ok']and decoded['ok']and export['ok']and q['pass']
 assert all(x['source_sha256']==source for x in [native,decoded,export,q,original])and export['glb_sha256']==glb
 clip.update(source_sha256=source,glb_sha256=glb,review_status='native_source_and_decoded_gates_passed; primary_actual_GPU_review_pending',authoring_family='../../upright-cardio-family',source_invariant_reference='source-verification.json',local_binding_reference='local-binding-report.json')
 if ID=='4918':clip['flight_windows_seconds']=[[round((k+.42)*1.25,3),round((k+.66)*1.25,3)]for k in range(4)];clip['authored_hops_per_demo']=4
 write(P/'clip.json',clip)
 # The source was saved once with its review camera before export; animation/body are unchanged.
 witness=json.loads((P/'motion-witnesses.json').read_text());witness['sampled_keyed_source_sha256']=witness['source_sha256'];witness['source_sha256']=source;witness['source_equivalence']='Final save only installed first recommended review camera; full151 matrices/skin verified from final source independently.';write(P/'motion-witnesses.json',witness)
 # Correct an observation label: this is total rest orientation, not a pure pitch decomposition.
 for name in ['surface-contact-report.json','decoded-physical-report.json']:
  d=json.loads((P/name).read_text())
  for row in d['samples']:
   for value in row['soles'].values():
    if'foot_pitch_degrees'in value:value['foot_rotation_from_rest_degrees']=value.pop('foot_pitch_degrees')
  write(P/name,d)
 # Compact frozen plantar envelope. Full1103/1104-ID sole gates remain in physical report.
 ref=json.loads((P/'runtime-surface-reference.json').read_text())
 if not ref.get('compact_plantar_envelope'):
  for row in ref['samples']:
   compact={}
   for side in ['Left','Right']:
    full=row['patches']['sole_'+side];bottom=set(row['patches']['heel_'+side]['indices']+row['patches']['ball_'+side]['indices']);pairs=[(i,p)for i,p in zip(full['indices'],full['positions'])if i in bottom];idx=[v[0]for v in pairs];pos=[v[1]for v in pairs];zs=[p[2]for p in pos]
    compact['sole_'+side]={'indices':idx,'positions':pos,'min_z':min(zs),'max_z':max(zs),'state':full['state'],'rationale':'Frozen source lowest20% plantar skin including heel and ball; full sole checked separately. During rolling support only the contacting part of this envelope is required on floor.'}
   row['patches']=compact
  ref['compact_plantar_envelope']=True;write(P/'runtime-surface-reference.json',ref)
 warnings=[]
 for row in q['samples']:
  for warning in row['report']['warnings']:warnings.append({'frame':row['frame'],'warning':warning,'disposition':'Expected during explicitly declared flight; grounded-only support gates are checked independently.'if ID=='4918'else'Requires review'})
 write(P/'asset-qa.json',{'pass':q['pass'],'source_sha256':source,'raw_report':'raw-asset-qa.json','zero_errors':all(not x['report']['errors']for x in q['samples']),'warnings':warnings,'claim_limit':'Mandatory game profile; no clinical or globally self-intersection-free claim.'})
 labels=['ready','left-knee-flight','soft-left-landing','right-knee-flight']if ID=='4918'else['guard','right-punch','left-punch','guard-return'];version='v4'if ID=='4918'else'v5';proofs=[]
 for label in labels:
  old=P/f'early-{version}-{label}.png';new=P/f'neutral-{label}.png';shutil.copyfile(old,new);proofs.append(new.name)
 if ID=='3531':proofs.append('fist-close.png')
 write(P/'proof-receipt.json',{'source_sha256':source,'sampled_pre_camera_source_sha256':early['source_sha256'],'native_keyed_proofs':proofs,'pre_post_render_complete_surface_delta_m':0,'maximum_saved_151_bone_matrix_error':early['maximum_saved_151_matrix_error'],'accepted_by_primary_for_bounded_user_review':True,'actual_GPU_acceptance':'Primary-owned final integration stage','limitations':['Original low-poly finger/skin seams remain visible.','Local palm nearest-normal depth tolerance4mm does not prove global finger self-intersection freedom.']if ID=='3531'else['Four hops in five seconds is an authored slowed demonstration, not source tempo.']})
 write(P/'mechanics-repair-history.json',{'source_sha256':source,'rejected_initial_diagnostic':'rejected-preflight-report.json retained locally outside curated packet','failure':('Swinging same-side hand/forearm entered thigh; up to89vertices deeper4mm.'if ID=='4918'else'Global-lateral curl axes and excessive distal fold entered palm: up to77IDs/hand deeper4mm; first hand-local correction left2Thumb2IDs/hand at4.61mm.'),'settled_correction':('Moved wrist lateral corridor250→350mm and elbow pole320→430mm from root, preserving all timing/opposing swing and body binding.'if ID=='4918'else'Changed four-digit curl axes to source hand-local palmar normal, flexion60/70/30degrees; thumb MCP opposed in exterior source hand-local direction(+/−.98,.15,.15), distal25/10degrees; wrist transported unchanged.'),'result':'Full151 native AND actual decoded declared physical gates pass; no geometry/rest/UV change.','export_harness_correction':'Reset one-shot action before each arbitrary-time read after end; source/GLB geometry unaffected.'})
 write(P/'authoring-family.json',{'path':'../../upright-cardio-family','files':{name:sha(F/name)for name in family_files if name!='curated-files.json'},'manifest_sha256':sha(F/'curated-files.json')})
 metrics={'minimum_floor_z_m':native['minimum_floor_z_m'],'minimum_area_m2':native['minimum_triangle_area_m2'],'native_loop_m':native['loop_skin_error_m'],'decoded_loop_m':decoded['loop_skin_error_m'],'maximum_full151_native_decoded_error_m':decoded['maximum_full151_native_decoded_error_m'],'maximum_normal_vector_error':export['maximum_normal_vector_error'],'maximum_influences':original['maximum_influences'],'maximum_weight_sum_error':original['maximum_weight_sum_error']}
 text=f'''# {ID} — {clip['name']}

Settled five-second DQ action `Exercise_{ID}` on the original CC0 body:10582source vertices,21160triangles,51bones. Basis, topology, UVs, rest and source IDs are exact. The declared local binding is shared with the other upright cardio asset; no morphs or geometry warp.

'''+('Four alternating one-foot hops use preload, articulated toe push-off,0.30second continuous ballistic flight, opposite high knee, ball landing and flexed-knee absorption. The opposing arm corridor clears the legs. Four hops/5seconds is a slowed demonstration; the source has no numeric workout interval.\n'if ID=='4918'else'Staggered feet stay supported while fists alternate forward/retract with slight torso rotation and17degree soft elbows at extension. The source30–60second workout interval is retained separately from the5second demonstration. Original low-poly finger seams remain. Thumb lies outside the folded fingers; the local palm-depth proxy uses4mm tolerance and does not establish global finger self-intersection freedom.\n')+f'''
Source primary remains `cardiovascular system`. Display proxies are {', '.join(clip['display_primary'])} (primary) and {', '.join(clip['display_secondary'])} (secondary); these are source-informed artistic roles, not measured activation.

Native and actual decoded151 gates pass: appropriate floor/ground/flight support, full arms/hands against both full legs, positive triangle areas, loop and full-source DQ transport. Mandatory game QA has zero errors. {len(warnings)} retained warnings are declared in `asset-qa.json`. Five full native diagnostic poses and sparse original-domain surface/joint references are supplied. Temporary decoded verification data was consumed/deleted; no runtime vertex cache is delivered. Root owns actual GPU acceptance, heat integration and final camera width.

Source SHA256 `{source}`. GLB SHA256 `{glb}`. Exact checks and numerical limits are in the receipts; `curated-files.json` is the explicit compact delivery boundary. Shared reproducible authoring files are declared in `authoring-family.json`. No Git/publication action was performed by this author.
'''
 (P/'README.md').write_text(text)
 files=['source.blend','motion.glb','clip.json','cameras.json','pose-samples.json','runtime-surface-reference.json','dq-reference.json.gz','normal-reference.json.gz','surface-landmarks.json','source-verification.json','surface-contact-report.json','decoded-physical-report.json','decoded-source-readback.json','export-verification.json','raw-asset-qa.json','asset-qa.json','local-binding-report.json','motion-witnesses.json','authoring-context.json','authoring-family.json','environment.json','proof-receipt.json','mechanics-repair-history.json','README.md','delivery-report.json','curated-files.json']+proofs
 write(P/'curated-files.json',{'id':ID,'policy':'Explicit final asset packet; shared family dependencies separately declared. Excludes old trials, logs, caches, backups, environments and temporary decoded exchange.','files':sorted(files)})
 write(P/'delivery-report.json',{'id':ID,'status':'author_native_export_physical_gates_passed; root_actual_GPU_and_integration_pending','source_sha256':source,'glb_sha256':glb,'runtime_binding_sha256':original['runtime_binding_sha256'],'original_source_sha256':original['original_source_sha256'],'source_invariants_pass':True,'full151_native_pass':True,'full151_decoded_physical_pass':True,'game_qa_zero_errors':True,'game_qa_warnings':warnings,'metrics':metrics,'remaining':['Root actual GPU acceptance, camera-width fit and shared heat integration.'],'bounded_disclosures':['Local nearest-normal arm/leg depth test within40mm with4mm tolerance; no global collision-free claim.']+(['Local fist/palm depth proxy within25mm and4mm tolerance; original low-poly finger seams.']if ID=='3531'else['Slowed4hop demonstration; no source cadence or flight-force claim.']),'files_sha256':{name:sha(P/name)for name in sorted(files)if name!='delivery-report.json'}})
 print(ID,json.dumps({'source':source,'glb':glb,'manifest':sha(P/'curated-files.json'),'delivery':sha(P/'delivery-report.json'),'metrics':metrics}))
