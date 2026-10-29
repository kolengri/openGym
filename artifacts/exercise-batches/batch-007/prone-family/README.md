# Batch 007 prone family

Local native and decoded evidence for 4702/4715 alternating superman and 3294 archer push-up. The root owns the live viewer, heat fields, camera width, actual GPU review and final integration.

4702/4715 share the original 10,582-vertex body, 51-bone rest skeleton, binding and physical motion, with two action identities. Their editable source and GLB are byte-identical; exercise-specific instructions, phase metadata and native references remain separate. The 1.0-second peak raises the right arm and left leg; the 3.5-second peak raises the left arm and right leg. Frames 0/75/150 are neutral.

3294 alternates a lateral lower/press toward one bent loading arm while the opposite arm stays nearly straight with its palm planted. Both central/heel palms and distal foot/toe skin support the same floor. Ambiguous instruction 2 is interpreted using the title, description and approved batch handoff. The load peaks are at 1.0 and 3.5 seconds. A small pelvic yaw balances both full-length leg reaches without sliding the ankle targets. Ranges and timing are authored illustration choices.

The source-derived palm frame and four-degree extension matter: an earlier whole-hand minimum passed on fingertips while the palm floated 12 mm. Final support gates freeze a source-only central/heel palm patch: dominant Hand weight above 80%, 25–105 mm along Hand from the wrist. Fingers are excluded from this support patch; the separate full-hand floor check remains. Prone pelvic/lower-chest and nonraised distal limb support are measured separately. Modest upper-thoracic extension preserves the neutral neck/head relation without face support. Superman elbows use a 170-degree internal angle. Archer knees remain at 175.636 degrees; peak extended elbows are 169.5–169.7 degrees.

Only accepted causal waist/plantar binding helpers are reused, through read-only imports. No previous posed binding, shape targets, runtime caches, Basis/rest/UV/topology edits or additional bones are introduced. The source has 21,160 triangles and one neutral material. Runtime has no texture, shadow or AO dependency. The original low-poly armpit/shoulder crease remains visible at overhead extremes. Final sampled game QA has zero errors and zero warnings; the source UV layout remains unchanged. The evidence does not establish global self-collision freedom or clinical anatomy.

## Reproduction and evidence

Use Blender 5.2.3 with `-b -t 2 --python-exit-code 1 --python <script>`, followed by script arguments below. No new dependencies are installed.

- `build.py -- <id>` creates source-safe binding, 151 keyed samples and neutral start/peak/return proofs. Build 4702 once; copy its source and GLB to 4715 after export.
- `export_motion.py -- <id>` exports the native skin, original source IDs and relevant action identities.
- `verify_native.py -- <id> --game-qa` checks all 151 native samples for support, arm/leg clearance, loop closure and positive triangle areas. It saves five complete DQ reference poses, normals and actual saved weights by stable group name.
- `verify_export.mjs <id>` reads the actual GLB through GLTFLoader and the DQ adapter, checking positions, normals, source IDs, joints and sparse surfaces. Its temporary full-cycle buffer is verification-only.
- `verify_native.py -- <id> --decoded <temporary-buffer>` repeats physical gates against actual decoded positions and compares every vertex at every frame. It deletes the exchange buffer.
- `review.py -- <id>` renders diagnostic solid/wire multi-angle sheets and palm views without saving or changing the frozen source.
- `write_metadata.py` and `finalize.py` write source facts, reports and curated exact hashes.

`curated-files.json` is the inclusion list. Logs, backups, temporary decoded buffers, diagnostic/test scripts and caches are excluded. Root may update clip heat metadata and camera widths with an integration receipt. Sparse native reference files are evidence only; playback never reads them.
