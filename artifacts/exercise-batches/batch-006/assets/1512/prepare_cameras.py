"""Two fixed views; full-cycle source-ID framing for the grasp companion."""
import bpy,json,hashlib,numpy as np
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P/'source.blend'));b=bpy.data.objects['SK_BlenderStudioHuman'];s=bpy.context.scene
names={g.index:g.name for g in b.vertex_groups}
prefixes=('LeftHand','LeftIndex','LeftMiddle','LeftRing','LeftLittle','LeftThumb','LeftFoot','LeftToeBase')
ids=sorted(v.index for v in b.data.vertices if sum(g.weight for g in v.groups if names[g.group].startswith(prefixes))>.5)
assert len(ids)==len(set(ids))and min(ids)>=0 and max(ids)<10582
lo=np.full(3,np.inf);hi=np.full(3,-np.inf)
for frame in range(151):
 s.frame_set(frame+1);bpy.context.view_layer.update();e=b.evaluated_get(bpy.context.evaluated_depsgraph_get());m=e.to_mesh();p=np.array([m.vertices[i].co[:]for i in ids]);lo=np.minimum(lo,p.min(axis=0));hi=np.maximum(hi,p.max(axis=0));e.to_mesh_clear()
target=(lo+hi)/2;target[0]=.15
views=[{'label':'Whole-body quad and grasp oblique','position':[2.8,-2.3,1.55],'target':[0,.06,.43],'scale':2.46},
 {'label':'Hand and foot side companion','position':(target+np.array([3.6,-.04,.35])).tolist(),'target':target.tolist(),'scale':1.6,'frameSourceIds':ids}]
camera=s.camera;c=views[1];camera.location=c['position'];camera.rotation_euler=(Vector(c['target'])-camera.location).to_track_quat('-Z','Y').to_euler();rotation=camera.rotation_euler.to_matrix().transposed()
max_x=0;max_y=0
for frame in range(151):
 s.frame_set(frame+1);bpy.context.view_layer.update();e=b.evaluated_get(bpy.context.evaluated_depsgraph_get());m=e.to_mesh()
 for i in ids:
  p=rotation@(m.vertices[i].co-Vector(c['target']));max_x=max(max_x,abs(p.x));max_y=max(max_y,abs(p.y))
 e.to_mesh_clear()
aspect=s.render.resolution_x/s.render.resolution_y;c['scale']=float(max(2*max_x,2*max_y*aspect)*1.12)
(P/'cameras.json').write_text(json.dumps(views,indent=2)+'\n')
(P/'camera-framing-report.json').write_text(json.dumps({'source_sha256':hashlib.sha256((P/'source.blend').read_bytes()).hexdigest(),'frames':151,'companion_original_id_count':len(ids),'active_domain':'Complete dominant left hand/finger and foot/toe source IDs, unique original10582vertex domain. Entire model retained.','full_cycle_selected_bounds':{'min':lo.tolist(),'max':hi.tolist()},'source_proof_aspect':aspect,'side_companion_horizontal_width':c['scale'],'whole_body_horizontal_width':views[0]['scale'],'ratio_companion_to_whole':c['scale']/views[0]['scale'],'limit':'Full hand travel prevents a static tight hold-only crop. This fixed companion includes approach/hold/open/return IDs through the full cycle; primary runtime width fitting remains required.'},indent=2)+'\n')
s.frame_set(76);camera.data.ortho_scale=c['scale']/aspect;s.render.filepath=str(P/'grasp-companion-hold.png');bpy.ops.render.render(write_still=True)
print('CAMERA_COMPANION',len(ids),c['scale'])
