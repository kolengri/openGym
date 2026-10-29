"""Required random/solid and wire review; source remains immutable."""
import bpy,sys,json,hashlib,numpy as np
from pathlib import Path
F=Path(__file__).resolve().parent;sys.path.insert(0,str(Path.home()/'.codex/skills/blender-asset-qa/scripts'));import review_shots
bpy.ops.wm.open_mainfile(filepath=str(F.parent/'assets/3214/source.blend'));r=bpy.data.objects['RIG_BlenderStudioHuman'];b=bpy.data.objects['SK_BlenderStudioHuman'];s=bpy.context.scene
for ID,f in [('3214',33)]:
 r.animation_data.action=bpy.data.actions['Exercise_'+ID];r.animation_data.action_slot=r.animation_data.action.slots[0];s.frame_set(f+1);bpy.context.view_layer.update();P=F.parent/'assets'/ID
 e=b.evaluated_get(bpy.context.evaluated_depsgraph_get());me=e.to_mesh();before=np.array([v.co[:]for v in me.vertices]);e.to_mesh_clear();reports=[]
 for mode in ['random','wire']:reports.append({'mode':mode,'result':review_shots.run(objects=[b.name],out=str(P/f'qa-{mode}.png'),views=['front','back'],mode=mode,res=600)})
 e=b.evaluated_get(bpy.context.evaluated_depsgraph_get());me=e.to_mesh();after=np.array([v.co[:]for v in me.vertices]);e.to_mesh_clear();assert np.array_equal(before,after)
 (P/'qa-render-receipt.json').write_text(json.dumps({'source_sha256':hashlib.sha256((F.parent/'assets/3214/source.blend').read_bytes()).hexdigest(),'id':ID,'frame':f,'pre_post_render_skin_delta_m':0,'source_saved':False,'reports':reports},indent=2)+'\n')
