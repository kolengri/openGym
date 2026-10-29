# 3995 held cuff component

The native held shape `a50d65d6c27e` is accepted. Its immutable POSITION+NORMAL
archive is `wrap-cuff-target.npz`, SHA-256
`32711c5d0e73e06372aa2b037403763e2e263e10a27d42864e1a1ba4fb5677ca`.
`corrective.py` installs the `WrapRightOverCuff` key at value zero. It validates
the canonical source binding and existing targets, adds no animation, and is
idempotent. The production writer owns keyframes, reset, export and decoded
runtime verification.

This packet does **not** establish full-cycle shape acceptance. The direct
`p * held_delta` transition was rejected at runtime frame 18 because its cuff
looks cut open. `mid-wrap/` contains unaccepted diagnostic targets and unique
proofs, excluded from the held deliverable manifest. Work on further targets
is paused while the independent midpoint diagnosis tests the excessive
intermediate humeral axial repair. The frozen held target, start pose, and
three other actions must remain exact.

## Input and scope

`inputs-contact/source.blend` is an immutable snapshot of the writer's
`held-wrap-tangent-88c2da9b3095/source.blend`, SHA-256
`88c2da9b30955e3793637fe5f8a086e0ca7339d395cf20997d6b3fdcac817c1e`.
Its contract and exact motion source are beside it. The held state is
`Exercise_3995`, runtime frame 37.5 / Blender frame 38.5. The action contains
two repetitions of the same right-over hug. The source does not require
alternating the upper arm.

The component preserves the original 10,582-vertex body, 21,160 triangles,
51-bone rig, Basis, rest transforms, UVs, weights, all existing actions and
both accepted ownership targets. Its binding signature is
`6c3c40b3a5ba6fcbe33e75b6599b21233b8ad03d29b0bd028e0efcff967f1b38`.
The old targets remain independent and can stay at zero for this hug.

## Construction and channels

The source has a severe ownership cliff at the axillary attachment. One
6.34 mm source edge stretches to about 297.6 mm at the held pose. Reducing
that edge to twice its source length requires at least 142.46 mm of symmetric
endpoint displacement. The initial 60 mm diagnostic budget could not meet
that bound; the authorized local source cap is 175 mm.

The accepted target uses a positive-cotangent screened harmonic **virtual**
influence field, a compact C1 graph-geodesic collar, transported source-edge
differentials, and two exact barycentric hand-contact points with tangent
planes. Local unilateral fairness checks the immutable distal arm surfaces.
The construction field does not replace any canonical skin weight. It is
compiled into one source POSITION target using the inverse of Blender's
native blended unit dual-quaternion rotation.

POSITION changes 845 source IDs. The maximum source displacement is
156.609058 mm; the measured native held displacement is 156.609043 mm.
The 9,485 protected source positions are exact, including physical neck/head,
hands, fingers, distal forearms, hips, legs and support. The local collar
has a protected-distance feather rather than a hard semantic POSITION seam.
The upper shoulder/trapezius fringe is classified anatomically; any nonzero
`Neck` skin weight is not treated as proof of physical neck membership.

NORMAL comes from Blender's source `ShapeKey.normals_vertex_get()` target
minus immutable Basis normals, matching standard glTF source-normal
semantics. It is not an independently invented smoothing field. NORMAL
changes 1,026 source IDs, of which 181 have unchanged POSITION. The union of
POSITION and NORMAL support is 1,026 IDs; both channels are zero outside it.
`normal-boundary.json` records six unchanged neck POSITION vertices whose
geometric NORMAL changes because an opposite corner of an original quad
moves. Their maximum source normal-vector delta is 0.025029, about 1.43°.
Those legitimate coface changes are retained; POSITION protection does not
imply artificial NORMAL pinning.

## Evidence and limits

