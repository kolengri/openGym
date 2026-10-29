# One bounded posterior hip fairing

The new adapter is `static-cage.npz`. It is numerically validated and frozen. After viewing all three images, the primary accepted it only as a bounded motion/runtime user-review candidate, with the residual upper notch and angular side crease disclosed. This is not full anatomy or catalogue approval. No action, runtime asset, GLB or export was created here.

The previous adapter and all prior evidence remain unchanged. Reuse `../transferred-weights.json`, `../new-vertex-provenance.json` and `../generated-cap-provenance.json`; their hashes are recorded in `delivery-report.json`. Triangle order, source IDs, birth IDs, cap/patch masks, UVs, neutral fields and all source-attribute samples remain exactly unchanged. Normals are updated only on the declared free vertices/corners.

## Geometry and verification

- One constrained Laplacian bending-energy solve, converged in 119 iterations. The complete step passed collision checks; no alternate solve, hull, remeshing or method sweep occurred.
- The finite authorized domain contains the 330 hip-patch vertices plus 104 one-ring collar vertices, each added vertex within 33.734 mm of the patch. Exactly 190 posterior/lateral vertices may move; anterior motion smoothly tapers to zero. The complete masks and IDs were saved before optimization in `fairing-domain.npz` and `fairing-domain.json`.
- Hands, feet, glute-floor witnesses and both generated cap banks plus their one-ring neighbors are pinned. Every vertex outside the free mask, and every boundary vertex of the expanded affected-face domain, remains bit-exact.
- Maximum delivered displacement from frozen static P0: **7.999904 mm**. A deterministic 0.1-micrometer serialization margin keeps the float32 output inside the exact 8 mm bound; this is not another solve.
- Unchanged closed, consistently oriented manifold: **13,405 vertices, 26,806 triangles, one component, Euler characteristic 2**, no nonmanifold links, no open edges and no duplicated faces.
- Float64 and delivered float32 both have **zero strict and exact-CGAL intersections** involving the pelvic/expanded repair domain. The 182 exact global residual pairs all belong to the unchanged baseline complement; no new global pairs occur.
- No zero-area faces; positive projected face orientation throughout the affected region. The smallest projected-area ratio is approximately 0.1.
- Visible crease median dihedral decreases from **116.8° to 31.3°**. Targeted edges over 120° decrease from **25 to 4**. These statistics describe the geometry, not visual acceptance.
- Native Blender readback preserves positions, faces, source IDs, UVs and full float32 weights. Mandatory game QA passes with no errors or z-fighting flags. Ten back-to-back proximity warnings remain: the nine unchanged exterior pairs and the explicitly separated generated cap pair. No faces were removed in response to those proximity warnings.

## Visual result and limits

The specialist inspected `faired-front-oblique.png`, `faired-rear-oblique.png` and `faired-side.png`. Most rear sawtooth points are removed and the lateral transition is smoother. A short upper notch/crease remains in the rear view, and the side view retains a broad angular crease. The overall accepted pose, bounds and floor-support silhouette remain unchanged. The primary accepted this limited shape for bounded runtime review, retaining the stated visual limits; no further solver variant is authorized.

Fairing is explicit generated geometry. Existing barycentric provenance continues to describe source attribute samples, not final fairing positions. `fairing_displacement`, `fairing_free_vertices` and `fairing_affected_faces` in the new NPZ record the correction from frozen static P0.

## Receipts

- `fairing-solve-report.json`: solver, displacement, topology and both-precision final collision/orientation checks.
- `native-review.json`: saved-file readback, game QA and image hashes.
- `delivery-report.json`: exact unchanged arrays, expanded boundary, artifact hashes and source-attribute references.
- `butterfly-hip-faired.blend`: standalone static review only.

The shared `new-vertex-provenance.json` retains pre-fairing geometry fields as checkpoint history. Its candidates remain authoritative for source attributes. Final P0 is exclusively this folder's `static-cage.npz:positions`; `fairing_displacement` records the subsequent geometric correction. Generated cap faces remain `birth=-1` with `cap_faces=true`, never falsely assigned an original surface triangle.
