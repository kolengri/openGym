# Air bike 0003

This original five-second alternating bicycle crunch is ready for the primary's actual GPU/viewer review. The primary approved the corrective-bearing neutral DQ cage. Source, geometry/contact QA, exported POSITION/NORMAL morphs and Three.js CPU DQ parity pass. The final authorized hand change moves each head-relative wrist target laterally by 3 mm; protected torso/shoulder/leg joints and the original posterior pelvic support surfaces remain exactly unchanged in the recorded samples.

## Motion and source roles

`Exercise_0003` is the only action, with skeletal and three corrective-weight channels together. At 1.25 s (runtime frame 37.5), the right elbow approaches the left knee while the right leg extends. At 3.75 s (frame 112.5), the opposite pairing occurs. The initial knee angles are 90 degrees; the source says “towards,” so no elbow/knee surface-contact claim is made. Palms remain separate behind the head, fingers articulate gently, and both feet remain airborne. The five-second pace and detailed joint angles are authored illustration choices.

The source target is **abs**, with **hip flexors** additional. The description's mention of obliques does not add a display role. Source text comes from `catalogue/exercises/0003.json`; Gym Visual media and paid generation were not used. The original body is the Blender Studio CC0 Human Base Mesh. Existing repository notices govern the source text and project distribution.

## Geometry and skinning

The asset retains the original connected 10,582-vertex / 21,160-triangle cage, 51 bones, Basis, rest transforms, UVs, original IDs and weights. Binding/rest/UV SHA256 is `227ede3fc31d1a2b47ff40f20a4a7288fe7bb36179add23bae953993826c8b7b`. No helpers or topology changes were added. `clip.skinning` explicitly requires the shared optional **dual-quaternion** adapter; standard linear skinning is not the accepted surface.

`JointNeutral`, `JointRightCross` and `JointLeftCross` retain native original-cage CorrectiveSmooth displacement only around whole knee and shoulder/elbow transitions. A smoothly feathered posterior flank pocket in those same keys prevents flank penetration while preserving the natural lumbar arch and frozen pelvic support. Each world-space displacement is mapped back through stable inverse unit DQ rotation. The three nonnegative weights form a partition through the cycle. Matching NORMAL targets are exported and checked using the actual morph-before-DQ equation. No global Smooth is doubled at runtime.

The maximum local rest displacement is 52.7615 mm at original vertex 8353, source coordinate `[0.180363193, 0.001618512, 1.329651237]`, in the left shoulder/axilla transition. Per-key changed counts are 1528 / 1525 / 1525. The flank pocket amplitudes are 11.698 / 14.064 / 15.740 mm. Exact original IDs, per-key maxima and method are recorded in `joint-corrective-report.json`.

## Verification and limits

- Actual DQ cage floor/support and airborne feet: all 151 authored frames pass. Minimum actual floor height is +0.9997 mm, minimum posterior pelvic near-floor fraction is 25%, and minimum foot clearance is 100.654 mm. Support indices and illustration thresholds remain unchanged.
- Detailed surface, hand/head, wrist and all-bone samples cover 13 phases, including both cross peaks and blend midpoints. Opposing hand surfaces have at least 3.077 mm unsigned separation; the minimum nearest-normal signed separation is +2.137 mm. Minimum hand/head signed separation is +4.224 mm. The authored wrist direction bound is 35 degrees, not a clinical limit.
- The observed lumbar patch's minimum gap across detailed phases is 2.669–9.618 mm; all vertices in that patch span 2.669–62.450 mm above the floor. This is a natural arch measurement, not a claim of whole-lumbar contact.
- Mandatory asset geometry QA passes the actual DQ cage at runtime frames 0 / 19 / 37.5 / 112.5 with zero warnings. `asset-qa.json` and its exact source/file hashes are bound in `delivery-report.json`.
- All 10,582 original-ID positions at frames 0 / 30 / 75 / 120 / 150 match native DQ within 1.495 micrometres. Every exported UV-split Basis and full-key normal matches the independent source normal references within 0.00008188 vector error. Loop surface error is 0.177 micrometres.

The disabled optional Multires preview has 9 / 12 hidden back-to-back pair warnings and 5.6 / 2.7 mm ground-gap notices at start / peak; warning locations remain in `asset-qa.json`. Preserve the original topology. These warnings describe the separate preview, not the saved/runtime DQ cage. Blender GLB reimport stills are excluded from normal approval because that importer does not faithfully reproduce these morph normals. The primary owns actual GPU appearance, heat zones, alpha, controls, live loops and final camera fit. No clinical, EMG or continuous-collision certification is implied.

## Frozen outputs

| File | Bytes | SHA256 |
| --- | ---: | --- |
| `source.blend` | 13,924,336 | `499763d1dd004eee635cdd829b4efaa0e307c3e613058cf6aa4b9e9289f668fe` |
| `motion.glb` | 1,140,376 | `0cbb282620f167c2f84685adfcb308677b81b9384f611a970372482137d121b4` |

`delivery-report.json` is the exact curated staging manifest, with hashes for every delivery file except the report itself. It separates current source-bound references from the explicitly historical hand-repair baseline. Rejected pose/support probes, raw target trials, logs, imported diagnostic PNGs and optional preview PNGs remain local and are excluded. Curated neutral solid/wire stills are source-cage proofs, not an animation sequence.

## Reproduction

Run from the repository worktree using Blender 5.2.3 LTS, two threads, existing Python/NumPy and the installed Three.js package:

```sh
/opt/homebrew/bin/blender -b -t 2 --python-exit-code 1 --python artifacts/exercise-batches/batch-004/assets/0003/build_motion.py -- --final
/opt/homebrew/bin/blender -b -t 2 --python-exit-code 1 --python artifacts/exercise-batches/batch-004/assets/0003/verify_corrective_source.py
node artifacts/exercise-batches/batch-004/assets/0003/verify_export.mjs
python3 artifacts/exercise-batches/batch-004/assets/0003/write_metadata.py
python3 artifacts/exercise-batches/batch-004/assets/0003/verify_hand_repair.py
/opt/homebrew/bin/blender -b -t 2 --python-exit-code 1 --python artifacts/exercise-batches/batch-004/assets/0003/render_export.py -- --source --blend-only
```

Local dependencies are `air_bike_pose.py`, `local_joint_target.py` and `joint_correctives.py`; the build invokes `verify_asset.py` and `write_metadata.py`. `verify_corrective_source.py` produces independent source normal references; `verify_export.mjs` checks canonical GLTFLoader data against them and the exact shared DQ adapter. `verify_hand_repair.py` compares final receipts with the frozen pre-repair baseline, without saving the source. `render_export.py --source --blend-only` makes the native DQ midpoint proof.

Read-only shared dependencies are `batch-003/authoring.py`, `artifacts/bodyweight-five/bodyweight-five.blend`, `artifacts/bodyweight-next-five/warning_observer.py`, `artifacts/exercise-batches/dual-quaternion.js`, `artifacts/first-exercise-3d/runtime/node_modules/three` and the installed Blender asset-QA `scripts/qa_check.py`. Original input blend SHA256 is `fbf635733118dc190fdb3cefabcde7fe4367bbccfa40aa3495a2ab2e7537d070`. Only `batch-004/assets/0003/` was written; completed 6033 and shared files are preserved. No Git operations, new agents, paid jobs, videos or frame sequences were performed.
