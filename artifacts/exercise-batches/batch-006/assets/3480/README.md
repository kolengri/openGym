# 3480 — alternate sprinter lunge

A complete bilateral reverse-lunge cycle with upright trunk and opposing sprint-style arms. The front whole sole and planted rear toe patch stay fixed; stepping and recovery are explicitly airborne. The rear knee stays above the floor.

One shared original body/rig contains two distinct actions, `Exercise_3479` and `Exercise_3480`. Both asset folders contain identical GLB/source bytes; `clip.asset` is `standing-leg-family`, so integration should cache one geometry. Root owns that mapping and the muscle fields.

The original CC0 Blender Studio body retains exact Basis, rest matrices, UVs, topology, 10,582 source IDs and 51 bones. The accepted squat binding is reused with a toe-preserving grounded plantar overlay. Actual saved weights are normalized with at most four influences. Four compact POSITION/NORMAL targets treat only the diagnosed mirrored lunge popliteal and heel-touch shoulder collars. Source displacement is capped at 25 mm with C1 collars; uncapped fairing requirements of approximately49–52mm are disclosed in the family target report. All feet, fingers and target exteriors remain exact. Runtime skinning is standard linear.

All151 native and decoded samples pass floor, declared sole/toe support, complete arm/hand versus leg clearance, positive-area and loop checks. Maximum decoded/native position error: 1.131 µm. Decoded loop error: 0.205 µm. Minimum body height: 0.2997 mm above the floor. The full-source reference has five poses; all51 native bone positions and independent shader normals are checked. This is CPU-decoded Three.js evidence; browser/GPU acceptance remains root-owned.

Mandatory game QA has zero errors. Retained warnings: 37: hidden back-to-back faces: SK_BlenderStudioHuman (1 pairs) - delete to save tris; 112: hidden back-to-back faces: SK_BlenderStudioHuman (1 pairs) - delete to save tris. These local folded facets belong to the continuous original body; deleting them would change protected topology. Root accepted the bounded visible candidate with remaining joint creases. Exact local self-fold witnesses and opposed-normal counts remain in the full reports; this is not a globally collision-free or clinical claim.

`review-*.png` are transparent neutral/wire stills of the final saved source, with action/key/skin readback in `proof-manifest.json`. `delivery-report.json` collects measurements and limits. `curated-files.json` is the publication list; historical trials, logs, backups and caches are excluded. Shared generation/check scripts and binding/target provenance are in `../../standing-leg-family/`.

Source SHA256: `f716265a508389e5a72a151d65234341fb3013939df66b90d532df91a1bc60ab`

GLB SHA256: `3fc9b638106efc8cb697fc49f5149535cb3e45d81f6d3b875788feaaa5c7c96d`
