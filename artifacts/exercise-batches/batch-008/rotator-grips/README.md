# Rotator-grip stretches 1987 / 1986

One canonical CC0 body and binding contains independent five-second wrist-grasp and elbow-grasp actions. The original Basis, rest skeleton, UVs, source IDs, topology and 51 bones remain unchanged. Only bounded shoulder and distal plantar binding components change. Native DQ and standard GLB bone tracks are used; there are no shape keys or runtime vertex caches.

All scripts are in this directory. Run Blender scripts from the workspace root with `/opt/homebrew/bin/blender -b -t 2 --python-exit-code 1 --python <script>`; pass their arguments after `--`.

1. Authoring and native checks (Blender): `make_timing.py`, `build.py -- --final --no-proofs`, `verify_timing.py`, `reuse_1987.py`, `verify_native.py -- --id 1986`, `finish_qa.py -- --id 1986`, then `export_motion.py`.
2. Transport: run Node `verify_export.mjs 1987` and `verify_export.mjs 1986`, then ordinary Python `check_decoded.py 1987` and `check_decoded.py 1986`. These consume and delete temporary full-skin transport exchanges.
3. Evidence and inventory: run Blender `render_timing.py`, then ordinary Python `write_delivery.py`. Accepted held neutral/solid/wire images and QA are retained with explicit reuse receipts. Only newly timed transitions and release are rendered again.

The root-requested contact-valid timing baseline is preserved under `timing-baseline/` with its own explicit manifest. `verify_timing.py` measures whole-hand/forearm centroid speed and acceleration, all 51 native joint steps, unchanged 1987 keys and the held endpoint. The existing native matrix round-trip tolerance is 2e-6. `solve_native_contact.py` retains its frozen initial recipe for the bounded actual-native palm fit. Diagnostic helpers and causal receipts are separate from final mandatory QA.

Original shortest-arc and independent frame choices caused hidden transition roll and an elbow fold despite clean held proofs. Continuous upper/lower frame transport, a coherent original left elbow plane from neutral and one smooth return to the accepted basis resolve these defects. An authoring-only C1 scalar path-length clock redistributes the same joint-position route into the two-second entry with 150 ms rate ramps. The exported animation remains ordinary 151-frame bone keys. The hand clears the crown before its medial approach; the 15 mm clearance bulge and held goal remain explicit.

Source 20–30 second holds and the mirrored-side workout instruction remain distinct from the 2 s entry / 1 s hold / 2 s return one-side demonstration. Root owns actual GPU playback, muscle fields, final framing and publication. Runtime frames 46/47 are critical GPU neck/shoulder views; native clay shading alone does not establish whether that crease is visible in the final renderer. No production, clinical or global collision-free claim is made.
