# Exercise animation production guide

This guide and [generation-contract.json](generation-contract.json) apply to every future exercise animation. They combine the catalogue evidence, source gaps, explicit authoring choices and lessons from the five bodyweight prototypes. The [packet preparer](prepare_generation.py) puts applicable baseline requirements, the full canonical brief, aliases, selected overrides and open issues into the exercise's generation context **before** authoring. Read that packet when authoring; a link to this document alone is insufficient.

This change defines the production contract; it does not regenerate or repair animation assets. In particular, **0001 remains an open visual defect**: the feet/pelvis do not convincingly share a floor, and the hands/arm bends near the head look unnatural. The other four delivered clips remain prototypes, not production-certified motion.

The integration is **contract + per-exercise packet preparation + the existing first-five entrypoint guard**. Packet preparation carries the constraints into generation context; the guard rejects known blocking issues before opening the Blender source. Neither is an automatic rig/contact solver or proof that all catalogue exercises are valid.

## Corpus, authority and status

The authoritative [compressed briefs](briefs.jsonl.gz) cover **6,554 source IDs: 5,632 canonical exercises and 922 aliases**. [Coverage](coverage-report.json) distinguishes **4,342 canonical records with source gaps** from **159 consequential unresolved storyboards**. The remaining 5,473 storyboards have proposals suitable for owner review, not automatic production acceptance. [review-queue.json](review-queue.json) contains source gaps as well as blockers; select `storyboard_readiness.status == "blocked_on_source_resolution"` for the 159. Keep every reason and evidence pointer when preparing an exercise.

Use these existing sources in order:

| Source | Authority and limit |
|---|---|
| [Catalogue instructions](../../catalogue/README.md), canonical `catalogue/exercises/<id>.json`, [briefs](briefs.jsonl.gz), [alias resolution](aliases.json) | Original movement, training labels, steps, hold/needs flags and exact evidence. Alias stubs inherit the canonical movement. Body-weight metadata does not prove absence of supports or equipment. |
| [Selected first five](selected-first-five.json), [readable selections](selected-first-five.md) | Explicit pilot interpretation for 5965 and reversible staging proposals. Their choices are authored, not additional source facts. |
| [Current clip manifest](../bodyweight-five/clips.json), [five-clip README](../bodyweight-five/README.md) | Current delivered pilot choices, including working side, preview timing and role overrides. The delivered 5915/5887/9066 use the **left** working or raised leg; an earlier right-first proposal must not silently overwrite this. |
| [Atlas README](../mannequin-muscle-atlas/README.md), [region map](../mannequin-muscle-atlas/region-map.json) | Illustrative surface regions and explicit surface/proxy/deep/systemic/unsupported status. These are not physiological activation or anatomical segmentation. |
| [Pose receipt](../bodyweight-five/pose-verification.json), [render receipt](../bodyweight-five/render-report.json), [runtime receipt](../bodyweight-five/runtime-verification.json) | Existing sampled checks of this prototype. A numerical pass covers only the stated measurement, not every contact patch, pose or visual requirement. |
| [Touch receipt](../bodyweight-five/touch-verification.json), [touch check](../bodyweight-five/check_touch.mjs) | Actual Chromium/Metal mobile touch emulation in the review player at 390×850. Physical iOS/Android and real application integration remain unverified. |
| [0001 contact investigation](../bodyweight-five/situp-contact-investigation.json) | Current proxy-gap and elbow measurements plus the open user report; explicitly not a contact or biomechanics approval. |

Retain the [text notices](THIRD_PARTY_NOTICES.md). The [Gym Visual media restrictions](../../catalogue/media/NOTICE.md) prohibit feeding the licensed stills or clips to AI or creating derivatives from them. Use catalogue text, authorized authoring choices and the accepted CC0 body. Do not extract, trace, regenerate from or use that media as visual guidance.

## Per-exercise intake and authoring

