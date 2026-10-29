"""Readable neutral diagnostic poses; never save camera changes to source."""
import bpy,json,numpy as np
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent;bpy.ops.wm.open_mainfile(filepath=str(P/'source.blend'));s=bpy.context.scene;b=bpy.data.objects['SK_BlenderStudioHuman'];cam=s.camera;views=json.loads((P/'cameras.json').read_text())
def points():
 bpy.context.view_layer.update();e=b.evaluated_get(bpy.context.evaluated_depsgraph_get());m=e.to_mesh();p=np.array([v.co[:]for v in m.vertices]);e.to_mesh_clear();return p
proofs=[]
for f,label,view in [(0,'guard',0),(5,'right-attack',0),(8,'right-punch',0),(16,'right-retraction',0),(25,'between-punches-guard',0),(33,'left-punch',1),(150,'guard-return',1)]:
 s.frame_set(f+1);v=views[view];cam.location=v['position'];cam.rotation_euler=(Vector(v['target'])-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=2.25;before=points();s.render.filepath=str(P/f'fast-{label}.png');bpy.ops.render.render(write_still=True);assert np.array_equal(before,points());proofs.append({'frame':f,'file':Path(s.render.filepath).name,'pre_post_render_skin_delta_m':0,'diagnostic_ortho_scale':2.25,'source_camera_saved':False})
(P/'timing-render-readback.json').write_text(json.dumps({'source_unchanged':True,'proofs':proofs},indent=2)+'\n')
