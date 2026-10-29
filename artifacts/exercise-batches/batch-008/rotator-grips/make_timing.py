"""Redistribute the same1986 spatial path into a C1 two-second entry parameter."""
import bpy,sys,json,math,numpy as np,hashlib
from pathlib import Path
sys.dont_write_bytecode=True
F=Path(__file__).resolve().parent;sys.path[:0]=[str(F),str(F.parent.parent/'batch-003'),str(F.parents[2]/'mannequin-mpfb-prototype/local-topology-repair/dependencies/venv/lib/python3.13/site-packages')]
from scipy.interpolate import PchipInterpolator,CubicHermiteSpline
import authoring as a
a.initialize();import motion
n=1200;ts=np.linspace(0,2,n+1);cost=[0.];previous=None
for t in ts:
 d=motion.overhead_raw(a,float(t));q={name:m.to_quaternion()for name,m in d.items()};heads=np.array([m.translation[:]for m in d.values()]);tails=np.array([(m@a.rest[name].inverted()@a.tails[name])[:]for name,m in d.items()])
 if previous is not None:
  pq,ph,pt=previous;angle=max(min((x:=pq[name].rotation_difference(q[name]).angle),2*math.pi-x)for name in q);displacement=max(np.linalg.norm(heads-ph,axis=1).max(),np.linalg.norm(tails-pt,axis=1).max());cost.append(max(float(angle),float(displacement)/.15,1e-10))
 previous=q,heads,tails
cumulative=np.cumsum(cost);progress=cumulative/cumulative[-1];inverse=PchipInterpolator(progress,ts);knots=np.arange(61)/30
#150ms raised-cosine acceleration/deceleration, with a constant middle rate.
def ease_progress(t):
 u=t/2;r=.075;v=1/(1-r)
 if u<r:return v*(u/2-r/(2*math.pi)*math.sin(math.pi*u/r))
 if u>1-r:return 1-ease_progress(2*(1-u))
 return v*(u-r/2)
values=inverse([ease_progress(t)for t in knots]);curve=PchipInterpolator(knots,values);slopes=curve.derivative()(knots);slopes[[0,-1]]=0;compiled=CubicHermiteSpline(knots,values,slopes)
report={'scope':'Authoring-only scalar time-parameter curve; original1986 spatial route/binding and15mm clearance bulge unchanged. Not a runtime vertex/frame cache.1987 untouched. Hold2..3s exact; return mirrors entry.','method':'Fine1200-step path cost=max(maximum51-bone angular change radians, maximum head/tail displacement divided by0.15m). Inverse monotone path coordinate redistributes time.150ms raised-cosine start/finish rate ramps; constant middle rate. SciPy PCHIP inverse plus C1 cubic Hermite clock with exact zero endpoint slopes. Coefficients are compiled authoring parameters.','source_sha256':a.SOURCE_SHA,'baseline_source_sha256':hashlib.sha256((F/'timing-baseline/source.blend').read_bytes()).hexdigest(),'duration_seconds':2,'path_cost':float(cumulative[-1]),'knots_seconds':knots.tolist(),'base_path_seconds':values.tolist(),'endpoint_slopes':slopes[[0,-1]].tolist(),'cubic_coefficients':compiled.c.tolist()};(F/'entry-timing.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'path_cost':report['path_cost'],'base_tau_at_real_1s':float(compiled(1)),'base_tau_at_real_1_33s':float(compiled(40/30)),'endpoint_slopes':report['endpoint_slopes']}))
