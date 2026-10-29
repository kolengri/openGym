# 6033 ab tuck — accepted DQ review candidate

The primary and independent Terra reviewer passed the final actual Three.js knee shape and elevated abdominal view. Runtime parity, alpha, controls and loops passed in the primary's all-five packet. This asset is frozen for staging; `delivery-report.json` records final acceptance and the exact curated file manifest. Generated build/clip review-status fields precede that final runtime acceptance and remain frozen.

The standard GLB requires `clip.skinning="dualQuaternion"` and the shared optional DQ adapter. Generic linear-skinning viewers do not reproduce the accepted body. Small original-cage faceting remains explicitly accepted.

## Source and motion

The Blender Studio CC0 body retains all 10,582 original vertices, 21,160 triangles, 51 bones, original Basis/rest/weights/UVs and `_SOURCE_INDEX`. The binding/rest/UV hash is unchanged:

`227ede3fc31d1a2b47ff40f20a4a7288fe7bb36179add23bae953993826c8b7b`

One `Exercise_6033` action contains skeletal channels and one `KneeCapRound` weight channel through Blender OBJECT/KEY slots. Native frames 1–151 map to runtime frames 0–150 at 30 fps, forming one controlled five-second tuck/extend loop. The key is zero at entry/return and reaches one at peak. Its exported POSITION and matching NORMAL deltas affect the complete local knee transition, with 360 changed original positions and maximum displacement 25.324 mm within the approved 30 mm bound.

The key retains only the original-cage native CorrectiveSmooth displacement around the whole knee circumference, smoothly feathered into thigh/calf. A normalized, hemisphere-aligned inverse DQ rotation maps that accepted target into rest space; peak target reproduction error is 0.096 micrometres. There are no helper bones, changed weights, topology edits, spherical dome terms or whole-body correction. Global CorrectiveSmooth and every other non-Armature modifier are disabled in the saved source, so the local knee correction is never doubled. Optional Multires preview is separate.

All five catalogue instructions and source muscle roles remain in `clip.json`: main abs; additional lower abs and hip flexors. Source hand placement and foot support are unspecified. The explicit authored choice is open posterior/lateral support palms with fingers away from the body and hovering feet. Actual posterior pelvic skin is solved against the floor while reachable wrists and ankles keep independent targets. Chest and knees approach, then extend under control. No workout hold duration is invented.

## Verification

The final corrective-bearing source passed required asset QA at native frames 1 and 76 (runtime 0 and 75), on both actual DQ cage and separate Multires preview. `delivery-report.json.asset_qa_binding` binds `asset-qa.json` by its SHA-256 to the exact final source and the same source-bound geometry/contact run. DQ cage geometry checks have no warnings. Optional Multires has 9/12 hidden back-to-back pair warnings at entry/peak and some pelvic support differences; it is disabled in the saved runtime body.

Actual Three.js GLTFLoader plus the exact shared CPU DQ adapter matches all 10,582 original vertices within 1.085 micrometres at runtime frames 0, 30, 75, 120 and 150. Sampled joint error is at most 0.906 micrometres; endpoint skin error is 0.186 micrometres. The exported Basis/full-key NORMAL values match independently calculated source rest normals at every UV-split vertex within 0.000082 vector error. The shared shader morphs normals before unit DQ rotation, which preserves that error bound; final raster appearance was checked by the primary.

Comparing accepted pre-knee references with this candidate shows exactly unchanged positions for all 51 joints at all 11 checked phases, every support patch, every vertex outside the local knee, and all entry/return vertices. `knee-invariant-verification.json` records those comparisons. Both pelvic patches and palm pads retain at least 25% of selected vertices within the 12 mm floor band. Worst floor overlap is 2.00 mm inside the 4 mm illustration tolerance; maximum palm drift is 0.231 mm and minimum foot clearance is 92.98 mm. These sampled checks are not continuous collision guarantees.

