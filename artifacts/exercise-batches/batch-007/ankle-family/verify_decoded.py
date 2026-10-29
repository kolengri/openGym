"""Streaming actual decoded DQ skin: no frame/vertex cache is written."""
from pathlib import Path
import sys,json,math,hashlib
import numpy as np
from mathutils import Vector,geometry
from mathutils.bvhtree import BVHTree
P=Path(__file__).resolve().parent;B=P.parent
header=json.loads(sys.stdin.readline());assert header['source_sha256']==hashlib.sha256((P/'source.blend').read_bytes()).hexdigest();assert header['glb_sha256']==hashlib.sha256((P/'motion.glb').read_bytes()).hexdigest()
TOL=1e-8
def crossing(a,b):
 n=(a[1]-a[0]).cross(a[2]-a[0]);m=(b[1]-b[0]).cross(b[2]-b[0])
 if n.length<TOL or m.length<TOL:return False
 n.normalize();m.normalize()
 if abs(n.dot(m))>1-1e-9 and max(abs(n.dot(p-a[0]))for p in b)<TOL:
  axis=max(range(3),key=lambda i:abs(n[i]));axes=[i for i in range(3)if i!=axis];aa=[Vector((p[axes[0]],p[axes[1]]))for p in a];bb=[Vector((p[axes[0]],p[axes[1]]))for p in b]
  if any(geometry.intersect_point_tri_2d(p,*bb)for p in aa)or any(geometry.intersect_point_tri_2d(p,*aa)for p in bb):return True
  return any(geometry.intersect_line_line_2d(aa[i],aa[(i+1)%3],bb[j],bb[(j+1)%3])is not None for i in range(3)for j in range(3))
 for edges,target in [(a,b),(b,a)]:
  for i in range(3):
   start=edges[i];delta=edges[(i+1)%3]-start
   if delta.length_squared<TOL*TOL:continue
   hit=geometry.intersect_ray_tri(*target,delta,start,True)
   if hit is not None and -TOL<=(hit-start).dot(delta)/delta.length_squared<=1+TOL:return True
 return False
def lengths(pp,edges):ee=np.array(edges);return np.linalg.norm(pp[ee[:,0]]-pp[ee[:,1]],axis=1)
id=header['id'];L=header['landmarks'];domains=header['triangle_domains'];alltri=np.array(header['triangles']);rows=[];failures=[];crossings=[];initial=None;base={}
for line in sys.stdin:
 sample=json.loads(line);f=sample['frame'];p=np.array(sample['positions']);points=[Vector(v)for v in p];trees={name:BVHTree.FromPolygons(points,triangles,epsilon=0)for name,triangles in domains.items()}
 if initial is None:
  initial=p.copy();base={side:{'ankle':lengths(p,L['ankle_edges'][side]),'forefoot':lengths(p,L['forefoot_edges'][side])}for side in ['Left','Right']}
 pairrows={}
 for arm in ['LeftArm','RightArm']:
  for leg in ['LeftLeg','RightLeg']:
   candidates=trees[arm].overlap(trees[leg]);actual=[]
   for ai,li in candidates:
    at,lt=domains[arm][ai],domains[leg][li]
    if set(at)&set(lt):continue
    if crossing([points[i]for i in at],[points[i]for i in lt]):actual.append([at,lt])
   pairrows[arm+'_to_'+leg]={'bvh_candidates':len(candidates),'triangle_crossings':len(actual)}
   if actual:crossings.append({'frame':f,'pair':arm+'_to_'+leg,'original_id_triangles':actual})
 patches={}
 for name,patch in L['patches'].items():
  z=p[patch['indices'],2];metric={'min_z':float(z.min()),'max_z':float(z.max()),'fraction_near_floor':float(np.mean(abs(z)<=.012))};patches[name]=metric
  supported=name=='pelvic_support'
  if name.startswith('heel_'):
   side=name[5:];local=f/30-(0 if side=='Left'else 6);supported=id!='1368'or local<=0 or local>=6
  if supported and(metric['min_z']>.012 or metric['fraction_near_floor']<.2):failures.append(f'frame{f}: {name} support')
 feet={}
 for side in ['Left','Right']:
  ar=lengths(p,L['ankle_edges'][side])/base[side]['ankle'];fr=lengths(p,L['forefoot_edges'][side])/base[side]['forefoot'];heel=float(p[L['whole_heel_original_ids'][side],2].min());calf=float(p[L['calf_original_ids'][side],2].min());feet[side]={'ankle_edge_ratio_min':float(ar.min()),'ankle_edge_ratio_max':float(ar.max()),'forefoot_edge_max_change':float(abs(fr-1).max()),'whole_heel_min_z_m':heel,'whole_calf_min_z_m':calf}
  if ar.min()<.4 or ar.max()>2.5 or abs(fr-1).max()>.002:failures.append(f'frame{f}: {side} internal foot shape')
  local=f/30-(0 if side=='Left'else 6)
  if id=='1368'and .5<=local<=5.5 and(heel<.025 or calf<.015):failures.append(f'frame{f}: {side} leg not lifted')
 areas=.5*np.linalg.norm(np.cross(p[alltri[:,1]]-p[alltri[:,0]],p[alltri[:,2]]-p[alltri[:,0]]),axis=1);floor=float(p[:,2].min())
 if floor<-.004 or areas.min()<=1e-12:failures.append(f'frame{f}: floor/positive areas')
 rows.append({'frame':f,'floor_min_z_m':floor,'minimum_triangle_area_m2':float(areas.min()),'patches':patches,'internal_foot_shape':feet,'triangle_pairs':pairrows})
assert len(rows)==header['frames']
loop=float(np.linalg.norm(p-initial,axis=1).max())
if loop>1e-4:failures.append('Loop skin drift')
if crossings:failures.append('Confirmed arm/hand/finger vs whole-leg triangle crossings')
report={'id':id,'ok':not failures,'source_sha256':header['source_sha256'],'glb_sha256':header['glb_sha256'],'adapter_sha256':header['adapter_sha256'],'frames':len(rows),'failures':failures,'triangle_crossing_count':sum(len(row['original_id_triangles'])for row in crossings),'crossings':crossings,'loop_skin_error_m':loop,'samples':rows,'scope':'Actual canonical GLB, exact unchanged shared DQ adapter, complete original-ID skin and actual exported triangles streamed in memory. All-frame support, floor, positive areas, whole arm/hand/finger versus both legs, and internal ankle/rigid forefoot edges. No continuous-time or fully-enclosed-volume certificate. No runtime/frame/vertex cache written.'}
(B/'assets'/id/'decoded-physical-report.json').write_text(json.dumps(report,indent=2)+'\n');print('DECODED_RESULT',json.dumps({k:v for k,v in report.items()if k not in ['samples','crossings','scope']}),flush=True);assert report['ok'],failures[:12]
