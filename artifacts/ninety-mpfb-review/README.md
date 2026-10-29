# 90/90 interactive review candidate

Source exercise: `10565`, 90 to 90 press stretch. This is a separate replacement
candidate for user review, with a newly seated MPFB/MakeHuman body. It is not
production approval of the catalogue, the second 90/90 variant, or batch 004.

The five-second clip enters a 20-degree forward hip hinge in two seconds, holds
for one second, and returns in two seconds. The source workout hold remains
20–30 seconds. Hands rest separately on the front leg; the back stays straight.

## Delivery

- `ninety.glb`: 2,510,292 bytes, 13,408 vertices, 26,812 triangles, one continuous
  closed body, 116 joints including the common root, one standard glTF clip.
- Standard linear skinning, at most four influences, and two relative POSITION
  and NORMAL targets. No custom skinning shader or vertex-frame cache is needed.
- `inline.html`: interactive Three.js review, pinned to an immutable model
  revision. Orbit, zoom, reset, timeline, two views and a zone toggle are exposed.
- Transparent canvas; neutral inactive skin; no body shadows, textures or AO.
  Cyan soft zones indicate illustrative stretch emphasis, not measured physiology.

The native anatomical rig is preserved in the authoring snapshots. The runtime
joints are clip-specific deformation groups, rather than a generic retargeting rig.
The 276-vertex local runtime weight repair does not rewrite authored native weights.
Two disjoint corrective contributions affect six groin and 175 support/hand vertices;
the largest source-space corrective is 7.210 mm. The seated start and loop stay exact
within float32 transport tolerance.

## Evidence and limits

`surface-verification.json` checks all 151 actual GLTFLoader/AnimationMixer surface
samples: zero hip/replacement or complete hand/leg intersections, minimum floor
height −0.200006 mm, maximum classified inferior-glute gap 0.500 mm, feet within
0.066 mm of the floor, and no degenerate faces. `asset-build.json` records a maximum
GLB skinning roundtrip error of 0.123 micrometers. The groin solver additionally
checks triangle orientation over all samples. These are bounded checks, not a
continuous-time collision proof or medical validation.

Desktop renders were checked with zones both on and off. The neutral close views
do not substantiate a detached pelvis or a skin bridge between the thighs. A small
angular groin crease remains at close inspection, and a visible leg-bend shading
boundary is not classified as a deformation. The pre-existing axilla/knee contacts
(96 at the start) remain disclosed: there is no globally intersection-free claim.
Phone controls were checked with touch emulation on the unchanged viewer code;
physical-device performance and user approval remain unverified.

## Rebuild

Install the already declared Node dependencies in
`artifacts/first-exercise-3d/runtime/`. From the repository root:

```sh
node artifacts/ninety-mpfb-review/build_asset.mjs \
  --weight-override artifacts/ninety-mpfb-review/runtime-weight-override.json \
  --correctives artifacts/ninety-mpfb-review/combined-correctives.json
node artifacts/ninety-mpfb-review/build_review.mjs
python artifacts/ninety-mpfb-review/verify_surface.py
```

The Python verifier requires the versions in `requirements-qa.txt`. Its frozen
source-indexed masks are in `verification-input.npz`; provenance identifies the
unchanged original selectors. `runtime-linear-samples.bin` is generated locally
for QA and is excluded from delivery. `mesh-input.json`, `motion-input.json` and
the joint-only `joint-motion-source.npz` are deterministic authoring inputs,
without per-vertex animation samples.

## Provenance

Body, rig and target data come from MPFB v2.0.18, pinned commit
`d0a32e57a7f915cb2f2b95410e2117648c7bbb7e`, under CC0-1.0. See
`model-source-provenance.json` and `LICENSE.MODEL.md`. The MPFB addon is a separate
offline authoring dependency under GPL-3.0-or-later and is not bundled here.
Exercise staging uses the repository's textual instructions. No Gym Visual media
was used, and no paid generation service was called for this candidate.
