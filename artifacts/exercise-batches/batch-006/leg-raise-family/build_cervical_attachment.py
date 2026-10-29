"""One compact C2-collared posterior cervical fairing on the frozen pose.

This surface remedy preserves the non-neutral supine cervical chain. It is not
an anatomical-rest pose reconstruction and does not move any floor anchor.
"""
import json,sys,hashlib,time
from pathlib import Path
import numpy as np,bpy
P=Path(__file__).resolve().parent;sys.path[:0]=[str(P),str(P.parents[2]/'mannequin-mpfb-prototype/local-topology-repair/dependencies/venv/lib/python3.13/site-packages')]
from scipy.sparse import coo_matrix,diags,eye
from scipy.sparse.linalg import spsolve
from mathutils import Vector
import family_common as c,support_fields as fields
start=time.monotonic();binding=c.initialize();a=c.a;support_receipt=fields.install(a.body);rest=np.array([v.co[:]for v in a.body.data.vertices]);before,meta=c.sample(0,'4826');n=len(rest)
# Anatomy bounds precede the fairing. These collar dimensions are one authored
# proposal, not a parameter sweep. Quintic smoothstep has zero first/second
# derivative at each collar end, hence the displacement is compact C2.
def smooth(t):
 t=np.clip(t,0,1);return t*t*t*(10+t*(-15+6*t))
collar=smooth((rest[:,2]-1.370)/.025)*smooth((1.515-rest[:,2])/.035)*smooth((rest[:,1]-.065)/.045)*smooth((.165-abs(rest[:,0]))/.045)
# Preserve all original support target vertices and exact original head/upperback
# floor anchors, including one source-edge ring around each floor anchor.
protected=set(json.loads((P/'support-domain.json').read_text())['source_ids'])
protected.update(int(i)for i in np.flatnonzero(before[:,2]<=.0025))
for e in a.body.data.edges:
 u,v=e.vertices
 if int(u)in protected or int(v)in protected:
  if before[int(u),2]<=.0025 or before[int(v),2]<=.0025:protected.update([int(u),int(v)])
# C2 radial collars around fixed anchors avoid merely pinning an isolated vertex.
for i in sorted(protected):
 if rest[i,2]>1.32:collar*=smooth(np.linalg.norm(rest-rest[i],axis=1)/.018)
collar[list(protected)]=0;ids=np.flatnonzero(collar>1e-12);assert len(ids)>0
neighbors=[[]for _ in range(n)]
for edge in a.body.data.edges:
 u,v=map(int,edge.vertices);neighbors[u].append(v);neighbors[v].append(u)
# Uniform graph Laplacian fairing keeps topology and boundaries exactly. The
# screened biharmonic solve has one fixed regularizer and no fitting iterations.
rows=[];cols=[];values=[]
for i,near in enumerate(neighbors):
 rows.append(i);cols.append(i);values.append(1.)
 for j in near:rows.append(i);cols.append(j);values.append(-1/len(near))
L=coo_matrix((values,(rows,cols)),shape=(n,n)).tocsr();D=diags(collar[ids]);A=L[:,ids]@D;regularizer=.035
u=spsolve(A.T@A+regularizer*eye(len(ids)), -A.T@(L@before));posed_delta=collar[ids,None]*u
uncapped=float(np.linalg.norm(posed_delta,axis=1).max());scale=min(1.,.008/uncapped);posed_delta*=scale
# DQ blends rigid rotations. At frozen flat-head pose a rest-space vector maps
# to world by this exact normalized blended rotation; inverse it once per ID.
source_delta=np.array([fields.rotation(a.body,a.rig,int(i),a.rest).inverted()@Vector(d)for i,d in zip(ids,posed_delta)],dtype=np.float32)
assert np.linalg.norm(source_delta,axis=1).max()<=.00800001
np.savez_compressed(P/'cervical-attachment.npz',source_ids=ids.astype(np.int32),source_basis=rest[ids].astype(np.float32),deltas=source_delta,collar=collar[ids].astype(np.float32))
input_hashes={name:hashlib.sha256((P/name).read_bytes()).hexdigest()for name in ['pose-parameters.json','support-fields.npz','source-neutral-envelope.json','source-support-masks.json','source-glute-binding.json','binding_core.py']}
report={'method':'One screened biharmonic fairing of native posed posterior cervical surface, source-anatomy C2 collar, global8mm cap; inverse blended DQ rotation gives one sparse source-space additive shape key. No pose/binding/floor support target changes.','status':'candidate_pending_actual_native_shape_and_root_review','pose':c.posture(),'source_domain_m':{'z':[1.370,1.515],'z_low_collar':.025,'z_high_collar':.035,'posterior_y_start':.065,'posterior_y_collar':.045,'absolute_x_end':.165,'x_collar':.045,'fixed_anchor_radial_collar':.018},'source_ids':ids.tolist(),'protected_source_ids':sorted(protected),'protected_source_coordinates_sha256_float64':hashlib.sha256(before[sorted(protected)].tobytes()).hexdigest(),'regularizer':regularizer,'uncapped_maximum_posed_delta_m':uncapped,'one_global_cap_scale':scale,'maximum_new_rest_delta_m':float(np.linalg.norm(source_delta,axis=1).max()),'maximum_new_posed_delta_m':float(np.linalg.norm(posed_delta,axis=1).max()),'new_key_name':'CervicalAttachment','new_key_weight':1.,'input_sha256':input_hashes,'binding_sha256':binding['runtime_binding_sha256'],'original_support_key_hashes':support_receipt,'source_topology_unchanged':True,'elapsed_seconds':time.monotonic()-start}
(P/'cervical-attachment-recipe.json').write_text(json.dumps(report,indent=2)+'\n');print('CERVICAL_ATTACHMENT_BUILT',json.dumps({k:report[k]for k in ['status','maximum_new_rest_delta_m','maximum_new_posed_delta_m','uncapped_maximum_posed_delta_m','one_global_cap_scale']}))