1. **Resolve identity and source.** Resolve aliases to one canonical ID, attach the entire original instruction array and its path/hash, and retain all source gaps. Do not create a second movement because an alias has another figure ID. A source conflict needs an explicit disposition: for example, 0002's standing instructions do not justify the inventory's inferred 45-degree bench.
2. **Record choices before keyframing.** State the starting body/limb position, exact support objects, working side, grip/palm/finger orientation, movement phases, intended range and preview timing. Mark each as `source`, `authored`, `measured_unapproved` or `unresolved`. Preserve original cues beside the choice. A proposed neutral standing pose for an unspecified hand drill is an authoring choice, not proof that the catalogue prescribed standing.
3. **Define the support graph.** Name each contact patch, supporting surface, active phases and intended contact/lift state. Use model/world coordinates and declare anatomical L/R separately from screen direction. A contact on a bench, pedal or bar must refer to that actual object and its transform. For floor work, all intended supports must use the same declared floor plane.
4. **Define joint targets and checks.** Identify the IK targets/poles, local axes, relevant joint/segment angles, phase ranges and rotation paths for this exercise. Record the basis for any numerical target or tolerance. The catalogue's approximate torso angle is not a validated hip or lumbar limit; the pilot's bent arms are not a universal elbow setting. Leave unsupported limits null and unresolved rather than supplying plausible-looking anatomy numbers.
5. **Select muscle roles and sides.** Preserve the catalogue labels, then record any display-role override. Resolve through the atlas, restrict unilateral masks to actual working/support/stretch sides and attach proxy/unsupported notices. Choose views that jointly expose the movement, relevant contacts and selected visible regions.
6. **Author the exercise's own action.** Retain the CC0 continuous body, topology, skin, finger articulation and atlas binding. Remove inherited actions and avoid carrying the previous squat or a shared sine-wave pose into another exercise. Jointly solve support, torso and limb targets; adding a floor offset to the whole character is not a contact solver.
7. **Review posed surfaces and the delivered result.** Inspect start, mid-motion, top/end and every support transition. Compare the evaluated Blender skin with the actual exported runtime skin. Review actual decoded media and the interactive viewer, not only rig targets or a successful export command. Use the checks below only for their stated scope.

The JSON contract supplies stable requirement IDs, an intake schema, current pilot overrides and open issues. Every prepared exercise must retain unresolved source and production issues. Neither a source-complete brief nor an authored staging proposal grants a production-ready status.

## Problems, causes, prevention and observable checks

