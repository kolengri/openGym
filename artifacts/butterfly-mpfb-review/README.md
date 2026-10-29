# Butterfly runtime candidate — exercise 4512

The delivered candidate is `../exercise-batches/batch-004/assets/4512/motion.glb`. It uses a CC0 MakeHuman/MPFB body, original exercise text and standard GLB animation. No restricted reference media, paid generation, video or runtime vertex cache was used.

## Runtime sources

`runtime/mesh-input.json` contains the repaired, faired seated bind and saved hand-pad geometry. `runtime/motion-input.json` contains native joint TRS grouped into 45 deformation groups plus a common root. `runtime/hip-repair/runtime-weight-override.json` supplies one harmonic extension over 547 local vertices. `runtime/final/combined-correctives.json` supplies two source-space hand-contact targets over 112 disjoint vertices; their maximum displacements are 0.125 and 0.963 mm. `runtime/heat-regions.json` binds four bilateral adductor regions to this body's own 13,405-vertex domain.

The native motion opens the knees by six degrees around fixed hip/ankle endpoints, holds for one second and returns in a five-second cycle. The long trunk stays at its authored initial inclination. The source workout hold of 20–30 seconds is stated separately. Native Bbone/PreserveVolume appearance and the final standard-linear surface are distinct references.

The editable native action is delivered as `../exercise-batches/batch-004/assets/4512/source.blend`. It supplies joint reference motion; its unresolved native skin contacts are not final surface evidence. Final geometry, weights and targets are the explicit runtime inputs above. Local full-frame vertex samples are QA intermediates and are excluded from delivery.

## Validation and limits

The root-owned final integration report binds the actual loaded GLB to all 151 sampled states. Hip topology, orientation, full arms/hands against legs, support, loop and transport checks are separate from visual review. Hip material orientation is at least 0.9456 of the transported reference; finger material thickness remains at least 0.8541 of its neutral reference. Unrelated native surface contacts outside the repaired/contact domains remain disclosed; there is no whole-body intersection-free claim or continuous-time certificate.

The final faired topology is one connected closed oriented body with 26,806 triangles. Its unchanged game-profile static QA passes. A small upper gluteal notch and angular lateral crease remain visible and require user review. This is a bounded review candidate, not catalogue-wide anatomy approval or application deployment.

Historical first staging, forward-hinge trials, unfaired topology and the old 4512 asset are rejected. Their reports may remain local for diagnosis; they are not accepted sources.

## Rebuild

From the repository root, with the frozen JSON inputs:

```sh
node artifacts/ninety-mpfb-review/build_asset.mjs --input-dir artifacts/butterfly-mpfb-review/runtime --exercise-id 4512 --model-name motion.glb --root-name Butterfly --output-dir artifacts/butterfly-mpfb-review/runtime/final --weight-override artifacts/butterfly-mpfb-review/runtime/hip-repair/runtime-weight-override.json --correctives artifacts/butterfly-mpfb-review/runtime/final/combined-correctives.json
```

Use the existing surface verifier with this runtime input directory and final sample directory, then rebuild and verify batch 004. Building a GLB alone is not visual acceptance.
