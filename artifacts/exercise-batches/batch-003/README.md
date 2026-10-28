# Bodyweight batch 003 — live mannequin and soft muscle zones

Five original equipment-free catalogue illustrations, selected alphabetically after batches 001 and 002. Each exercise was authored independently on the same Blender Studio CC0 body. These are review candidates, not a deployed application change or a coaching certification.

| ID | Exercise | Authored movement and support |
| --- | --- | --- |
| 6033 | Ab tuck | Seated support with open palms beside the pelvis; one controlled knee tuck and extension with both feet airborne. |
| 4348 | Abdominal 4 points | Static abdominal brace on open palms and knees, wrists below shoulders, neutral neck and flat back. The source does not call for visible torso pulses or knee hover. |
| 3244 | Abdominal stretch | Prone chest lift with palms supporting, pelvis and lower body kept low. |
| 1906 | Abduction of one leg flexion stretch | Supine, left bent knee opens outward while the opposite leg stays extended; pelvis remains supported. The opposite side is a mirrored execution. |
| 1777 | Above head chest stretch | Standing, hands joined behind/above the head, elbows open to stretch the chest. |

The review cycle is five seconds. Stretches use two seconds to enter, one second to hold and two seconds to return. The isometric brace stays still for its five-second illustration. Source workout holds remain separately stated: 15–30 seconds for 4348 and 20–30 seconds for the stretches.

## Files and rendering

- `viewer.html` is an offline self-contained live Three.js viewer.
- `inline.html` loads the same per-exercise GLBs from the immutable commit in `source-revision.json`; it is generated after source publication.
- `assets/<id>/motion.glb` and `source.blend` are the runtime and editable assets. Each GLB has one skin, one untextured mesh and one skeletal action.
- `selection.json` records catalogue identities and source hashes. `contexts/` contains current source instructions, hand/foot/support constraints, muscle labels and unresolved source gaps. Each asset also retains its frozen `authoring-context.json` snapshot.
- `build-manifest.json` records exact model and runtime input hashes. `verification.json` records live Chromium evidence.

All five assets preserve the original 10,582-vertex Basis, UVs, rest skeleton and 51-bone binding. The ab tuck uses one local flexion-driven knee corrective and the optional volume-preserving dual-quaternion adapter in `../dual-quaternion.js`; use that adapter when integrating its standard skin data in Three.js. An ordinary linear-skin GLB viewer is not an appearance reference for this asset. The quadruped uses one constant corrective, and the left-leg stretch uses one small animated corrective with matching normal deltas. The other two assets use ordinary linear skinning. Native CorrectiveSmooth or Multires previews are distinguished from the runtime cage; unsupported Blender importer normal behavior is not treated as actual browser output.

The approved soft fields follow original mesh vertex IDs. Warm colors distinguish primary and additional load; cyan marks stretching. The rest of the body stays neutral. Color intensity is artistic emphasis, not measured EMG, force, temperature or recruitment. There are no body shadows, AO maps, color textures or bloom overlays. The WebGL canvas has real alpha; dark, white and checkerboard backgrounds are CSS behind the canvas.

Recommended views expose the selected anatomical side and supports. Drag/touch rotates, pinch zooms, and reset restores the recommendation. Panning is disabled and orbiting keeps motion running. Complementary views are available where one projection hides a selected region or contact.

## Rebuild and evidence

From the repository root:

```sh
node artifacts/exercise-batches/batch-003/build.mjs
node artifacts/exercise-batches/fit-cameras.mjs 003
node artifacts/exercise-batches/batch-003/build.mjs
node artifacts/exercise-batches/batch-003/verify.mjs
node artifacts/exercise-batches/batch-003/build.mjs
```

The camera fitter adjusts only view widths to contain the actual animated skin; final `assets/<id>/cameras.json` includes this integration override and can differ from the original authoring script defaults. Run `verify-inline.mjs` only after the pinned model commit is public. It checks the actual network resource bytes and hashes, all five selections and live motion, rather than accepting a loading poster.

Native asset reports measure sampled geometry, contacts, hand clearance and loop closure. The live verifier checks joint and actual skinned-surface parity, full original-index DQ references where applicable, five-second playback, switching races, controls, transparent canvas, responsive layout and the absence of media playback. Curated `neutral-<id>.png` and `zones-<id>.png` are single-pose appearance evidence, not animation frame sequences. Numeric parity alone cannot accept a collapsed hip, cut-looking knee or hidden active zone; actual rendered appearance is reviewed separately.

No video, animation frame sequence or paid model generation is part of this batch. Production app integration and physical-device testing remain separate from this review artifact.


The final integration state is recorded in `primary-review.json` and `verification.json`. Some asset-owned handoff reports describe the earlier source-authoring stage and its then-pending integration; they do not supersede the current live checks. User acceptance remains pending for these candidates. Frozen `authoring-context.json` snapshots are historical inputs; refreshed `contexts/` carries the current findings.
