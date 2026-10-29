"""Curate settled local evidence; root alone accepts actual GPU motion and publishes."""
import json,hashlib,sys,os
from pathlib import Path
F=Path(__file__).resolve().parent;B=F.parent;ROOT=B.parents[2];IDS=('3220','3672','6097')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def write(path,value):path.write_text(json.dumps(value,indent=2)+'\n')
def load(path):return json.loads(path.read_text())
source_sha=sha(F/'source.blend');glb_sha=sha(F/'motion.glb')
dependency_paths=[
 'artifacts/bodyweight-five/bodyweight-five.blend',
 'artifacts/bodyweight-five/build_motion.py',
 'artifacts/exercise-batches/batch-003/authoring.py',
 'artifacts/exercise-batches/batch-008/standing-dynamic/plantar_binding.py',
 'artifacts/exercise-batches/batch-008/standing-dynamic/check_motion.py',
 'artifacts/exercise-batches/batch-008/standing-dynamic/self_clearance.py',
 'artifacts/exercise-batches/batch-008/standing-dynamic/triangle_intersection.py',
 'artifacts/exercise-batches/dual-quaternion.js',
 'artifacts/first-exercise-3d/runtime/node_modules/three/package.json',
 'artifacts/first-exercise-3d/runtime/node_modules/three/build/three.module.js',
 'artifacts/first-exercise-3d/runtime/node_modules/three/build/three.core.js',
 'artifacts/first-exercise-3d/runtime/node_modules/three/examples/jsm/loaders/GLTFLoader.js',
 'artifacts/first-exercise-3d/runtime/node_modules/three/examples/jsm/utils/BufferGeometryUtils.js',
 'artifacts/first-exercise-3d/runtime/node_modules/three/examples/jsm/utils/SkeletonUtils.js',
 '/Users/kolengri/.codex/skills/blender-core/scripts/env_report.py',
 '/Users/kolengri/.codex/skills/blender-core/scripts/_bpyx.py',
 '/Users/kolengri/.codex/skills/blender-asset-qa/scripts/qa_check.py',
 '/Users/kolengri/.codex/skills/blender-asset-qa/scripts/_bpyx.py']
dependencies=dict(original_CC0_body=dict(path=dependency_paths[0],sha256=sha(ROOT/dependency_paths[0]),original_binding_sha256='227ede3fc31d1a2b47ff40f20a4a7288fe7bb36179add23bae953993826c8b7b'),read_only_dependencies=[dict(path=p,sha256=sha(Path(p) if p.startswith('/') else ROOT/p),modified=False,publication_dependency=not p.startswith('/') and 'node_modules' not in p) for p in dependency_paths],tools=dict(blender='/opt/homebrew/bin/blender',blender_version='5.2.3 LTS',threads=2,three_version='0.186.1',python='Blender bundled Python3.13.13/NumPy; system Python3 for packaging',scipy_libigl_venv='Provided existing environment; not required by this no-refit motion slice.'),rights='Original Blender Studio Human Base Meshes1.4.1 CC0 and catalogue text. Motion is newly authored; no mocap, GymVisual derivatives, restricted reference frames, paid generation or video.')
write(F/'dependencies.json',dependencies)
diagnosis=dict(reuse_choice='Canonical original body plus exact accepted batch008 distal plantar binding only. Stable parent-transported hinge frames, source-rest relaxed-arm endpoint and relaxed finger staging from accepted6014 are read-only analogues. No deep squat/hip binding, rejected foot variants, crossing-arm shoulder targets or new weight fit.',settled_fixes=[dict(exercise='3672',cause='Forward foot was placed beyond reachable leg length while pelvis remained at neutral.',early_maximum_unreachable_ankle_target_m=.2968014724866885,remedy='Pelvis travels with forward placement and lowers modestly before lunge loading; final all151 reach residuals0.'),dict(exercise='6097',cause='Overhead target exceeded actual shoulder-to-hand reach.',early_maximum_unreachable_wrist_target_m=.04468307783171862,remedy='Reach is limited within the actual arm chain; final all151 reach residuals0.'),dict(exercise='3220',cause='Vertical squat routing drove excessive shin/ankle fold.',early_minimum_mixed_ankle_edge_ratio=.46418879828755627,remedy='Hips travel back with forward torso inclination during squat and impact absorption, preserving exact planted foot anchors/binding.'),dict(exercise='3672',cause='Rear heel release was tied to lunge loading, after supporting shin had already advanced.',early_minimum_mixed_ankle_edge_ratio=.44405464690476043,remedy='Rear heel rises with forward step travel around a fixed toe/forefoot pivot.'),dict(exercise='6097',cause='35percent shin-relative foot transport left excessive local ankle deformation.',early_minimum_mixed_ankle_edge_ratio=.583131216138163,remedy='75percent shin-relative foot transport preserves a relaxed ankle point during backward kick.')],unchanged_guards=dict(forefoot_edge_ratio=[.85,1.15],mixed_ankle_edge_ratio=[.65,1.35],floor_penetration_m=.00035,grounded_heel_ball_max_gap_m=.002),source_sha256=source_sha,glb_sha256=glb_sha,review_boundary='Numerical gates do not establish natural motion. Root owns actual GPU motion acceptance before freeze.')
write(F/'causal-diagnosis.json',diagnosis)
gpu_accepted='--root-gpu-accepted' in sys.argv
if gpu_accepted:
 receipt=load(F/'root-gpu-acceptance.json');assert receipt['accepted'] and receipt['glb_sha256']==glb_sha and receipt['source_sha256']==source_sha
