"""Game-profile QA at neutral, working fold, assisted approach, hold and return."""
import bpy,sys,json,hashlib
from pathlib import Path
sys.dont_write_bytecode=True
F=Path(__file__).resolve().parent;P=F.parent/'assets/1986';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();source=sha(P/'source.blend');native=json.loads((P/'surface-contact-report.json').read_text());assert native['ok']and native['source_sha256']==source
sys.path.insert(0,str(Path.home()/'.codex/skills/blender-asset-qa/scripts'));import qa_check
bpy.ops.wm.open_mainfile(filepath=str(P/'source.blend'));b=bpy.data.objects['SK_BlenderStudioHuman'];r=bpy.data.objects['RIG_BlenderStudioHuman'];s=bpy.context.scene;r.animation_data.action=bpy.data.actions['Exercise_1986'];r.animation_data.action_slot=r.animation_data.action.slots[0];rows=[]
for f in [0,30,48,75,120]:
 s.frame_set(f+1);bpy.context.view_layer.update();rows.append({'frame':f,'report':qa_check.run(objects=[b.name],profile='game')})
result={'pass':all(q['report']['pass']for q in rows),'source_sha256':source,'samples':rows};(P/'raw-asset-qa.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'pass':result['pass'],'errors':[q['report']['errors']for q in rows],'warnings':[q['report']['warnings']for q in rows]}));assert result['pass']
