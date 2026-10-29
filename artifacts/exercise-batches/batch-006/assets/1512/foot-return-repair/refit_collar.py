"""One compact, constrained re-fit against the corrected actual collar skin.

Only hand placement/roll and digit angles vary. Foot transport, body geometry,
weights, joint lengths and staging remain frozen. Numerical candidates outside
arm reach are penalized; source building always enforces exact connected reach.
"""
import sys,json,math,time
from pathlib import Path
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent;A=P.parent
sys.path.insert(0,str(A));sys.path.append(str(A.parents[3]/'mannequin-mpfb-prototype/local-topology-repair/dependencies/venv/lib/python3.13/site-packages'))
import bpy,numpy as np
from scipy.optimize import least_squares
from mathutils import Vector
from mathutils.bvhtree import BVHTree
import build_motion as build
build.prepare(False);a=build.a;b=a.body;r=a.rig
names={g.index:g.name for g in b.vertex_groups}
def ids(prefixes):return [v.index for v in b.data.vertices if sum(g.weight for g in v.groups if names[g.group].startswith(tuple(prefixes)))>.5]
parts={digit:ids(['Left'+digit])for digit in ['Hand','Thumb','Index','Middle','Ring','Little']};hand=sorted({i for values in parts.values()for i in values})
leg=set(ids(['LeftUpLeg','LeftLeg','LeftFoot','LeftToeBase']));foot={i for i in leg if b.data.vertices[i].co.z<.22}
faces=[list(p.vertices)for p in b.data.polygons if all(i in leg for i in p.vertices)]
footfaces=[list(p.vertices)for p in b.data.polygons if all(i in foot for i in p.vertices)]
def apply(t):
 d,_=build.pose(t,enforce_reach=False);build.apply(d);u=build.leg_amount(t)
 for name,w in zip(['LocalStart','LocalEntry','LocalHold'],[max(0,1-2*u),1-abs(2*u-1),max(0,2*u-1)]):b.data.shape_keys.key_blocks[name].value=w
 bpy.context.view_layer.update();return d
times=[1.10,1.20,1.30,2.0]
trees={}
for t in times:
 apply(t);pos=build.coords();trees[t]=(BVHTree.FromPolygons([Vector(p)for p in pos],faces),BVHTree.FromPolygons([Vector(p)for p in pos],footfaces))
# Recorded starting parameters from the rejected collapsed-collar fit.
base=np.array([.27694025034626746,.2624512104545332,.4995693933634437,0,.9537739320043801,0,-.3,7.801586255860871,1.4967909102011283,-.3,8.132767960334201,4.6315574936040536,-.3,8.171365831357866,5.657086474774548,-.3,4.773199851053538,6.511006088188439,1.2270500801524582,1.9148190786196064,1.6298194026296104,3.0406557748223295],float)
active=[0,1,2,4]+list(range(6,22));initial=base[active].copy()
lower=np.array([-.2,-2,-2,-2]+[-.5,0,0]*4+[-2,0,0]+[-5],float)
upper=np.array([1.5,2,2,2]+[8,10,7]*4+[5,7,6]+[6],float)
def expand(x):
 values=base.copy();values[active]=x;return values
calls=0;start=time.monotonic();best=[float('inf'),None]
def residual(x):
 global calls
 calls+=1;build.configure_fit(expand(x));build.shift_transport_grasp();result=[]
 for t in times:
  d=apply(t);pos=build.coords();tree,ftree=trees[t];signed={};dist={}
  for i in hand:
   p=Vector(pos[i]);q,n,_,distance=tree.find_nearest(p);signed[i]=(p-q).dot(n)if distance<.06 else distance
   dist[i]=ftree.find_nearest(p)[3]
  result.extend(max(0,.001-signed[i])*12 for i in hand)
  if t>=1.3:
   result.extend([max(0,min(dist[i]for i in parts['Hand'])-.003)*8,max(0,min(dist[i]for i in parts['Thumb'])-.003)*6,max(0,min(dist[i]for name in ['Index','Middle']for i in parts[name])-.004)*6])
   target=(d['LeftFoot']@build.GRIP_REL).translation;reach=(target-build.shoulder(d,'Left')).length;limit=a.length['LeftArm']+a.length['LeftForeArm']-.004
   result.append(max(0,reach-limit)*30)
   elbow,wrist,palm=[r.pose.bones[n].head for n in ['LeftForeArm','LeftHand','LeftMiddle1']];deviation=math.degrees((wrist-elbow).angle(palm-wrist));result.append(max(0,deviation-22)*.003)
 # Curvature/parameter regularization keeps unsupported digits shaped and
 # favors the existing source articulation when clearance permits it.
 result.extend((x-initial)*.00008)
 arr=np.array(result);loss=float(arr@arr)
 if loss<best[0]:best[:]=[loss,x.copy()]
 if calls%200==0:print('COLLAR_FIT',calls,round(loss,7),round(time.monotonic()-start,1),flush=True)
 return arr
baseline=residual(initial)
def jacobian(x):
 columns=[]
 for i in range(len(x)):
  step=.02;plus=x.copy();minus=x.copy();plus[i]+=step;minus[i]-=step;columns.append((residual(plus)-residual(minus))/(2*step))
 return np.column_stack(columns)
fit=least_squares(residual,initial,jac=jacobian,bounds=(lower,upper),max_nfev=35,ftol=1e-6,xtol=1e-5,gtol=1e-7)
x=best[1];final=residual(x)
report={'method':'One authorized constrained SciPy least_squares re-fit of corrected-collar hand placement/roll and digit angles; actual whole-hand DQ skin against complete leg and foot collar. No grid, body warp, geometry/weight/foot-path change.','parameters':expand(x).tolist(),'active_parameter_indices':active,'accepted':False,'parameter_units':'Translations10mm; rotations10degrees. Same22parameter layout as the recorded source fit.','bounds':{'lower':lower.tolist(),'upper':upper.tolist()},'times_seconds':times,'contact_contract':'Meaningful palm + thumb + index/middle contact; other digits curved outside skin. No requirement that every digit be within5mm.','baseline_residual_squared':float(baseline@baseline),'final_residual_squared':float(final@final),'solver_success':bool(fit.success),'solver_message':fit.message,'function_calls':calls,'elapsed_seconds':time.monotonic()-start,'acceptance':'One numerical result only; actual saved reach, whole-cycle signed clearance, triangle intersections and close proof determine acceptance.'}
(A/'grip-pose-fit.json').write_text(json.dumps(report,indent=2)+'\n');(P/'corrected-collar-fit.json').write_text(json.dumps(report,indent=2)+'\n');print('COLLAR_FIT_DONE',json.dumps(report),flush=True)
