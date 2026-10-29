"""Bounded candidate safety failure evidence; no geometry modifications."""
import sys,json
from pathlib import Path
import numpy as np
P=Path(__file__).resolve().parent;sys.path.insert(0,str(P));import family_common as c,support_fields as support,cervical_attachment as cervical
c.initialize();a=c.a;support.install(a.body);a.body.data.calc_loop_triangles();tri=np.array([t.vertices[:]for t in a.body.data.loop_triangles]);before,_=c.sample(0,'4001');cervical.install(a.body);after,_=c.sample(0,'4001')
def normals(v):return np.cross(v[tri[:,1]]-v[tri[:,0]],v[tri[:,2]]-v[tri[:,0]])
old=normals(before);new=normals(after);areas=np.linalg.norm(new,axis=1)/2;dots=np.sum(old*new,axis=1)/(np.linalg.norm(old,axis=1)*np.linalg.norm(new,axis=1));fail=np.flatnonzero((areas<=1e-12)|(dots<=0));rows=[{'triangle':int(i),'ids':tri[i].tolist(),'before_area_m2':float(np.linalg.norm(old[i])/2),'after_area_m2':float(areas[i]),'normal_dot':float(dots[i]),'source_m':[list(a.body.data.vertices[int(j)].co)for j in tri[i]],'before_m':before[tri[i]].tolist(),'after_m':after[tri[i]].tolist()}for i in fail]
# An analytic orientation bound of this SAME displacement field: dot(oldNormal,
# cross(e1+t*d1,e2+t*d2)) is a quadratic in t, so its earliest positive root
# bounds admissible global amplitude without any target/pose grid.
delta=after-before;e1=before[tri[:,1]]-before[tri[:,0]];e2=before[tri[:,2]]-before[tri[:,0]];d1=delta[tri[:,1]]-delta[tri[:,0]];d2=delta[tri[:,2]]-delta[tri[:,0]]
q2=np.sum(old*np.cross(d1,d2),axis=1);q1=np.sum(old*(np.cross(d1,e2)+np.cross(e1,d2)),axis=1);q0=np.sum(old*old,axis=1);roots=[]
for i,(aa,bb,cc)in enumerate(zip(q2,q1,q0)):
 rr=np.roots([aa,bb,cc])if abs(aa)>1e-25 else np.roots([bb,cc])if abs(bb)>1e-25 else []
 for r in rr:
  if abs(r.imag)<1e-8 and r.real>0:roots.append((float(r.real),i))
root=min(roots,default=(float('inf'),-1));report={'status':('current_candidate_failed_triangle_orientation'if rows else'current_sample_passes_triangle_orientation'),'frame':0,'id':'4001','minimum_actual_area_m2':float(areas.min()),'minimum_before_after_normal_dot':float(dots.min()),'failures':rows,'same_field_first_analytic_orientation_root_scale':root[0],'limiting_triangle':root[1],'limiting_triangle_ids':tri[root[1]].tolist()if root[1]>=0 else [],'safe_one_global_amplitude_scale_80percent_of_first_root':min(1.,.80*root[0]),'no_pose_or_field_direction_grid':True};(P/'cervical-head-up-safety-diagnosis.json').write_text(json.dumps(report,indent=2)+'\n');print('CERVICAL_SAFETY',json.dumps({k:v for k,v in report.items()if k!='failures'}));print('FAILURES',len(rows))
