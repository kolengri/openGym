# Shared arms-forward squat: 3948

Frozen user-review candidate. Production approval has not been granted.

`clip.json` selects `asset: squat` and `Exercise_3948`. The shared GLB contains one body/rig and the two canonical action identities `Exercise_3948` and `Exercise_4714`. Their glTF samplers are identical. Both asset folders carry byte-identical source/GLB files; the viewer should cache only3948/motion.glb under the family key. Geometry and motion were authored once. Separate contexts retain the catalogue roles: quads primary; glutes, hamstrings and core secondary;4714 additionally lists calves.

The five-second cosine loop lowers the hips back/down to approximately parallel, then stands without a hold. Feet remain shoulder width, toes12degrees out. Arms reach forward30degrees below world horizontal with10degree elbow flexion, neutral palms and soft fingers. The sagittal camera is a true90degree side view; its companion is posterior oblique. Native frames1–151 map to runtime0–150 at30fps.

Original CC0 Blender Studio Basis,51 rest bones, UVs,10582 source IDs and21160 triangles are unchanged. Bounded source-dependent binding edits are fully listed in `local-weight-report.json`. Runtime uses linear skinning with at most four normalized weights and three25mm-capped POSITION/NORMAL correctives. Native DQ is used only to construct the compact hip target; runtime needs no DQ adapter. Feet, fingers, head and the target exterior are protected. `joint-corrective-report.json` records the inverse-map condition, exact changed IDs, applied cap and uncapped required depths. Native smoothing/Multires are disabled in the delivered source.

All151 actual exported frames were streamed directly from the project Three.js GLTFLoader/AnimationMixer surface into Blender BVHTree checks, without a stored frame cache. Floor/sole support, complete arms/hands versus legs, source parity and area checks pass. Maximum native/export position difference is1.432µm; minimum whole-body floor clearance is0.1997mm; minimum arm/hand-to-leg surface gap is151.637mm. Mandatory game QA at standing/entry/parallel passes with zero errors. Entry and parallel each retain one warning for two opposing facet pairs in the disclosed joint folds; deleting those body facets would violate the original topology/source-ID requirement. Standing has no warnings. Native alpha stills are RGBA with transparent corners.

Minor hip/knee/axillary folds remain disclosed. Exact facet crossings, opposed normals, areas and original-ID/weight witnesses are retained in `runtime-physics-report.json`. The earlier strict native zero-self-fold diagnostic intentionally remains false in `surface-contact-report.json`; do not interpret that diagnostic as a failed floor/support gate or claim complete self-collision clearance. Root accepted the actual side/rear/oblique candidate shape for user review and froze it.

Source SHA256: `026db4baa0185082af3deda03edbec24cac1e04c9b61eceefe96adff9741ae06`. GLB SHA256: `2a109b9f6ea9a99ac5de7f83f7e18610ad2b036e54a16942221bcf3c4c2acb6f`. Receipt reuse between identities follows byte-identical source, geometry, motion and targets.

Reproduction uses the unchanged `batch-003/authoring.py` helper and accepted original source. Run Blender5.2.3 offline with two threads:

```sh
/opt/homebrew/bin/blender -t 2 -b --factory-startup --offline-mode --python-exit-code 1 --python artifacts/exercise-batches/batch-005/assets/3948/build_motion.py -- --no-proofs
/opt/homebrew/bin/blender -t 2 -b --factory-startup --offline-mode --python-exit-code 1 --python artifacts/exercise-batches/batch-005/assets/3948/package_shared.py
node artifacts/exercise-batches/batch-005/assets/3948/verify_export.mjs
node artifacts/exercise-batches/batch-005/assets/3948/verify_runtime_stream.mjs
```

`verify_asset.py` writes the source-domain reference files, raw mandatory QA and strict native fold diagnostics; its final assertion deliberately preserves the earlier zero-self-fold diagnostic. The frozen agreed acceptance result is `runtime-physics-report.json`. Regeneration changes file hashes and requires fresh references.

Only `curated-files.json` belongs to the frozen packet. Earlier experiments, logs, backups and diagnosis stills are uncurated working evidence. No paid generation, restricted exercise media, videos, global preference writes, commits or shared-code changes were used. Root owns heat fields, viewer integration and final user acceptance.
