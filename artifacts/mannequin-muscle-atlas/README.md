# Illustrative mannequin muscle atlas

Reusable surface highlighting for the original CC0 Blender Studio realistic male body in `../human-animation-base/professional-base.blend`. The module preserves the entire continuous body, all 10,582 base vertex indices, 10,590 base polygons, native sculpt and modifiers. It adds no shell, clothing, separate muscle object, anatomical organs or animation.

The 96 bilateral regions are **illustrative artist-authored surface masks, not true anatomical segmentation, EMG, physiological activation values or medical guidance**. They use the original rest coordinates and explicit anatomical layering limits. No BP3D, FaceForge or GymVisual geometry, data or media was used.

## Blender API

```python
import sys
sys.path.insert(0, '/absolute/path/to/artifacts/mannequin-muscle-atlas')
import muscle_atlas as atlas

body = bpy.data.objects['SK_BlenderStudioHuman']
weights = atlas.prepare(body)  # dict[region_id, float32[10582]], persisted MA_* point attributes
image = atlas.prepare_texture(body)  # optional, recommended for visible boundaries and fibers
bpy.context.scene.display.shading.color_type = 'TEXTURE'

atlas.apply(body, ['quads', 'glutes'], ['core', 'calves'], strength=0.85)
atlas.apply(body, ['shoulders'], ['core'], stretch_names=['hamstrings'])
atlas.apply(body)  # uniform neutral body, with no drawn muscle regions
atlas.apply(body, ['biceps'])  # detail appears only inside the selected biceps
```

`prepare()` accepts an existing Armature modifier and vertex groups. The original rest cage coordinates and ordered topology must match the source; changing only the pose is safe. New topology or altered rest coordinates are rejected. `prepare()` returns vertex-index fields that deform with any rig bound to that cage. Call it once per loaded mesh. An in-process cache avoids field solving in subsequent `apply()` calls. `force=True` rebuilds the atlas attributes only.

`apply(body, primary_names=(), secondary_names=(), strength=1.0, *, stretch_names=(), strict=False, show_inactive_anatomy=False)` accepts catalogue names or exact IDs such as `deltoid_posterior.L`, `rectus_abdominis_3.R`, `soleus_lateral.L`. `.L` is anatomical left (+X). Strength is a finite visual color blend in [0,1]. Red denotes a selected primary, amber a secondary, cyan a stretch; primary selection takes precedence where roles overlap. By default, unselected skin has one uniform neutral color with no drawn regions, fibers or seams. Fiber and boundary detail appears only inside selected regions. Empty selection produces a uniform neutral body; the original sculpt and ordinary surface shading are preserved. Exercise metadata and motion phase determine the roles; the atlas does not infer recruitment or stretching from an exercise name.

`show_inactive_anatomy=True` explicitly restores the complete neutral anatomy drawing for an atlas inspection. It is off by default and is not used by the supplied exercise textures or previews. The detailed neutral drawing and fiber fields remain cached separately; switching back to the default does not destroy selected-region detail.

The return value lists resolved regions, unknown names and explicit deep/proxy/systemic/unsupported notices. Unknown names are not guessed. `strict=True` raises for unknown strings. Systemic and unsupported catalogue entries resolve successfully with an empty region list and an explanation.

`COLOR_ATTRIBUTE == 'MuscleAtlas'`; `BASE_ATTRIBUTE == 'MuscleAtlasBase'`. The base attribute is uniform neutral. For the simplest vertex-only path, skip `prepare_texture()` and set Workbench shading to `VERTEX`. This retains anatomical fields but selected boundaries/fibers blur on the sparse source torso/thigh cage. The sharper preview uses the texture path.

## Sharp texture path and export

`prepare_texture(body, resolution=(4096, 2048))` copies the original UVMap into `MuscleAtlasUV`, normalized from the original 9×4 tile layout. The source UVMap is retained. It projects surface coordinates once, prepares sparse texel masks and adds four texels of padding. `apply()` updates the same generated image from cached sparse masks. No per-frame spatial solve or disconnected surface is required. The UVs and image deform with the original skin. The generated texture and its material can be included with a `.blend` or standard mesh export.

The texture path provides fan, oblique, longitudinal and pennate illustrative fiber contrast inside selected supported regions. All unselected skin, including unselected muscles, head, hands, feet and fascia, stays uniformly neutral. Fiber paths and straightened region boundaries are diagrammatic rather than a fascicle reconstruction. The same color attribute remains available for other consumers. `ensure_material(body)` creates a Principled material reading vertex colors; `prepare_texture()` adds the image to that material. No global procedural bump draws fibers on inactive skin. Materials/UVs are atlas-owned additions; the source's coordinate/topology signature excludes these additions.

