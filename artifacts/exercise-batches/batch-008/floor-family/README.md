# Batch 008 floor family

Original CC0 Blender Studio body: 10,582 source vertices, 21,160 triangles and 51 bones. Basis coordinates, rest skeleton, UVs, topology and source IDs are invariant. The existing causal waist/plantar binding helper is reused read-only; saved weights are read back by stable group names, normalized and limited to four influences. No shape keys, textures, new geometry, video or runtime frame/vertex caches are used.

3204 is a complete upright sit-up with arms straight overhead relative to the trunk. Pelvic skin is solved against the same z=0 plane as the independent plantar heel and forefoot patches. Continuous lumbar/thoracic rotation provides the curl and controlled return. The explicit support-plane proofs show the actual native skin at the start and top.

4935 and 3483 have compatible source cues and share identical source/GLB bytes containing two distinct actions. Both legs remain lifted approximately four centimetres through the wide overhead-to-hips-to-overhead sweep. Pelvic/lower-trunk skin stays supported and head/neck follow the upper trunk. The neutral hand offset is solved against actual deformed skin because wrist height also changes the source-derived palm frame. No original shoulder component is removed or replaced.

The numeric angles, timings and millimetre illustration tolerances are authoring choices, separately identified in each clip. Source muscle labels remain distinct. Soft muscle fields, camera-width fitting and actual GPU acceptance belong to root integration.

## Reproduction

Use `/opt/homebrew/bin/blender -b -t 2 --python-exit-code 1 -P <script> -- <id>` for `build.py`, `export_motion.py`, `verify_native.py` and `review.py`. Author 4935 once and copy its source/model/cameras/binding/early-proof files to 3483; both action identities are already embedded. Run `write_metadata.py` with the existing Python interpreter.

Run native verification after the final export freezes source bytes. `verify_native.py -- <id> --game-qa` writes 151-frame native physics, all-51-joint references, sparse surface patches, and five full-source DQ position and transported normal references. 3483 reuses the identical-source/action-equivalent sampled game-QA receipt. `verify_export.mjs <id>` evaluates the actual GLB with the shared Three DQ adapter and sends all 151 decoded surfaces through a temporary local verification exchange. Feed that path to `verify_native.py -- <id> --decoded <path>`; a successful readback removes the exchange. It is never a viewer input or a deliverable.

`review.py` renders multi-angle solid/wire sheets without saving source changes. The final curated manifests contain exact file/dependency hashes and explicitly include themselves. A self manifest uses canonical JSON with `self_integrity` omitted for its self digest; all other hashes cover exact on-disk bytes. `finalize.py` creates receipts and checks the accepted file list.

## Limits

Native proofs and decoded CPU transport are distinct from actual GPU/viewer acceptance. Original low-poly hip and overhead shoulder/armpit facets remain visible and were accepted by root in the native proofs. Whole-arm/hand-versus-leg checks are local nearest-normal diagnostics within 40 mm; they do not certify globally collision-free anatomy. Original out-of-tile UVs are preserved; the neutral material has no image texture. Game-profile QA has zero errors and warnings at the three diagnostic poses per physical motion.
