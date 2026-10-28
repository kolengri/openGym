# Next five live exercise review prototypes

Five independently authored actions on the original continuous CC0 Blender Studio
human. The catalogue text and prepared batch002 context packets supply the movement
cues. No Gym Visual media, paid service, BP3D or FaceForge data was used.

`next-five.blend` is the editable native source. Its original rest coordinates,
topology, UVs, skin weights and 51 bones remain unchanged. Native skin retains the
accepted corrective smooth and one subdivision. `next-five.glb` exports only the
original linear Armature cage: one mesh, one skin, 51 bones and 21,160 triangles, with
`_SOURCE_INDEX` on every exported vertex. The single neutral material has no color
textures; the approved live heat shader uses the unchanged original-index masks.

## Actions and source interpretation

| ID | Authored demonstration |
| --- | --- |
|5265|Seated balance, torso about 45 degrees, feet airborne; alternating knee and **opposite** elbow approach. Light fingers behind the head, without neck pulling. The source classifier blocker is retained beside its explicit authored resolution.|
|4007|Fixed raised legs with approximately 90 degree knee bend; alternate ipsilateral reaches toward the lateral heel.|
|6428|Both feet stay on the floor; slight shoulder lift and alternating lateral near-heel reaches.|
|10565|Left leg in front/right leg trailing in seated 90/90; flat-back pelvic/spine hinge, relaxed hands,24 second hold and return. Hand placement is an authored source-gap choice.|
|6560|The same documented90/90 hip stretch, with hands on the floor. Light fingertip contact rolls toward palms-down contact through the hinge.24 second hold and return.|

The two stretch sources substantially overlap. Their documented hand cues are
preserved without inventing a different stretch mechanic. One representative side
is shown; repeat the mirrored side. `clips.json` preserves the original muscle
labels and assigns both to the cyan stretch display. Stronger front-left glute
emphasis and softer source-label context are illustrative; deep hip/adductor/lumbar
surface proxies do not establish passive elongation, instantaneous activation or
EMG. Inactive skin remains uniform.

## Rebuild and checks

Run from the repository with Blender 5.2.3:

```sh
/opt/homebrew/bin/blender -b --python-exit-code 1 -P artifacts/bodyweight-next-five/build_motion.py
/opt/homebrew/bin/blender -b --python-exit-code 1 -P artifacts/bodyweight-next-five/verify_poses.py
/opt/homebrew/bin/blender -b --python-exit-code 1 -P artifacts/bodyweight-next-five/export_runtime.py
/opt/homebrew/bin/blender -b --python-exit-code 1 -P artifacts/bodyweight-next-five/review_poses.py
swift artifacts/bodyweight-next-five/compose_qa.swift artifacts/bodyweight-next-five
python3 artifacts/bodyweight-next-five/refine_runtime_cameras.py
```

The last command refines only the two90/90 runtime camera pairs after native QA.
The anterior view exposes the trailing-right hip and the posterior view exposes
the selected front-left glute. It updates the camera JSON and delivery manifest;
the native source, GLB and their motion/surface receipts remain unchanged. Final
Three.js framing and interaction checks cover these runtime views separately.

The authoring script checks the accepted input SHA and all 21 context rules before
loading it. It imports only math helpers from the old authoring script through AST,
never runs that entrypoint, removes inherited actions, and verifies the complete
rest/topology/UV/binding signature. Sparse authored keys are sampled at 30 fps during
export; the24 second stretch holds are genuinely stationary timeline intervals.

`landmarks.json` freezes local original skin indices and the floor/support state
for each exercise. These are artist-authored skin patches, including the seated
pelvic/upper-thigh junction, not clinical ischial landmarks or atlas-only proxies.
`surface-contact-report.json` measures native and pure-linear skins at 49 phase
poses each. It includes distance distributions, estimated near-contact skin area,
near fractions, penetration, tangential drift, signed hand/head/lower-body
clearance, segment angles and loop closure. Six-direction ray parity avoids
mistaking a distant nearest triangle's half-space for inside-body penetration.

The declared illustration bands reuse 12 mm for curved support proximity, 20% near
fraction, and 4 mm maximum skin/floor penetration. A pass does not imply exact rigid
collision or medical/coaching approval. The original asset-QA gate and thresholds
are unchanged; every error must clear. Remaining warning dispositions are recorded
against their actual skin locations in `qa-review.json`.

`pose-samples.json` has `{id,frame,joints}` records for engine bone parity.
`runtime-surface-reference.json` has `{source_sha256,source_vertices,samples}`;
each sample is `{id,frame,global_floor_z,patches:{name:{indices,min_z,max_z}}}` in
Blender world metres. Original indices map to `_SOURCE_INDEX` after UV splits;
engine coordinates convert to`[x,z,-y]`. Actual Three.js verification is owned by
the primary integration slice.

The five `qa/*-solid-wire-sheet.png` files are curated independent QA views at
start/peak/opposite or hold poses, not an animation image sequence. They use a
temporary checker floor, flat neutral material and no shadow/AO/specular overlay.
The floor/cameras/wire objects are never saved into the source or exported.

These are review prototypes. User acceptance and real application/physical-device
behavior remain separate from the sampled Blender and engine receipts. Input and
output fingerprints are in `source-identity.json`, `runtime-export.json` and
`delivery-manifest.json`; transient trials and individual sheet-input stills are
excluded from the curated delivery.
