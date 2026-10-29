# Versioned 90/90 whole-body repair

Ready for the primary's final GPU appearance review and promotion decision.
Only this directory was written. Canonical ninety files and frozen next-five
assets remain unchanged. `promotion-manifest.json` lists exact source/target
paths, hashes, guards and curated dependencies; do not promote debug candidates.

## Diagnosis and decisions

The rejected pose spread the thighs by 135 degrees while hinging the trunk away
from the front thigh. Knee-axis and contact checks did not detect that layout
failure. Original posterior glute vertices were roughly 90–99% thigh weighted;
the excessive hip rotation therefore moved the buttock with the thigh. LBS
collapsed that region, while DQ retained its badly placed volume. Rest-body
proportions were natural. The rejected arm pose also used an inward left elbow
pole, partial elbow-plane roll and 18-degree shoulder depression.

The final pose points the front left thigh forward and the rear right thigh to
the side, preserving the measured source knee bend axes. Outward elbow poles
and consistent upper-arm/forearm frames replace the rejected arm configuration.
Original Basis, weights, UVs, source IDs and all 51 rest bones are unchanged;
the unsuccessful pelvic reweighting and free surface fairing were discarded.

Four local keys reproduce original-cage CorrectiveSmooth targets, upright and
hinged for each hand variant. The original CS5 target is combined with a
posterior-waist-only CS15 witness to soften a horizontal lumbar shelf. Inverse
unit DQ rotation transfers each target offset into a key without a singular
inverse-LBS solve. Runtime enables only the Preserve Volume Armature modifier.
There is no runtime Smooth, Multires, helper bone or topology replacement.

Final keys affect 1,885–1,887 source vertices each. Maximum offsets are 46.5,
52.3 or 59.9 mm, depending on key; local p95 offsets are 18.8–21.6 mm. These
are authored shape corrections, not clinical measurements. Endpoint native
target reproduction is below 0.001 mm. Two endpoint keys per clip approximate
intermediate native-CS shapes: maximum difference 7.56 mm, local p95 below
0.755 mm. Inspect the actual entry/return stills.

Rear thigh/calf/foot orientation establishes the floor support without lifting
the whole model. Press hands occupy separate knee/shin locations. Original
curled finger chains were extended, and the shin palm tilts 16 degrees across
the round surface. Palm-only checks had missed finger penetration; final
checks include every hand/finger vertex and hand-to-hand separation.

## Verification

- Source check: all 302 frames, 10,582 original vertices, 21,160 triangles,
  51 bones, normalized skin with at most four influences, exact original
  binding/rest/UV hash `227ede3fc31d1a2b47ff40f20a4a7288fe7bb36179add23bae953993826c8b7b`.
- All-skin floor minimum: -2.201 mm; native loop skin gap: zero.
- Hand separation: at least 34.55 mm. Press whole-hand/leg penetration:
  left 1.19 mm, right 3.65 mm. Maximum nearest palm gap: 2.60/7.34 mm on
  the curved knee/shin surface. These are illustration contact witnesses.
- Forearm-to-proximal-middle directions: press left 8.3–29.8 degrees,
  right 60.3–89.3; floor left 54.7–88.9, right 58.4–89.0. The upright
  shin hand is substantially extended; supplied close-ups remain controlling
  appearance evidence. No clinical limit is asserted.
- Asset QA passes: one closed connected mesh, no boundary/nonmanifold,
  degenerate, duplicate or inconsistent-normal errors. Two hidden opposing
  triangle pairs remain an accepted warning; no original faces were deleted.
- GLB: one mesh/skin/material, zero textures, two 5-second actions, four
  POSITION and four NORMAL morphs, complete original IDs across 12,010
  exported UV-split vertices. Both actions contain correct morph animation.
- All exported Basis/key normals match rest-normal witnesses within
  0.000083 vector error. Three.js GLTFLoader plus the exact shared CPU DQ
  adapter matches all source IDs at 22 poses: skin maximum 0.0065 mm,
  joints 0.0058 mm, morph weight error zero.

`proof/` contains curated start, entry, hinge and return views, hand close-ups
and evaluated cage wire. It uses the frozen keyed source with Armature plus
morphs, neutral skin, no AO/body shadows or source smoothing. The temporary
checker floor is absent from the GLB. `diagnosis/` shows the rejected skin and
same-source rest comparison. `early-proof/`, candidate blends and rejected
scripts are diagnostic history, not promotion inputs.

## Reproduce

Run with Blender 5.2.3 and two threads, from the worktree root:

```sh
/opt/homebrew/bin/blender -b -t 2 --python-exit-code 1 --python artifacts/bodyweight-next-five/repair-90/full-body-v2/build.py
/opt/homebrew/bin/blender -b -t 2 --python-exit-code 1 --python artifacts/bodyweight-next-five/repair-90/full-body-v2/verify_source.py
/opt/homebrew/bin/blender -b -t 2 --python-exit-code 1 --python artifacts/bodyweight-next-five/repair-90/full-body-v2/hand_contacts.py
/opt/homebrew/bin/blender -b -t 2 --python-exit-code 1 --python artifacts/bodyweight-next-five/repair-90/full-body-v2/proof_source.py
/opt/homebrew/bin/blender -b -t 2 --python-exit-code 1 --python artifacts/bodyweight-next-five/repair-90/full-body-v2/build.py -- --export
python3 artifacts/bodyweight-next-five/repair-90/full-body-v2/verify_export.py
node artifacts/bodyweight-next-five/repair-90/full-body-v2/verify_three.mjs
python3 artifacts/bodyweight-next-five/repair-90/full-body-v2/make_packet.py
```

Export limitation found and handled: Blender 5.2 ACTIONS does not collect an
inactive KEY action as it does armature actions. The exporter prepares muted
KEY NLA tracks in memory for both existing slots, without resaving the source.
The per-action weight-channel assertion caught a missing second morph clip.
Retain that assertion for future assets with several morph actions.

Actual GPU DQ/morph shading, muscle overlays, recommended camera appearance
and final human silhouette acceptance remain with the primary. CPU geometry
parity and contact numbers do not certify visual anatomy.
