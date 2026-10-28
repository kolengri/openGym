# 4348 — abdominal 4 points

Original CC0 hands-and-knees isometric illustration. One `Exercise_4348` action spans 5 seconds at 30 fps. The skeleton remains still throughout brace (0–2 seconds), hold (2–3), and relaxation (3–5). The source workout instruction remains **15–30 seconds while breathing normally**. No knee hover, plank transition, torso pulse or physiological activation curve is invented.

The source requires wrists under shoulders, knees under hips, flat back, neutral neck and abdominal bracing. Reversible staging uses open palms, articulated fingers with horizontal distal phalanges, relaxed feet behind the knees, and a straight torso inclined 11 degrees toward the shoulders to fit unchanged limb lengths with natural elbows. Review stills include thin Z=0 datum lines without a filled or masking floor. The datum is excluded from GLB.

## Shape correction

The initial linear cage was rejected for triangular waist/upper-thigh and shoulder/armpit folds; its numeric support pass did not establish acceptable shape. The current asset uses one authorized `StaticPoseCorrective_4348` morph at constant default weight 1 to reproduce the clean native CorrectiveSmooth cage in GLB LBS. There is no morph action, per-frame cache, remesh, weight repair, new bone, Basis-coordinate change, UV change or rig-rest change.

The builder uses NumPy to invert each original vertex's actual normalized weighted bone matrix. Maximum condition number is 1.544; maximum rest offset is 44.27 mm at the shoulder/armpit, p99 is 13.75 mm, median is 0.00068 mm. It rejects nonfinite results, condition numbers ≥10, maximum offsets ≥50 mm or p99 ≥20 mm. Sub-micron noise is discarded. The corrected cage matches the native target within 1 µm. The static morph directly reproduces the accepted target while preserving weights; a weight repair would create a different reskinning result.

Native stack: constant morph → Armature → Multires. Original CorrectiveSmooth is disabled after baking to avoid double correction. Runtime: original Basis plus the same morph → Armature only. Native smoothing does not hide an exported geometric defect.

The ordinary exported morph normals still produced up to 138.02 degrees of error under Three.js skinning. `glb_normals.py` writes inverse-transported normals into the **same morph's NORMAL target**, using `normalize(R_blend × (N_basis + N_delta))`. Maximum posed-normal error falls to 0.0232 degrees. This changes no positions, weights, material or morph count; the dense normal target uses 144,120 bytes.

Blender 5.2's importer ignores morph NORMAL, and Armature custom-normal transport differs from Three.js. Raw Blender importer shading is therefore not a valid morph-normal proof. `readback_glb.py` renders a temporary copy of independently decoded GLB posed positions with the actual transmitted normals transported by the exact Three.js equation. No positions or materials are substituted; the temporary mesh is neither saved nor exported. Primary's live browser review remains decisive.

## Deliverables

- `source.blend`: editable rig, original Basis, one constant corrective; 13,353,963 bytes.
- `motion.glb`: 1,193,736 bytes; one body, 10,582 original / 12,010 UV-split vertices, 21,160 triangles, 51 bones, one neutral material, zero textures, one morph at weight 1 and one 5 second action. `_SOURCE_INDEX` retains original identity.
- Shared interfaces: `clip.json`, `cameras.json`, `pose-samples.json`, `runtime-surface-reference.json`. Native frames 1..151 map to runtime 0..150; Blender world meters convert to runtime [x,z,-y].
- Current-hash evidence: `static-corrective.json`, `normal-corrective.json`, `support-patches.json`, `surface-contact-report.json`, `asset-qa.json`, `glb-readback.json`.
- Viewed target: `native-corrective-target.png`. Viewed decoded GLB proof: `glb-readback-oblique.png`, `glb-readback-hands.png`. Native start/hold/return, hand detail and corrected cage: `early-start.png`, `early-hold.png`, `early-return.png`, `early-hands.png`, `early-linear.png`. Viewed topology: `review-wire.png`. These are curated stills, not an animation frame sequence.

## Affected verification

Native and corrected linear geometry QA pass: one island, no holes, nonmanifold edges, degenerates, flipped islands, invalid weights or excess influences. Linear has no warnings. Native retains 9 hidden back-to-back face pairs around mouth/face and toes, located in `asset-qa.json`; deleting them would change accepted topology. Original out-of-range UVs remain unchanged and no textures are sampled.

All 14 separately named support patches—both palms, all ten finger pads and both knees—pass at runtime frames 0,30,60,75,90,120,150. Reports include signed distance distributions, near-contact area/fraction and zero drift. Both paths have zero loop surface error.

| Measurement | Native | Corrected linear / GLB |
| --- | ---: | ---: |
| Palm closest gaps | 1.93–1.94 mm | 2.05 mm |
| Ten finger-pad closest gaps | 1.76–3.85 mm | 1.91–4.30 mm |
| Knee closest gaps | 8.44 / 8.62 mm | 7.49 / 7.54 mm |
| Minimum near-contact fraction | 38.7% | 50% |
| Global floor minimum | 1.60 mm | 1.71 mm |
| Triangles | 84,680 | 21,160 |

The existing illustration bands are 12 mm near contact, at least 20% near fraction and at most 4 mm penetration. Both corrected paths stay above the floor. These are approximations, not exact collision or clinical guarantees. Actual GLB reimport preserves all original IDs and bones; maximum skin discrepancy against the authored corrected cage is 3.16 µm at start/hold/return.

## Provenance and remaining scope

Geometry is accepted Blender Studio Human Base Meshes v1.4.1 CC0, through `artifacts/bodyweight-five/bodyweight-five.blend`. Historical actions are removed. The action was authored from catalogue text; no capture trajectory, Gym Visual media, paid generation, texture or clothing was used. Notices remain in `artifacts/human-animation-base/README.md` and `artifacts/exercise-animation-briefs/THIRD_PARTY_NOTICES.md`.

Primary owns live visual acceptance, heat mapping, alpha, controls and integration. This corrective is valid only for the constant 4348 pose. No anatomy, coaching, physiological recruitment or production certification is implied.

## Hashes

- Original Basis/binding/rest/UV: `227ede3fc31d1a2b47ff40f20a4a7288fe7bb36179add23bae953993826c8b7b` (unchanged).
- `source.blend`: `c84b9489cae7d1f1f471afef5938b6534fd8c5c2bb0ffda6bf42183c0f7b44f3`.
- `motion.glb`: `0d7b71203d9c7918358ec9abce8b805f4d50d3e7ababf74b4c04949bec49de13`.

## Reproduce

From repository root with Blender 5.2.3 LTS:

```sh
/opt/homebrew/bin/blender -b -t 2 --python-exit-code 1 --python artifacts/exercise-batches/batch-003/assets/4348/build_motion.py
/opt/homebrew/bin/blender -b -t 2 --python-exit-code 1 --python artifacts/exercise-batches/batch-003/assets/4348/verify_asset.py
/opt/homebrew/bin/blender -b -t 2 --python-exit-code 1 --python artifacts/exercise-batches/batch-003/assets/4348/readback_glb.py
/opt/homebrew/bin/blender -b -t 2 --python-exit-code 1 --python artifacts/exercise-batches/batch-003/assets/4348/review_wire.py
```

No services, dependencies, separate viewer, videos or frame sequences are created. Shared `authoring.py` remains unchanged. Serialization hashes may change on rebuild; regenerate evidence together.
