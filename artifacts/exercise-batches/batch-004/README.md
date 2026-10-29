# Batch 004 — live mannequin and soft muscle zones

Five original equipment-free catalogue illustrations follow batch 003 in casefolded English-name order. Four use the continuous Blender Studio CC0 body. Butterfly uses the CC0 MakeHuman body authored through MPFB. These are review candidates for GLB + Three.js integration, not a deployed application change.

| ID | Exercise | Required movement and contact |
| --- | --- | --- |
| 1980 | Across chest shoulder stretch | One straight arm crosses the chest; the other forearm gently presses it, with the working shoulder relaxed. |
| 2098 | Adduction hand with elbow extended stretch | Straight left elbow, vertical palm and thumb up; the assisting hand guides ulnar deviation toward the little finger. |
| 1977 | Adduction of arm in back stretch | One arm behind the back, opposite hand holding its wrist and gently drawing it across the body; shoulders level. |
| 4512 | Adductor stretch | Seated butterfly, soles together, hands holding ankles, elbows gently pressing thighs. Knees need not reach the floor. |
| 0003 | Air bike | Supine alternating opposite elbow/knee approach with the other leg extended and hands behind the head. |

The four stretch demonstrations enter for two seconds, hold for one second and return for two seconds. Source workout holds remain separately stated as 20–30 seconds. Air bike shows both sides in a complete five-second cycle. One-sided stretches explicitly allow a mirrored execution.

The earlier 4512 broad-groin-fold candidate is rejected. Its replacement uses a repaired seated cage, a six-degree knee-opening path and separate runtime binding/hand-contact fixes. The trunk stays fixed. A small upper gluteal notch and angular lateral hip crease remain disclosed for user review; passing numeric checks does not establish anatomical approval. Historical failed staging and forward-hinge experiments are excluded from delivery.

## Delivery contract

`assets/<id>/source.blend` is editable; `motion.glb` is the runtime asset. For 4512 the Blender file is the native kinematic reference, not an exact runtime surface. Its final repaired bind, grouped joint motion, harmonic runtime weights and two hand corrective targets are explicit inputs under `../../butterfly-mpfb-review/runtime/`. Rebuild that runtime asset with the generic `../../ninety-mpfb-review/build_asset.mjs` writer. The four Blender Studio assets retain their original 51 bones, Basis, UVs, source vertex IDs and rest skeleton. A replacement MPFB asset must declare its own source-vertex domain and clip-specific deformation groups. Local topology changes require explicit parent-face provenance and an unchanged complement. Any diagnosed local binding change or small pose corrective must be declared by the asset's delivery report; original-weight preservation is not a substitute for a plausible human figure.

`selection.json` binds catalogue identities and source hashes. `contexts/` carries current instructions and source gaps; frozen asset-level `authoring-context.json` records the inputs used by its author. `clip.json` declares source muscle labels, timing, display mode, highlighted anatomical side and skinning method. `cameras.json` contains two recommended orthographic views. `build-manifest.json` binds the generated viewer to actual source/runtime inputs.

1980 and 1977 use ordinary linear skinning with explicitly recorded local shoulder weight diffusion; original weights outside their declared neighborhoods are exact. 2098 keeps the entire original linear binding without morph targets. Air bike uses the original binding, the shared `../dual-quaternion.js` adapter and three compact position/normal targets, including a small local flank correction that preserves actual pelvic support. Standard linear GLB playback does not reproduce this DQ asset's intended appearance. Butterfly uses ordinary linear GLB playback with 13,405 source vertices, 26,806 triangles, 45 deformation groups plus a common root, four normalized influences and two hand-contact targets. Its runtime weight override affects 547 hip vertices; the two corrective targets affect 112 hand vertices and do not overlap that domain. The native Bbone/PreserveVolume surface is not claimed to match runtime skinning. The viewer binds muscle fields to each asset's actual source-vertex domain. Native Smooth/Multires previews and Blender importer normal handling are not runtime appearance evidence.

`viewer.html` is a self-contained offline live Three.js viewer. `inline.html` loads the same GLBs from the immutable source commit in `source-revision.json` after publication. There is no video or animation frame sequence. Curated neutral/wire stills document posed-surface QA only.

Warm fields indicate primary/additional load; cyan fields indicate stretching. Inactive skin stays neutral. These are artistic anatomical proxies, not measured activation, force or temperature. Body shadows, AO and color textures are disabled. The WebGL canvas is transparent; selectable backgrounds sit behind it. Drag/touch rotates, pinch zooms, reset restores the recommended view, and orbiting keeps motion running.

## Rebuild

From the repository root:

```sh
node artifacts/exercise-batches/batch-004/build.mjs
node artifacts/exercise-batches/fit-cameras.mjs 004
node artifacts/exercise-batches/batch-004/build.mjs
node artifacts/exercise-batches/batch-004/verify.mjs
node artifacts/exercise-batches/batch-004/build.mjs
```

The camera fitter changes only horizontal widths to frame actual animated skin. Every exercise retains a whole-body view. An optional `frameSourceIds` array explicitly declares the original vertices to frame in a companion detail view; 2098 uses a hand/forearm close-up. Both views retain the complete model, and orbiting is unrestricted. Detail framing does not weaken whole-body support or surface-parity checks. Run `verify-inline.mjs` only after the immutable source commit is public. Actual rendered anatomy and contacts require primary review in addition to numerical parity. Source-authoring handoff reports do not supersede the final integration state. The five assets remain user-review candidates until their movement and anatomy are approved.
