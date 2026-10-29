"""All-frame crossing check of both complete arm skins, including forearms."""
import bpy,json,hashlib,numpy as np
from pathlib import Path
from mathutils.bvhtree import BVHTree
P=Path(__file__).resolve().parent;bpy.ops.wm.open_mainfile(filepath=str(P/'source.blend'))
b=bpy.data.objects['SK_BlenderStudioHuman'];labels=[b.vertex_groups[max(v.groups,key=lambda g:g.weight).group].name for v in b.data.vertices]
mask=lambda side:np.array([n.startswith(side) and (n.endswith('Arm') or 'Hand' in n or any(k in n for k in ['Thumb','Index','Middle','Ring','Little'])) for n in labels])
L,R=mask('Left'),mask('Right');rows=[]
for f in range(151):
 bpy.context.scene.frame_set(f+1);bpy.context.view_layer.update();e=b.evaluated_get(bpy.context.evaluated_depsgraph_get());m=e.to_mesh();m.calc_loop_triangles();X=np.array([v.co[:] for v in m.vertices]);T=np.array([t.vertices for t in m.loop_triangles]);e.to_mesh_clear();l=BVHTree.FromPolygons(X.tolist(),T[np.all(L[T],axis=1)].tolist(),all_triangles=True);r=BVHTree.FromPolygons(X.tolist(),T[np.all(R[T],axis=1)].tolist(),all_triangles=True);rows.append({'frame':f,'cross_arm_skin_triangle_intersections':len(l.overlap(r))})
report={'ok':not any(x['cross_arm_skin_triangle_intersections'] for x in rows),'source_sha256':hashlib.sha256((P/'source.blend').read_bytes()).hexdigest(),'scope':'All original skin vertices dominantly weighted to Arm/ForeArm/Hand/finger bones, both sides, every integer runtime frame 0–150; Armature-only linear source. Adjacent same-limb skin is excluded from cross-limb comparisons.','samples':rows}
(P/'arm-clearance-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'ok':report['ok'],'failures':[x for x in rows if x['cross_arm_skin_triangle_intersections']]}))
