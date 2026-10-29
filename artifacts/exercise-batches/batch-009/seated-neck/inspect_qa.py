"""Explain mandatory QA warnings using its unchanged warning observer."""
from pathlib import Path
import bpy,sys,json,hashlib
sys.dont_write_bytecode=True
F=Path(__file__).resolve().parent;P=F.parent/'assets/1843';W=F.parents[3];sys.path[:0]=[str(Path.home()/'.codex/skills/blender-asset-qa/scripts'),str(W/'artifacts/bodyweight-next-five')];import qa_check,warning_observer
warning_observer.install(qa_check);bpy.ops.wm.open_mainfile(filepath=str(P/'source.blend'));s=bpy.context.scene;b=bpy.data.objects['SK_BlenderStudioHuman'];out=json.loads((P/'asset-qa.json').read_text());assert out['source_sha256']==hashlib.sha256((P/'source.blend').read_bytes()).hexdigest()
for row in out['samples']:
 if not row['report']['warnings']:continue
 s.frame_set(row['frame']+1);bpy.context.view_layer.update();q=qa_check.run(objects=[b.name],profile='game');assert q==row['report'];row['warning_locations']=qa_check.QA_WARNING_DETAILS
 for pair in row['warning_locations']:
  pair['source_vertex_ids']=[list(b.data.polygons[i].vertices)for i in pair['evaluated_quad_ids']]
  pair['source_rest_centroids']=[list(sum((b.data.vertices[i].co for i in poly),b.data.vertices[0].co*0)/len(poly))for poly in pair['source_vertex_ids']]
(P/'asset-qa.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps([{'frame':r['frame'],'details':r.get('warning_locations',[])}for r in out['samples']],indent=2))
