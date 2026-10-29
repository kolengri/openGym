# Above head chest stretch — 1777

The canonical asset is the original **plain LBS GLB**, with one action `Exercise_1777`, 5 seconds at 30 fps. Geometry, contact and export-parity checks pass. Final live appearance acceptance belongs to the primary's shared Three.js review.

`motion.glb` and `motion-plain.glb` are identical: 879,444 bytes, SHA256 `a4c646a2c6333fc67fc968dfd2d6d13d00138ee5f5cdb03e56dd81371f568b7f`. Editable `source.blend` is 13,729,746 bytes, SHA256 `17a0cdde636cf0bd810877d37901bb2ff71f8903e27b54c2406eb4ec368cd555`. Complete file hashes and measurements are in `qa-summary.json`.

## Authored choices

The catalogue's fingers-linked standing setup rises through a forward clearance arc, reaches overhead and slightly back, holds quietly, then lowers gently to release the stretch. The upper thorax lifts by an authored 3.5-degree world-X pitch; the pelvis, lumbar pitch and both standing legs remain unchanged. Forearm orientation follows the upper-arm frame before elbow flexion to avoid an independent antiparallel roll. A loose interlaced finger-hook arrangement uses articulated fingers and small relative hand offsets. These are reversible illustration choices, not validated joint prescriptions.

Timing is 0–2 seconds entry, 2–3 hold, 3–5 return. The source **20–30-second workout hold** is separately preserved in `clip.json`. The symmetric staging makes the catalogue's conditional one-sided switch unnecessary. Breathing is not exaggerated into a bobbing motion.

Source roles remain pectorals primary, shoulders and upper chest additional. The primary integrates the existing soft cyan stretch field. There are no color textures, added body shells or local viewer.

`cameras.json` has two Blender-world presets: front oblique for bilateral chest/hands/feet and side oblique for reach, back contour and scalp clearance. Both have **3.8 m horizontal width** for the shared 1.65-aspect runtime panels. Curated portrait proofs use their own smaller review framing.

## Evidence

- Original binding/rest/UV hash remains `227ede3fc31d1a2b47ff40f20a4a7288fe7bb36179add23bae953993826c8b7b`: 10,582 original vertices, 21,160 triangles, 51 bones, one continuous neutral body. GLB has 12,010 UV-split vertices and complete `_SOURCE_INDEX` coverage.
- Eleven phase samples independently check native smooth skin and original-cage linear skin. All bilateral heel/forefoot patches are supported together, with zero tangential drift. Native minimum floor distance is −0.049 mm; linear is −0.00019 mm. Illustration tolerances are declared in `surface-contact-report.json`.
- Minimum sampled hand/head clearance is 37.84 mm; sampled cross-hand triangle intersections are zero. Endpoint surface error is zero. All 151 source frames are checked for rotation continuity; maximum world rotation step is 9.71 degrees per frame.
- Independently decoded GLB skin differs from source linear skin by at most 0.00144 mm; joints differ by at most 0.00123 mm. `export-parity-report.json` covers all exported UV-split vertices at eleven poses.
- Mandatory asset QA passes native/linear start and hold. Native evaluated skin retains 10–11 hidden back-to-back triangle pairs from local body folds; the unchanged linear cage has no warnings. Source UV tile coordinates are retained; no color texture is used.
- The author viewed `early-{start,peak,return}-oblique.png`, `early-entry-oblique.png`, `early-peak-{side,hands}.png`, native/linear peak wire stills and exported start/entry/peak/return stills. Curated PNG corner alpha is zero. No video or animation-frame sequence was generated.

Raw Blender import stills show shoulder shading bands and are **not** faithful Three.js-normal acceptance proof. Primary actual WebGL smoke compiled plain LBS and its existing DQ adapter without errors and observed no material armpit band under the approved material. Primary front/side intermediate/peak review, fields, interactions and live canvas alpha remain pending. No new normal precision gate applies.

`motion-normal-trial.glb` and `normal-trial-report.json` preserve a frozen, unaccepted 58-target NORMAL-only experiment. It has exactly zero POSITION deltas, but its size and GPU target count were disproportionate. It is excluded from `motion.glb`, and no final QA or faithful-render acceptance was run for it. Do not enable it by default.

## Reproduce

Use Blender 5.2.3 LTS with `-t 2`. `build_motion.py -- --final` authors the unchanged shared CC0 rig and exports the canonical plain GLB. `export_motion.py -- --plain` re-exports the saved source to `motion-plain.glb`. Run `verify_asset.py`, then `verify_export.py`, and `write_report.py` to refresh receipts after an authorized source change. `render_export.py` can render decoded GLB positions with the exact Three.js normal equation; actual browser acceptance still belongs to the primary. The frozen normal experiment requires explicit `--normal-trial`.

Only this asset directory was authored. Shared helper/runtime, other assets and Git were not changed. Motion was authored from repository text on the accepted Blender Studio CC0 body; no restricted exercise media was used.
