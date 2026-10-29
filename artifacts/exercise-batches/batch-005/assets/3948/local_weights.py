"""Bounded source-coordinate weight diffusion at diagnosed hard joint boundaries."""
import numpy as np

def smooth(x):
 x=np.clip(x,0,1);return x*x*(3-2*x)
def band(x,lo,hi,feather):return smooth((x-lo)/feather)*(1-smooth((x-hi+feather)/feather))
def apply(body):
 R=np.array([v.co[:] for v in body.data.vertices]);names=[g.name for g in body.vertex_groups];W=np.zeros((len(R),len(names)))
 for v in body.data.vertices:
  for g in v.groups:W[v.index,g.group]=g.weight
 original=W.copy();E=np.array([e.vertices[:] for e in body.data.edges]);deg=np.bincount(E.ravel(),minlength=len(R));union=np.zeros(len(R),bool);domains=[]
 # Restore the earlier, visually better lower binding. No new weight trial.
 domains.append(('pelvis_thigh',band(R[:,2],.66,1.04,.08),['Hips','Spine','LeftUpLeg','RightUpLeg'],10,.45))
 for side,sign in [('Left',1),('Right',-1)]:
  blend=band(R[:,2],.38,.61,.055)*smooth((sign*R[:,0]-.04)/.06)
  domains.append((side+'_knee',blend,[side+'UpLeg',side+'Leg'],10,.45))
 rows=[]
 for label,blend,groups,iterations,mix in domains:
  cols=np.array([n in groups for n in names]);ids=np.flatnonzero(blend>1e-8);union[ids]=True
  for _ in range(iterations):
   summed=np.zeros_like(W);np.add.at(summed,E[:,0],W[E[:,1]]);np.add.at(summed,E[:,1],W[E[:,0]])
   mean=summed/np.maximum(deg,1)[:,None];W[:,cols]+=mix*blend[:,None]*(mean[:,cols]-W[:,cols]);W/=W.sum(axis=1)[:,None]
  rows.append({'domain':label,'source_indices':ids.tolist(),'bounds':[R[ids].min(0).tolist(),R[ids].max(0).tolist()],'groups':groups,'iterations':iterations,'mix':mix,'status':'Restored earlier visually better lower binding; new upper-hip envelope rejected.'})
 # Pinned graph-harmonic reconstruction replaces the diagnosed shoulder seam.
 # Original exterior vertices are exact Dirichlet conditions; solve the finite
 # vertex-star graph once, rather than running arbitrary diffusion iterations.
 for side,sign in [('Left',1),('Right',-1)]:
  mask=(sign*R[:,0]>.065)&(sign*R[:,0]<.40)&(R[:,2]>1.085)&(R[:,2]<1.535)
  armdir=np.array((.145*sign,-.015,-.27));armdir/=np.linalg.norm(armdir)
  station=(R-np.array((.18*sign,.035,1.43)))@armdir
  anchors=(original[:,names.index(side+'Arm')]>=.95)&(station>.16)
  mask &= ~anchors
  ids=np.flatnonzero(mask);lookup=np.full(len(R),-1,int);lookup[ids]=np.arange(len(ids));L=np.diag(deg[ids].astype(float));rhs=np.zeros((len(ids),len(names)))
  for u,v in E:
   for i,j in [(int(u),int(v)),(int(v),int(u))]:
    if lookup[i]<0:continue
    if lookup[j]>=0:L[lookup[i],lookup[j]]-=1
    else:rhs[lookup[i]]+=original[j]
  solution=np.linalg.solve(L,rhs);assert np.min(solution)>-1e-8
  residual=float(abs(L@solution-rhs).max());assert residual<1e-8
  W[ids]=np.maximum(solution,0);W[ids]/=W[ids].sum(1)[:,None];union[ids]=True
  rows.append({'domain':side+'_shoulder_harmonic','source_indices':ids.tolist(),'bounds':[R[ids].min(0).tolist(),R[ids].max(0).tolist()],'method':'Graph-harmonic Dirichlet solve on the original edge graph; all exterior original source weights and original distal rigid upper-arm core (Arm>=0.95 and longitudinal station>0.16m) pinned exactly. Four-influence projection after solve.','linear_residual':residual,'vertices':len(ids)})
 # Diagnosed original shin influence on plantar heel vertices lifts the heel
 # despite a fixed ankle. Blend only the distal original foot into its rigid
 # Foot transform; ToeBase has the same world transform in this squat.
 for side,sign in [('Left',1),('Right',-1)]:
  blend=(1-smooth((R[:,2]-.035)/.045))*smooth((sign*R[:,0]-.08)/.04)
  local=np.flatnonzero(blend>1e-8);union[local]=True
  target=np.zeros_like(W);target[:,names.index(side+'Foot')]=1
  W=W*(1-blend[:,None])+target*blend[:,None]
  rows.append({'domain':side+'_plantar_heel','source_indices':local.tolist(),'bounds':[R[local].min(0).tolist(),R[local].max(0).tolist()],'method':'Rigid Foot below sourceZ35mm, feather to80mm; excludes ankle and changes no coordinates.'})
 W[~union]=original[~union]
 ids=np.flatnonzero(union)
 for i in ids:
  row=W[i];keep=np.argsort(row)[-4:];row[np.setdiff1d(np.arange(len(row)),keep)]=0;row[row<.001]=0;row/=row.sum()
  for group_index in [g.group for g in body.data.vertices[int(i)].groups]:body.vertex_groups[group_index].remove([int(i)])
  for k in np.flatnonzero(row):body.vertex_groups[int(k)].add([int(i)],float(row[k]),'REPLACE')
 return {'purpose':'Source-bound hard shoulder/pelvis/knee weight discontinuities exposed by the diagnosed arms-forward parallel squat. DQ was rejected after direct unchanged-cage comparison.', 'method':'Pinned harmonic shoulder reconstruction and diagnosed bounded monotone hip/knee/plantar envelopes; source Basis, UV, topology and all51 bone rest matrices unchanged.', 'domains':rows,'affected_source_indices':ids.tolist(),'affected_vertices':len(ids),'maximum_weight_change':float(abs(W-original).max()),'unchanged_outside_neighborhood':bool(np.array_equal(W[~union],original[~union])),'maximum_influences':max(len(v.groups) for v in body.data.vertices),'maximum_normalization_error':max(abs(sum(g.weight for g in v.groups)-1) for v in body.data.vertices),'edits':[{'source_index':int(i),'original':{names[k]:float(original[i,k]) for k in np.flatnonzero(original[i])},'new':{body.vertex_groups[g.group].name:float(g.weight) for g in body.data.vertices[int(i)].groups}} for i in ids]}
