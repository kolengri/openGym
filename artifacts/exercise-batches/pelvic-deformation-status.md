# Seated hip deformation: unresolved acceptance

The 90/90 repair remains rejected. Do not promote another clip because selected
contacts, joint angles or Blender-to-Three.js parity pass. The neutral visible
body must have continuous hip and glute contours without crossing triangles,
and its actual inferior skin must meet the floor consistently.

## Foundation provenance

The current body is `GEO-body_male_realistic` from Blender Studio Human Base
Meshes v1.4.1. Its collection metadata credits Dan Ulrich and identifies the
asset as CC0. Both untouched local bundle copies have SHA-256
`3c121505651140ceb4d69fd1d8923f7788ffadd81672f5be14845a5f2c75c137`.

Read-only inspection found no armatures anywhere in that original bundle.
This mesh has no vertex groups, parent or shape keys; its only modifier is
Multires. No original artist rig was discarded. The present skeleton was
constructed in `artifacts/human-animation-base/retarget_motion.py`, initially
with 21 bones and Blender native `ARMATURE_AUTO` bone-heat weights. The saved
binding receipt confirms automatic binding, no unweighted vertices and four
maximum influences. Upper-back weights were subsequently restricted to trunk
bones; 30 finger bones and explicit finger weights were added later. Repeating
the same heat binder on that same skeleton is not a different repair strategy.

## Rejected approaches and their limits

- Existing 90/90 v2 support selection excludes true inferior glutes. Their
  original weights lift them 101–124 mm relative to rigid pelvis transport;
  current shape keys remove only 7–10 mm. See the direct source inspection in
  `../bodyweight-next-five/repair-90/full-body-v3/`.
- Two independent 90/90 binding candidates retained surface intersections.
  The second preserved 90-degree knees, yet actual skin penetrated the floor
  by up to 46.10 mm while selected support residuals passed. Its binding is
  failed diagnostic evidence, not an accepted reusable map.
- The butterfly investigation independently found the same coupled pelvic
  binding, root-height and support-selection problem. Its local weights,
  fixed-boundary fairing, whole-pelvis reattachment and native smoothing trials
  were rejected. Their reports live under `batch-004/assets/4512/repair-v2/`,
  `repair-v3/` and `repair-v4/`.
- Source-frame inspection did not establish a thigh-roll or frame-convention
  bug. A prescribed two-helper swing/half-twist prototype was therefore tested
  separately. The corrected knee-length field reduces crossings in the same
  hip region from 114 to 24 at start and 110 to 22 at hold, but visible anterior
  ribbons and lateral overlap remain. Its expanded-region counts are different
  measurements and must not be compared directly with the smaller-region
  counts. See `../mannequin-hip-rig-v1/prototype-report.json`.

These failures do not prove that a valid corrective surface is impossible or
that retopology is mandatory. They do rule out claiming the present candidates
fixed, accepting selected support residuals as whole-body support, and repeating
unstructured weight or angle sweeps.

## Current next step

The 53-bone prototype is stopped, unexported and unpromoted. Official MPFB
v2.0.18 source at commit `d0a32e57a7f915cb2f2b95410e2117648c7bbb7e` supplies
its own MakeHuman mesh, imported authored weights and Rigify pelvis helpers.
Its release notes include Blender 5.2 compatibility work. This establishes a
different available foundation, not successful execution or 90/90 appearance.

A separate isolated prototype is authorized under
`../mannequin-mpfb-prototype/`. Its own topology and authored rig are allowed;
frozen source IDs and the old muscle atlas cannot be transferred blindly.
No global Blender preferences, accepted assets or application files may be
changed by that prototype. It must first demonstrate a plausible neutral
seated body before motion authoring, muscle-field transfer, export or
application integration. Required helper scale must not be removed to fit the
old rigid DQ adapter: a later GLB may use ordinary Three.js linear skinning,
with evaluated translation, rotation and scale baked and separately checked.

