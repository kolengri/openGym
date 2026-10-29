"""All151actual decoded-DQ frames; complete arm/hand vs leg triangles.

The Node verifier passes positions only through stdin. No runtime frame cache
or temporary geometry file is written. BVH overlap is broad phase; mathutils
ray/triangle and coplanar segment tests determine actual crossings.
"""
import sys,json,hashlib,math
from pathlib import Path
from mathutils import Vector,geometry
from mathutils.bvhtree import BVHTree
P=Path(__file__).resolve().parent
packet=json.loads(sys.stdin.read())
assert packet['source_sha256']==hashlib.sha256((P/'source.blend').read_bytes()).hexdigest()
assert packet['glb_sha256']==hashlib.sha256((P/'motion.glb').read_bytes()).hexdigest()
TOL=1e-8
def intersect(a,b):
 n=(a[1]-a[0]).cross(a[2]-a[0]);m=(b[1]-b[0]).cross(b[2]-b[0])
 if n.length<TOL or m.length<TOL:return False
 n.normalize();m.normalize()
 if abs(n.dot(m))>1-1e-9 and max(abs(n.dot(p-a[0]))for p in b)<TOL:
  axis=max(range(3),key=lambda i:abs(n[i]));axes=[i for i in range(3)if i!=axis]
  aa=[Vector((p[axes[0]],p[axes[1]]))for p in a];bb=[Vector((p[axes[0]],p[axes[1]]))for p in b]
  if any(geometry.intersect_point_tri_2d(p,*bb)for p in aa)or any(geometry.intersect_point_tri_2d(p,*aa)for p in bb):return True
  return any(geometry.intersect_line_line_2d(aa[i],aa[(i+1)%3],bb[j],bb[(j+1)%3])is not None for i in range(3)for j in range(3))
 for edges,target in [(a,b),(b,a)]:
  for i in range(3):
   start=edges[i];delta=edges[(i+1)%3]-start
   if delta.length_squared<TOL*TOL:continue
   hit=geometry.intersect_ray_tri(*target,delta,start,True)
   if hit is not None:
    factor=(hit-start).dot(delta)/delta.length_squared
    if -TOL<=factor<=1+TOL:return True
 return False

samples=[];crossings=[];domains=packet['domains']
foot_rows=[];foot_domain=packet['foot_domain'];first=packet['frames'][0]['positions']
initial_lengths={name:[math.dist(first[i],first[j])for i,j in edges]for name,edges in foot_domain.items()}
for sample in packet['frames']:
 foot_row={'frame':sample['frame']}
 for name,edges in foot_domain.items():foot_row[name+'_maximum_change_from_planted']=max(abs(math.dist(sample['positions'][i],sample['positions'][j])/base-1)for(i,j),base in zip(edges,initial_lengths[name]))
 foot_rows.append(foot_row)
 points=[Vector(p)for p in sample['positions']]
 trees={name:BVHTree.FromPolygons(points,triangles,epsilon=0)for name,triangles in domains.items()}
 checks={}
 for arm in ['LeftArm','RightArm']:
  for leg in ['LeftLeg','RightLeg']:
   candidates=trees[arm].overlap(trees[leg]);actual=[]
   for ai,li in candidates:
    at,lt=domains[arm][ai],domains[leg][li]
    # Source-adjacent triangles are the same continuous skin boundary and do
    # not represent a separated arm/leg collision. None are expected here.
    if set(at)&set(lt):continue
    if intersect([points[i]for i in at],[points[i]for i in lt]):actual.append({'arm_original_ids':at,'leg_original_ids':lt})
   key=arm+'_to_'+leg;checks[key]={'bvh_candidate_pairs':len(candidates),'triangle_crossings':len(actual)}
   if actual:crossings.append({'frame':sample['frame'],'pair':key,'crossings':actual})
 samples.append({'frame':sample['frame'],'pairs':checks})
report={'pass':not crossings,'source_sha256':packet['source_sha256'],'glb_sha256':packet['glb_sha256'],'adapter_sha256':packet['adapter_sha256'],'frames':len(samples),'reference_kind':'Actual GLTFLoader canonical GLB, animated POSITION/NORMAL key weights, and unchanged shared DQ adapter, original-ID positions passed in memory.','domain':'All actual exported triangles incident on any>50%arm/hand/finger or whole-leg weighted vertex; one boundary ring retained. Both whole arms/hands vs both whole thighs/calves/feet.','domain_triangle_counts':{name:len(triangles)for name,triangles in domains.items()},'method':'Blender BVHTree broad phase followed by mathutils ray-triangle segment tests in both directions and coplanar2Dcontainment/edge tests. Shared-original-ID adjacency excluded.','numeric_tolerance_m':TOL,'triangle_crossing_count':sum(len(x['crossings'])for x in crossings),'crossings':crossings,'samples':samples,'limits':'Discrete151frame surface crossing check; no continuous-time or fully-enclosed-volume certification. Positive-clearance/nearest-normal penetration diagnostics remain separate.'}
(P/'decoded-triangle-contact-report.json').write_text(json.dumps(report,indent=2)+'\n')
foot_report={'pass':all(row[name+'_maximum_change_from_planted']<.002 for row in foot_rows for name in foot_domain),'source_sha256':packet['source_sha256'],'glb_sha256':packet['glb_sha256'],'adapter_sha256':packet['adapter_sha256'],'frames':151,'maximum_ankle_edge_change_from_planted':max(row['ankle_edges_maximum_change_from_planted']for row in foot_rows),'maximum_forefoot_edge_change_from_planted':max(row['foot_edges_maximum_change_from_planted']for row in foot_rows),'threshold':.002,'samples':foot_rows,'scope':'Actual decoded canonical GLB and exact shared DQ adapter, original-ID mixed ankle and whole forefoot edges. Internal shape regression relative to actual planted skin; reaches the rejected hook missed by generic positive-area checks.'}
(P/'foot-return-repair/decoded-foot-regression.json').write_text(json.dumps(foot_report,indent=2)+'\n')
print(json.dumps({'decoded_triangle_pass':report['pass'],'frames':len(samples),'triangle_crossings':report['triangle_crossing_count'],'domain_triangles':report['domain_triangle_counts']}))
assert report['pass']
assert foot_report['pass'],foot_report
