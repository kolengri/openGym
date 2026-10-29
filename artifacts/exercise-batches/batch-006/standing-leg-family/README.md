# Shared standing-leg family — batch006

Two distinct text-authored five-second bilateral actions share one immutable-source body, linear rig and four compact local targets. Canonical final files are in `../assets/3479/`; identical bytes are also supplied in3480 for the per-asset contract. Integration should cache asset key `standing-leg-family` once and select the corresponding action.

The original Blender Studio CC0 source and helper `batch-003/authoring.py` are unchanged. Binding provenance reuses the accepted batch005 squat recipe, replacing only its rigid plantar Foot overlay with the original local Foot/Toe ratio so the rear toe articulation can stay planted. The saved-weight report records actual memberships by stable names.

The heel-touch contact is an authored same-side relaxed little-fingertip edge tap on medial/posterior heel skin. A middle-finger target caused the outer hand edge to cross the ankle; the outer edge target resolves the whole-hand geometry while keeping the wrist in the source neutral relation. Native DQ improved the elbow but caused a gross hip bulge, so it was rejected. Runtime remains linear. The lunge trajectory is separate, with upright torso, fixed planted portions and naturally curled sprint hands.

Root accepted the final joint8 visible candidate with residual shoulder/knee crease detail and froze the25mm target cap. Only one bounded native local-fairing construction was used for each mirrored shoulder or popliteal collar. Uncapped requirements and inverse-map conditions remain in `joint-target-report.json`. All target exterior vertices are pinned exactly; no feet/fingers/head or global body warp.

Blender5.2.3 ACTIONS exports inactive armature OBJECT slots automatically, but only discovers inactive KEY slots through NLA. `package.py` retains an explicitly muted inactive3480 KEY strip with `use_nla=False`; this standard export association adds both morph channels without changing native evaluation. Both actual decoded actions and shader normals pass.

Rebuild/check from workspace root, offline with two Blender threads:

```sh
/opt/homebrew/bin/blender -b --factory-startup --offline-mode -t 2 --python-exit-code 1 --python artifacts/exercise-batches/batch-006/standing-leg-family/build_draft.py
/opt/homebrew/bin/blender -b --factory-startup --offline-mode -t 2 --python-exit-code 1 --python artifacts/exercise-batches/batch-006/standing-leg-family/build_joint_targets.py
/opt/homebrew/bin/blender -b --factory-startup --offline-mode -t 2 --python-exit-code 1 --python artifacts/exercise-batches/batch-006/standing-leg-family/package.py
/opt/homebrew/bin/blender -b --factory-startup --offline-mode -t 2 --python-exit-code 1 --python artifacts/exercise-batches/batch-006/standing-leg-family/verify_invariants.py
/opt/homebrew/bin/blender -b --factory-startup --offline-mode -t 2 --python-exit-code 1 --python artifacts/exercise-batches/batch-006/standing-leg-family/verify_native.py
node artifacts/exercise-batches/batch-006/standing-leg-family/verify_export.mjs 3479
node artifacts/exercise-batches/batch-006/standing-leg-family/verify_export.mjs 3480
node artifacts/exercise-batches/batch-006/standing-leg-family/verify_runtime_stream.mjs 3479
node artifacts/exercise-batches/batch-006/standing-leg-family/verify_runtime_stream.mjs 3480
/opt/homebrew/bin/blender -b --factory-startup --offline-mode -t 2 --python-exit-code 1 --python artifacts/exercise-batches/batch-006/standing-leg-family/proof_final.py
python3 artifacts/exercise-batches/batch-006/standing-leg-family/curate.py
```

The runtime checker streams one ascending traversal of each actual decoded clip directly to Blender; no vertex/frame cache is stored. `LoopOnce` is never traversed again after its clamped endpoint. Five diagnostic full-source references per clip are verification data, not runtime playback data.

`curated-files.json` lists only final reports and reproducible source/check scripts. Generated intermediate/family copies of `.blend`/GLB, logs, trials, backups and environments remain local and are excluded. Root owns muscle fields, camera width fitting, viewer mapping, browser/GPU acceptance and final user approval.
