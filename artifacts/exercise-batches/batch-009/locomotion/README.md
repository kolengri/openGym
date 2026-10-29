# Batch009 locomotion family

Three distinct five-second cycles share one original CC0 body/binding and standard three-action GLB:3220 two controlled squat jumps,3672 right/left forward lunge and return,6097 four alternating backward kicks with simultaneous overhead presses. Source resolutions and authored timing/range choices are kept separate in per-asset contexts and clip metadata.

The canonical source keeps exact Basis/rest/UV/topology/source IDs and51bones. `build.py` loads the original standing body using read-only batch003 rig helpers and installs only the exact accepted batch008 distal plantar binding. It does not import earlier deep-hip/foot pose variants. Parent-transported anatomical hinge frames, fixed grounded toe anchors, heel/ball skin support, deliberate flight, and relaxed connected hands govern the routes. No new binding fit, corrective target, motion cache or video is used. `causal-diagnosis.json` records rejected local routing causes and the settled bounded remedies.

`verify_native.py` checks every saved native/actual decoded frame, including full support, local foot shape, full arms/hands against legs, bilateral legs, distal arms/body, positive areas and exact loop closure. `verify_export.mjs` independently loads through the actual project Three.js/DQ adapter, checks all51 joints, sparse source surface patches and five complete source POSITION/NORMAL witnesses, and writes a temporary local decoded physical exchange that the native checker deletes after acceptance. Normal evidence uses native pose/bind quaternion blending independently from runtime skeleton matrices; it is shader-normal transport evidence, not Blender recomputed surface-normal equivalence. The151-frame mechanical receipts are distinct from root actual GPU motion acceptance.

Game QA:0errors for every sampled asset. The declared airborne3220 peak retains a correct not-resting-on-floor warning. No global self-collision or clinical claim. The packet is locally frozen after root GPU acceptance. Root owns viewer mapping, muscle fields, final camera-width integration, staging, Git and publication.

## Reproduce

Use Blender5.2.3 at `/opt/homebrew/bin/blender`, threads2, the installed project Three.js0.186.1 and the exact read-only hashes in `dependencies.json`. No new dependency installation is required. Run from the repository root:

```sh
/opt/homebrew/bin/blender -b -t 2 --python-exit-code 1 --python artifacts/exercise-batches/batch-009/locomotion/build.py
```

For each ID3220,3672,6097 run:

```sh
/opt/homebrew/bin/blender -b -t 2 --python-exit-code 1 --python artifacts/exercise-batches/batch-009/locomotion/verify_native.py -- --id ID --game-qa
node artifacts/exercise-batches/batch-009/locomotion/verify_export.mjs ID
```

Pass the exact `decoded_physical_exchange` path printed by the last command to:

```sh
/opt/homebrew/bin/blender -b -t 2 --python-exit-code 1 --python artifacts/exercise-batches/batch-009/locomotion/verify_native.py -- --id ID --decoded PATH
python3 artifacts/exercise-batches/batch-009/locomotion/write_delivery.py
```

The final packaging flag `--root-gpu-accepted` is used only after explicit root actual GPU acceptance. The explicit manifests include read-only project reproduction dependencies but exclude `node_modules`, installed skills, logs, candidates, caches and temporary exchanges from publication. Tool receipts record the existing local environment.

Source SHA256: `eafd8a3ba0e34e9fcc19cf080352de813d9fe87ad05b4bb93cffd0e6308e3862`

GLB SHA256: `3095df8b32f6b6d264007e6d94f767841ac08d291f3e6e060f50fa4b5ca3ede9`
