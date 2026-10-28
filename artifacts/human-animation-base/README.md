# Human squat animation

This replaces the rejected hand-built SVG mannequin with the realistic male
surface from Blender Studio Human Base Meshes v1.4.1 and a real CMU motion-capture
repetition. The continuous human mesh retains the source's face, fingers, muscle
sculpt and quad topology. It has no clothing or explicit genital anatomy.

## Deliverables

- `human-squat.svg`: standalone animated vector paths, 68 frames, 30 fps,
  640 × 640, 2.267-second loop; no embedded raster images or JavaScript.
- `human-squat.mp4`: H.264 export rendered from the actual standalone SVG.
- `human-highlight.blend`: editable human, rig, captured action and muscle colors.
- `svg-review.json`, `asset-qa.json`, `render-report.json`, `video-review.json`:
  technical verification receipts.

The camera is orthographic and perpendicular to the sagittal movement plane.
Arms have a lighter neutral color to separate them from the torso. Red marks
illustrative quadriceps/gluteal regions; amber marks illustrative trunk/calf
regions. Colors follow the deforming surface. They are artistic activation cues,
not measured EMG, a muscle simulation or a claim that every visible patch is an
anatomically segmented muscle. The existing sculpt supplies anatomical detail.

This is a visual prototype, not a replacement for the exercise catalog yet.
The SVG stores complete traced frames and is 11.4 MB. For a large
catalog, using the underlying rig in Three.js avoids duplicating complete vector
geometry per frame and allows equipment, camera and muscle-mask reuse.

## Sources and motion adaptation

Geometry: official Blender Studio Human Base Meshes v1.4.1, CC0.
Object `GEO-body_male_realistic`, 10,582 base vertices / 10,590 faces, normalized
to 1.8 m. Download the official archive from
<https://mirror.blender.org/demo/asset-bundles/human-base-meshes/human-base-meshes-bundle-v1.4.1.zip>.
The extracted `human_base_meshes_bundle.blend` SHA-256 is
`3c121505651140ceb4d69fd1d8923f7788ffadd81672f5be14845a5f2c75c137`.
The official listing is <https://www.blender.org/download/demo-files/>.

Motion: Carnegie Mellon Graphics Lab Motion Capture Database, subject 13,
capture 30, approximately 12.000–14.250 s at 120 fps, via the cgspeed BVH
conversion mirrored at fixed commit `09a07f54f3bbb58797325f009282d0b2048a2871`:
<https://raw.githubusercontent.com/una-dinosauria/cmu-mocap/09a07f54f3bbb58797325f009282d0b2048a2871/data/013/13_30.bvh>.
Source: <https://mocap.cs.cmu.edu/>; unit explanation:
<https://mocap.cs.cmu.edu/faqs.php>.

CMU permits use in commercial products but prohibits reselling the raw or
converted motion data directly. It is not CC0. The source data was obtained from
mocap.cs.cmu.edu; the database was created with funding from NSF EIA-0196217.
The full input BVH is intentionally excluded from tracked deliverables.

The capture is retargeted to a fitted 21-bone skeleton with native Blender heat
weights, at most four influences per vertex, linear skinning and corrective
smoothing. Upper-back weights respect authored torso region boundaries.
Captured angular excursion is reduced to 82% for this body; horizontal drift is
removed, foot-floor contact is corrected, and the last 10% blends to the start.
The timing and joint directions come from capture, not procedural sine poses.

No Gym Visual media, FaceForge/BP3D muscle data or paid generation was used in
this version. No fal.ai generation was submitted.

## Reproduce

Requires Blender 5.2.3, Python with `vtracer==0.6.15`, the existing local
`../first-exercise-3d/runtime/node_modules/playwright-core`, Chromium and macOS
Swift/AVFoundation. `retarget_motion.py` uses the installed
`blender-character-rigging/scripts/bind_mesh.py` skill helper.

Place the extracted source blend beside the scripts and download `13_30.bvh`
from the fixed URL above. Then run, in order:

```sh
blender -b -t 4 -P artifacts/human-animation-base/prepare_base.py
blender -b -t 4 -P artifacts/human-animation-base/retarget_motion.py
blender -b -t 4 -P artifacts/human-animation-base/render_human.py
python artifacts/human-animation-base/vectorize_motion.py
node artifacts/human-animation-base/review_svg.mjs
EXERCISE_RENDERER='SVG / Chromium' swift artifacts/first-exercise-3d/encode.swift artifacts/human-animation-base/svg-frames artifacts/human-animation-base/human-squat.mp4 30 800000
swift artifacts/human-animation-base/review_video.swift artifacts/human-animation-base
```

Asset QA passes with no errors: 84,680 evaluated triangles, one connected island,
zero nonmanifold/boundary edges, degenerates, duplicate vertices or invalid
weights. Accepted warnings: Workbench uses vertex colors without a material
slot; nine hidden back-to-back triangle pairs occur in the posed source surface.
The original UVs extend outside 0–1; this vertex-color render does not sample
textures. These warnings do not establish a production export pass.

Independent visual review found the previous shoulder protrusion and shorts-like
highlight block resolved. Remaining prototype limits: vectorization facets small
anatomical details, and the far forearm is occluded in the upright profile, so its
visible hand can look isolated. All 68 SVG states show exactly one frame. All 68
MP4 frames decode; the normalized RGB change at the loop boundary is 0.00493,
below the largest ordinary adjacent-frame change of 0.01040. This continuity
measurement is not a biomechanical exercise-technique assessment.
