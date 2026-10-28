# Five equipment-free exercise animations

Current application delivery is live **GLB + Three.js**. New video generation is disabled. These video files describe historical batch001; the current style trial is the [live chaturanga heat-zone example](../chaturanga-heatmap/README.md), awaiting user confirmation.

Editable motion and runtime assets for catalogue IDs 5965, 5915, 5887, 0001 and 9066, the first equipment-free entries in alphabetical order after excluding undeclared supports such as boxes or cones. Floor/ground is the only support.

The accepted Blender Studio CC0 continuous human has 51 bones, including 30 articulated finger bones. All five actions are authored from catalogue text and explicitly recorded staging choices. They contain no earlier captured squat motion. No GymVisual media was used.

## Open findings and generation input

These are review prototypes. [Review batch 001](../exercise-batches/batch-001/README.md) contains a repaired **0001 candidate for user review**. The hip path, planted-foot IK, torso curl, head rest, wrist spacing and finger bend were solved together. The original floor/arm report is retained in `situp-contact-investigation.json` and the batch baseline. Known issues remain open until the corrected candidate is reviewed; a numerical pass is not production approval.

`situp-repair/landmarks.json` freezes authored original-vertex pelvic, heel, sole, lumbar, hand, fingertip and head patches, phase samples and tolerances. These are illustrative skin landmarks rather than clinical ischial landmarks. `situp-repair/contact-report.json` measures native corrective/subdivided skin and the pure linear cage separately. `situp-repair/runtime-contact-report.json` checks the actual loaded GLB surface, exported head triangles and UV seam copies. The earlier global minimum-Z and bone-loop checks did not cover these contacts.

Read `../exercise-animation-briefs/production-guide.md` and prepare the exercise's evidence/constraints packet before authoring:

```sh
python3 artifacts/exercise-animation-briefs/prepare_generation.py --exercise 0001
```

`build_motion.py` now refuses to regenerate known blocking defects by default. An explicit remediation-only draft may append `-- --allow-known-issues`; the flag does not resolve or approve an issue. The first review batch replaces only the 0001 video. The other four media files and sampled poses are unchanged from the recorded baseline; its immutable archive preserves the version under review. The review player now opens recommended views and supports linked one-finger orbit, two-finger pinch zoom and camera reset without pausing animation. `touch-verification.json` records Chromium mobile touch emulation; physical-device and actual app integration remain unverified.

## Deliverables

- `bodyweight-five.glb`: the application asset, one continuous skin, 21,160 triangles, 51 bones, five actions and one material. The neutral skin is uniform gray.
- `runtime-muscles.json`: 96 sparse illustrative region weights and all 57 catalogue muscle-name mappings. `_SOURCE_INDEX` connects original vertices across glTF UV splits.
- `web-textures/`: neutral and five activation states at 2048×1024. Only selected muscles contain drawn detail. Native Blender textures remain 4096×2048.
- `camera-presets.json`: two complementary views per movement. They expose different muscle groups instead of duplicating mirrored left/right views.
- `threejs-viewer.html`: locally generated self-contained interactive viewer. One model/mixer drives both recommended views. Finger/mouse orbit and pinch zoom affect both complementary cameras; reset restores their presets. A single view can also be selected. The canvas has real alpha transparency; its background is CSS only.
- `bodyweight-five-highlight.blend`: editable five-action source with the packed neutral atlas. The reusable atlas retains all 96 masks separately.
- `ID.webm`: transparent VP9-alpha master, 1536×768, two synchronized 768px views, 30 fps.
- `ID.mp4`: white-background H.264 fallback with the same views/timing. MP4 does not preserve transparency.
- `ID-preview.webm`: smaller transparent 15 fps review copy. Use masters or the GLB to judge fine detail.
- `viewer.html`: offline video review page with selectable backgrounds.
- `five-bodyweight-animations.zip`: all five WebM masters and five MP4 fallbacks with their staging/camera manifest.
- `threejs-asset.zip`: GLB, web textures, region lookup and camera/clip manifests for application integration.

All clips are silent. Yoga previews are four seconds; hops are 6.4 seconds. These are short preview loops rather than catalogue hold durations.

## Motion, muscle roles and views

