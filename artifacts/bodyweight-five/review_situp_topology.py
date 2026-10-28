"""Render temporary multi-angle solid/wire QA for the repaired sit-up extreme."""
import bpy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'bodyweight-five.blend'))
rig = bpy.data.objects['RIG_BlenderStudioHuman']
rig.animation_data.action = bpy.data.actions['Exercise_0001']
bpy.context.scene.frame_set(61)
sys.path.insert(0, str(Path.home() / '.codex/skills/blender-asset-qa/scripts'))
import review_shots

for mode in ['random', 'wire']:
    review_shots.run(objects=['SK_BlenderStudioHuman'],
                     out=str(ROOT / 'situp-repair' / ('native-' + mode + '.png')),
                     views=['right', 'back', 'three_quarter'], mode=mode, res=768)
