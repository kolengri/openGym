# Standing arm motions

Four catalogue-text-authored five-second actions share one editable canonical Blender Studio CC0 body and one standard GLB. The runtime uses the existing Three.js dual-quaternion adapter. Geometry, vertex order/source IDs, Basis, UVs, rest skeleton, the accepted standing binding, and its two existing shoulder components remain exact.

- `Exercise_1404`: standing front clasp, forward reach and gentle upper-back rounding. Source hold: 20–30 seconds.
- `Exercise_4515`: conventional clasp behind the body, gentle hand lift and chest opening. Source hold: 20–30 seconds.
- `Exercise_1405`: right-over crossed forearms, hooked interlocking fingers with palms away, then a comfortable lift. Source hold: 15–30 seconds; the catalogue's other-side instruction remains separate.
- `Exercise_3995`: two identical right-over open/wrap/reopen repetitions. This follows the root-authorized staging amendment; the catalogue source instructions remain verbatim in each asset's `clip.json`.

The three stretches use 2 seconds to enter, 1 second to hold and 2 seconds to return. All actions have 151 native keys at 30 fps, native frames 1–151 and runtime frames 0–150. Both soles remain supported at an authored 1 mm skin margin. The camera records use native Blender Z-up coordinates; the runtime performs its own conversion.

## Motion and contact decisions

Hands approach reachable arm placements before clasp acquisition, and release before unwinding. The crossed clasp uses one coherent bilateral hand arrangement and a small coupled longitudinal separation, without independently moving finger tips. Its lift routes the upper forearm behind the opposite hand while preserving the accepted held clasp.

The wrap traverses the original outside wrist controls by arc length across the full protraction phase. Incremental transport with endpoint calibration keeps the elbow bend and both arm frames continuous. Hand orientation interpolates the accepted open and held rotations in each forearm's local frame; the relaxed fingers follow their hand. The top palm frame and placement were solved against a coherent posterolateral shoulder-patch tangent.

A C1 anterior detour of the left wrist clears the opposite arm during acquisition. Its 193.194 mm peak offset comes from a conservative whole-hand separating-plane constraint with a 4 mm skin margin and a 1 mm numerical margin. The fixed-length elbow and transported arm frames are recomputed with the moved wrist; hand orientation keeps the same forearm-local interpolation. The detour vanishes at both endpoints and repeats/reverses through the same phase scalar. Exact native endpoint channels preserve the accepted held palm touches and open pose.

The wrap has one bounded held-cuff pose target, weighted by the shared protraction fraction `p`. Its POSITION and geometric NORMAL support are declared by source ID, with a 175 mm displacement bound. All three component weights explicitly reset to zero in the other actions. `accepted-native-identity.json` and `accepted-decoded-identity.json` compare all 151 POSITION/NORMAL states and all 51 bone matrices against the accepted 25b5/f879 lineages.

## Evidence and current state

The accepted early conventional-clasp GLB is frozen at `checkpoints/25b5af549368/motion.glb`; the accepted crossed-clasp route is frozen at `checkpoints/f87959934283/motion.glb`. The wrap's held contact input is frozen at `held-wrap-tangent-88c2da9b3095/source.blend`.

The final detour GLB `5c960475287e6aa14852cf3acfcc2d88a8ea15a1db47b0c406a21c81459d584d` passed the root's actual GPU 20-pose review, including the acquisition frames 21, 22, 23 and 53. `continuity-wrist-detour.json` records actual saved global and parent-local rotation steps; `wrist-detour-witness.json` retains the preceding 51-state exact-skin witness. `route-native-parity.json` distinguishes rigid channel-conversion precision from unchanged native endpoints. The three accepted actions retain exact all-151 native and actual-decoded POSITION/NORMAL/51-bone identity.

Final shared-model hashes, complete native/actual-decoded physical results, the root-reviewed cuff targets and the explicit curated release manifest are recorded in `delivery-report.json` when the integrated packet is frozen. Root owns GPU acceptance, heat fields, final camera width fitting, integration and Git. Do not rebuild over root-integrated metadata after handoff.

Raw exact-skin crossing reports retain inherited lower-axilla attachment diagnostics. Those reports are not global collision-free claims. Genuine hand, finger, forearm, opposite-arm or unrelated body crossings remain hard issues. Mandatory game-profile QA reports its actual errors and warnings separately.

## Reproduction

Use the existing `/opt/homebrew/bin/blender`, Blender 5.2.3, and read-only dependencies pinned in `dependencies.json`. `build.py` verifies dependency hashes before baking; `export_motion.py` exports the standard GLB and writes explicit 151-key morph tracks for every action. No native smoothing modifier, runtime vertex cache, paid generation or restricted-media derivative is used.

```sh
/opt/homebrew/bin/blender -b -t 2 --python-exit-code 1 --python artifacts/exercise-batches/batch-009/standing-arms/build.py
/opt/homebrew/bin/blender -b -t 2 --python-exit-code 1 --python artifacts/exercise-batches/batch-009/standing-arms/verify_invariants.py
/opt/homebrew/bin/blender -b -t 2 --python-exit-code 1 --python artifacts/exercise-batches/batch-009/standing-arms/export_motion.py
```

After native and GPU acceptance of the corrected wrap route, run the affected `verify_native.py -- --id 3995 --game-qa` and `node verify_export.mjs 3995` checks. Feed the temporary path written in that asset's `verification-exchange-path.txt` to `verify_native.py -- --id 3995 --decoded <path>`. The checker consumes and removes the exchange; it is never a viewer input. Run `verify_conventional_identity.py` and `verify_accepted_identity.mjs` after final export. Once both establish exact identity for the other three actions, `reuse_accepted_verification.py` transfers their frozen physical receipts with explicit source/model provenance; `verify_export.mjs ID --reuse-physical` still checks their current export, reset and reference parity. Inspect the raw failure arrays even when a command exits for the disclosed attachment diagnostics.

Geometry provenance: official Blender Studio Human Base Meshes v1.4.1, CC0, original `GEO-body_male_realistic`, 10,582 vertices/10,590 faces, normalized to 1.8 m. The official archive is `https://mirror.blender.org/demo/asset-bundles/human-base-meshes/human-base-meshes-bundle-v1.4.1.zip`; the original extracted blend hash is `3c121505651140ceb4d69fd1d8923f7788ffadd81672f5be14845a5f2c75c137`. The accepted standing source and canonical body hashes are pinned in `dependencies.json`. These four actions are newly authored from catalogue text; no captured squat motion or GymVisual media is used.