| Problem / evidence | Prevent or fix | Observable check and current status |
|---|---|---|
| Generative body textures can introduce seams or apparent clothing; rebuilding clothing/anatomy destabilizes the accepted asset. [Accepted source provenance](../human-animation-base/README.md) and [runtime mesh QA](../bodyweight-five/runtime-asset-qa.json) describe the continuous CC0 path. | Reuse the original continuous surface and retained source coordinates; do not rebuild clothing or replace it with disconnected colored muscle shells. Limit additions to the rig/atlas and authorized props. | Current runtime QA records one connected island, 10,582 vertices, 21,160 triangles and no nonmanifold/open geometry. This verifies the current asset, not every future pose. |
| Coarse global floor checks can pass while intended contacts fail. The user reports 0001's feet/pelvis floor mismatch. [Investigation](../bodyweight-five/situp-contact-investigation.json) records small foot minima but much higher illustrative glute-proxy minima. | Define left/right sole and heel patches and an anatomically reviewed pelvic support patch. Solve them together with lumbar/back clearance, knees and torso pose. Do not lower the whole body by the glute-proxy gap. | Check signed distance, contact area/fraction, penetration and tangential slip of each **evaluated surface patch**, at start/mid/top and throughout contact phases. Review against a temporary QA plane from side and oblique views. **Open; no accepted pelvic contact landmark or tolerance exists yet.** |
| 0001 hands behind the head and elbow bends look unnatural despite exact loop closure. [Pose samples](../bodyweight-five/pose-samples.json) and [investigation](../bodyweight-five/situp-contact-investigation.json) support diagnosis, not approval. | Resolve shoulder/elbow/wrist orientation together with palm/head contact and finger pose. Keep hands behind the head without clipping the head/ears, crossing forearms or implying a neck pull. Do not lock a copied elbow angle across the motion as a correctness shortcut. | Start/mid/top visual review of both sides; inspect palm/head clearance, wrist bend, upper-arm twist and elbow path on the deformed skin. The measured internal elbow angle near **50.0494°** is **unapproved**, not a target or valid range. **Open.** |
| A hand-bone or foot-bone target can be correct while skin/fingers penetrate or hover. [build-report.json](../bodyweight-five/build-report.json) reports zero target error; this does not validate contact surfaces. | Author palm normals, finger extension/curl and actual sole/forefoot support geometry. Use original vertex IDs and `_SOURCE_INDEX` across exported UV splits. Include opposing limb/body surfaces in intersection checks. | Measure patch normals/gaps and inspect fingers/palms/soles in Blender and runtime. Reject limb twists and intersections even if target/loop checks pass. Per-exercise contact acceptance is still required. |
| The former 9066 motion read as rigid bobbing. [Current manifest](../bodyweight-five/clips.json), [pose receipt](../bodyweight-five/pose-verification.json) and README record the revised hop. | Author grounded compression, forefoot push-off, flight and cushioned landing, with the working knee/hip responding and the free leg controlled. Keep directional travel and support-state timing exercise-specific. | Inspect every take-off/landing, support changes and flight intervals in both complementary views. Current prototype has revised phases and sampled knee/flight checks; that is not a ground-reaction-force or biomechanics validation. |
| Mirrored left/right views repeat the same hidden muscle surfaces. [Camera presets](../bodyweight-five/camera-presets.json) use different movement/detail views. | Choose a minimal complementary view set; add views when selected regions or important contacts are occluded. Record which view/phase shows each intended visible region. Do not claim visibility of deep or unsupported regions. | Review the actual images/runtime viewports at the difficult phases, with a coverage table. Existing complementary camera choices are recorded; exhaustive per-region visibility remains a production review task. |
| Unselected fibers/seams or bilateral highlights can suggest activity in the wrong region/side. [Atlas verification](../mannequin-muscle-atlas/verification.json), [roles](../bodyweight-five/clips.json) and [render report](../bodyweight-five/render-report.json) distinguish active-only selection. | Keep all inactive skin uniformly neutral. Draw detail only in selected masks; use **red main load, amber additional involvement, cyan stretch**. Apply actual working-side masks. Treat roles as illustrative labels, not EMG or time-varying recruitment. | Existing atlas checks verify neutral uniformity and unchanged unselected pixels/vertices. Current 9066 selects loaded left calf/quads/glute; 5887 separates raised-left glute from right-leg posterior stretch. Review the visible masks on every new exercise. |
| Name-prefix mapping included hamstring `biceps_femoris` in the upper-arm `biceps` selection. | Match exact region base IDs and review group/proxy semantics; reference validity alone does not prove correct muscle meaning. | The rebuilt [map](../mannequin-muscle-atlas/region-map.json) contains only `biceps.L/R` for `biceps`; [verification](../mannequin-muscle-atlas/verification.json) has `biceps_excludes_biceps_femoris: true` and `mapping_references_valid: true`. **Focused fix measured; no claim all 57 labels received physiological review.** |
| Shadows, AO/cavity or specular overlays darken or distort selected colors. [Lighting receipt](../bodyweight-five/render-report.json) and [runtime receipt](../bodyweight-five/runtime-verification.json) record the disabled effects. | Disable cast shadows, AO/cavity and specular overlays in both native rendering and runtime. Do not bake fake cavities or background/checker patterns into the atlas. Keep QA ground aids separate from delivery. | Existing render/runtime checks record shadows/AO off and alpha-safe backgrounds. Compare overlapping limbs and selected colors in actual native and runtime views after each material/export change. |
| A checkerboard or codec flag can be mistaken for transparency. | Keep actual canvas alpha, `scene.background = null`, alpha context and clear alpha zero; CSS may show selectable backgrounds outside the canvas. Export VP9-alpha WebM for alpha and explicitly label white-background H.264 MP4 as fallback. | [Transparency verification](../bodyweight-five/transparency-verification.json) decodes every WebM master/preview frame with libvpx and checks empty alpha/opaque body. [MP4 review](../bodyweight-five/video-review.json) decodes actual files; MP4 is **not** transparent. Existing runtime checks verify actual canvas corner alpha. |
| Replacing a texture can silently select the original UV channel; loading every catalogue texture scales poorly. | Preserve exported atlas **UV channel 1** on every replacement map. Retain `_SOURCE_INDEX`. Use 2048×1024 runtime textures and a lazy neutral/active color cache with stale-load protection and disposal. Native atlas authoring may retain 4096×2048. | [Runtime receipt](../bodyweight-five/runtime-verification.json) measures channel 1, two loaded color textures, stale-switch guard and actual texture dimensions. Its GPU count also includes skeleton/internal textures. Do not preload 5,632 activation states. |
| Two views can accidentally duplicate the animated model/mixer; correct Blender poses can deform differently after export. | Use one rig/skeleton/mixer update per frame and render it through the complementary cameras. Keep native corrective smoothing/subdivision and runtime cage differences explicit. | Current [runtime receipt](../bodyweight-five/runtime-verification.json) reports one model, skeleton and mixer, synchronized viewports and sampled maximum joint error about 1.39e-6 m. Bone parity does not certify skin contacts, muscle visibility or identical shading. |
| Matching endpoint bones does not prove a smooth visible loop or a valid encoded file. | Check root/joint transforms and relevant surface/contact states across the boundary, including velocity where motion should be continuous. Decode the actual encoded output after export, with its real frame count/duration. | Existing [pose](../bodyweight-five/pose-verification.json), [video](../bodyweight-five/video-review.json), [encoding](../bodyweight-five/encoding-report.json) and [alpha](../bodyweight-five/transparency-verification.json) receipts cover sampled bones/decoded pixels/metadata. Compare seam motion against ordinary adjacent frames; still perform visual review. |
| Desktop orbit alone does not establish the requested touch playback behavior. | Open at the exercise's recommended camera(s); support finger orbit, pinch zoom and reset-to-recommended camera while motion continues. Disable panning. Preserve useful extra views for occluded selected muscles. Reset camera must not reset the clip's animation time. | The new [touch receipt](../bodyweight-five/touch-verification.json) verifies two recommended views, one-finger orbit of both views, pinch zoom, no pan, camera reset and continued animation using Chromium/Metal touch events at 390×850. **Implemented and emulation-verified in the review player; physical iOS/Android and real application integration remain open.** |