If exporting animated activation to a format with static textures, export distinct activation states or drive highlight weights in the viewer. A changing Blender image is not automatically a glTF animation channel. Vertex attributes and color state remain exportable, while arbitrary MA_* attributes may require explicit export options or a companion mapping.

## Coverage and limitations

`region-map.json` covers every distinct target/secondary string in all 5,632 canonical catalogue records, including approved `muscleMap` overrides. The 922 alias stubs add no muscle metadata. There are 57 distinct muscle strings. `catalogue-strings.json` records their fields and occurrences. `region-map.schema.json` defines the mapping contract; every referenced region is validated by the build.

Chest has clavicular/sternocostal regions; shoulders have three heads; rectus abdominis has four paired blocks; serratus has four visible paired slips. Separate masks cover biceps, triceps, forearm compartments, trapezius divisions, lats, erector columns, gluteal regions, superficial quads, adductors, hamstrings, both gastrocnemius heads, visible soleus strips and tibialis anterior. Small partial regions are limited by the original source cage's resolution.

Rhomboids and iliopsoas are explicitly marked **deep projections**. Rotator cuff uses a posterior infraspinatus area proxy rather than painting the whole cuff as superficial tissue. Levator scapulae uses an explicitly approximate upper trapezius surface proxy. Broad terms such as core and back are group proxies. Hidden vastus intermedius, gluteus minimus and deep portions of other muscles are omitted. Hands, feet, ankles and ankle stabilizers are unsupported; cardiovascular system is systemic. No localized patch is invented for those categories.

The previews demonstrate a uniform neutral body and deliberately broad example role selection with detail only inside selected muscles; they do not assert that a single exercise activates all highlighted regions. An individual exercise should select its actual catalogue roles. Occluded muscles remain prepared for other camera views. The silhouette is the original unmodified sculpt.

## Reproduce and evidence

Run from the repository root using installed Blender 5.2.3 LTS:

```sh
/opt/homebrew/bin/blender -b artifacts/human-animation-base/professional-base.blend --python-exit-code 1 -P artifacts/mannequin-muscle-atlas/build_preview.py
```

`build_preview.py` writes the mapping, verifies complete canonical coverage, nonempty/finite region fields, exact rest-coordinate/topology equality, repeatable colors, rejection of unknown strict names and nonfinite strengths, and renders actual front/side/back PNGs. It also checks uniform default neutral vertex and texture colors, unchanged colors outside selected masks, retained selected fiber contrast and the explicit detailed-neutral option. `verification.json` contains measured results. `mannequin-muscle-atlas.blend` contains the uniform neutral body with original geometry and no baked exercise animation. `check_delivery.py` verifies the packed neutral texture, uniform vertex colors and absence of a global bump after reopening the file.

Anatomy references checked against OpenStax *Anatomy and Physiology 2e*: [11.4 abdominal wall and thorax](https://openstax.org/books/anatomy-and-physiology-2e/pages/11-4-axial-muscles-of-the-abdominal-wall-and-thorax), [11.5 pectoral girdle and upper limbs](https://openstax.org/books/anatomy-and-physiology-2e/pages/11-5-muscles-of-the-pectoral-girdle-and-upper-limbs), [11.6 pelvic girdle and lower limbs](https://openstax.org/books/anatomy-and-physiology-2e/pages/11-6-appendicular-muscles-of-the-pelvic-girdle-and-lower-limbs). These references support layer/region decisions; they do not validate the approximate mask boundaries as anatomical segmentation.

`export_texture(body, filepath, pack=True)` writes the current activation texture as an sRGB PNG and packs the current pixels into the Blender image. `export_role_mask(body, filepath, primary_names, secondary_names, stretch_names=())` writes a linear, non-color RGB weight image (red channel primary, green secondary, blue stretch). Use the role image with the neutral base and viewer-controlled colors/intensity; no texture updates are necessary for a fixed exercise. The first five catalogue examples are supplied in `textures/manifest.json`. For exercise 5887, the primary supplied a stretch role for hamstrings, which is represented in cyan instead of active primary red. The other role lists come directly from the catalogue.

The current previews use `lighting.py`: cast shadows, cavity/AO and specular
highlights are disabled so overlapping limbs cannot darken the selected muscle
colors. Lighting preferences change only in the background process and are never
saved to the user profile.
