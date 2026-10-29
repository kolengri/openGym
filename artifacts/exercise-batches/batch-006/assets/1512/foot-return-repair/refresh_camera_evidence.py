"""Read-only camera evidence; runtime width fitting remains primary-owned."""
import bpy,json,hashlib,numpy as np
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent;A=P.parent
bpy.ops.wm.open_mainfile(filepath=str(A/'source.blend'));b=bpy.data.objects['SK_BlenderStudioHuman'];s=bpy.context.scene
views=json.loads((A/'cameras.json').read_text());c=views[1];ids=c['frameSourceIds'];assert len(ids)==len(set(ids))and all(isinstance(i,int)and 0<=i<10582 for i in ids)
camera=s.camera;camera.location=c['position'];camera.rotation_euler=(Vector(c['target'])-camera.location).to_track_quat('-Z','Y').to_euler();rotation=camera.rotation_euler.to_matrix().transposed();lo=np.full(3,np.inf);hi=np.full(3,-np.inf);mx=my=0
for frame in range(151):
 s.frame_set(frame+1);bpy.context.view_layer.update();e=b.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=e.to_mesh();pp=np.array([mesh.vertices[i].co[:]for i in ids]);lo=np.minimum(lo,pp.min(axis=0));hi=np.maximum(hi,pp.max(axis=0))
 for point in pp:
  projected=rotation@(Vector(point)-Vector(c['target']));mx=max(mx,abs(projected.x));my=max(my,abs(projected.y))
 e.to_mesh_clear()
aspect=s.render.resolution_x/s.render.resolution_y;proof_width=max(2*mx,2*my*aspect)*1.12
report={'source_sha256':hashlib.sha256((A/'source.blend').read_bytes()).hexdigest(),'frames':151,'companion_original_id_count':len(ids),'active_domain':'Same unique active hand/finger and foot/toe IDs; complete body retained.','full_cycle_selected_bounds':{'min':lo.tolist(),'max':hi.tolist()},'source_proof_aspect':aspect,'native_proof_horizontal_width':proof_width,'runtime_companion_width_at_readback':c['scale'],'whole_body_horizontal_width':views[0]['scale'],'runtime_camera_sha256_at_readback':hashlib.sha256((A/'cameras.json').read_bytes()).hexdigest(),'limit':'No cameras.json mutation. Native proof width is measured for1100x850; primary fits the runtime aspect and records integration separately.'}
(A/'camera-framing-report.json').write_text(json.dumps(report,indent=2)+'\n');s.frame_set(76);camera.data.ortho_scale=proof_width;s.render.filepath=str(A/'grasp-companion-hold.png');bpy.ops.render.render(write_still=True);print(json.dumps(report))
