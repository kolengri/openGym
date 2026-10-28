# Bodyweight batch002 — live soft zones

Five new equipment-free catalogue candidates follow batch001's deterministic alphabetical selection. The user approved the soft surface heat-zone style demonstrated on chaturanga5915. These new motions remain candidates for user review.

| ID | Source exercise | Authored interpretation |
| --- | --- | --- |
| 5265 | 45 degree bicycle twisting crunch | Seated pelvic support, torso inclined about45degrees above the floor, both feet airborne, alternating knee/opposite-elbow approach. Hands behind the head without a neck-pull grip. |
| 4007 | 90 degree heel touch | Supine, raised thighs and knees bent about90degrees; alternate ipsilateral reaching while the legs remain elevated. |
| 6428 | 90 degree heel touch v.2 | Supine, both feet planted; alternate lateral reaches with the shoulders slightly lifted. |
| 10565 | 90 to90 press stretch | A representative seated90/90 side with forward hinge and a1second demonstration hold. The source does not prescribe the initial hands. |
| 6560 | 90 to90 stretch | The same source hip-stretch mechanics with explicitly documented hands on the floor and a1second demonstration hold. |

The two90/90 descriptions overlap. No different exercise mechanics are invented merely to distinguish their IDs. One representative side is shown; the opposite side is a mirrored execution. Approximate angles and contact patches are authored visual targets, not clinical measurements.

## Delivery

- [Live offline viewer](viewer.html): one downloadable HTML file containing both assets, runtime and all five selected clips; no server or network is required.
- [Inline viewer](inline.html): the same interactive scene, using a pinned source commit and Three.js0.186.1 from public URLs. The honest loading poster is replaced by the actual WebGL canvas when ready.
- [Repaired 90/90 GLB](../../bodyweight-next-five/ninety-repaired.glb) and [editable source](../../bodyweight-next-five/ninety-repaired.blend), requiring the optional [dual-quaternion adapter](../dual-quaternion.js).
- The first three actions retain the frozen [original GLB](../../bodyweight-next-five/next-five.glb). Its historical rejected 90/90 actions are excluded from the current viewer.
- [Selection and source hashes](selection.json), complete pre-authoring [contexts](contexts/), [generation contract](../../exercise-animation-briefs/generation-contract.json).

No video or animation-frame sequence is generated. The small curated PNGs are asset/contact review evidence and a startup poster, not animation output. The production application's React/Capacitor screens are not changed by this review batch.

The two90/90 demonstrations last5seconds:2seconds to hinge,1second to hold and2seconds to return. The source exercise recommendation remains20–30seconds of stretching and is stated separately in the viewer. The previous28second review loops were rejected by the user.

## Surface cues

The viewer imports the approved [field builder](../../chaturanga-heatmap/heat-field.js) and [material](../../chaturanga-heatmap/heat-material.js) unchanged. Diffusion follows the rest-mesh topology through the original vertex IDs. Nearby hands, legs or torso surfaces do not exchange color simply because they approach each other in a pose.

The three load exercises show warm primary abdominal zones and softer source additional zones. Both oblique sides describe the exercise's combined superficial/deep training emphasis; there is no invented left/right physiological activation curve. The two stretching exercises reuse the same soft falloff with a cyan palette, separating stretch from contraction/load. The front-leg glute and trailing-leg hip-flexor selection follows the authored90/90 side. Adductor, hip-flexor and lumbar surface proxies do not expose deep muscles or prove their mechanical loading.

Inactive skin is uniform neutral. There are no colored fibers or hard boundaries. The body uses one opaque material, no color maps, no AO map, no body cast/received shadows and no bloom overlay. The canvas has real alpha; dark, white and checkerboard backgrounds belong to CSS only. Relative color strength is artistic, not measured temperature, EMG, force or muscle recruitment.

## Interaction and evidence

The five buttons lazily select their GLB assets, actions and role fields. A failed model download preserves the previous live scene and allows another click to retry; older requests cannot replace a newer selection. Load exercises open a larger recommended muscle view; a complementary side/contact view and dual mode are available in the view selector. Stretching opens complementary views to expose the hip regions and supports. Drag/touch rotates, pinch zooms, reset restores the preset, and orbiting does not stop the motion. Panning is disabled. Timeline seeking and pause/resume apply to the live skeleton.

`build.mjs` builds the standalone viewer. After the accepted model is committed and published, `source-revision.json` pins that immutable commit for the inline viewer. `verify.mjs` checks all five exported poses against Blender joint samples and actual CPU-skinned GLB surfaces against original-index support patches, including full native DQ references for the repaired 90/90 asset, plus palettes, alpha, controls, action switching and responsive layout. It captures only curated review stills. `verify-inline.mjs` checks the actual network-loaded scene separately; a visible poster alone does not count as a live result.

Verification receipts state their actual scope. Desktop Chromium and emulated mobile touch checks do not certify physical iOS/Android performance or production app integration. Native corrective/subdivision and runtime linear skinning are reviewed separately. Accepted asset warnings and contact tolerances belong to the source QA reports; user review remains pending.

## Source rights

The continuous mannequin is the original CC0 Blender Studio Human Base Meshes v1.4.1 body used in batch001, with the existing51bone binding. New motions are authored from the catalogue text and explicit reversible staging choices. No licensed Gym Visual image/video is used as a derivative source. See the [source identity](../../bodyweight-next-five/source-identity.json) and [atlas provenance](../../mannequin-muscle-atlas/README.md).


## Repaired skinning and review scope

The repaired 90/90 asset uses volume-preserving dual-quaternion deformation in the live material. The original Basis, UVs, weights, rest skeleton and 51 bones are unchanged. Only the Armature modifier is enabled in its source; native CorrectiveSmooth/Multires previews are separate. Standard GLB linear playback does not reproduce this asset's approved runtime deformation. The first three actions keep ordinary linear skinning.

The separate repair restores rounded pelvic volume, natural hand support and forearm/thigh clearance. Exact source and model identities are recorded in `ninety-source-identity.json`; the final live source-bound checks are in this batch's `verification.json`. `neutral-10565.png`, `neutral-6560.png` and their zone counterparts show the actual runtime peak from complementary views. Static views do not independently prove timing or contact measurements. The initial long-hold/collapsed-pelvis version remains historical evidence, not the current candidate.

Reusable runtime code passed an independent review and a targeted retry/race correction check; see `../runtime-code-review.json`. This does not replace per-asset shape checks, user acceptance, physical-device testing or production application integration.
