#6539 exact resting-motion reuse

`clone_native.py` renames the accepted4365 action and proves all151 native skins,51 matrices and morph weights remain exact. `clone_metadata.py` changes only the same-length GLB JSON action name while preserving the entire binary tail, then transfers native references with explicit lineage. `verify_identity.mjs` independently loads both models and compares all151 actual decoded DQ surfaces. Current standalone runtime and export checks use the unchanged shared DQ adapter; no runtime frame cache is saved.

Old batches are read-only. All source geometry, original weights, keyed joint paths, target buffers and timing are exact. Source hold20–30s and lats-primary labels are separate from4365. See `reuse-lineage.json`, `native-identity.json`, `decoded-identity.json` and the asset delivery report.