The MPFB base mesh, macro targets, rig definitions and weights are bundled
CC0 assets; MPFB addon code is GPL-3.0-or-later. Official sources:
[release](https://github.com/makehumancommunity/mpfb2/releases/tag/v2.0.18),
[compatibility notes](https://static.makehumancommunity.org/mpfb/releases/release_2018.html),
[authored rig definition](https://raw.githubusercontent.com/makehumancommunity/mpfb2/v2.0.18/src/mpfb/data/rigs/rigify/rig.human.json),
and [asset licensing](https://static.makehumancommunity.org/about/license.html).

## MPFB checkpoint: execution succeeds, contacts remain rejected

The pinned source archive was downloaded and verified at 45,601,989 bytes,
SHA-256 `ada7c4ff11e79cf6ed9b441bccabc52c9359f2848b988f66e89c14c30b21fed7`.
Factory-startup, offline, artifact-contained extension loading and native rig
generation succeeded in Blender 5.2.3 without saved preferences. The visible
macro-evaluated cage has 13,380 vertices and 26,756 triangles; the authored rig
has 930 total bones and 181 deform bones. This is execution evidence, not
appearance or export acceptance.

The first horizontal-axis construction left the legs 48–71 mm above the
floor despite both knee angles being 90 degrees. A single local grounding
solve lowered the thigh directions by 8.797/9.394 degrees, kept transverse
shins and original lengths, and maintained 90-degree knees. Calf and foot
minima became 0.063–0.068 mm above the floor. This is an actual skin-grounding
improvement, not acceptance of all supports.

The grounded source (`5899b079aed9d43a3f3211c05d0052f16099351b4f37a4904f10c149a481f6e1`)
still fails contact acceptance:

- 42 strict face crossings form one left anterior/medial groin cluster. The
  broader skirt is absent in the inspected views, but this residual fold is
  real. Neutral has zero pairs under the same pelvic-region predicate.
- 388 hand/leg crossings form two clusters. Correct 1.50 mm palm-center
  clearance did not protect finger skin. Check the complete contacting skin.
- The whole-skin floor point is source 4466, near the central perineum and
  91.6% attached to the right thigh. The separately classified posterior
  inferior-glute patch remains 5.07 mm above the floor. This does not certify
  buttock loading.

The native/export boundary is also explicit: 139 deform bones use 8 or 10
B-Bone segments, helper scales vary, and the native cage uses mixed linear
and masked Preserve Volume modifiers. Ordinary 181-joint TRS export cannot
be assumed to reproduce that deformation. Evaluated quad tessellation also
changes between poses; freeze delivery triangles before comparisons.

One separate fixed-triangulation seated bind-cage cleanup is authorized:
bounded 3D local groin fairing, complete hand-skin contact correction and a
small posterior seat fit. No original rig weights or bone lengths may be
changed. Maximum posed displacements are 15 mm, 10 mm and 8 mm respectively,
with exact exterior equality and actual skin/crossing review required. It is
an unaccepted target, not a finished animation or export.

A later clip-specific seated bind pose is a narrower runtime option than
reproducing the entire native control rig. Three.js 0.186.1 source confirms
that `Skeleton.calculateInverses()`, `SkinnedMesh.bind()` and `GLTFExporter`
can write inverse binds at sampled joint transforms. This can preserve an
accepted seated cage at the bind sample, including affine helper transforms.
It does not establish correct subsequent hinge deformation. Future motion,
floor contact and exported surfaces still require their own actual checks.

## Exact local topology repair: structurally valid, visually unfinished

The single bounded fixed-topology fair target failed: 42 strict groin pairs
became 22, ten vertices reached the 15 mm cap, and the minimum triangle-area
ratio fell to 0.05757. No hand or seat target was attempted in that phase.
Its records are under `../mannequin-mpfb-prototype/seated-cage-cleanup/`.
The complete conservative hand/finger selector finds 407 strict hand/leg
pairs; the earlier thresholded selector omitted 19 wrist/blend witnesses.

Released libigl 2.6.3 provides an exact-CGAL outer-hull implementation through
a compatible arm64 Python wheel. The local topology prototype classifies the
closed whole body, then splices only hull faces born from the declared groin
disk into the untouched complement. It does not accept whole-body hull changes
or fuse the hands and legs. The library is an isolated, reproducible offline
dependency, not a new application renderer.

The replacement has 350 triangles and 203 vertices with the same oriented
54-edge boundary and disk Euler characteristic 1. The full body has 13,408
vertices and 26,812 triangles and remains one closed manifold with Euler
characteristic 2. Original hip-domain descendants and every replacement face
have zero strict and exact-CGAL intersection/contact reports, including after
float32 conversion. Unaffected positions, oriented triangle identities, UVs
and weights are exact. Newly stitched weights have explicit parent-face
provenance and reconciliation, without influence pruning.

These structural passes do not finish the anatomy. The close view exposes
an angular, serrated crease. No animation, GLB, runtime or promotion follows
from the numerical result alone. The frozen static source SHA-256 is
`011c1931b45a7ba8d0c6b4212959205226684d17e7b52dbac556c42f4ccc7d2b`;
exact evidence and the close view are under
`../mannequin-mpfb-prototype/local-topology-repair/`.

Two independent source-indexed targets are now in progress on that frozen
mesh: one collision-constrained local fairing target (at most 8 mm), and the
separate complete-hand contact and posterior-seat targets. Their vertex
domains must be disjoint. No composition, shape acceptance or export is
claimed until the actual combined surface and contacts have been checked.

The complete-hand diagnosis also distinguishes bad articulation from soft
contact compression. Right-thumb source vertex 3584 is 22.5801 mm inside the
leg; signed distance, a nearly unit winding number, and an outward exit ray
agree. A 10 mm skin-only displacement cannot clear this witness. One directed
native thumb/finger articulation is therefore being evaluated with wrist,
arm and leg staging, bone lengths and authored weights fixed. The 10 mm cap
applies only to any subsequent residual pad compression. Natural joint
rotation must be measured and reviewed separately rather than disguised as
flattened hand geometry.

The initial enlarged fairing collar touches nine pre-existing hand/leg pairs.
The only local exception requires both triangles of each named pair to stay
bit-exact, with source vertices 11120 and 11121 additionally pinned. This is
not a final-body exception: the combined hand and groin target must be checked
again. Another 96 baseline CGAL pairs concern right axilla/torso and knee
creases, not facial internals; they remain disclosed and require actual
surface inspection before any whole-body acceptance.

## Composed seated cage and actual runtime hinge

The composed static cage (`b84300ccdea22f9908944175c6d5fc4aee051f5d786c47298acc55b86ee1c9ff`)
combines disjoint groin fairing, anatomically articulated fingers with bounded
residual pad compression, and a posterior seat fit. The whole combined surface
has zero groin and hand/leg crossings; the 96 unchanged axilla/knee pairs remain.
Five classified posterior glute vertices touch the floor, rather than using the
perineum as a support witness. Native Blender QA reports no errors. Root accepted
this cage only for a bounded motion prototype: the close groin view still has a
small triangular ridge. Evidence is under `../mannequin-mpfb-prototype/composed-bind/`.

The separate native control reference supplies a genuine 20-degree forward hip
hinge with fixed feet and wrists, natural arm reach and unchanged bone lengths.
Its five-second clip contains two seconds entering, one holding and two returning.
The sampled reference is `f97e2a7df19e9d3f3a1c7869a6bd4dd0339e7820efecd16e35374956fa428e29`.
It is a control-motion reference, not proof of the repaired runtime surface.

The standard GLB prototype coalesces deformation-equivalent trajectories, keeping
115 deformation groups plus the common root and four normalized skin influences.
Use native joint TRS with inverse binds sampled at the seated start. Decomposing
the relative delta matrices directly loses shear induced by scaled inverse binds
and previously produced a 2.46 mm surface error. The corrected export/readback
error is 0.123 micrometers. These transport checks do not certify anatomy.

Actual GLB samples still fail physical acceptance. At 20 degrees there are 67
groin pairs and 20 hand/leg pairs; skin penetrates the floor by 4.295 mm and the
classified glute support rises 6.148 mm. A fold begins at frame 7, only about
0.268 degrees into the hinge. Across one 0.787 mm edge, grouped influence vectors
differ by 0.876 in L1 norm. A valid static mesh therefore does not imply motion-safe
weights after rebasing and local topology replacement.

A transported fixed-plane corrective method was stopped with a reproducible
infeasibility witness: one held-pose pair needs 24.687 mm of relative separation
along that chosen plane, while two 8 mm displacement balls provide at most 16 mm.
This disproves that constraint method, not every possible corrective shape.
The next bounded repair is a local harmonic extension of runtime-only grouped
weights, preserving authored native weights, static positions, topology, boundary
weights and joint trajectories. Separate small pose targets address support and
hand contact. Neither the current GLB nor either pending repair is promoted.

## Separate interactive replacement candidate

The local harmonic runtime-weight repair plus a six-vertex residual groin target
now passes all 151 hip-contact and orientation samples. The residual source-space
maximum is 1.393 mm; the 10-degree groin target remains zero. Separate disjoint
support/hand targets preserve their exterior, fingers and planted feet/calf skin.
Both contributions are combined into the same two standard morph targets.

Actual exported GLB `d6c160b3bcaace820ba04b92c6e7ed8ade940a252f70f67f088ff77837609ac3`
has zero hip and hand/leg pairs across the 151 loaded animation samples, a worst
floor height of -0.200006 mm and classified glute gap at most 0.500 mm. No custom
skinning shader or delivery vertex cache is needed. This establishes a bounded
runtime surface pass, not a globally contact-free body: baseline axilla/knee
contacts remain.

The independent visual review initially interpreted the rear contour as a skirt,
then withdrew that finding after inspecting concrete neutral close views. Those
views show continuous seated glute/thigh contours and do not substantiate a skin
bridge or detached junction. A close angular groin crease and the uncertain leg
shading boundary remain disclosed. User approval of the new interactive candidate
is pending; the published older 90/90 assets are still rejected. The separate
candidate and reproducible joint-only inputs are in `../ninety-mpfb-review/`.

## Butterfly: distinguish compressed staging from a pelvic topology defect

The first MPFB butterfly cage (`43320780e38d25863d3f67b52a520e6b3fed04906f9ee2455496c6bc5e16b6a2`)
is not accepted. Three native views look more plausible than the rejected old
body, but complete-hand checks find 543 strict hand/leg pairs and penetration
up to 30.55 mm. A palm-centre clearance of 1.5 mm does not establish safe fingers.
Resolve this through wrist/finger articulation and actual skin contact before
considering any small residual pad compression.

The apparent 148-pair pelvic failure contains two different causes: 140 hip-fold
crossings and eight remote lower-thigh/shin crossings. The exact-CGAL count is
156, including the same eight remote pairs. A single local groin hull cannot
resolve both causes safely. The crossing domain has six components and seven
boundary loops; connecting those components would risk fusing separate leg
surfaces. The topology specialist therefore stopped before generating a hull.

The same native pose has 139.55-degree knee flexion and only 11.99-degree elbow
flexion: the feet are close to the pelvis while the arms are almost at maximum
reach. A single mechanics-guided restaging moves the ankles approximately 10 cm
forward and inclines the long, straight torso by 15 degrees. Reach preflight gives
125.08-degree knee flexion, 39.78-degree predicted elbow flexion and 487.30 mm wrist
reach within the unchanged 518.19 mm arm length. These are authored illustration
choices and preflight measurements, not validated final skin or clinical angles.

Classify opposing sole regions separately. In the first cage, minimum gaps are
2.94 mm at the heel, 0.80 mm at the ball and 14.20 mm at the toe tips. A median
distance over the entire arched sole neither proves nor disproves useful contact.
Foot yaw/spacing must be checked against heel and forefoot skin, without changing
the foot shape. New staging, topology, motion and exported contact acceptance are
still pending under `../butterfly-mpfb-review/`.

The restaged pose resolves the remote knee class, but positive hand-vertex
distances still miss 32 triangle-chord crossings. Refined thumb/web interiors
reach 1.0665 mm inside the opposing skin. One disjoint local material target,
with rigid contact cores and a geodesic feather, clears all hand/leg triangles
after actual Blender float32 readback. Maximum displacement is 1.5165 mm;
finger thickness remains at least 85.4% of the source measure. Whole triangles,
not only vertices or the palm centre, are the required contact evidence.

The bilateral local hull preserves its exterior boundary but initially adds
one handle. Boundary equality and manifold edges therefore do not prove the
correct body topology: the complete connected body must retain Euler
characteristic 2. The added handle is a 13.20 mm three-edge cycle enclosing
a tiny empty tunnel. One documented cut, duplicated banks and two generated
caps restore the required topology; a 0.20 mm outward bank displacement clears
the caps. Generated cap geometry is explicitly distinguished from original
birth-triangle geometry. Its attributes retain separate bank/corner provenance.
The structural adapter has 13,405 vertices and 26,806 faces. A conspicuous
jagged lateral glute/thigh crease remains visually rejected and is undergoing
one bounded local fairing; this is not a final shape acceptance.

Do not borrow the forward-hinge motion from 90/90 for this exercise. Holding
the wrists and legs fixed while adding that hinge produces a real forearm/shin
crossing: source vertex 3799 reaches 5.229 mm penetration at 2.344 degrees.
The opposing source vertices are dominated by DEF-shin weights, correcting
the initial generic "forearm/thigh" label. An elbow-only contact patch misses
the offending proximal forearm just outside its 50 mm selector. The source
cue is to let the knees fall out; the replacement motion keeps the long torso
stable and coordinates knee lowering, complete-arm clearance and ankle-skin
grip. That path still requires complete native and actual runtime validation.

## Final 4512 runtime integration

The accepted bounded butterfly candidate uses the faired 13,405-vertex seated cage and the native six-degree knee-opening path, with the trunk held fixed. One runtime harmonic extension over 547 local hip vertices removes the binding reversal; no hip morph is needed. Two compact hand targets affect 112 disjoint vertices, at most 0.125/0.963 mm. The integrated GLB SHA-256 is `b87a562c19b476849ce77f7603d5f8b38585965bd416c5fefd4716008bb27bc5`.

All 151 actual decoded samples pass exact hip, complete-arm/leg and complete-hand/leg checks, positive areas and floor/support checks. Final samples match the independently accepted hip and hand candidates exactly on their respective domains. Minimum hip material orientation ratio is 0.945631; minimum finger thickness ratio is 0.854105. Maximum glute gap is 0.701 mm, feet remain about0.200 mm above the plane. Global source contacts outside these domains remain disclosed.

Actual neutral and cyan-zone renderer views show continuous glutes without the rejected broad anterior wedge. A small upper gluteal notch and angular lateral crease remain disclosed for user review. Numeric parity does not override silhouette rejection. The native Blender action supplies joint references; the final standard-linear surface is rebuilt from explicit geometry, weights and targets. Older 4512 trials remain rejected. 6560 still requires a separate accepted replacement.