## Contact and pose acceptance details

Each support patch must identify its mesh and stable source vertices/triangles, actual supporting surface, plane/geometry transform, anatomical side, phase interval and intended state (`supported`, `pushing_off`, `airborne`, `landing`, `light_touch` or `clear`). A whole vertex group or global minimum can be useful diagnostic input, but is not an accepted contact landmark by itself.

For a plane, compute signed surface distance in the same world frame for all patches. Retain the distance distribution, near-contact area/fraction, deepest penetration and tangential displacement across supported frames. Declare scale-aware tolerances with an authoring/review basis; this guide supplies **no universal validated gap or joint-angle limits**. Check rotated support objects using their transformed surfaces, not a global Z-only test. A lifted limb must be clear during flight/lift, rather than being pulled to the floor by a generic correction.

For 0001, the current [investigation](../bodyweight-five/situp-contact-investigation.json) samples frames 0/30/60. Foot-surface minima are approximately 0.003276 m, while illustrative glute-core proxy minima are approximately 0.06286–0.06545 m; no glute-proxy vertices are within 1 cm of the floor. The glute region is **not a verified ischial contact landmark**. These observations do not establish that the entire pelvis floats by that amount, and do not justify translating the whole body down. Jointly review the intended pelvic/heel contact patches, lower-back clearance and corrective pose on the native and exported skin. Keep both open issues until per-patch results and start/mid/top visual review support closure.

