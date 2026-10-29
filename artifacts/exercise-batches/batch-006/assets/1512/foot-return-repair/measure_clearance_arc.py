"""Geometry-derived outward correction for the final closing thumb sample."""
import bpy,json,math,hashlib
from pathlib import Path
from mathutils.bvhtree import BVHTree
P=Path(__file__).resolve().parent;A=P.parent
bpy.ops.wm.open_mainfile(filepath=str(A/'source.blend'));s=bpy.context.scene;s.frame_set(39);bpy.context.view_layer.update();b=bpy.data.objects['SK_BlenderStudioHuman'];r=bpy.data.objects['RIG_BlenderStudioHuman'];names={g.index:g.name for g in b.vertex_groups}
def selected(prefixes):return {v.index for v in b.data.vertices if sum(g.weight for g in v.groups if names[g.group].startswith(tuple(prefixes)))>.5}
leg=selected(['LeftUpLeg','LeftLeg','LeftFoot','LeftToeBase']);thumb=selected(['LeftThumb']);faces=[list(p.vertices)for p in b.data.polygons if all(i in leg for i in p.vertices)]
e=b.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=e.to_mesh();points=[v.co.copy()for v in mesh.vertices];tree=BVHTree.FromPolygons(points,faces);values=[]
for i in thumb:
 q,n,_,distance=tree.find_nearest(points[i]);signed=(points[i]-q).dot(n)
 if distance<.04:values.append((signed,i,n,points[i],q))
signed,i,normal,point,target=min(values,key=lambda row:row[0]);t=38/30;u=(t-1.10)/.20;weight=math.sin(math.pi*u)**2;delta=normal*((.0005-signed)/weight);local=r.pose.bones['LeftFoot'].matrix.to_3x3().inverted()@delta
report={'source_sha256':hashlib.sha256((A/'source.blend').read_bytes()).hexdigest(),'method':'Single measured outward normal correction: peak displacement=(0.5mm target clearance - actual signed clearance)/known arc basis at frame38. No angle/parameter grid or new held fit.','frame':38,'thumb_original_id':i,'actual_signed_clearance_m':signed,'skin_outward_normal_world':list(normal),'current_arc_basis':weight,'additional_peak_world_m':list(delta),'additional_peak_foot_local_m':list(local),'additional_peak_length_m':delta.length,'target_local_clearance_m':.0005,'limits':'Local tangent-plane prediction; full151 actual skin/triangle checks must verify final trajectory.'}
(P/'closure-clearance-arc.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report));e.to_mesh_clear()