rows=[]
for ID in IDS:
 P=B/'assets'/ID;native=load(P/'surface-contact-report.json');decoded=load(P/'decoded-physical-report.json');export=load(P/'export-verification.json');qa=load(P/'raw-asset-qa.json');source=load(P/'source-verification.json')
 for report in [native,decoded,export,qa,source]:assert report['source_sha256']==source_sha
 assert native['ok'] and decoded['ok'] and export['ok'] and qa['pass'] and source['ok']
 assert all('heel_min_z_m' in contact and 'ball_min_z_m' in contact for sample in decoded['samples'] for contact in sample['soles'].values())
 assert all(not x['report']['errors'] for x in qa['samples'])
 assert export['glb_sha256']==glb_sha and sha(P/'source.blend')==source_sha and sha(P/'motion.glb')==glb_sha
 warnings=[dict(frame=x['frame'],warnings=x['report']['warnings']) for x in qa['samples'] if x['report']['warnings']]
 assert max(max(x['reach_errors_m'].values()) for x in load(P/'motion-witnesses.json')['samples'])==0
 clip=load(P/'clip.json');clip['review_status']='root_GPU_accepted_local_frozen' if gpu_accepted else 'local_checks_passed_pending_root_GPU';clip['native_frame_origin']=1;clip['source_sha256']=source_sha;clip['glb_sha256']=glb_sha;clip['asset']='locomotion';write(P/'clip.json',clip)
 row=dict(id=ID,source_sha256=source_sha,glb_sha256=glb_sha,source_vertices=10582,bones=51,triangles=21160,native_and_actual_decoded_frames=151,all_151_reach_residuals_m=0,maximum_decoded_native_position_error_m=decoded['maximum_full_cycle_native_decoded_error_m'],maximum_DQ_shader_NORMAL_vector_error=export['maximum_DQ_shader_NORMAL_vector_error'],loop_skin_error_m=decoded['loop_skin_error_m'],minimum_triangle_area_m2=decoded['minimum_triangle_area_m2'],minimum_skin_floor_z_m=decoded['minimum_floor_z_m'],maximum_grounded_toe_anchor_step_m=decoded['maximum_grounded_toe_anchor_step_m'],forefoot_edge_ratio=decoded['forefoot_edge_ratio_range'],mixed_ankle_edge_ratio=decoded['mixed_ankle_edge_ratio_range'],arm_leg_crossings=decoded['arm_leg_triangle_crossings'],bilateral_leg_crossings=decoded['bilateral_leg_triangle_crossings'],arm_self_crossings=decoded['arm_self_triangle_crossings'],game_QA_errors=0,retained_warnings=warnings,morphs=0,corrective_reset='Not applicable; no targets/tracks.',root_GPU_accepted=gpu_accepted,scope='Complete native and actual decoded DQ skin, declared full heel/ball or rear-forefoot support, foot shape and limb checks; no global collision-free or clinical claim.')
 write(P/'delivery-report.json',row);rows.append(row)
 record=load(ROOT/'catalogue/exercises'/f'{ID}.json');source_resolution=load(B/'source-resolutions.json')[ID]
 (P/'README.md').write_text(f'''# {ID} — {record['name']}

{source_resolution}

All ranges and five-second timing are authored demonstration choices. Source text, labels and ambiguity remain in `authoring-context.json`. The shared canonical GLB/source contain three distinct `Exercise_<id>` actions; all three asset copies have identical bytes. Runtime uses the unchanged shared DQ adapter and ordinary bone tracks. There are no corrective targets or runtime frame caches.

The original CC0 Blender Studio Human Base Meshes1.4.1 body retains exact Basis, rest, topology, UVs,10,582 source IDs and51 bones. Only the accepted sourceZ35..80mm distal plantar recipe is reused; all source weights above80mm remain exact. No hip, shoulder or knee fit is introduced. Exact model/helper/runtime hashes and reproduction details are in `../../locomotion/dependencies.json` and `../../locomotion/README.md`.

All151 native and actual decoded states pass declared support/floor, actual heel/ball or rear-forefoot support, full arm/hand versus both legs, bilateral leg and arm/body triangle clearance, internal forefoot/ankle shape, positive areas and loop closure. Decoded/native maximum skin error is {row['maximum_decoded_native_position_error_m']*1e6:.3f}µm. Maximum independent DQ shader NORMAL vector error is {row['maximum_DQ_shader_NORMAL_vector_error']:.9f}. These are local CPU decoding measurements; root owns actual GPU judgment. Game QA has0errors. Retained warnings: {json.dumps(warnings) if warnings else 'none'}. The jump flight warning is intentional when present. These checks do not establish global collision freedom or clinical correctness.

`early-*.png` show the settled native neutral skin at start/intermediate/peak/return from both whole-body cameras. Native matrices and full skin are asserted unchanged by rendering. `pose-samples.json` has all51 native joints; surface patches retain original source IDs and separately declare the floor plane. Five full-source POSITION and independent native-pose DQ shader NORMAL witnesses are diagnostics only. `curated-files.json` excludes logs, transient decoded exchanges, caches, trials and backups.

Source SHA256: `{source_sha}`

GLB SHA256: `{glb_sha}`

Release state: {'Root GPU accepted; local packet frozen.' if gpu_accepted else 'Local checks pass; root actual GPU motion acceptance pending.'}
''')
 asset_files=['README.md','source.blend','motion.glb','clip.json','cameras.json','pose-samples.json','authoring-context.json','local-binding-report.json','motion-witnesses.json','early-report.json','runtime-surface-reference.json','surface-landmarks.json','dq-reference.json.gz','normal-reference.json.gz','surface-contact-report.json','source-verification.json','decoded-physical-report.json','decoded-source-readback.json','export-verification.json','raw-asset-qa.json','environment.json','delivery-report.json','curated-files.json']+[x['path'] for x in load(P/'early-report.json')['proofs']]
 write(P/'curated-files.json',dict(policy='Explicit final asset files only; no logs, caches, trials, environments or decoded frame exchanges.',files=sorted(asset_files),read_only_dependency_manifest='../../locomotion/dependencies.json'))
