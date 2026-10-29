"""Expose actual mandatory game-QA source triangle pairs for a causal pose repair."""
import bpy,sys,inspect,json
from pathlib import Path
sys.dont_write_bytecode=True
F=Path(__file__).resolve().parent;sys.path.insert(0,str(Path.home()/'.codex/skills/blender-asset-qa/scripts'));import qa_check
bpy.ops.wm.open_mainfile(filepath=str(F.parent/'assets/1986/source.blend'));r=bpy.data.objects['RIG_BlenderStudioHuman'];b=bpy.data.objects['SK_BlenderStudioHuman'];s=bpy.context.scene;r.animation_data.action=bpy.data.actions['Exercise_1986'];r.animation_data.action_slot=r.animation_data.action.slots[0];s.frame_set(31);bpy.context.view_layer.update();scope=dict(vars(qa_check));source=inspect.getsource(qa_check.run);source=source.replace('zf = _describe(zf_pairs)',"DIAG.extend([{'triangles':[list(tris[i]),list(tris[j])],'positions':[[list(verts[v])for v in tris[k]]for k in[i,j]]}for i,j in zf_pairs]);zf = _describe(zf_pairs)");scope['DIAG']=[];exec(compile(source,'diagnostic_qa_run','exec'),scope);report=scope['run'](objects=[b.name],profile='game');data={'frame':30,'source_sha256':__import__('hashlib').sha256((F.parent/'assets/1986/source.blend').read_bytes()).hexdigest(),'raw_qa':report,'zfight_pairs':scope['DIAG']}
for row in data['zfight_pairs']:row['source_vertices']=[{'id':i,'basis':list(b.data.vertices[i].co),'groups':{b.vertex_groups[g.group].name:g.weight for g in b.data.vertices[i].groups}}for i in sorted(set(sum(row['triangles'],[])))]
(F/'qa-pair-diagnosis.json').write_text(json.dumps(data,indent=2)+'\n');print(json.dumps(data['zfight_pairs']))