## Frozen inputs

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| `source.blend` | 13,584,966 | `144190a81099f5abae8180533d0c600652d27255fc598e4a0d812bf722245067` |
| `motion.glb` | 945,416 | `8a928882f94a9935ebf46abf1d7538f9b9d276abc52edc941d6710dee67bdcb2` |
| `asset-qa.json` | See manifest | `2a24372201d4686132e090f74f6f45245ab7ad6b342f0c26056f49eb8bd5be9d` |

`dq-reference.json.gz` contains full original-ID-order Blender Z-up DQ positions at five phases and the final source hash. All reference/QA/script/proof hashes and exact staging paths appear in `delivery-report.json.files` and `curated_delivery`.

## Curated staging set

Stage only the named files in `delivery-report.json.curated_delivery`:

- Source/runtime: `source.blend`, `motion.glb`, `clip.json`, `cameras.json`.
- Reproduction: `build_motion.py`, **`knee_corrective.py`, `knee_native_target.py`**, `verify_asset.py`, **`verify_corrective_source.py`**, `verify_export.mjs`, `render_export.py`. The knee helper modules are required build dependencies. There is no binary normal patch: Blender exports the matching NORMAL morph directly; `verify_corrective_source.py` produces the independent normal reference used by the Three.js verification.
- References: `pose-samples.json`, `runtime-surface-reference.json`, `dq-reference.json.gz`, `knee-normal-reference.json.gz`, `landmarks.json`.
- Receipts: `build-report.json`, `knee-corrective-report.json`, `knee-source-verification.json`, `knee-invariant-verification.json`, `surface-contact-report.json`, `asset-qa.json`, `export-verification.json`.
- Viewed final proof: `early-start-side.png`, `early-peak-side.png`, `early-peak-oblique.png`, `early-peak-rear.png`, `early-return-side.png`, `wire-peak-oblique.png`, `exported-dq-start-side.png`, `exported-dq-peak-oblique.png`, `exported-dq-return-side.png`.
- Accepted baseline comparison: `pre-knee-pose-samples.json`, `pre-knee-runtime-surface-reference.json`, `pre-knee-dq-reference.json.gz`.
- Delivery: `README.md`, `delivery-report.json`.

Exclude rejected helper/weight fits, knee roll/dome probes and preview scripts, proposal/limitation/checkpoint files, logs, caches, optional native-preview stills and old `exported-*` stills without `-dq-`. They are historical diagnostics and are not final build dependencies. The primary's actual Three.js screenshots/receipts live outside this owned folder.

## Reproduction

From the repository root with Blender 5.2.3 and existing Three.js dependencies:

```sh
/opt/homebrew/bin/blender -b -t 2 --python-exit-code 1 --python artifacts/exercise-batches/batch-003/assets/6033/build_motion.py -- --final
/opt/homebrew/bin/blender -b -t 2 --python-exit-code 1 --python artifacts/exercise-batches/batch-003/assets/6033/verify_corrective_source.py
node artifacts/exercise-batches/batch-003/assets/6033/verify_export.mjs
/opt/homebrew/bin/blender -b -t 2 --python-exit-code 1 --python artifacts/exercise-batches/batch-003/assets/6033/render_export.py
```

Shared read-only dependencies are `batch-003/authoring.py`, the original `artifacts/bodyweight-five/bodyweight-five.blend`, `artifacts/bodyweight-next-five/warning_observer.py`, the installed `blender-asset-qa/scripts/qa_check.py`, `artifacts/exercise-batches/dual-quaternion.js` and the existing `artifacts/first-exercise-3d/runtime/node_modules/three`. Original source geometry, authoring math and shared renderer files were not edited. Rebuilding produces a new source hash and source-bound receipts; the frozen delivery hashes above identify this accepted candidate.

Only curated stills were generated, with a first-draw Workbench warmup to avoid stale import caches. No video, animation frame sequence, paid service or restricted Gym Visual media was used. Root owns cameras, runtime integration and Git. Text is original openGym material under repository AGPL; geometry is Blender Studio Human Base Meshes v1.4.1 CC0. See repository `NOTICE.md`, `LICENSE`, `catalogue/media/NOTICE.md` and `artifacts/exercise-animation-briefs/THIRD_PARTY_NOTICES.md`.
