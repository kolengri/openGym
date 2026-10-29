"""Complete selected mandatory game QA while reusing an unchanged held-pose receipt."""
import bpy,sys,json,hashlib
from pathlib import Path
sys.dont_write_bytecode=True
F=Path(__file__).resolve().parent;ID=sys.argv[sys.argv.index('--id')+1];assert ID in['1987','1986'];P=F.parent/'assets'/ID;source=hashlib.sha256((P/'source.blend').read_bytes()).hexdigest();native=json.loads((P/'surface-contact-report.json').read_text());assert native['ok']and native['source_sha256']==source;timing=json.loads((F/'timing-comparison.json').read_text());assert timing['maximum_held_pose_matrix_error']<2e-6;sys.path[:0]=[str(F.parent.parent/'batch-003'),str(Path.home()/'.codex/skills/blender-asset-qa/scripts')];import authoring as a,qa_check
bpy.ops.wm.open_mainfile(filepath=str(P/'source.blend'));b=bpy.data.objects['SK_BlenderStudioHuman'];r=bpy.data.objects['RIG_BlenderStudioHuman'];s=bpy.context.scene;original=json.loads((F/'timing-baseline'/ID/'source-verification.json').read_text());assert a.binding_hash(b,r)==original['runtime_binding_sha256'];r.animation_data.action=bpy.data.actions['Exercise_'+ID];r.animation_data.action_slot=r.animation_data.action.slots[0];rows=[]
for f in[0,30,75,120]:
 if f==75:
  old=json.loads((F/'timing-baseline'/ID/'raw-asset-qa.json').read_text());report=next(q['report']for q in old['samples']if q['frame']==75);rows.append({'frame':f,'report':report,'receipt_reuse':'Same authored hold within existing2e-6 matrix tolerance, exact binding. No hold QA rerun.','maximum_held_pose_matrix_error':timing['maximum_held_pose_matrix_error'],'baseline_source_sha256':old['source_sha256']})
 else:s.frame_set(f+1);bpy.context.view_layer.update();rows.append({'frame':f,'report':qa_check.run(objects=[b.name],profile='game')})
result={'pass':all(q['report']['pass']for q in rows),'source_sha256':source,'samples':rows};(P/'raw-asset-qa.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'pass':result['pass'],'errors':[q['report']['errors']for q in rows]}));assert result['pass']
