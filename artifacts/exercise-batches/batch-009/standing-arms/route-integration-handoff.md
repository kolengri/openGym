# Frozen coherent 3995 acquisition route

The primary provisionally accepted the native early-midpoint cuff/arm/wrist
appearance in `coherent_hand_mid-{front,side,rear}.png`. Production integration,
actual GLB/GPU inspection, complete affected-frame geometry classification and
other-action preservation belong to the standing-arms writer and primary.
The sparse raw torso crossing counts have **not** been physically accepted.

## Copy these frozen inputs

| File | SHA-256 |
| --- | --- |
| `coherent_route.py` | `e7c6f436b867a668f46efd48ad9f08e64715fa96fcc6970b13776e8f1b1415b4` |
| `coherent-route-coefficients.npz` | `c0417c262db584c2e0f54844c7e7f683ffdfd02db2407f5330cf94ef8537202b` |
| `coherent-hand-matrices.npz` | `23e5e3874c6aec05b8d63cea026330a76f00f026445195ead15009d25770f711` |

Source is frozen `88c2da9b30955e3793637fe5f8a086e0ca7339d395cf20997d6b3fdcac817c1e`.
The existing held POSITION archive remains
`a50d65d6c27e7b18a9aeb962919f9ff196b4dae19ce295d3c6a4d7b26415d4f9`.
There is no fourth target, binding change, topology change or corrective solve.

The helper is side-effect-free on import. Constructing it reads only the supplied
hash-checked archive. Runtime dependencies are the standard library, NumPy and
Blender mathutils. SciPy was used only to construct frozen spline coefficients;
the standalone evaluator uses Horner evaluation and requires no SciPy.

```python
from coherent_route import CoherentRoute

route = CoherentRoute(path_to_copied_coefficients)
desired, held_key_p = route.pose(runtime_frame)
```

Call only for exercise 3995. Keep all three accepted actions on their original
implementation and exact existing channels. `desired` contains all 51 named
armature-space matrices. It does not apply them, edit an action, modify a mesh,
create any object or install a shape key. Fractional runtime frames are supported.

## Pose and channel conventions

- Runtime frames are zero-based, 30 fps, 75 frames per repeat, two same Right-over
  repeats. `original_p = sin(pi * (frame % 75) / 75) ** 2`.
- The actual frozen source peak is `p_peak = 0.9995614150494292`, the equal
  frame-37/frame-38 samples. Route progress is `min(1, original_p / p_peak)`.
- Returned `held_key_p` is **original_p**, not normalized route progress. Preserve
  the existing p-held key driver and explicit neutral/other-action reset policy.
- Quaternions in the archive are **WXYZ**, as used by mathutils. Matrices are
  row-major arrays of 4x4 matrices acting on column vectors, in original Blender
  Z-up rig coordinates. Bone names/order are in `bone_names`.
- `coherent-hand-matrices.npz['matrices']` has shape `(151, 51, 4, 4)` in that order.
- Feet, head and trunk use the frozen source state. All 51 open and actual held
  endpoint matrices are explicitly retained. The endpoint branch also guarantees
  deterministic loop/repeat endpoints.
- Fingers preserve the source relaxed local transforms and inherit the final
  Hand frame. No spread, grip or fist change is introduced.

The archive additionally contains exact original native endpoint local channels:
`endpoint_native_matrix_basis`, `endpoint_native_location`,
`endpoint_native_rotation_wxyz`, `endpoint_native_scale`, and
`endpoint_native_global_matrices`. Axis 0 is open/native frame 1; axis 1 is actual
held/native frame 38.5. The desired endpoint globals were reconstructed from
captured skin matrices and rest matrices, and differ from direct native globals
by at most `2.5331974029541016e-7` in matrix elements. Use the native local channels
when exact saved endpoint preservation would otherwise be lost to another
global/local decomposition. Report any unavoidable native/export floating-point
difference explicitly; do not silently change the accepted endpoint.

## Construction and measurements

The wrist uses the original five outside-route control positions, including
the opposite-side overshoot before the held palm turns onto the back. A
shape-preserving C1 cubic spline is parameterized by chord length and traversed
by arc length across the entire normalized acquisition progress. This removes
the former compressed p=.35..70 crossing.

The elbow-plane direction is incrementally parallel-transported along the
shoulder-to-wrist axis, with a smooth axial correction to the exact held bend
direction. Arm and ForeArm frames use the same continuous transport principle
and exact endpoint axial calibration. The hand is composed from the continuous
ForeArm frame and smooth5 interpolation of the endpoint **forearm-local** Hand
quaternions. This removes the former late independent hand-frame compensation.
The fixed 401-node transport table is deterministic transport quadrature, not
a selection among candidate poses.

`frozen-route-parity.json` verifies that the standalone evaluator reproduces the
accepted construction at all 151 integer frames and nine fractional samples
with **maximum matrix difference exactly zero**. This is independent polynomial
evaluation from frozen coefficients, not lookup of the witness matrices.

| Maximum step | Original route | Coherent route |
| --- | ---: | ---: |
| Left Arm global | 131.720 degrees | 9.923 degrees |
| Right Arm global | 68.756 degrees | 10.387 degrees |
| Left ForeArm global | 151.119 degrees | 19.001 degrees |
| Right ForeArm global | 86.625 degrees | 18.507 degrees |
| Left Hand local | 143.142 degrees | 4.753 degrees |
| Right Hand local | 85.814 degrees | 3.809 degrees |
| Largest elbow displacement | 256.478 mm | 57.214 mm |
| Largest wrist displacement | 179.357 mm | 62.756 mm |

The coherent Hand global maxima are 17.191/16.581 degrees Left/Right. All measured
Arm/ForeArm global and local maxima are below 19.482 degrees per frame. These are
measurements, not a universal acceptance threshold or clinical claim.

Sparse native geometry samples cover open, runtime frame 18, normalized p=.85,
p=.95 and actual held. Arm/arm crossings are zero in these samples. Raw
torso-domain crossings remain explicit in `coherent-hand-report.json`; primary
classification and full-cycle review are still required. No full 151-frame mesh
QA, export, browser inspection or final review was performed by this specialist.

All new diagnostic, helper and witness files are contained in this directory.
No production files, canonical bindings, source assets, Git commits or remote
state were changed.
