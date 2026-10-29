# Bounded residual hand-contact target

One local source-indexed pad target clears the 32 hand/leg triangle chords in the
frozen restaging. It does not change the native grip, joints, weights, topology,
wrist/arm positions or the original source files.

The first 24-subdivision measurement localized 12 hand faces. Middle/ring finger
chords were 13-61 micrometers deep; four thumb/web faces were about 1.02 mm deep.
Refined 128-subdivision witnesses found a deepest thumb/web sample of about 1.07
mm. The primary explicitly authorized this local case under a strict 2 mm source
displacement cap. The correction uses six small translated material cores and an
18 mm geodesic feather. Measured palmar/dorsal finger pairs move together where
the correction crosses a finger section, preventing finger flattening.

`pad-report.json` records zero strict complete-hand/leg triangle crossings, maximum
displacement 1.51649 mm over 376 vertices, minimum source finger thickness ratio
0.854105, exact frozen wrist/outside-hand positions and unchanged native source.
`geometry-QA.json` records the mandatory unchanged game-profile static-cage QA.
Existing hip/axilla/knee source contacts are outside this correction's scope.

`readback-target.npz` is the actual saved float32 target, keyed by original
`source_ids`, with positions, delta, fixed triangles, geometric normals and normal
deltas. `readback-QA.json` verifies strict hand/leg zero on that saved surface,
thickness, source IDs, triangles, outside-hand identity and exact native joint M0.
Use the separate target/delta when composing with the independent hip repair.
`pad-target.blend` is an owned diagnostic copy; the original native authoring rig
remains unchanged inside it. No new render, motion or runtime export was created.

Frozen native source SHA-256:
`7d34e83cc84f821cacb1188cc0e044fc38640401d3d5d00c6d4c4b65f785ce9b`.
