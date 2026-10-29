# Adductor stretch — 4512

Five-second live standard GLB candidate: knees open gently while the long trunk stays fixed, both hands hold the ankles and the elbows follow the thighs. Two-second entry, one-second hold, two-second return. The source workout hold remains 20–30 seconds.

The CC0 MakeHuman/MPFB body has 13,405 vertices and 26,806 triangles, one connected closed surface, 45 deformation groups plus a root and two compact hand-contact targets. The hip runtime binding and hand targets have disjoint domains. No video, runtime vertex cache, custom skinning shader or restricted reference media is used.

`source.blend` is the editable native joint action. Its Bbone/PreserveVolume surface is a separate authoring reference and contains residual native skin contacts. The delivered repaired bind, native grouped motion, harmonic weights and hand targets are declared in `clip.json`; those inputs rebuild `motion.glb` through the shared writer. `pose-samples.json` independently records native joint origins. `runtime-surface-reference.json` checks GPU transport against the decoded standard-linear surface, not native surface parity.

`delivery-report.json` records source-bound all151 contact/support/orientation checks and static QA warnings. Ten opposing proximity pairs are retained: nine from unchanged source geometry and one generated cap pair separated by0.4mm; no duplicate, nonmanifold or z-fighting error remains. Global contacts outside the repaired/contact domains are disclosed, so this is not a whole-body collision-free certificate.

Primary inspection of the actual neutral and highlighted front/rear views accepts this bounded user-review candidate. A small upper gluteal notch and angular lateral crease remain visible. User anatomy approval and application integration are pending.
