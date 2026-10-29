# Exercise 2098: thumb-up ulnar deviation

Original equipment-free motion authored from `catalogue/exercises/2098.json`. The anatomical left arm stays extended in front with a down shoulder and a naturally near-straight elbow. The right hand acquires an articulated overhand grasp, then guides the left hand toward its little-finger edge. The palm stays vertical with the thumb above the little finger. This is sideways wrist adduction/ulnar deviation.

The five-second action uses 0–2 seconds to acquire the grasp and enter the stretch, 2–3 seconds to hold, and 3–5 seconds to release and return. The catalogue's 20–30-second workout hold is retained separately in `clip.json`. Mirror the complete motion for the right arm.

## Frozen asset

- Source SHA-256: `35f8d1cdff57834b527d8a672b1ae7fdef0fa62e4888c82f9f24261f38c6af33`
- GLB SHA-256: `4870528ba9034643617f816aec430bb794dcee77710fc20ca03ee6a2f4bb94ed`
- Original binding/rest/UV hash: `227ede3fc31d1a2b47ff40f20a4a7288fe7bb36179add23bae953993826c8b7b`
- One continuous watertight CC0 body: 10,582 original vertices, 21,160 triangles, 51 bones, one material, no exported images.
- One action: `Exercise_2098`, native frames 1–151, runtime frames 0–150, 30 fps, five seconds.
- Linear skinning with the original weights, Basis/rest/UV/source IDs. No weight edits, morph targets, extra bones or DQ. Original CorrectiveSmooth and Multires data are disabled in the canonical source; they are not runtime fixes.
- The accepted original input is `artifacts/bodyweight-five/bodyweight-five.blend` with SHA-256 `fbf635733118dc190fdb3cefabcde7fe4367bbccfa40aa3495a2ab2e7537d070`. The immutable batch-003 helper is imported directly; its hash is in `delivery-report.json`.

## Evidence

`surface-contact-report.json` checks all 151 native frames on the actual Armature-only cage. It reports zero cross-hand triangle intersections, fixed feet, hand/head clearance at least 0.311 m, and hand/torso clearance at least 0.295 m. `arm-clearance-report.json` also checks both complete arm/forearm/hand skins through all 151 frames with zero cross-arm surface intersections. The elbow internal angle is 172.86 degrees; the hand changes direction by 17.99 degrees at hold. Those are authored illustration measurements, not validated clinical targets.

Immutable original-index support and terminal-finger masks are in `surface-landmarks.json`. The hold thumb/index/middle minimum surface gaps are 10.24/1.72/3.11 mm; their terminal surface fractions within 12 mm are 2.4%/78.0%/66.7%. The index and middle fingers supply the clearest contact patches. The distal thumb remains a small near-contact patch and needs primary visual acceptance. Ring and little fingers remain gently articulated without an invented all-fingertip contact requirement. No proximity threshold or mask was relaxed after seeing a result.

`geometry-support-report.json` gives signed sole-distance distributions, areas, near fractions and every-frame static drift. `runtime-surface-reference.json` gives original-index sole patches at 11 frames. `asset-qa.json` passes start/hold with no errors or warnings: one island, no holes, nonmanifold edges, degenerate faces, duplicate vertices or inverted normals; normalized weights use at most four influences. Original tiled UV coordinates are intentionally preserved. No texture depends on their 0–1 range.

`export-parity-report.json` independently decodes the actual GLB node transforms, quaternion interpolation, inverse bind matrices and linear skin. All 12,010 UV-split vertices map to all 10,582 source IDs. Eleven full-surface samples have maximum skin error 1.24e-06 m and joint error 1.14e-06 m. The endpoint skin error is exactly zero. No native-only smoothing is used for these receipts.

The `early-*.png` files are curated neutral solid/wire proofs at start, grasp entry and hold, from oblique/side/rear angles, plus hand details. `hold-hands-reverse.png` exposes the opposite side of the grasp. These are individual QA stills, not an animation frame sequence. No videos were generated.

## Source facts, choices and limits

The catalogue supplies standing setup, extended elbow, thumb-up palm, opposite-hand grasp, tilt toward the little finger, down shoulder, 20–30-second hold and opposite-side repeat. Reversible choices include the anatomical left side, slight across-midline arm direction, a near-straight rather than hyperextended elbow, an approximately 18-degree tilt, a clearance arc for grasp acquisition and local thumb abduction. The initial wrist-hook gap, thumb/palm crossings and excessive elbow flexion were corrected before this freeze. The final source uses natural linear skin rather than a DQ or global geometry workaround.

The body and motion are original CC0/text-source work; no Gym Visual images or clips were opened, traced or used as animation derivatives. No clothing, genital details, muscle shells, painted fibers, textures, AO, cast shadows or specular overlays were added. The runtime-owned display should use soft cyan on selected anatomical-left forearm proxies, with softer source wrist flexor/extensor surfaces. Right assisting anatomy and hand intrinsic muscles stay neutral. These are illustrative anatomical fields, not measured recruitment, temperature, force or EMG.

The shared Three.js material/heat fields, final camera-width fit, actual canvas alpha, touch/orbit/pinch/reset and loop/endpoint-resume verification remain primary-owned. Source QA and decoded skin parity do not certify human anatomy, coaching or production readiness. `clip.json` and `delivery-report.json` retain that review status.

## Reproduce

Use Blender 5.2.3 LTS, bundled Python/numpy, and the installed Blender asset-QA skill. Each Blender process uses two threads. All outputs stay in this asset directory.

```sh
/opt/homebrew/bin/blender -b -t 2 --python artifacts/exercise-batches/batch-004/assets/2098/build_motion.py
/opt/homebrew/bin/blender -b -t 2 --python artifacts/exercise-batches/batch-004/assets/2098/verify_asset.py
/opt/homebrew/bin/blender -b -t 2 --python artifacts/exercise-batches/batch-004/assets/2098/verify_limb_clearance.py
/opt/homebrew/bin/blender -b -t 2 --python artifacts/exercise-batches/batch-004/assets/2098/export_motion.py
/opt/homebrew/bin/blender -b -t 2 --python artifacts/exercise-batches/batch-004/assets/2098/verify_export.py
/opt/homebrew/bin/blender -b -t 2 --python artifacts/exercise-batches/batch-004/assets/2098/finalize_evidence.py
```

Do not regenerate or change the frozen model without coordinating with primary; source-bound receipts must be renewed after a source change. `curated-files.json` is the delivery list. Shared files and other asset folders were not edited.
