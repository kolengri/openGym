"""One source-knee harmonic UpLeg/Leg reconstruction, with fixed exterior.

Causal input: mixed femur/shin weights cross20->80% over~30mm at the visible
cut cap. Solve a source-edge harmonic scalar across an anatomical knee collar;
retain original non-leg fields and use rigid thigh/shin cores. No pose fit.
"""
import sys,json
from pathlib import Path
import numpy as np
P=Path(__file__).resolve().parent
sys.path.insert(0,str(P.parents[2]/'mannequin-mpfb-prototype/local-topology-repair/dependencies/venv/lib/python3.13/site-packages'))
from scipy.sparse import lil_matrix
from scipy.sparse.linalg import spsolve

def smooth(a,b,x):
 t=np.clip((np.asarray(x)-a)/(b-a),0,1);return t*t*(3-2*t)
def apply(body):
 R=np.array([v.co[:]for v in body.data.vertices]);original=[{body.vertex_groups[g.group].name:float(g.weight)for g in v.groups}for v in body.data.vertices];adj=[{}for _ in R]
 for edge in body.data.edges:
  i,j=edge.vertices;w=1/max(np.linalg.norm(R[i]-R[j]),1e-7);adj[i][j]=w;adj[j][i]=w
 changes=[];domains=[]
 for side,sign in [('Left',1),('Right',-1)]:
  up=side+'UpLeg';leg=side+'Leg';total=np.array([r.get(up,0)+r.get(leg,0)for r in original]);old=np.array([r.get(up,0)/t if t>1e-10 else 0 for r,t in zip(original,total)])
  domain=set(np.flatnonzero((R[:,2]>.36)&(R[:,2]<.64)&(sign*R[:,0]>.025)&(sign*R[:,0]<.25)&(total>.99)).tolist())
  # Source-space collar, independent of current action/pose; boundary and
  # anatomically rigid cores are Dirichlet constraints, not optimized knobs.
  boundary={i for i in domain if any(j not in domain for j in adj[i])}
  shin={i for i in domain if R[i,2]<=.385};thigh={i for i in domain if R[i,2]>=.615}
  pinned=boundary|shin|thigh;unknown=sorted(domain-pinned);index={i:n for n,i in enumerate(unknown)}
  values=old.copy();values[list(shin)]=0;values[list(thigh)]=1
  A=lil_matrix((len(unknown),len(unknown)));rhs=np.zeros(len(unknown))
  for i in unknown:
   row=index[i]
   for j,w in adj[i].items():
    A[row,row]+=w
    if j in index:A[row,index[j]]-=w
    else:rhs[row]+=w*values[j]
  values[unknown]=spsolve(A.tocsr(),rhs);assert values[unknown].min()>=-1e-8 and values[unknown].max()<=1+1e-8
  mask=smooth(.36,.41,R[:,2])*(1-smooth(.59,.64,R[:,2]))
  for i in sorted(domain):
   ratio=float(np.clip(old[i]+mask[i]*(values[i]-old[i]),0,1));before=original[i];after={n:w for n,w in before.items()if n not in [up,leg]}
   if ratio>1e-8:after[up]=float(total[i]*ratio)
   if 1-ratio>1e-8:after[leg]=float(total[i]*(1-ratio))
   if max(abs(after.get(n,0)-before.get(n,0))for n in set(after)|set(before))<1e-8:continue
   norm=sum(after.values());after={n:w/norm for n,w in after.items()};assert len(after)<=4
   for name in before:body.vertex_groups[name].remove([i])
   for name,value in after.items():body.vertex_groups[name].add([i],value,'REPLACE')
   observed={body.vertex_groups[g.group].name:float(g.weight)for g in body.data.vertices[i].groups};changes.append({'id':i,'source_m':R[i].tolist(),'before':before,'after':observed,'harmonic_upLeg_fraction':float(values[i]),'C1_collar_weight':float(mask[i])})
  domains.append({'side':side,'domain_ids':sorted(domain),'pinned_boundary_ids':sorted(boundary),'rigid_shin_core_ids':sorted(shin),'rigid_thigh_core_ids':sorted(thigh),'unknown_ids':unknown,'graph':'Original source edges with positive inverse length weights','source_z_bounds_m':[.36,.64],'C1_zero_to_full_collars_m':[[.36,.41],[.59,.64]]})
 current=[{body.vertex_groups[g.group].name:float(g.weight)for g in v.groups}for v in body.data.vertices];changed={r['id']for r in changes};assert all(current[i]==original[i]for i in range(len(R))if i not in changed);assert max(map(len,current))<=4;assert max(abs(sum(w.values())-1)for w in current)<2e-6
 report={'method':__doc__,'changed_ids':sorted(changed),'changes':changes,'domains':domains,'outside_exact':True,'basis_rest_uv_untouched':True,'maximum_influences':max(map(len,current)),'maximum_actual_weight_sum_error':max(abs(sum(w.values())-1)for w in current),'pose_parameter_fit':False,'rejected_component':'25mm KneeVolume corrective removed; unbounded62mm smoothing not promoted.'}
 (P/'knee-binding-receipt.json').write_text(json.dumps(report,indent=2)+'\n');return report
