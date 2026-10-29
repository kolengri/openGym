# Lying leg raise family — frozen user-review packet

One continuous Blender Studio CC0 source body and one physical GLB contain four five-second actions. The original 10,582 source vertices, 21,160 triangles, 51 bones, Basis, rest skeleton, UVs and topology remain exact. Each asset has its own catalogue/muscle metadata, action identity, camera recommendations and native references. `clip.asset` is `leg-raise-family` for all four records; identical source/GLB bytes are available under each asset directory. Root deduplicates the runtime resource.

| Record | Authored action |
| --- | --- |
| 4826 | Flat supported head; alternating straight legs from 4° to 90°. |
| 3590 | Separate source/action identity, exactly the same physical track as 4826. |
| 4001 | Same noncontacting straight-leg action; head slightly raised. |
| 5106 | Both straight legs remain 82–90°; alternate a restrained ceilingward leg/toe reach with ankle/toe extension. No scissors or pelvic lift. |

The first three loops begin at a 47° mid-transfer, distinct from the source's initial floor setup. Neither the source nor the metadata claims the first animated frame has grounded heels. The measured minimum foot-skin clearance is about 100 mm. For 5106, the source leaves the reach mechanism unspecified; restrained hip-angle travel supplies little ankle-height change near vertical, so ankle/toe extension supplies most visible toe-tip rise. Numerical angles, timing and mechanism are illustration choices, not measured physiology.

## Frozen physical composition

`family_common.py` replays one causal source-anatomy above-hip/posterior-waist binding and the declared harmonic proximal-glute recipe, with actual normalized ≤4-weight readback. No old bicycle pose, morph, flank guard or schedule is imported. `pose-parameters.json` contains the accepted constant-root pose. There are six compact C2 lower-back/pelvis support POSITION/NORMAL targets and one compact posterior cervical attachment POSITION/NORMAL target.

The six support buffers remain exact when adding the cervical target. The cervical source delta is capped at 8 mm, with a C2 source collar and exact protected head/upper-back/lumbar/pelvic positions. Its action weight is 1 for the flat-head actions and 0.6218309238136919 for 4001. The latter is 80% of the first analytic orientation-zero amplitude of this same field. Full-weight 4001 was rejected for eight flipped cervical triangles; no alternate target direction or stronger target was substituted. Root accepted the remaining small posterior cervical attachment crease. Exact-rest cervical anatomy is not claimed.

The lower-back criterion retains the original 45 raw IDs and old flat-19 diagnostics. The source-only lower-38 posterior-envelope profile preserves the source centerline groove; all midline/ridge residuals, pelvic minima and whole-body floor gates are measured on actual skin. The original 2/5 mm contact thresholds and −0.35 mm whole-body floor threshold were not relaxed. `source-neutral-envelope.json`, `source-support-masks.json` and `final-composition-receipt.json` are authoritative.

## Evidence

`final-metrics.json` summarizes all four native and actual decoded 151-frame checks. These include exact loop closure, stationary pelvis/hip joint centers, straight knees, airborne feet, positive triangles, the frozen posterior support contract and conservative whole-arm/hand versus both-leg triangle checks. Minimum decoded arm/hand-to-leg clearance is 88.909 mm. Maximum full native-to-decoded DQ skin error is 1.148 µm. Every native bone is checked across all 151 decoded frames, with the LoopOnce endpoint explicitly resumed before random access. All seven NORMAL buffers are checked independently; maximum normal-vector error is 8.19×10⁻⁵. Actual exported weights have at most four influences and maximum sum error 4.48×10⁻⁸. Mandatory game QA has zero errors and zero warnings.

The standard Blender exporter omitted three inactive KEY weight channels. `complete_morph_channels.py` appends only their standard glTF animation channels from the exact saved native 151-sample schedules, retaining the original geometry/bone/POSITION/NORMAL binary prefix. The explicit receipt and final decoded parity cover the completed canonical GLB.

The current flat-head and raised-head cervical proofs are the accepted corrected surface. Selected `settled-5106-*` proofs establish the accepted near-vertical leg/support staging before the final compact cervical field; final canonical export/normal/physical checks cover the final body. Root owns actual GPU raster review, muscle fields, camera-width fitting and final user acceptance. This packet does not certify continuous-time or globally collision-free motion, clinical suitability or production readiness.

`causal-history.json` preserves the changed source-profile interpretation, one unsuccessful coupled cervical solve, the exact-neutral source-depth obstacle, the rejected full-weight raised-head field and the mislabeled 3303 reference. Diagnostic 3303 remains 4.987 mm high in the frozen accepted pose; actual preexisting protected upper-back floor anchors 3311/8568 are 1.382/1.632 mm high. No refit followed that metadata correction.

## Replay

Use Blender 5.2.3 with `--background --factory-startup -t 2 --python-exit-code 1 --python <script>`. Run the following owned scripts in order only when deliberately regenerating the frozen packet:

1. `build_family.py` installs the frozen NPZ fields and bakes the four native actions.
2. `verify_source.py` compares the saved source with the immutable canonical original and checks exact field composition.
3. `verify_native.py` checks native physics/game QA and writes the five diagnostic DQ poses plus temporary full-skin QA streams.
4. `export_family.py` exports and completes only missing/inaccurate native morph-weight channels.
5. `node verify_export.mjs`, `node verify_export_weights.mjs`, then Blender `verify_decoded_physical.py` check actual decoded geometry, NORMALs, weights and physics.
6. `python3 curate_delivery.py` hashes the curated files. Remove temporary `.native-all151-*`, `.decoded-all151-*` and `.decoded-topology.json` after verification.

The one-shot construction programs are derivation provenance. Frozen NPZs, pose, masks, binding and schedules are the replay inputs; do not refit them during integration. Installed Blender/QA tools and local NumPy/SciPy construction prerequisites remain external. The exact canonical body and safe helper, shared DQ adapter, Three.js dependency manifests and warning observer are listed with hashes as external workspace dependencies in `curated-files.json`.

Root's `../root-integration.json` explicitly supersedes handoff camera hashes after width-only fitting and reference hashes after deriving required `min_z`/`max_z` summaries from unchanged native positions. Curation never rewrites those metadata files.
