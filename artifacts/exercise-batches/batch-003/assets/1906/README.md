# 1906 — abduction of one leg flexion stretch

Skin repair is authored and targeted checks pass. **Model, source, clip, cameras and references are frozen for primary live Three.js verification.** Soft-material appearance and final visual acceptance remain with the primary. Numeric parity does not certify the shape; a small rounded inner-knee flexion crease remains visible in the close proof.

Exactly one action, `Exercise_1906`, lasts 5 seconds at 30 fps: 0–2 enter, 2–3 hold, 3–5 return. Native frames 1–151 map to runtime frames 0–150. The catalogue's **20–30 second workout hold** remains separate in `clip.json`. The anatomical left knee bends and opens out, with a reversible heel-slide/outer-foot-roll staging choice. The pelvis stays level, the opposite leg remains naturally extended, and relaxed articulated hands rest palms upward. Optional hand guidance is omitted. Repeat mirrored for the other side.

Cyan fields belong only to anatomical left. Adductors remain the source main label; groin and hip flexors remain additional labels. Groin shares a visible medial-thigh proxy; iliopsoas uses a limited deep projection with visible sartorius. These are artistic stretch-location cues, not measured EMG, force, temperature or recruitment. The primary owns the live fields and interaction checks.

## Bounded skin repair

One animated corrective, `LeftHipKnee_Soften`, affects 355 feathered selected-left hip/knee vertices. It inverse-transports the existing native CorrectiveSmooth cage into rest-space offsets. The original Basis coordinates, weights, UVs, source indices, 51-bone rig rest and motion mechanics are unchanged. Maximum rest offset is 24.443 mm; maximum posed target displacement is 15.862 mm; maximum inverse-LBS condition number is 1.608. A stronger smoothing candidate exceeded the declared bound and was rejected. No remeshing, frame cache, added bones or unrelated clips are used.

The corrective is zero at both endpoints and fully active before the hold. Its keys share the single `Exercise_1906` action through a Key slot. GLB default morph weight is zero. Native original smoothing/subdivision remain in the editable source, so native versus runtime skin remains explicitly checked rather than assumed identical.

The exported NORMAL target is fitted at the hold through the actual Three.js equation, `R_blend * (N_basis + weight * N_delta)`. It corrects local normal transport without changing positions. This matters because **Blender 5.2 glTF import ignores morph NORMAL targets** and retains base custom normals. Raw importer shading can therefore show an old apparent wedge after geometry correction. The local helper was reused from the 4348 owner's normal-transport investigation, then adapted for this animated default-zero morph.

Authoritative export proofs decode actual GLB animated positions, morphs and the Three.js normal equation, then assign those posed positions/normals to temporary render-only meshes. They do not change the asset. Use `export-peak-oblique.png`, `lbs-final-peak-close.png`, `lbs-final-entry-close.png` and `export-peak-contact-side.png`; `lbs-final-proof.json` records the method. `skin-candidate-*` images are historical diagnostics, including deliberately misleading raw-import shading, and are not final acceptance proofs.

The peak fitted normal field has a maximum decoded angular discrepancy of 0.00000284° against its local geometric target. This is a CPU equation check, not a measured GPU-render error or anatomical certification. Intermediate phases are separately viewed and checked for nonzero finite normal interpolation; they are not claimed to match freshly recomputed geometry normals exactly. The minimum sampled pre-normalization normal length is 0.321.

## Geometry, provenance and frozen hashes

The accepted continuous CC0 mannequin retains 10,582 original vertices, 21,160 runtime triangles, 51 bones, one connected skin and one neutral material. GLB has 12,010 UV-split vertices, all original `_SOURCE_INDEX` values, one skin, one POSITION/NORMAL morph, one animation and no textures/images. Native rendering retains one subdivision: 42,342 vertices / 84,680 triangles.

Binding/rest/UV SHA-256 remains `227ede3fc31d1a2b47ff40f20a4a7288fe7bb36179add23bae953993826c8b7b`.

- `source.blend`: 13,506,760 bytes; SHA-256 `e6d3e9d866291229bcd17961ebcbb1031b4c2c14a705981bbccfd48a349fdbfe`.
- `motion.glb`: 1,053,304 bytes; SHA-256 `da9eec0be34e40f3e54c361fef26b52153c4db494123ee676b4e0a6d88bd9316`.

