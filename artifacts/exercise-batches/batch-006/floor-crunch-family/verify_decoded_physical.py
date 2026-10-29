"""Physical checks on actual decoded GLB/DQ positions and exported triangles."""
from pathlib import Path
import json,hashlib,bpy,numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
P=Path(__file__).resolve().parent;B=P.parent
tri=np.array(json.loads((P/'.decoded-topology.json').read_text()),np.int32);assert tri.shape==(21160,3)and tri.min()>=0 and tri.max()<10582
sets={n:set(v)for n,v in json.loads((P/'changed-candidate-check.json').read_text())['source_domains'].items()};faces={n:[row.tolist()for row in tri if all(int(i)in ids for i in row)]for n,ids in sets.items()};sha=hashlib.sha256((P/'motion.glb').read_bytes()).hexdigest()
for id in ['0006','4354']:
 out=B/'assets'/id;export=json.loads((out/'export-verification.json').read_text());assert export['ok']and export['sha256']==sha;landmarks=json.loads((out/'landmarks.json').read_text());points=np.memmap(P/f'.decoded-all151-{id}.f64',dtype='<f8',mode='r',shape=(151,10582,3));rows=[];failures=[];footdrift=0
 for f,p in enumerate(points):
  verts=[Vector(v)for v in p];trees={n:BVHTree.FromPolygons(verts,faces[n])for n in ['arms','legs']};overlap=trees['arms'].overlap(trees['legs']);minimum=float('inf');witness=None
  for region,other in [('arms','legs'),('legs','arms')]:
   for i in sets[region]:
    q,n,face,d=trees[other].find_nearest(verts[i])
    if d<minimum:minimum=d;witness={'region':region,'source_id':i,'opposite_exported_triangle':face}
  areas=np.linalg.norm(np.cross(p[tri[:,1]]-p[tri[:,0]],p[tri[:,2]]-p[tri[:,0]]),axis=1)*.5;metrics={}
  for n,v in landmarks['patches'].items():
   if v['state']!='supported':continue
   z=p[v['indices'],2];metric={'min_z':float(z.min()),'max_z':float(z.max()),'fraction_near_floor':float(np.mean(abs(z)<=.012))};metrics[n]=metric
   if metric['min_z']>.012 or metric['fraction_near_floor']<.2:failures.append(f'frame{f}:{n} unsupported')
  for suffix in ['L','R']:
   ids=sorted(sets['foot'+suffix]);footdrift=max(footdrift,float(np.linalg.norm(p[ids]-points[0,ids],axis=1).max()))
  if overlap or minimum<.0005:failures.append(f'frame{f}:decoded arm/hand versus leg clearance')
  if p[:,2].min()<-.004:failures.append(f'frame{f}:decoded floor')
  if np.min(areas)<=0:failures.append(f'frame{f}:decoded nonpositive triangle area')
  rows.append({'frame':f,'actual_decoded_arm_hand_leg_intersections':len(overlap),'minimum_sampled_arm_hand_leg_distance_m':minimum,'clearance_witness':witness,'floor_min_z_m':float(p[:,2].min()),'minimum_triangle_area_m2':float(areas.min()),'nonpositive_triangles':int(np.sum(areas<=0)),'supported_patches':metrics})
  if f%50==0:print('DECODED_PHYSICAL',id,f,flush=True)
 if footdrift>1e-5:failures.append('Decoded grounded foot skin drifts')
 report={'id':id,'ok':not failures,'failures':failures,'glb_sha256':sha,'source_sha256':export['source_sha256'],'sampled_frames':151,'original_vertices':10582,'exported_triangles':21160,'topology_sha256':hashlib.sha256((P/'.decoded-topology.json').read_bytes()).hexdigest(),'actual_decoded_position_stream_sha256':hashlib.sha256((P/f'.decoded-all151-{id}.f64').read_bytes()).hexdigest(),'maximum_fixed_foot_skin_drift_m':footdrift,'minimum_arm_hand_leg_skin_clearance_m':min(r['minimum_sampled_arm_hand_leg_distance_m']for r in rows),'minimum_triangle_area_m2':min(r['minimum_triangle_area_m2']for r in rows),'worst_floor_min_z_m':min(r['floor_min_z_m']for r in rows),'samples':rows,'scope':'Actual GLTFLoader+exact shared DQ CPU probe positions at all151frames, full float64 source-domain skin, and actual exported triangle indices. Whole arms/hands versus both complete lower-limb domains use triangle overlap and two-way vertex/triangle witnesses, plus direct floor/support/areas/foot-skin drift. No native-surrogate or generic linear-skin claim. GPU raster review remains root-owned; no continuous-time/global self-collision certification.','transient_stream_delivered':False}
 (out/'decoded-physical-verification.json').write_text(json.dumps(report,indent=2)+'\n');print('DECODED_RESULT',id,json.dumps({'ok':not failures,'failures':failures,'minimum_clearance_m':report['minimum_arm_hand_leg_skin_clearance_m']}),flush=True);assert not failures,failures
