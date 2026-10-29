"""Actual native skin arm/leg clearance and fixed-tabletop witnesses."""
import bpy,json,hashlib,math
from pathlib import Path
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
P=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P/'source.blend'))
b=bpy.data.objects['SK_BlenderStudioHuman'];r=bpy.data.objects['RIG_BlenderStudioHuman'];s=bpy.context.scene
for mod in b.modifiers:mod.show_viewport=mod.show_render=mod.type=='ARMATURE'
baseline=json.loads((P/'support-baseline/mechanics-verification.json').read_text())
sets={name:set(ids)for name,ids in baseline['domain_original_ids'].items()}
faces={name:[list(f.vertices)for f in b.data.polygons if all(i in ids for i in f.vertices)]for name,ids in sets.items()}
assert all(faces.values())
rows=[];initial={};leg_drift=0.;failures=[]
for frame in range(151):
 s.frame_set(frame+1);bpy.context.view_layer.update();e=b.evaluated_get(bpy.context.evaluated_depsgraph_get());m=e.to_mesh();points=[v.co.copy()for v in m.vertices]
 trees={name:BVHTree.FromPolygons(points,polys)for name,polys in faces.items()};intersections=trees['arms'].overlap(trees['legs'])
 minimum=(float('inf'),None)
 for region,other in [('arms','legs'),('legs','arms')]:
  for i in sets[region]:
   nearest,normal,poly,distance=trees[other].find_nearest(points[i])
   if distance<minimum[0]:minimum=(distance,{'region':region,'original_vertex_id':i,'opposite_polygon_index':poly})
 knees={}
 for side in ['Left','Right']:
  names=[side+token for token in ['UpLeg','Leg','Foot','ToeBase']]
  joints={n:r.pose.bones[n].head.copy()for n in names}
  for name,point in joints.items():
   initial.setdefault(name,point.copy());leg_drift=max(leg_drift,(point-initial[name]).length)
  thigh=joints[side+'UpLeg']-joints[side+'Leg'];shin=joints[side+'Foot']-joints[side+'Leg'];knees[side]=math.degrees(thigh.angle(shin))
 if intersections:failures.append(f'Frame{frame}: arm/hand versus leg triangle intersections')
 if any(abs(angle-90)>.1 for angle in knees.values()):failures.append(f'Frame{frame}: tabletop knee angle drift')
 rows.append({'frame':frame,'arm_hand_leg_triangle_intersections':len(intersections),'minimum_sampled_vertex_to_opposite_skin_m':minimum[0],'clearance_witness':minimum[1],'knee_internal_angle_degrees':knees})
 e.to_mesh_clear()
if leg_drift>1e-5:failures.append('Leg joints move during fixed-tabletop cycle')
report={'ok':not failures,'failures':failures,'source_sha256':hashlib.sha256((P/'source.blend').read_bytes()).hexdigest(),'sample_frames':151,'maximum_tabletop_joint_drift_m':leg_drift,'minimum_sampled_arm_hand_leg_skin_clearance_m':min(row['minimum_sampled_vertex_to_opposite_skin_m']for row in rows),'domain_original_ids':{k:sorted(v)for k,v in sets.items()},'samples':rows,'basis':'Actual Armature-only original-ID DQ cage including current compact targets. All source-weighted upper arms/forearms/hands/fingers tested against both complete lower-limb surface domains throughout the full entry and alternating loop. Surface vertex/triangle distances and triangle overlap are geometry witnesses; not joint-only clearance or exact continuous collision certification.'}
(P/'mechanics-verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items()if k not in ['samples','domain_original_ids']}));assert report['ok'],failures