Motion was newly authored from `catalogue/exercises/1906.json`. No Gym Visual still/clip, traced pose, paid generation or inherited source trajectory was used. Historical actions were cleared. See repository `NOTICE.md`, `catalogue/media/NOTICE.md` and `artifacts/human-animation-base/README.md` for notices and CC0 body provenance.

## Current evidence

After the early actual-LBS skin proof, the repair rechecked affected poses rather than repeating the original whole check packet:

- `surface-contact-report.json`: seven poses per native/linear path, 14 surface states. Actual original-index support patches, native interpolated rest neighborhoods, contact area/fraction and tangential drift are recorded together.
- Worst floor penetration remains **2.607 mm native / 1.915 mm linear**, within the existing **4 mm** limit. Opposite-glute closest gap is at most **9.592 mm native / 11.411 mm linear**; the opposite heel remains fixed. Support closest-gap limit is 12 mm, with a 20 mm curved-surface near band. Lumbar contour is separately checked at **17.146 mm native / 8.790 mm linear**, without flattening natural lumbar curvature into the floor.
- `asset-qa.json`: both affected peak checks pass, native and linear, with no topology/weight errors. The inherited native warning is 11 hidden back-to-back triangle pairs. Original UVs extend outside 0–1; they remain unchanged and no color texture is sampled.
- `export-parity-report.json`: 11 actual GLB phase samples include animated morph POSITION/NORMAL. Maximum skin discrepancy is **0.000000674 m**, joint discrepancy **0.000000478 m**, and endpoint skin error **0 m**. Morph influence is zero at start/end; exactly one named animation and 51 bones remain.
- `hand-clearance-report.json`: six affected native/linear states, minimum sampled hand/finger-to-torso/leg gap **90.631 mm**, no penetration. Arm attachment surfaces are excluded from that nearest-triangle approximation.

Contact tolerances are declared illustration approximations, not continuous collision or clinical guarantees. A previous posterior-forearm penetration was resolved with a small elbow-pole adjustment and 4 mm wrist-target lift; the provisional 8 mm penetration band was discarded. The skin repair does not change those supports.

The early native proof and later actual runtime-equation close/overview proofs were viewed. `visual-review.json` distinguishes available images, viewed images and pending primary acceptance. Contact views use a thin Z=0 perimeter datum without an occluding floor plane. No animation-image sequence or video was generated.

## Reproduce after the freeze is released

The frozen `cameras.json` uses an overhead horizontal scale of **2.39**; the authoring generator still contains its earlier **2.15** baseline. Preserve the frozen integration preset or reconcile that baseline before regeneration. No input is being changed during the current verification freeze.

Use Blender 5.2.3 LTS and two threads per process, from the repository root:

```sh
/opt/homebrew/bin/blender -b -t 2 --python artifacts/exercise-batches/batch-003/assets/1906/build_motion.py -- --final
python3 artifacts/exercise-batches/batch-003/assets/1906/write_metadata.py
/opt/homebrew/bin/blender -b -t 2 --python artifacts/exercise-batches/batch-003/assets/1906/export_motion.py
/opt/homebrew/bin/blender -b -t 2 --python artifacts/exercise-batches/batch-003/assets/1906/verify_asset.py -- --repair
/opt/homebrew/bin/blender -b -t 2 --python artifacts/exercise-batches/batch-003/assets/1906/verify_export.py
/opt/homebrew/bin/blender -b -t 2 --python artifacts/exercise-batches/batch-003/assets/1906/verify_hands.py -- --repair
/opt/homebrew/bin/blender -b -t 2 --python artifacts/exercise-batches/batch-003/assets/1906/render_export.py
```

`build_motion.py` without `--final` stops after the early native proof and editable source. Both export entrypoints include the NORMAL-target patch. `verify_asset.py` regenerates numerical vertex references used by independent GLB verification. `render_export.py` deliberately uses decoded LBS/morph normals rather than trusting Blender's morph-normal importer.

Remaining acceptance: primary live soft-material rendering, cyan laterality, synchronized controls/loop playback and visual judgment of the rounded knee crease/groin contour. No clinical coaching, anatomical segmentation or catalogue-wide production certification is implied.
