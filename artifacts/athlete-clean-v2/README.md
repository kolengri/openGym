# Repaired athlete and Three.js motion previews

This is a review asset, not a replacement for the application's exercise media.
The character was generated from our own reference image with Meshy 7.1 through
fal.ai, then repaired locally in Blender 5.2.3 LTS. No Gym Visual images or frames
were used as generative inputs. The source request and original reference are in
`../athlete-fal-v1/`.

## Deliverables

- `athlete-clean.blend`: editable repaired rest model with packed textures.
- `athlete-motion.glb`: repaired character, 24-bone skeleton and three clips.
- `motion-viewer.html`: generated offline viewer with orbit controls, clip
  selection, timeline, muscle regions and garment opacity. Rebuild it with the
  command below; the large generated HTML is intentionally not tracked.
- `muscle-movements.mp4`: Three.js render, 640 × 640, 30 fps, 11.6 seconds.
- `muscle-movements-preview.mp4`: smaller inline preview of the same frames.
- `shorts-quad-cage.png`: actual garment control cage from three angles.

The video contains lateral steps (0–5.2 s), a squat (5.2–8.4 s), and overhead arm
raises (8.4–11.6 s). The latter two are deformation demonstrations, not approved
exercise instructions.

## Changes and validation

Removed 31,151 faces from the fused generated garment region. Constructed separate
pelvis and shorts surfaces, each with 1,999 control vertices and 1,920 quads.
The pelvis has no genital anatomy. The garment has an even waistband and its own
material, thickness and skin weights. Its opacity is controlled in the viewer.

Rebaked the hand material locally to remove gray streaks, retaining the original
image data and material assignments outside the hand region. Adjusted 102 nose
vertices; the measured root-to-tip projection increased from 8.7 mm to 23.1 mm.
Retuned 2,127 shoulder vertices and added clavicle elevation for overhead poses.

`asset-qa.json` passed with no errors. One warning is retained: 3,473 coincident
source vertices at UV/normal seams. Welding those would damage source shading
and texture boundaries. The review does not imply production-quality topology
over the entire generated body. The final GLB contains 75,930 triangles, three
meshes, five materials, five embedded images and one skin.

`threejs-motion-report.json` passed for all three clips. Maximum exported foot
joint discrepancy against Blender targets is below 0.009 mm; planted foot drift
and loop closure are below 0.001 mm. These are skeleton measurements, not a proof
of anatomical correctness or perfect surface deformation. The actual encoded
preview was decoded and visually checked (`mp4-review.png`). No page errors were
observed; clip, muscle and opacity controls were exercised.

## Remaining limitations

- Finger geometry retains some generated faceting/webbing. The 24-bone rig has
  no individual finger joints, so convincing barbell/dumbbell grips require hand
  topology and rig work before catalog production.
- The shorts crotch is a simplified procedural construction. It is suitable for
  this deformation review, rather than a final garment simulation.
- Muscle colors are illustrative spatial regions attached to skinned vertices,
  not precise anatomical meshes or measured muscle activation. The abdominal
  region is shown as a stabilizer. Regions must be reviewed per exercise.
- Rendering, opacity and muscle colors are viewer behavior; standard GLB viewers
  show the mesh and animation without these custom controls.

No additional paid generation was submitted for these repairs or animations.
The earlier single Meshy request had an expected published price of $1.40
($1.20 textured model + $0.20 rigging); this is not an account billing receipt.

## Reproduction

The Blender scripts use the installed skills' `blender-asset-qa` and
`blender-export-pipelines` Python helpers under `~/.codex/skills/`. The original
rigged GLB is retained as a local build input. Commands run from the repository
root:

```sh
blender -b -t 4 -P artifacts/athlete-fal-v1/build_clean_athlete.py -- --with-handface
blender -b -t 4 -P artifacts/athlete-clean-v2/animate_previews.py
blender -b -t 4 -P artifacts/athlete-clean-v2/review_clean.py
npm ci --prefix artifacts/first-exercise-3d/runtime
node artifacts/athlete-clean-v2/build_motion_viewer.mjs
node artifacts/athlete-clean-v2/render_previews.mjs
python3 artifacts/athlete-clean-v2/assemble_preview_frames.py
swift artifacts/first-exercise-3d/encode.swift artifacts/athlete-clean-v2/combined-frames artifacts/athlete-clean-v2/muscle-movements.mp4 30 2000000
swift artifacts/first-exercise-3d/encode.swift artifacts/athlete-clean-v2/combined-frames artifacts/athlete-clean-v2/muscle-movements-preview.mp4 30 180000
swift artifacts/athlete-clean-v2/review_video.swift artifacts/athlete-clean-v2
```

The encoder uses macOS AVFoundation. The renderer uses a cached Chromium headless
shell on Apple Silicon; set `EXERCISE_CHROME` to override its executable path.
The skill helpers and Chromium are environment dependencies, not bundled here.