Joint targets must state angle convention and reference frame: bone-local, segment internal angle, torso-to-floor or another explicitly defined measure. Preserve the source cue, authored choice and measured result separately. Record pole direction and rotation continuity so an IK solution cannot swap elbows/knees or twist a limb through the body. Finger articulation and palm orientation belong in the pose specification rather than being an export afterthought.

## Runtime, export and playback acceptance

Use the [existing runtime](../bodyweight-five/runtime_viewer.js) and [checks](../bodyweight-five/verify_runtime.mjs) as the implementation analogue. Preserve its texture channel/cache, shared animation update and transparent canvas. The required playback behavior is implemented in that review player and covered by [touch-verification.json](../bodyweight-five/touch-verification.json): recommended dual views, finger orbit, pinch zoom, reset to recommended cameras, no panning and continued animation. This is actual Chromium/Metal **mobile emulation**, not physical iOS/Android or real application integration evidence. Keep that remaining integration/device scope open; do not rely on an older orbit-only flag or mislabel the new emulation receipt as a device pass.

Use [camera-presets.json](../bodyweight-five/camera-presets.json) as current pilot camera data, not universal camera coordinates. View coverage must mention selected visible atlas regions, working side and phase. Mirror images are not complementary coverage. A single interactive view can be enough for a simple case; additional synchronized views are needed where important muscles or contacts remain hidden.

Runtime textures are currently 2048×1024; the native atlas is 4096×2048. Replacing a map must preserve the material's atlas UV channel rather than resetting to channel 0. A fixed exercise can use a fixed activation state. Dynamic highlight strength is art direction and must not be presented as measured physiological recruitment.

Validate the exact delivered files and runtime resources, recording their hashes, decoded frame count, dimensions, frame rate, silent audio state, alpha/fallback behavior and loop result. Current short previews are not real-time prescriptions for the catalogue's hold durations. Numerical receipts and visual reviews must name the asset revision, runtime/native path, frames and scope they actually inspected.

## Existing reproduction commands

Run from the repository root. These commands reproduce existing artifacts; this documentation follow-up does not authorize running another animation batch. Select only the commands needed after an authorized change, and carry the contract/intake into that change.

Prepare full canonical context, including an alias request:

```sh
python3 artifacts/exercise-animation-briefs/prepare_generation.py --exercise 0001 0004
```

The default output directory is `artifacts/exercise-generation`; `--output-dir PATH` selects another destination. Request 0004 resolves to canonical 5266. `--require-ready` writes the packets and then exits 2 if a source blocker or blocking known issue remains. It never means production approval. The 0001 packet must retain `OPEN-0001-CONTACTS` and `OPEN-0001-HAND-HEAD-POSE`; expanded playback evidence is also open but does not itself block clip authoring. The selected 5965 pilot interpretation does not erase its canonical source-pattern gap.

Normalize/check source briefs:

```sh
python3 artifacts/exercise-animation-briefs/generate.py
python3 artifacts/exercise-animation-briefs/verify.py
```

For an authorized change to the current five-clip pilot, the [existing recipe](../bodyweight-five/README.md) uses:

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
node artifacts/bodyweight-five/check_touch.mjs
```

Ordinary first-five regeneration is currently rejected because 0001 has blocking known issues. For an **explicitly authorized remediation draft**, the existing entrypoint supports this override:

```sh
blender -b -t 4 --python-exit-code 1 -P artifacts/bodyweight-five/build_motion.py -- --allow-known-issues
```

The override permits a draft repair attempt; it does not close issues, relax acceptance, approve the pose or turn the other four clips into certified motion.

These existing checks are necessary evidence for their respective changes, but do not implement or replace the new per-contact-patch, exercise-specific pose, visibility or touch-playback acceptance described here. Do not interpret a successful old command as closure of an issue outside its scope. No additional paid service, publication, global preference change or whole-catalogue render is required by this contract.
