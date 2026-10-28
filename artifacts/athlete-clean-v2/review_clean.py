"""Review the true regular-quad shorts cage separately from overlapping body layers."""
import bpy,sys,json
from pathlib import Path
P=Path(__file__).resolve().parent;bpy.ops.wm.open_mainfile(filepath=str(P/'athlete-clean.blend'))
sys.path.insert(0,str(Path.home()/'.codex/skills/blender-asset-qa/scripts'));import review_shots
objects=['SK_Athlete','SK_CleanPelvis','SK_CleanShorts']
result={} if '--cage-only' in sys.argv else {'material':review_shots.run(objects=objects,out=str(P/'asset-review.png'),views=['front','right','back'],mode='material',res=320)}
shorts=bpy.data.objects['SK_CleanShorts']
# A fresh unparented copy avoids inherited rig scale and parent-inverse transforms.
bpy.context.view_layer.update()
mesh=bpy.data.meshes.new('QA_ShortsCage')
mesh.from_pydata([shorts.matrix_world @ v.co for v in shorts.data.vertices],[],[tuple(p.vertices) for p in shorts.data.polygons])
mesh.update()
cage=bpy.data.objects.new('QA_ShortsCage',mesh);bpy.context.scene.collection.objects.link(cage)
result['shorts_control_cage']=review_shots.run(objects=[cage.name],out=str(P/'shorts-quad-cage.png'),views=['front','right','back'],mode='wire',res=384)
(P/'review.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
