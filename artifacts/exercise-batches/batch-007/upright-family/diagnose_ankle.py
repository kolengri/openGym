"""Identify actual mixed-ankle distortion before proposing a repair."""
import bpy,numpy as np,json,math
from pathlib import Path
from mathutils import Vector
F=Path(__file__).resolve().parent;bpy.ops.wm.open_mainfile(filepath=str(F/'source.blend'));b=bpy.data.objects['SK_BlenderStudioHuman'];r=bpy.data.objects['RIG_BlenderStudioHuman'];s=bpy.context.scene;rest=np.array([v.co[:]for v in b.data.vertices]);cam=s.camera
names={g.index:g.name for g in b.vertex_groups}
def sample(f):
 s.frame_set(f+1);bpy.context.view_layer.update();e=b.evaluated_get(bpy.context.evaluated_depsgraph_get());m=e.to_mesh();p=np.array([v.co[:]for v in m.vertices]);e.to_mesh_clear();return p
out={}
for ID,f,side in [('4437',10,'Left'),('4436',18,'Right')]:
 P=F.parent/'assets'/ID;r.animation_data.action=bpy.data.actions['Exercise_'+ID];r.animation_data.action_slot=r.animation_data.action.slots[0];base=sample(0);baseangle=r.pose.bones[side+'Leg'].matrix.to_quaternion().inverted()@r.pose.bones[side+'Foot'].matrix.to_quaternion();p=sample(f);angle=r.pose.bones[side+'Leg'].matrix.to_quaternion().inverted()@r.pose.bones[side+'Foot'].matrix.to_quaternion();d=math.degrees(baseangle.rotation_difference(angle).angle);d=min(d,360-d)
 leg={v.index for v in b.data.vertices if sum(g.weight for g in v.groups if any(names[g.group].startswith(side+x)for x in ['UpLeg','Leg','Foot','ToeBase']))>.5};domain={i for i in leg if .07<rest[i,2]<.22};edges=np.array([e.vertices[:]for e in b.data.edges if all(i in domain for i in e.vertices)]);before=np.linalg.norm(base[edges[:,0]]-base[edges[:,1]],axis=1);after=np.linalg.norm(p[edges[:,0]]-p[edges[:,1]],axis=1);ratio=after/before;rows=[]
 for k in sorted(set(list(np.argsort(ratio)[:5])+list(np.argsort(ratio)[-5:]))):
  ids=edges[k];rows.append({'ids':ids.tolist(),'source_coordinates_m':rest[ids].tolist(),'planted_length_m':float(before[k]),'current_length_m':float(after[k]),'ratio':float(ratio[k]),'weights':[{names[g.group]:g.weight for g in b.data.vertices[int(i)].groups}for i in ids]})
 ankle=r.matrix_world@r.pose.bones[side+'Foot'].head;cam.location=ankle+Vector((1.5,-2,.5));target=ankle+Vector((0,0,.04));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=.5;s.render.filepath=str(P/'ankle-regression-close.png');bpy.ops.render.render(write_still=True)
 out[ID]={'frame':f,'side':side,'source_sha256':__import__('hashlib').sha256((F/'source.blend').read_bytes()).hexdigest(),'actual_shin_relative_foot_rotation_change_degrees':d,'edge_count':len(edges),'extreme_edges':rows,'proof':'ankle-regression-close.png'}
(F/'ankle-diagnosis.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({ID:{'relative_angle_change':x['actual_shin_relative_foot_rotation_change_degrees'],'minimum':min(z['ratio']for z in x['extreme_edges']),'maximum':max(z['ratio']for z in x['extreme_edges']),'minimum_edge':min(x['extreme_edges'],key=lambda z:z['ratio'])}for ID,x in out.items()}))