`component.json` contains exact source IDs, protected IDs, all attachment
pairs, bounds, contact anchors, preservation receipts and game QA. At the
held pose all 21,160 triangle areas are positive; the minimum is
`5.8951972192744506e-8 m²`. No true distal-arm, hand, head or bilateral arm
crossings remain. The 55 raw attached Arm/Spine1 pairs are retained as
explicit localized cuff/pectoral compression diagnostics. Root accepted
that held shape; these are not hidden by a broad group exemption.

The accepted contact anchors preserve the opposite posterolateral upper-back
patches. The native top palm is about 2.00 mm from the body, with coherent
skin-normal dot about -0.820; the bottom palm is about 5.10 mm away, dot
about -0.985. This is hand reach with an anterior/lateral wrist, not a wrist
forced deep behind the opposite shoulder.

The native game-profile QA has zero errors and zero warnings at neutral and
held states. `qa-wire*.png` provides the required wire review. The importer
verification is idempotent and reproduces the accepted held POSITION,
geometric NORMAL and all 51 bone matrices bit exactly. Twelve sparse
zero-component samples across the four actions preserve native POSITION,
NORMAL and bones bit exactly. The writer owns the complete 151-frame
native/decoded and other-action preservation checks.

`proofs/a50d65d6c27e/{neutral,held}-{front,side,rear}.png` are the accepted
shape packet. The associated historical preview receipt also contains a
provisional squared-p intermediate sample; it is not a current transition
acceptance receipt. Likewise, `component.json` records the originally
proposed direct-p timing. Both timing proposals are superseded by the
ongoing midpoint diagnosis; the archive itself stays frozen.

`boundary-contact-classification.json` localizes the later frame-18
RightArm/Neck-owned pair to proximal axillary arm and upper pectoral chest.
Its exact finite triangle intersection is 1.458 mm long and a chest corner
crosses the cuff facet plane by 1.780 mm. Anatomical localization does not
establish visual acceptance: root rejected the whole midpoint cuff despite
that small local pair. No broad Neck exception is justified.

## Import and reproduction

Load `corrective.py` from its exact frozen path and call
`install(body, rig, scene)`. The default archive hash is read from
`component.json`; the existing-key hashes are read from `capture.json`.
The helper does not activate old keys, edit slots or write animation.
The archive includes sparse source POSITION deltas plus full source-indexed
Basis NORMAL and NORMAL deltas. The writer must export/transport those
channels, preserve source IDs, and reset the component outside action 3995.

The source POSITION archive `accepted-position.npz` is frozen separately at
SHA-256 `a50d65d6c27e7b18a9aeb962919f9ff196b4dae19ce295d3c6a4d7b26415d4f9`.
`accepted-construction.json` records its exact construction. The compact
`accepted-held-reference.npz` replaces a duplicate working blend for native
import verification. Working blends, old contact inputs, trials, logs,
caches and unaccepted midpoint targets are excluded from `curated-files.json`.

The existing environment is recorded in `environment.json`; nothing was
installed. Use `/opt/homebrew/bin/blender -b -t 2 --python-exit-code 1 -P`
for Blender scripts, and the existing project interpreter at
`artifacts/mannequin-mpfb-prototype/local-topology-repair/dependencies/venv/bin/python`
for `construct.py`. `dependencies.json` records exact read-only inputs and
QA helper hashes. A reproduction sequence is:

1. `capture.py` captures the frozen canonical channels and four sparse FK states.
2. `contact.py` records actual native palm/back contacts.
3. `measure_target.py` recreates canonical clearance domains using the accepted target.
4. `construct.py` reconstructs the held POSITION target for comparison with the frozen archive.
5. `finalize.py` uses the frozen accepted POSITION archive, derives geometric NORMAL,
   checks protection and game QA, and writes the final component payload.
6. `verify_import.py` checks default import, idempotence and exact accepted native parity.

Do not regenerate the accepted proof directory in place, replace either old
ownership key, refit binding, or activate a full-cycle export from this held
packet before the midpoint issue is resolved.
