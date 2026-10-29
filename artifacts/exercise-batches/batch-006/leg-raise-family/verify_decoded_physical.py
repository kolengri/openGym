"""Actual exported topology + decoded DQ skin all151 physical verification."""
import sys,json,hashlib,copy
from pathlib import Path
import bpy,numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
P=Path(__file__).resolve().parent;B=P.parent;sys.path.insert(0,str(P));import family_common as c
tri=np.array(json.loads((P/'.decoded-topology.json').read_text()),np.int32);assert tri.shape==(21160,3)and tri.min()>=0 and tri.max()<10582
sets={n:set(v)for n,v in json.loads((P/'physical-domains.json').read_text())['source_domains'].items()};faces={n:[row.tolist()for row in tri if any(int(i)in ids for i in row)]for n,ids in sets.items()};sha=hashlib.sha256((P/'motion.glb').read_bytes()).hexdigest();shared=None
for eid in ['4826','4001','5106','3590']:
 out=B/'assets'/eid;export=json.loads((out/'export-verification.json').read_text());assert export['ok']and export['sha256']==sha;points=np.memmap(P/f'.decoded-all151-{eid}.f64',dtype='<f8',mode='r',shape=(151,10582,3));rows=[];failures=[];same_error=0.
 if eid=='3590':reference=np.memmap(P/'.decoded-all151-4826.f64',dtype='<f8',mode='r',shape=(151,10582,3))
 for f,p in enumerate(points):
  if eid=='3590':same_error=max(same_error,float(np.linalg.norm(p-reference[f],axis=1).max()));assert same_error<1e-12;row=copy.deepcopy(shared[f]);rows.append(row);continue
  verts=[Vector(v)for v in p];trees={n:BVHTree.FromPolygons(verts,faces[n])for n in ['arms','legs']};overlap=trees['arms'].overlap(trees['legs']);minimum=float('inf');witness=None
  for region,other in [('arms','legs'),('legs','arms')]:
   for i in sets[region]:
    near,normal,face,distance=trees[other].find_nearest(verts[i])
    if distance<minimum:minimum=distance;witness={'region':region,'source_id':i,'opposite_exported_triangle':face}
  areas=np.linalg.norm(np.cross(p[tri[:,1]]-p[tri[:,0]],p[tri[:,2]]-p[tri[:,0]]),axis=1)/2;m=c.support_metrics(p);foot={side:float(p[sorted(sets['foot_'+side]),2].min())for side in ['L','R']}
  if overlap or minimum<.0005:failures.append(f'frame{f}:decoded whole arm/hand versus leg clearance')
  if areas.min()<=1e-12:failures.append(f'frame{f}:nonpositive actual exported triangles')
  if m['whole_body_min_z_m']<-.00035 or m['profile_median_m']>.005 or m['profile_fraction_within5mm']<.5 or m['midline_profile_max_m']>.002 or m['ridge_max_z_m']>.002 or max(m['pelvic_min_m'].values())>.002:failures.append(f'frame{f}:decoded frozen posterior support contract')
  if min(foot.values())<.005:failures.append(f'frame{f}:decoded airborne foot/floor cue')
  row={'frame':f,'actual_decoded_arm_hand_leg_intersections':len(overlap),'minimum_arm_hand_leg_skin_clearance_m':minimum,'clearance_witness':witness,'minimum_actual_exported_triangle_area_m2':float(areas.min()),'nonpositive_triangles':int(np.sum(areas<=1e-12)),'airborne_foot_min_z_m':foot,**m};rows.append(row)
  if f%50==0:print('DECODED_PHYSICAL',eid,f,flush=True)
 if eid=='4826':shared=copy.deepcopy(rows)
 report={'id':eid,'ok':not failures,'failures':failures,'glb_sha256':sha,'source_sha256':export['source_sha256'],'sampled_frames':151,'original_vertices':10582,'exported_triangles':21160,'actual_exported_topology_sha256':hashlib.sha256((P/'.decoded-topology.json').read_bytes()).hexdigest(),'actual_decoded_position_stream_sha256':hashlib.sha256((P/f'.decoded-all151-{eid}.f64').read_bytes()).hexdigest(),'minimum_arm_hand_leg_skin_clearance_m':min(r['minimum_arm_hand_leg_skin_clearance_m']for r in rows),'minimum_triangle_area_m2':min(r['minimum_actual_exported_triangle_area_m2']for r in rows),'worst_floor_min_z_m':min(r['whole_body_min_z_m']for r in rows),'minimum_airborne_foot_clearance_m':min(z for r in rows for z in r['airborne_foot_min_z_m'].values()),'maximum_midline_profile_residual_m':max(r['midline_profile_max_m']for r in rows),'maximum_ridge_z_m':max(r['ridge_max_z_m']for r in rows),'identical_action_physics_reuse':({'from':'4826','all151_actual_decoded_skin_max_error_m':same_error}if eid=='3590'else None),'samples':rows,'scope':'Actual GLTFLoader + exact shared DQ probe all151 skin and actual exported triangles: strict frozen source-envelope/pelvic/floor QC, positive areas, whole arm/hand versus legs overlap and two-way vertex/triangle witnesses. No native surrogate or globally/continuous-time collision-free claim. GPU raster review remains root-owned.','transient_stream_delivered':False};(out/'decoded-physical-verification.json').write_text(json.dumps(report,indent=2)+'\n');print('DECODED_RESULT',eid,json.dumps({'ok':not failures,'failures':failures,'minimum_clearance_m':report['minimum_arm_hand_leg_skin_clearance_m']}),flush=True);assert not failures,failures
