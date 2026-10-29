# Batch 005 — live soft-zone exercise review

Five equipment-free catalogue records follow batch 004: 2395, 3948, 4714, 5266 and 1512. Delivery is an interactive GLB + Three.js review, with transparent canvas, neutral inactive skin, warm load emphasis and cyan stretching emphasis. The fields represent source muscle labels, not measured force, temperature or EMG. No generated video, runtime vertex cache or restricted reference-media derivative is used.

| ID | Exercise | Motion and reuse |
| --- | --- | --- |
| 2395 | Air bike v2 | Alternating opposite elbow/knee movement, with the additional source lower-back-support cue. Reuses the prior bicycle authoring and original corrective components; support, posterior binding and shoulder corrections are declared separately. |
| 3948 | Air squat | Parallel-thigh squat with grounded feet and arms reaching forward. |
| 4714 | Air squat v2 | Same physical model and compatible trajectory as 3948, with its own action identity and additional calf emphasis. The viewer loads one shared `squat` GLB. |
| 5266 | Air twisting crunch | Knees remain fixed in a raised tabletop position while the upper trunk turns alternately. Shares the frozen lower-back-support and posterior binding recipe with 2395. |
| 1512 | All-fours quadriceps stretch | One-sided same-hand ankle-held interpretation of conflicting catalogue prose and steps. The other side is mirrored. |

Each dynamic clip completes both sides in five seconds. The stretch uses two seconds to enter, one second to hold and two seconds to return. Its source workout hold of 20–30 seconds remains separate from demonstration timing. Numeric joint angles and staging choices are authored values, not source facts.

## Playback

The recommended views open by default. Drag or touch rotates the body; pinch or the wheel changes scale, and reset restores the selected view. Both whole-body views retain the complete motion. No body shadows, ambient occlusion, color textures or background plane cover the muscle fields. Shared-asset selection restores each catalogue record's action and muscle field.

Run `node artifacts/exercise-batches/batch-005/build.mjs` from the repository root to create the offline `viewer.html`. Open that file directly. An immutable `source-revision.json` additionally enables the compact `inline.html`, which fetches the exact committed model bytes. The offline file is generated locally and excluded from Git.

The review uses Three.js 0.186.1. Abdominal exercises and 1512 require the existing dual-quaternion adapter; the shared squat uses standard linear skinning. A generic GLB player without that adapter does not reproduce the DQ previews. Asset READMEs and explicit manifests document the source recipes and dependencies. The original CC0 `bodyweight-five.blend` is included as an immutable shared source dependency.

## Evidence and limits

The per-asset packets preserve native pose and surface references, full 151-sample physical checks, export/native parity, original source IDs and game-profile mesh QA. `verification.json` covers live playback, framing, action selection, seeking, transparency and simulated touch/pinch/reset. `camera-fit.json` records width-only fitting without changing recommended angles or targets. `visual-review.json` records the actual accepted images and bounded shape judgments.

The original continuous body has angular joint contours in deep flexion. Minor knee/grip facets and a small thigh/pelvis contour notch remain disclosed. Retained crease/self-fold diagnostics are distinguished from mandatory mesh errors and complete arm/hand-versus-leg clearance. The suspected long thigh “sheet” was disproved by raycasting: it is a raised thigh occluding the separate waist. See `findings.md` and the causal receipt; no needless corrective is added to erase real occlusion.

This is a user-review artifact. Production application integration, physical-device performance and clinical exercise validation remain outside this batch. Previous rejected 90/90 and butterfly geometries are not source foundations.