report=dict(source_sha256=source_sha,glb_sha256=glb_sha,root_GPU_accepted=gpu_accepted,root_GPU_receipt='root-gpu-acceptance.json' if gpu_accepted else None,local_checks_passed=True,assets=rows,read_only_dependencies='dependencies.json',canonical_asset='motion.glb',runtime_cache=False,publication_owner='root')
write(F/'delivery-report.json',report)
(F/'README.md').write_text(f'''# Batch009 locomotion family

Three distinct five-second cycles share one original CC0 body/binding and standard three-action GLB:3220 two controlled squat jumps,3672 right/left forward lunge and return,6097 four alternating backward kicks with simultaneous overhead presses. Source resolutions and authored timing/range choices are kept separate in per-asset contexts and clip metadata.

The canonical source keeps exact Basis/rest/UV/topology/source IDs and51bones. `build.py` loads the original standing body using read-only batch003 rig helpers and installs only the exact accepted batch008 distal plantar binding. It does not import earlier deep-hip/foot pose variants. Parent-transported anatomical hinge frames, fixed grounded toe anchors, heel/ball skin support, deliberate flight, and relaxed connected hands govern the routes. No new binding fit, corrective target, motion cache or video is used. `causal-diagnosis.json` records rejected local routing causes and the settled bounded remedies.

`verify_native.py` checks every saved native/actual decoded frame, including full support, local foot shape, full arms/hands against legs, bilateral legs, distal arms/body, positive areas and exact loop closure. `verify_export.mjs` independently loads through the actual project Three.js/DQ adapter, checks all51 joints, sparse source surface patches and five complete source POSITION/NORMAL witnesses, and writes a temporary local decoded physical exchange that the native checker deletes after acceptance. Normal evidence uses native pose/bind quaternion blending independently from runtime skeleton matrices; it is shader-normal transport evidence, not Blender recomputed surface-normal equivalence. The151-frame mechanical receipts are distinct from root actual GPU motion acceptance.

Game QA:0errors for every sampled asset. The declared airborne3220 peak retains a correct not-resting-on-floor warning. No global self-collision or clinical claim. The packet is {'locally frozen after root GPU acceptance' if gpu_accepted else 'locally verified and awaiting root GPU motion acceptance before freeze'}. Root owns viewer mapping, muscle fields, final camera-width integration, staging, Git and publication.

## Reproduce

Use Blender5.2.3 at `/opt/homebrew/bin/blender`, threads2, the installed project Three.js0.186.1 and the exact read-only hashes in `dependencies.json`. No new dependency installation is required. Run from the repository root:

```sh
/opt/homebrew/bin/blender -b -t 2 --python-exit-code 1 --python artifacts/exercise-batches/batch-009/locomotion/build.py
```

For each ID3220,3672,6097 run:

```sh
/opt/homebrew/bin/blender -b -t 2 --python-exit-code 1 --python artifacts/exercise-batches/batch-009/locomotion/verify_native.py -- --id ID --game-qa
node artifacts/exercise-batches/batch-009/locomotion/verify_export.mjs ID
```

Pass the exact `decoded_physical_exchange` path printed by the last command to:

```sh
/opt/homebrew/bin/blender -b -t 2 --python-exit-code 1 --python artifacts/exercise-batches/batch-009/locomotion/verify_native.py -- --id ID --decoded PATH
python3 artifacts/exercise-batches/batch-009/locomotion/write_delivery.py
```

The final packaging flag `--root-gpu-accepted` is used only after explicit root actual GPU acceptance. The explicit manifests include read-only project reproduction dependencies but exclude `node_modules`, installed skills, logs, candidates, caches and temporary exchanges from publication. Tool receipts record the existing local environment.

Source SHA256: `{source_sha}`

GLB SHA256: `{glb_sha}`
''')
family_files=['README.md','source.blend','motion.glb','motion.py','build.py','verify_native.py','verify_export.mjs','write_delivery.py','dependencies.json','causal-diagnosis.json','delivery-report.json','curated-files.json']+(['root-gpu-acceptance.json'] if gpu_accepted else [])
publication_dependencies=[os.path.relpath(ROOT/p,F) for p in dependency_paths if p.startswith('artifacts/') and 'node_modules' not in p]
write(F/'curated-files.json',dict(policy='Explicit local family and read-only project dependencies only. Installed skill helpers and node_modules are hash-declared reproduction prerequisites, not publication files.',files=family_files+publication_dependencies,asset_manifests=['../assets/'+i+'/curated-files.json' for i in IDS]))
for manifest in [F/'curated-files.json']+[B/'assets'/i/'curated-files.json' for i in IDS]:
 for path in load(manifest)['files']:assert (manifest.parent/path).is_file(),(manifest,path)
print(json.dumps(dict(ok=True,source_sha256=source_sha,glb_sha256=glb_sha,root_GPU_accepted=gpu_accepted,assets=[dict(id=row['id'],maximum_decoded_native_error_m=row['maximum_decoded_native_position_error_m']) for row in rows]),indent=2))
