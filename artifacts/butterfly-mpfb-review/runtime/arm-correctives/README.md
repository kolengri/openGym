# Exercise 4512 runtime arm and hand correctives

The one bounded two-key candidate passes actual loaded standard GLB checks at all 151 times: complete arm/leg, complete hand/leg, nonhand arm/leg and the corrective domain against the whole surface each have **zero exact CGAL intersection pairs**. This handoff covers the arms; the primary owns the separate hip repair and final combined acceptance.

## Integration

- `arm-correctives.json` uses the existing two-target schema, with `sourceMotionSha256` bound to the frozen runtime motion and `weightOverrideSha256: null` for this baseline candidate. SHA256: `3fb3a2fb3295f8a6f9371f012de9c9d939938254e4a3c1214ad3de39b9631ddc`.
- Targets `KneesOutHalfArmContact` and `KneesOutFullArmContact` are sparse relative source-space POSITION deltas at knee progress 0.5 and 1. The schedule is `[min(2q, 2-2q), max(0, 2q-1)]`, with `q` read directly from the frozen native knee motion through `../progress.json`. Bind and return weights are exactly zero.
- `motion.glb` is the checked candidate with 45 deformation groups plus root and two ordinary POSITION/NORMAL morph targets. SHA256: `9913eff696e4ed0baadab6065b0c2139125b6df8b2ab4b37d6a5640cb0a3f4e0`.
- The primary may merge the two sparse arm deltas with its disjoint hip deltas and rebind the override hash. The final combined actual surface still needs its own complete all-151 proof.

## Geometry and solve

The actual baseline has no complete arm/leg pair at bind or half progress, and 36 hand/ankle pairs at hold. The all-151 baseline diagnosis found no nonhand arm/leg crossing. The deepest sampled hand penetration was 0.5193 mm, at the thumb pad and thumb/web.

One 12-variable solve jointly fits the two world translation keys for two contact cores, one per hand. Source palmar/dorsal thumb section endpoints move together. An 18 mm geodesic C1 feather connects each rigid core to an exact fixed exterior. Each vertex is transported back to source coordinates with its actual blended inverse skin map at the key. The solve uses all 151 moving-leg contact halfspaces and explicit 8 mm source displacement balls; it converged in two SLSQP iterations. No pose variants, new topology, weight changes or global skin flattening were used.

Only 112 original hand vertices move. Maximum target source displacement is **0.124772 mm** at half progress and **0.962560 mm** at full progress. The active vertices do not overlap the supplied hip domain. All vertices outside these 112 positions, including complete feet and inferior glute support, remain bit-exact to the actual baseline at every sampled time. Bind and loop surfaces are bit-exact to the baseline.

## Actual verification

`actual-verification.json` records the complete exact triangle-pair proof from the generic builder's exported/reloaded standard GLB samples, rather than only predicted coordinates or vertex distances. `geometry-QA.json` is the compact receipt; `report.json` is the curated handoff.

| All 151 actual GLB checks | Result |
| --- | --- |
| Complete arm/leg, complete hand/leg, nonhand arm/leg intersections | 0 each |
| Corrective domain against all triangles | 0 |
| Minimum retained finger material thickness ratio | 0.85410453, above 0.8 |
| Affected-face reversals or zero-area triangles | 0 |
| Whole-skin minimum floor Z | -4.65 nanometres, within numerical tolerance |
| Minimum complete-arm vertex signed clearance | +28.48 micrometres |
| Maximum actual versus analytical reconstruction error | 84.35 nanometres |
| Maximum GLB codec surface error | 46.00 nanometres |
| Outside-active, feet, glute, bind and loop positions | Exact to baseline |

Native joint references and all parent input files remain unchanged. No native work, renders, hip correction, shared code changes, Git or publication work was performed. `runtime-linear-samples.bin` is local QA evidence only; it must not be delivered as a vertex cache. `corrective-targets.npz` contains the two source fields and schedule, without a native frame-by-frame vertex sequence.

## Local reproduction

The existing read-only NumPy/SciPy/libigl environment is `artifacts/mannequin-mpfb-prototype/local-topology-repair/dependencies/venv/bin/python`. Run owned scripts with `-B`. `generate_correctives.py` refuses to overwrite the frozen target. The generic writer was invoked with input `artifacts/butterfly-mpfb-review/runtime`, exercise ID `4512`, root `Butterfly`, model `motion.glb`, output this folder, and `--correctives` pointing to `arm-correctives.json`. No weight override was used.
