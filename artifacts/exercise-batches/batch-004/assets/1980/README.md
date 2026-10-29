# 1980 — across chest shoulder stretch

Original catalogue-text motion on the continuous Blender Studio CC0 body. The
representative **LEFT** arm reaches straight across the chest; the **RIGHT
forearm** supports it near the elbow. The open right hand does not grip or pull
the left wrist. Mirror both the motion and anatomical highlight side for the
other shoulder. No restricted GymVisual media, captured motion, paid generation,
video or animation-frame sequence was used.

`Exercise_1980` is the only action in both `source.blend` and `motion.glb`.
Native frames 1–151 map to runtime frames 0–150 at 30 fps. The five-second phase
envelope is enter 0–2 s, hold 2–3 s, return 3–5 s. Within entry, the left reach
finishes by 1.30 s and the right forearm enters during 1.25–2.0 s; release reverses
that order. This source-step staging avoids the two forearms passing through one
another while the active arm is still rising. The source's 20–30-second workout
hold remains separate in `clip.json`. Exact angles, foot placement and demo tempo
are authored illustration choices, not validated coaching limits.

The geometry remains the original 10,582 vertices, 21,160 triangles, one connected
skin, 51 rest bones and original UVs. Linear skinning is used in both native and
runtime paths. Corrective Smooth and Multires are disabled; no DQ, shape keys,
normal morphs, geometry warps or preview-only smoothing are used. Diagnosed axial
roll and a bounded source-topology weight diffusion remove the original sharp
trunk/upper-arm boundary. `local-weight-report.json` records the 487 original IDs,
exact original/new weights, both binding hashes, four-influence maximum and
normalization checks. The Basis, rest matrices, UVs, topology and all weights
outside that shoulder neighborhood are unchanged. A small axillary pinch remains
visible in the neutral cage; this is disclosed for primary visual acceptance.

Exactly two orthographic presets expose the left posterior shoulder/upper back
and complementary front forearm contact. `scale` is horizontal world width in
Blender coordinates. The shared runtime owns final width fitting, cyan stretch
fields, uniform inactive color, browser alpha, view synchronization and touch
interaction. All source labels (`delts`, `rear deltoids`, `upper back`) are retained
and filtered to anatomical LEFT. No recruitment curve or instantaneous activation
claim is encoded.

## Evidence

- `early-{start,entry,hold}-{side,oblique,rear}.png`,
  `early-hold-contact.png` and `hold-wire.png`: inspected neutral linear cage;
  entry is runtime frame 45. These are curated diagnostic stills, not a sequence.
- `surface-contact-report.json`: source-bound contact and fixed-foot evidence
  through every runtime frame, plus invariant and rotation-continuity checks.
- `asset-qa.json`: mandatory topology/normal/weight QA at start and hold.
- `runtime-surface-reference.json`, `pose-samples.json`, `landmarks.json` and
  `linear-vertex-reference.json.gz`: source-hash-bound original-index references.
- `export-parity-report.json`: actual project Three.js GLTFLoader/AnimationMixer
  linear position, all-51-joint and shader-normal parity at eleven phase samples.
- `alpha-report.json`: actual native PNG RGBA and transparent-corner measurements;
  this does not substitute for the primary's live WebGL canvas checks.
- `delivery-report.json`: frozen inputs, outputs, hashes, dependencies, warning
  dispositions and remaining primary-owned acceptance.

The 12 mm proximity, 4 mm floor-penetration and 2 mm support-drift bands are
illustration checks. BVH tests do not certify anatomy, coaching safety or
continuous-time collision absence. Open-patch oriented distances are diagnostics,
not closed-solid penetration depths. Contact is solved using actual skin and
ordinary IK wrist placement, without moving the body mesh or changing thresholds.

## Rebuild and verify

Run from the repository root with the immutable batch-003 helper available:

```sh
/opt/homebrew/bin/blender -b -t 2 --python-exit-code 1 --python artifacts/exercise-batches/batch-004/assets/1980/build_motion.py -- --final
/opt/homebrew/bin/blender -b -t 2 --python-exit-code 1 --python artifacts/exercise-batches/batch-004/assets/1980/verify_asset.py -- --dense
node artifacts/exercise-batches/batch-004/assets/1980/verify_export.mjs
```

The dependency body is `artifacts/bodyweight-five/bodyweight-five.blend` SHA-256
`fbf635733118dc190fdb3cefabcde7fe4367bbccfa40aa3495a2ab2e7537d070`.
Its original binding hash is
`227ede3fc31d1a2b47ff40f20a4a7288fe7bb36179add23bae953993826c8b7b`;
the explicit local shoulder binding is
`43375e8b642805a74c8d79829e82bc83045fabb57386c49cf86341c33ea6ad55`.
The Node verifier reuses the repository's existing Three.js dependency. The
historical `diagnose_*`, `contact_probe.py` and `solve_contact.py` record the local
investigation; they are not the accepted rebuild entrypoint.
