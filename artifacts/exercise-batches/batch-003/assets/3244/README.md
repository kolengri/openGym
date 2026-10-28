# Abdominal stretch 3244

Original bilateral low prone press-up on the accepted Blender Studio CC0 human. The pelvis stays down throughout. One action, `Exercise_3244`, runs for 5 seconds at 30 fps: 0–2 enter, 2–3 hold, 3–5 return. The catalogue workout hold remains **20–30 seconds** in `clip.json`.

The low entry keeps the chest slightly clear while the body remains prone. This is a reversible illustration choice that prevents the accepted neutral chest/forearm cage from being forced through the floor. Extension is distributed over the trunk; the hold keeps naturally bent elbows and a relaxed near-forward gaze. Both palms face down, fingers point forward with mild spread, and individual finger segments place the distal pads near the same support plane. No pelvis lift, upward-dog transition, remeshing, reskinning, weight edit or pose morph was added.

`clip.json` preserves primary **abs** and additional **hip flexors, chest**. These are cyan stretch display roles for the shared viewer, not measured physiological recruitment. Inactive skin is neutral. Authoring uses repository text only, without restricted exercise images or video. Body provenance: [accepted source notes](../../../../human-animation-base/README.md). Text notices: [repository exercise-text notices](../../../../exercise-animation-briefs/THIRD_PARTY_NOTICES.md).

## Files and verification

- `source.blend`: editable source with inherited native corrective/subdivision enabled; 13,554,427 bytes, SHA-256 `7a9b32c54489fa4640292688cd03ce6a643fdd8731820e111f3fc8499e87a4b4`.
- `motion.glb`: original cage, linear skinning, one neutral material, no textures; 882,088 bytes, SHA-256 `77cfeb4a8b8f379656be51f9cf9050b20e61cffa7443d8a6266bf995b5b652b7`.
- Binding/rest/UV SHA-256 remains `227ede3fc31d1a2b47ff40f20a4a7288fe7bb36179add23bae953993826c8b7b`: 10,582 original vertices, 21,160 triangles, 51 named bones. `_SOURCE_INDEX` survives UV splits.
- `cameras.json`, `pose-samples.json`, `runtime-surface-reference.json` follow the shared asset interface. Camera coordinates and joints use Blender world meters; native frame 1 maps to runtime frame 0.
- `asset-qa.json`: unchanged-base topology, weights, UV and geometry checker passes with **no errors or warnings**.
- `pose-contact-qa.json`: native and independently parsed GLB support checks pass. Twenty frozen original skin patches cover bilateral ventral pelvis, thigh, shin, foot dorsum, palm heel and each distal finger pad. Eleven representative phases inspect each patch separately; the exported whole-skin floor sweep includes all 151 authored samples.
- Native/exported cage maximum position error: **0.000000587 m**. Exported skin loop error: **0.000000000 m**.
- Worst exported floor penetration: **2.405 mm**; native: **1.318 mm**. Maximum planted-patch tangential drift: **0.0073 mm**. Minimum hand-to-torso skin clearance: **98.47 mm**.

Contact checks declare a 12 mm near band, 4 mm penetration ceiling, at least 20% near patch vertices and 5 mm tangential drift ceiling at the 1.8 m illustration scale. The near fraction is a fraction of actual patch vertices. These are illustration approximations, not exact collision or clinical guarantees. Source joint pitch values are staging measurements, not validated safe anatomical limits.

Early heat-off start/peak/return proofs were viewed before full QA. Native and exported solid/wire proofs were then viewed; see `visual-review.json`. The GLB proof uses actual exported triangles, weighted positions and normals, preserving smooth normals across UV splits. No videos or animation-frame sequences were created; the PNGs are curated review stills.

## Reproduce

From the repository root, using Blender 5.2.3 LTS:

```sh
/opt/homebrew/bin/blender -b -t 2 --python artifacts/exercise-batches/batch-003/assets/3244/build_motion.py -- --early
/opt/homebrew/bin/blender -b -t 2 --python artifacts/exercise-batches/batch-003/assets/3244/build_motion.py
/opt/homebrew/bin/blender -b -t 2 --python artifacts/exercise-batches/batch-003/assets/3244/verify_asset.py
```

The immutable shared `authoring.py` loads only accepted CC0 rig/math helpers. `verify_asset.py` independently evaluates exported glTF accessors, animation channels, inverse-bind matrices and linear skin weights; it does not reuse native bone matrices for the exported skin.

No unresolved asset issue remains within this slice. Root owns the shared Three.js viewer, cyan fields, alpha, live-loop playback and interaction checks. This asset-level pass does not claim catalogue-wide production, coaching, anatomical or EMG certification.
