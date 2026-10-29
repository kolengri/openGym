"""Safeguarded active-face/Newton continuation of one DQ protraction method."""
import bpy,json,sys,numpy as np,hashlib,math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
F=Path(__file__).resolve().parent;sys.path[:0]=[str(F),str(F.parent.parent/'batch-003')];import authoring as a,plantar_binding,motion
from self_clearance import SelfClearance
from triangle_intersection import intersect
a.initialize();plantar_binding.apply(a.body)
for m in a.body.modifiers:
 m.show_viewport=m.show_render=m.type=='ARMATURE'
 if m.type=='ARMATURE':m.use_deform_preserve_volume=True
assert next(m for m in a.body.modifiers if m.type=='ARMATURE').use_deform_preserve_volume
c=SelfClearance(a.body,a.rig);cache={};trace=[];MAX=24;TOL=.01;GUARD=35.;FRAMES=[37.5,112.5]
# One source-neighbor ring follows every newly active intersected face.
adj=[set()for v in a.body.data.vertices]
for edge in a.body.data.edges:
 i,j=edge.vertices;adj[i].add(j);adj[j].add(i)
def points(frame,angle):
 a.rig.animation_data_clear();d,_=motion.pose(a,frame,'5172',protraction_extra_degrees=angle-10);bpy.context.view_layer.update();error=max(float(np.max(abs(np.array(a.rig.pose.bones[n].matrix)-np.array(mat))))for n,mat in d.items());assert error<2e-6,error;e=a.body.evaluated_get(bpy.context.evaluated_depsgraph_get());me=e.to_mesh();p=np.array([v.co[:]for v in me.vertices]);e.to_mesh_clear();return p,d

def envelope(p,ids):
 v=[Vector(q)for q in p];tree=BVHTree.FromPolygons(v,c.torso,all_triangles=True);out={}
 for i in ids:
  q,_,_,_=tree.ray_cast(Vector((p[i,0],-3.,p[i,2])),Vector((0,1,0)),6.)
  if q is not None:out[i]=float(q.y-p[i,1])
 return out

def evaluate(angle):
 key=round(angle,10)
 if key in cache:return cache[key]
 rows=[];success=True
 for frame in FRAMES:
  p,d=points(frame,angle);metric,issues=c.sample(p);v=[Vector(q)for q in p];tree=BVHTree.FromPolygons(v,c.torso,all_triangles=True);active=set();pairs=[]
  for side in ['Left','Right']:
   faces=c.distal[side];arm=BVHTree.FromPolygons(v,faces,all_triangles=True)
   for ai,bi in arm.overlap(tree):
    A,B=faces[ai],c.torso[bi]
    if set(A)&set(B):continue
    if intersect([v[i]for i in A],[v[i]for i in B]):active.update(A);pairs.append([A,B])
  neighbors=active|set(j for i in active for j in adj[i]);rows.append({'frame':frame,'metrics':metric,'failures':issues,'active_source_faces':pairs,'active_and_neighbor_source_ids':sorted(neighbors),'anterior_envelope_clearance_m':envelope(p,neighbors)})
  success &=not issues
 result={'angle_degrees':angle,'pass':bool(success),'states':rows};cache[key]=result;trace.append(result);print('EVALUATE',angle,success,[(r['frame'],[v['exact_triangle_crossings']for v in r['metrics'].values()])for r in rows],flush=True);return result

def newton_angle(row):
 angle=row['angle_degrees'];probe=min(GUARD,angle+.5)
 if probe<=angle+1e-8:return GUARD
 needs=[]
 for state in row['states']:
  p,_=points(state['frame'],probe);q=envelope(p,state['active_and_neighbor_source_ids']);cur={int(i):v for i,v in state['anterior_envelope_clearance_m'].items()}
  for i,s0 in cur.items():
   if i not in q or s0>=.001:continue
   jac=(q[i]-s0)/(probe-angle)
   if jac>1e-7:needs.append((.001-s0)/jac)
 return angle+max(needs,default=.5)

lo=24.389722920983328;current=evaluate(lo);assert not current['pass']
# Boundary evaluation establishes a feasible bracket, not a preset parameter sweep.
upper=evaluate(GUARD);hi=GUARD if upper['pass']else None;candidate=current
if hi is not None:
 for iteration in range(MAX):
  if hi-lo<=TOL:break
  proposed=newton_angle(candidate)
  # Safeguard the finite-Jacobian step in the current feasible/infeasible bracket.
  if not(lo+.1*(hi-lo)<proposed<hi-.1*(hi-lo)):proposed=(lo+hi)/2
  candidate=evaluate(proposed)
  if candidate['pass']:hi=proposed
  else:lo=proposed
 best=evaluate(hi)
else:
 # The observed active constraints remain at the authored bound; no second kinematic method.
 best=upper
report={'status':'feasible_minimum_bracketed'if hi is not None else'no_feasible_candidate_within_authored_guard','method':'One scalar current-scapula protraction method with transported global wrists, nativeDQ, updated exact active faces+source neighbor ring, finite-Jacobian steps and safeguarded feasible-bracket bisection. No preset grid.','DQ_asserted':True,'all51_actual_desired_matrix_tolerance':2e-6,'iteration_cap':MAX,'angle_bracket_tolerance_degrees':TOL,'authored_guard_degrees':GUARD,'minimum_feasible_bracket_degrees':[lo,hi]if hi is not None else None,'chosen_peak_protraction_degrees':hi,'chosen_extra_degrees':None if hi is None else hi-10,'final':best,'trace':trace,'limits':'A bounded one-parameter numerical contact solve, not a clinical range or proof about arbitrary kinematic families.'}
(F/'protraction-continuation.json').write_text(json.dumps(report,indent=2)+'\n');print('FINAL',report['status'],report['chosen_peak_protraction_degrees'])
