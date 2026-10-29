"""Bounded digit-flexion diagnosis against fixed actual left distal-arm triangles."""
from pathlib import Path
import sys,json,math
import bpy,numpy as np
from mathutils import Quaternion,Vector
from mathutils.bvhtree import BVHTree
P=Path(__file__).resolve().parent
sys.path.insert(0,str(P.parents[2]/'batch-003'));import authoring as a
a.initialize();specs=dict(a.finger_specs);rest=dict(a.rest)
bpy.ops.wm.open_mainfile(filepath=str(P/'source.blend'));b=bpy.data.objects['SK_BlenderStudioHuman'];r=bpy.data.objects['RIG_BlenderStudioHuman'];s=bpy.context.scene
b.data.calc_loop_triangles();tri=np.array([t.vertices[:] for t in b.data.loop_triangles]);regions={}
for p,v in zip(b.data.polygons,b.data.attributes['.sculpt_face_set'].data):regions.setdefault(v.value,set()).update(p.vertices)
def mask(*ids):return np.isin(np.arange(10582),sorted(set.union(*(regions[i] for i in ids))))
A=mask(12,9,*range(64,84));fA=tri[np.all(A[tri],axis=1)]
rows=[]
for angle in [-60,-40,-20,0,20,40,60]:
 s.frame_set(76)
 for name,(head,tail,parent,digit,index) in specs.items():
  if not name.startswith('Right'):continue
  axis=(tail-head).normalized().cross(Vector((1,0,0))).normalized();axis=rest[name].to_3x3().inverted()@axis
  flex=([30,45,30][index] if digit!='Thumb' else [15,24,12][index])*.6
  q=Quaternion(axis,math.radians(flex))
  if digit=='Thumb' and index==0:
   hand_axis=rest[name].to_3x3().inverted()@Vector((1,0,0))
   q=Quaternion(hand_axis,math.radians(angle))@q
  r.pose.bones[name].rotation_quaternion=q
 bpy.context.view_layer.update();ev=b.evaluated_get(bpy.context.evaluated_depsgraph_get());m=ev.to_mesh();xyz=np.array([ev.matrix_world@v.co for v in m.vertices]);ev.to_mesh_clear();ta=BVHTree.FromPolygons(xyz.tolist(),fA.tolist(),all_triangles=True)
 row={'thumb_abduction_degrees':angle,'digits':{}}
 for label,ids in [('thumb',range(84,88))]:
  B=mask(*ids);tb=BVHTree.FromPolygons(xyz.tolist(),tri[np.all(B[tri],axis=1)].tolist(),all_triangles=True);near=[ta.find_nearest(tuple(xyz[i])) for i in np.flatnonzero(B)]
  row['digits'][label]={'intersections':len(ta.overlap(tb)),'min_distance':min(n[3] for n in near),'min_oriented_distance':min((xyz[i]-np.array(n[0])).dot(n[1]) for i,n in zip(np.flatnonzero(B),near))}
 rows.append(row)
(P/'thumb-spread-diagnosis.json').write_text(json.dumps(rows,indent=2,default=float)+'\n')
print(json.dumps(rows,default=float))