- **5965**: two lateral shuffle steps toward screen-left (the mannequin's anatomical right), then return. Front view shows quadriceps/core; rear-oblique view shows calves/glutes. The source leaves the exact one-two pattern unspecified; this is an explicit pilot interpretation.
- **5915**: three-leg chaturanga, left leg raised. Both palms/fingers lie on the floor, wrists are below the elbows at the bottom and elbows track backward. Oblique front/rear views expose both hands plus chest, triceps, shoulders, core and raised-side glute.
- **5887**: downward dog with left-leg lift, pelvis held level. Front/rear oblique views show shoulders, triceps, core, raised-side glute and the planted right leg's posterior stretch.
- **0001**: three-quarter sit-up, feet planted, knees bent and hands lightly behind the head with elbows open. Side view explains the movement; elevated front view exposes the abdominal selection.
- **9066**: eight short hops on the left leg, out/back along four directions. Grounded knee bend, toe push-off, flight and cushioned landing replace the earlier rigid bobbing. Front and rear-oblique views expose travel plus the loaded calf, quadriceps and glute. The free right leg stays neutral.

Red indicates selected primary load, amber additional involvement and cyan stretch. All unselected skin remains uniformly neutral, without painted muscle seams/fibers. The atlas is illustrative art direction, not true segmentation, EMG or a contraction simulation. Colors identify selected exercise regions rather than measured instantaneous recruitment. Deep/proxy/systemic/unsupported limitations are described in the atlas README. Exact roles and working-side overrides are recorded in `clips.json` and `render-report.json`.

For 5965 the catalogue target is cardiovascular system, which has no local surface patch; quadriceps/calves are a separate visible-load choice. For 5887 the hamstring target is shown as stretch. Body cast shadows, cavity/AO and specular highlights are disabled so overlapping limbs cannot darken the selected regions. `../mannequin-muscle-atlas/lighting.py` changes only background-process settings, never user preferences.

## Reproduction and evidence

The source binding is `../human-animation-base/professional-motion.blend`; rebuild instructions and CC0 provenance are in that folder. `build_motion.py` removes its old actions/source rig, adds the finger articulation and authors all five actions. It preserves the source body coordinates/topology.

```sh
blender -b -t 4 --python-exit-code 1 -P artifacts/bodyweight-five/build_motion.py
python3 artifacts/bodyweight-five/shot_plan.py
blender -b -t 4 --python-exit-code 1 -P artifacts/bodyweight-five/verify_poses.py
blender -b -t 4 --python-exit-code 1 -P artifacts/bodyweight-five/render_five.py
python3 artifacts/bodyweight-five/encode_five.py
swift artifacts/bodyweight-five/review_videos.swift artifacts/bodyweight-five
python3 artifacts/bodyweight-five/verify_transparency.py
cp artifacts/bodyweight-five/bodyweight-five-highlight.blend artifacts/bodyweight-five/runtime-source.blend
blender -b -t 4 --python-exit-code 1 -P artifacts/bodyweight-five/export_runtime.py
node artifacts/bodyweight-five/build_runtime_viewer.mjs
node artifacts/bodyweight-five/verify_runtime.mjs
python3 artifacts/bodyweight-five/build_review_page.py
node artifacts/bodyweight-five/check_review_page.mjs
```

Encoding uses installed FFmpeg/libvpx. `pose-verification.json` checks sampled evaluated floor contacts, exact joint loop closure, chaturanga forearms and the hop's loaded knee/flight. `video-review.json` decodes every MP4 frame and checks metadata/loop continuity. `transparency-verification.json` decodes every WebM frame through libvpx and checks real transparent background/opaque body pixels. `runtime-verification.json` compares loaded Three.js bone poses to Blender, including actual transparent-canvas and shadow checks. `verify_situp_runtime.mjs` additionally compares original-index support patches to the linear-cage reference and checks signed hand/head clearance on the actual exported triangles. These receipts do not certify biomechanics or exercise coaching.

The GLB uses the original cage/linear skinning; Blender renders additionally use corrective smoothing and one sculpt subdivision, so native renders have finer geometry. The self-contained viewer is locally ignored to avoid committing a duplicate of the assets. The application can load the GLB and companion resources directly instead of embedding base64 data.

The repaired pose's native QA has 84,680 triangles, one connected skin and zero
errors. Fourteen hidden back-to-back triangle pairs are accepted: seven source
mouth pairs, two source toe-fold pairs and five right axillary/medial upper-arm
fold pairs introduced by the raised-arm pose. They are folded skin, not duplicate
clothing or overlapping hands; `situp-repair/warning-correspondence.json` records
their source correspondence and locations. The checked linear cage has 21,160
triangles and no such pairs. The raw Workbench material warning is resolved when
the delivery stage assigns the neutral/activation atlas material.
