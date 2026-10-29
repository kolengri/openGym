# Exercise 4512 native knee-out joint reference

The five-second native joint reference is complete. All 151 sampled states pass the explicitly authorized reference contract. This is **not physical hand-contact acceptance**: the native hand/ankle triangle chords listed below remain for the primary to address and verify on the actual standard GLB surface.

## Frozen integration inputs

| File | Contents | SHA256 |
| --- | --- | --- |
| `native-joint-samples.npz` | `times`(151), `bone_names`(172), `bone_world_matrices`(151,172,4,4), source IDs, source controls, support/skin QA arrays | `41ec378cdfc7dcf1ab99156b983dc2ca173970dc6a17f0d4e74877251a1dbed2` |
| `native-joint-reference.blend` | Source MPFB body and native Rigify controls, with the authored 151-frame action | `b5e8da32ede6e808c29744b77f942d4fa014429e3e6a8742315bb6363b3b2753` |

`source-receipts.json` records the immutable neutral foundation, accepted P0/native cage/M0 and accepted local hand pad. The accepted P0 remains SHA256 `7d34e83cc84f821cacb1188cc0e044fc38640401d3d5d00c6d4c4b65f785ce9b`. No foreign source, shared code, topology repair, weights, proportions or rest lengths were edited.

## Authored mechanics

- The source cue is knees falling outward. Each knee rotates downward/outward 6° about its own fixed hip-to-ankle intersection-circle axis. Hip and ankle endpoints, source leg lengths and knee flexion 125.0837° are preserved. At hold each knee moves down 31.572 mm and laterally 23.696 mm; there is no floor forcing.
- Torso, hips, neck and anatomical head stay at the accepted 15° straight-spineP0. All 151 pooled head/trunk control-frame errors are exactly 0; every sampled `DEF-spine` through `DEF-spine.006` world matrix is exactly fixed.
- The arms use closed-form source-length shoulder/wrist reach circles. Only the elbow-pole angle varies. An analytic material-plane seed and bounded scalar native-skin root keep the **whole forearm/elbow** outside the complete leg surface. The continuous branch stays within 12.724° of P0, below the 25° bound; maximum adjacent-sample step is 0.411°.
- Six original palm/finger ankle contacts retain their source triangle barycentric coordinates and local surface frames. One equal-region rigid Kabsch fit tracks this skin. Maximum wrist shift is 9.4035 mm and hand rotation 4.8843°, within the explicitly authorized 12 mm/10° reference bounds. Finger articulation and material thickness are retained.
- The accepted static hand pad is transported by the actual moving hand frame for QA. The `.blend` retains the original source mesh: the pad remains a separate target, not a new mesh edit.
- Quintic 2 s entry, 1 s hold and 2 s return are sampled at 30 fps. Source guidance to hold 20–30 s is distinct from this 5 s demonstration.

The previously reported 39.555 mm “head-joint motion” means **the beginning of any bone**, specifically `DEF-shin.R` at the knee. It is not anatomical skull motion. Anatomical head/trunk drift is exactly 0.

## Actual verification and remaining defects

| All 151 measurement | Result |
| --- | --- |
| Complete nonhand arm against complete leg strict triangle intersections | 0 |
| Whole forearm/elbow sampled skin clearance | +0.530–0.560 mm |
| Actual elbow skin to thigh skin | +0.530–0.893 mm |
| Heel and forefoot/ball sole contact | Within 2 mm on both sides; toe tips reported separately |
| Maximum posterior glute support gap | +0.4021 mm |
| Whole skin minimumZ | 0; no floor penetration |
| Minimum retained finger material thickness ratio | 0.854104 |
| Native hand/leg strict triangle intersections | Up to 22, explicitly disclosed |
| Maximum measured native hand chord depth | 0.44695 mm; conservative local cover bound 0.65481 mm |
| FrozenP0 matrices and source start/end skin | Exact |
| Saved/reopened action against all 151 captured matrices, native skin and transported-pad skin | Exact; all maximum errors0 |
| Source mesh coordinates, weights, topology, rest matrices and rest lengths before/after action saving | SHA signatures exact |

Hand face-interior depths use 128-subdivision barycentric sampling against the actual native leg surface. Each face records a conservative maximum-edge/128 local cover radius and strict triangle pairs. At 3° the remaining four thumb/web faces cross the blended ankle surface, carrying 61.5% shin and 38.5% foot weight. These defects are below the reference-only 2 mm allowance; they are **not** silently treated as contact success.

The old fixed-knee forward-hinge failure was **forearm/shin**, not forearm/thigh: leg source 4751/4752/4771 carries more than 93%`DEF-shin.R`. The current whole-forearm constraint covers that previously missed region.

`native-motion-report.json`, `sample-measurements.json`, `geometry-QA.json` and `action-readback.json` are the current receipts. Three actual saved native phase checks are included for frames 0, 75, 150. `initial-5mm-contact-gate/` preserves the original conservative 5 mm tracking/strict-hand failure; the same path was then allowed as a native joint reference with 12 mm/10° tracking and disclosed hand chords. No pose variants or geometry repair were added.

Native segmented Bbone and masked Preserve Volume deformation differ from standard linear GLB. The native source also retains the posterior/lateral hip folds assigned to the separate topology repair. Final actual GLB hip, hand and complete arm checks must independently pass strict 0 across all 151 samples. Native QA position arrays are diagnostic evidence, not a delivery vertex cache. No GLB, new renders, video, Git or publication work was performed here.

## Local reproduction

The task-owned runner isolates Blender resources and runs Blender 5.2.3 offline with two threads. The finite preflight must pass before capture. `capture_path.py` refuses to overwrite its frozen joint samples; `author_action.py` refuses a second completed action. `finish_packet.py` only reads saved arrays and receipts. Runtime folders are ignored. No global preference/add-on installation is changed.
