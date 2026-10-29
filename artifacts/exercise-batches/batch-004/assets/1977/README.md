# Exercise 1977 — adduction of arm in back stretch

Original five-second, anatomical **left** shoulder stretch demonstration, authored from the repository's exercise text. The right hand acquires the left wrist behind the back and gently draws it across the body. Mirror the complete action and left-side highlights for the opposite side. This is an asset for review; final shared Three.js presentation and production acceptance belong to the batch integrator.

## Source facts and authored choices

`catalogue/exercises/1977.json` explicitly permits standing or sitting tall, requires one arm behind the back, the other hand grasping that wrist and drawing it across the body, level shoulders, and a 20–30-second hold followed by a side change. The source labels are main **delts**, additional **triceps** and **upper back**. These labels are not measured recruitment, force, temperature or EMG data.

Standing is the selected source-permitted option. Exact original foot placement, initial open arm pose, left-side order, hand orientation, elbow bend planes, path and range are reversible illustration choices. The intake's heuristic seated proposal does not override its verbatim standing-or-sitting cue. Numerical joint measurements are unapproved illustration values, without invented clinical limits. No prop is introduced.

The five-second action enters during 0–2 s, holds during 2–3 s and reverses during 3–5 s; the source workout recommendation remains 20–30 s. The active arm clears the rear torso first. The assisting hand approaches above and behind the wrist, acquires it, and follows the active forearm during the gentle cross-body draw. Thumb opposition and individual finger flexion form a loose wrist grasp; the active hand retains its original relaxed wrist/forearm segment relationship.

## Geometry and deformation

- One connected original body: 10,582 vertices, 10,590 original faces, 21,160 runtime triangles; 51 unchanged bones, one skin and one action `Exercise_1977`.
- Original Basis, rest skeleton, UVs, topology and `_SOURCE_INDEX` are preserved. The GLB has UV seam copies; `_source_index` reconstructs all original IDs and original oriented triangles.
- Linear skinning is explicit in `clip.json`. Native and export use the original cage with only the Armature enabled. Corrective Smooth and Multires remain disabled, so native stills do not conceal runtime deformation. No shape keys or DQ path are used.
- The original source had hard shoulder/trunk weight boundaries. After correcting the arm/elbow frames, a bounded bilateral shoulder diffusion repairs those boundaries. `local-weight-report.json` lists every original/new influence for 974 declared IDs; all other weights remain bit-exact. Maximum four normalized influences. No global warp, inverse-LBS fitting, basis edits or extra bones.
- Elbow bend directions parallel-transport the original plane and gradually apply the reviewed endpoint twist. Forearm frames move with their upper arm. This avoids a near-axis point-pole flip while preserving the lowered-elbow hold silhouette.
- One neutral material, no textures, clothing, disconnected muscle shells or genital detail. Root owns the stable cyan source-region fields, selected left side only.

## Evidence and limits

`surface-contact-report.json` checks every runtime frame 0–150, including acquisition and release, on actual Armature-only skin. It records fixed original-ID heel/forefoot patches, foot drift, actual global skin minimum separately from the floor datum, wrist grasp, arm/arm, distal-arm/trunk and hand/head distances and triangle intersections, shoulder levels and rotation continuity. `landmarks.json` fixes the original source patch IDs before posing. Signed distances to open anatomical patches are diagnostics, not solid penetration depths.

The 12 mm proximity, 4 mm penetration and 2 mm support-drift bands are existing illustration bands, not anatomical validation. Numerical parity or a passing band alone does not certify the human silhouette; curated side, oblique, rear, grasp and wire stills supply the visual evidence. A small stable source axilla crease is retained; the large torn shoulder boundary and squared elbow shear were repaired.

`asset-qa.json` is the installed mandatory Blender game-profile check at runtime frames 0,30,75. The original UV coordinates extend outside the first 0–1 tile; this diagnostic is preserved intentionally for source identity, with no runtime color texture. There are no standard QA errors or warnings in the accepted revision.

`export-parity-report.json` loads the actual GLB using the project's Three.js `GLTFLoader`, `AnimationMixer` and skin transforms. It compares complete original-ID skin positions and all 51 joints at 11 poses, original triangle orientation, loop closure, weights and normals. Normal comparison uses the exact Three.js four-weight `skinnormal_vertex` matrix equation; there are no POSITION/NORMAL morph targets. Export parity requires the source contact report to pass.

The native curated stills have true alpha and no shadows, cavity/AO or specular overlay. `native-proof-reference.json` binds their hashes to the final source, and `alpha-report.json` verifies transparent corners. Root still owns actual browser canvas alpha, cyan fields, default width fitting, synchronized views, orbit/pinch/reset, seeking, loop resume and final visual acceptance. These source/export receipts are not browser, physical-device, coaching or clinical validation.

## Files and reproduction

`curated-files.json` names the frozen delivery files, SHA-256 hashes and external dependencies. Diagnostic work files and Blender backup files are not part of the curated packet. Native frames 1–151 map to runtime frames 0–150 at 30 fps. `cameras.json` contains exactly two orthographic Blender-coordinate presets; its `scale` is horizontal world width. The posterior oblique exposes the left shoulder/upper-back and grasp; the complementary left side exposes posterior reach and torso clearance.

From the workspace root, using Blender 5.2.3 LTS and the existing project Three.js installation:

```sh
/opt/homebrew/bin/blender -b -t 2 --python-exit-code 1 --python artifacts/exercise-batches/batch-004/assets/1977/build_motion.py -- --final
/opt/homebrew/bin/blender -b -t 2 --python-exit-code 1 --python artifacts/exercise-batches/batch-004/assets/1977/verify_asset.py
node artifacts/exercise-batches/batch-004/assets/1977/verify_export.mjs
```

The authoring script imports immutable `batch-003/authoring.py` directly and calls `initialize()`; it does not execute historical build entrypoints or copy the helper. The input `artifacts/bodyweight-five/bodyweight-five.blend` has SHA-256 `fbf635733118dc190fdb3cefabcde7fe4367bbccfa40aa3495a2ab2e7537d070`. Original binding/rest/UV identity is `227ede3fc31d1a2b47ff40f20a4a7288fe7bb36179add23bae953993826c8b7b`; repaired binding is `a18e8f4522c51fdd752ecb46a33efb68d1bc539441d6349f4e5f023a628b1f39`.

## Rights and provenance

The continuous mannequin originates from official Blender Studio Human Base Meshes v1.4.1, CC0, through the repository's accepted original rig. See `artifacts/human-animation-base/README.md` for body provenance. This action is newly authored from text and does not reuse the historical squat/capture action.

Exercise text and derived repository material retain openGym's GNU AGPL v3.0 notices: `LICENSE`, `NOTICE.md` and `artifacts/exercise-animation-briefs/THIRD_PARTY_NOTICES.md`. No Gym Visual image, video or derivative was opened, traced, fed to AI or used. See `catalogue/media/NOTICE.md`. No paid generation, video or animation frame sequence was created; the PNGs are selected stills for skin and contact review.
