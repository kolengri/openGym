"""Solve one scalar separating-plane constraint for the authorized detour."""
from pathlib import Path
import math
from mathutils import Matrix
F=Path(__file__).resolve().parent
exec(compile((F/'build.py').read_text().split('soles=')[0],str(F/'build.py'),'exec'))
sys.path.append(str(Path.cwd()/'artifacts/mannequin-mpfb-prototype/local-topology-repair/dependencies/venv/lib/python3.13/site-packages'))
from scipy.optimize import brentq
from wrap_acquisition import ClearanceRoute,clearance_gain
route=ClearanceRoute(F/'coherent-route-coefficients.npz',0.)
b.data.calc_loop_triangles();tri=np.asarray([t.vertices[:]for t in b.data.loop_triangles]);names={g.index:g.name for g in b.vertex_groups};right=[];left=[]
for v in b.data.vertices:
 if sum(g.weight for g in v.groups if names[g.group]in['RightArm','RightForeArm'])>.5:right.append(v.index)
 if sum(g.weight for g in v.groups if names[g.group].startswith('Left')and any(x in names[g.group]for x in['Hand','Index','Middle','Ring','Little','Thumb']))>.5:left.append(v.index)
rt=tri[np.all(np.isin(tri,right),axis=1)];lt=tri[np.all(np.isin(tri,left),axis=1)];frames=np.arange(20.,25.01,.5).tolist();margin=.004;evaluations=[]
def skin(frame,amplitude):
 route.amplitude=amplitude;d,p=route.pose(frame)
 for pb in r.pose.bones:
  parent=pb.parent.name if pb.parent else None;rigid=Matrix.Translation(d[pb.name].translation)@d[pb.name].to_quaternion().normalized().to_matrix().to_4x4();relative=np.asarray(a.rest[parent],dtype=np.float64)@np.linalg.inv(np.asarray(d[parent],dtype=np.float64))if parent else np.eye(4);basis=np.linalg.inv(np.asarray(a.rest[pb.name],dtype=np.float64))@relative@np.asarray(rigid,dtype=np.float64);pb.matrix_basis=Matrix(basis.tolist())
 for key,value in zip(list(b.data.shape_keys.key_blocks)[1:],[0.,0.,p]):key.value=value
 bpy.context.view_layer.update();e=b.evaluated_get(bpy.context.evaluated_depsgraph_get());me=e.to_mesh();v=np.asarray([x.co[:]for x in me.vertices]);e.to_mesh_clear();return v
def constraint(amplitude,retain=False):
 rows=[]
 for frame in frames:
  v=skin(frame,amplitude);right=v[rt];left=v[lt];lo=right.min((0,1));hi=right.max((0,1));overlap=np.all(left.max(1)[:,[0,2]]>=lo[[0,2]],axis=1)&np.all(left.min(1)[:,[0,2]]<=hi[[0,2]],axis=1)
  if overlap.any():
   hand=left[overlap];hlo=hand.min((0,1));hhi=hand.max((0,1));near=np.all(right.max(1)[:,[0,2]]>=hlo[[0,2]],axis=1)&np.all(right.min(1)[:,[0,2]]<=hhi[[0,2]],axis=1)
   if near.any():front=float(right[near,:,1].min());violation=float(hand[:,:,1].max()-front+margin)
   else:front=None;violation=-margin
  else:front=None;violation=-margin
  rows.append({'frame':frame,'front_plane_y_m':front,'plane_violation_m':violation})
 value=max(x['plane_violation_m']for x in rows);evaluations.append({'amplitude_m':amplitude,'maximum_plane_violation_m':value})
 return (value,rows)if retain else value
limits=[]
for frame in np.arange(0.,37.01,.25):
 d,p=route.pose(frame);progress=min(1.,p/route.peak);gain=clearance_gain(progress)
 if gain<1e-8:continue
 sh=d['LeftArm'].translation;w=d['LeftHand'].translation;length=float(sum(route.data['Left_lengths']))-.002;radial=(w.x-sh.x)**2+(w.z-sh.z)**2;allowed=math.sqrt(max(0,length*length-radial))+w.y-sh.y;limits.append(allowed/gain)
upper=min(limits);start=constraint(0.);end=constraint(upper)
if end>0:
 report={'status':'No conservative wholehand separating-plane solution inside the fixed-length domain','maximum_reachable_amplitude_m':upper,'zero_offset_violation_m':start,'reachable_limit_violation_m':end,'evaluations':evaluations};(F/'wrist-detour-derivation.json').write_text(json.dumps(report,indent=2)+'\n');raise ValueError(report)
amplitude=brentq(constraint,0.,upper,xtol=.00005)+.001
value,rows=constraint(amplitude,True);report={'status':'One scalar geometric constraint solved; sparse exact triangle acceptance pending','amplitude_m':amplitude,'maximum_reachable_amplitude_m':upper,'clearance_margin_m':margin,'maximum_plane_violation_m':value,'constraint_frames':frames,'samples':rows,'evaluations':evaluations,'method':'Conservative wholehand triangle XZ overlap versus right upperarm/forearm front plane. Fixed arm lengths and frozen endpoint-corrected transported frames are recomputed for each candidate. Brent scalar root solves the smallest conservative anterior offset;1mm numeric margin added. No local hand rotation or independent finger change.'};(F/'wrist-detour-derivation.json').write_text(json.dumps(report,indent=2)+'\n');print('WRIST_DETOUR',json.dumps(report))
