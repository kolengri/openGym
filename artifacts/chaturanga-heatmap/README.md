# Chaturanga surface-heat prototype

One live Three.js example for user confirmation before applying the style to
other exercises. Application delivery is GLB + Three.js; video generation is
disabled by the latest user instruction. The existing batch001 videos are
historical review artifacts.

Open `viewer.html` for the self-contained offline example, or `inline.html` for
the small embedded example. The inline version loads the public model at the
immutable revision in `build-manifest.json` and Three.js0.186.1 from jsDelivr.
A transparent snapshot of the actual canvas covers startup only; it is removed
when the live model is ready, with an explicit loading/error status.

The accepted CC0 body and `Exercise_5915` action are reused unchanged. The left
leg stays raised, both palms stay planted, and the two recommended cameras show
the chest/supports and the triceps/glute respectively. Shared orbit, pinch and
reset work in both views; a single view can be selected. Mobile views stack.
One skin, material and mixer drive the live animation. The canvas has real alpha,
and the background is CSS. Body cast shadows, AO and color textures are disabled.

## Heat-field art direction

- Main sources: bilateral chest and triceps. Additional sources: shoulders,
  core and raised-side left glute. Catalogue roles and proxy limitations remain
  those in `../bodyweight-five/clips.json` and the muscle atlas.
- An original-vertex scalar field spreads along the mesh's rest-surface edges,
  then smooths. It crosses UV splits using `_SOURCE_INDEX`, so nearby posed limbs
  do not exchange heat because they overlap on screen.
- The selected source masks supply the field; the renderer draws a warm center
  and feathered falloff. There are no muscle outlines, fiber textures or detached
  muscle shells. Quiet skin stays neutral.
- Primary falloff is0.036m and additional falloff0.032m at the1.8m body scale.
  Additional visual emphasis is0.49 of the primary scalar. A gentle0.88–1.0
  phase factor emphasizes the bottom position. These are authored display
  settings, not measured recruitment, temperature, force or medical limits.
- Chaturanga has no stretch role in the selected pilot; this example does not
  decide the later stretch palette. Approval is pending for this example only.

`heat-field.js` and `heat-material.js` isolate the reusable computation/material
for later application integration after style confirmation. The material uses
the WebGLRenderer shader hooks and chunks from the installed Three.js0.186.1;
it is not a WebGPU material. API basis: [Material](https://threejs.org/docs/pages/Material.html)
and [BufferAttribute](https://threejs.org/docs/pages/BufferAttribute.html), verified
against the installed version and actual shader compilation. Context7 retrieval
was unavailable because its monthly quota was exhausted.

## Rebuild and checks

Run from the workspace root using the existing local JavaScript dependencies:

```sh
node artifacts/chaturanga-heatmap/build.mjs
node artifacts/chaturanga-heatmap/verify.mjs
node artifacts/chaturanga-heatmap/build.mjs
node artifacts/chaturanga-heatmap/verify-inline.mjs
```

The second build includes the actual canvas startup snapshot produced by the
check. No video encoder, Blender render or animation frame sequence is used.
`verification.json` checks actual desktop/mobile-emulated WebGL, pose parity,
visible warm pixels/toggle, soft scalar values, working-side selection, alpha,
linked touch orbit/pinch/reset, endpoint seek/resume and zero media requests.
`inline-verification.json` checks the actual network-loaded example replaces
its poster with a live canvas. Physical device and application integration
remain later work. The source model's existing asset/contact QA is retained.
