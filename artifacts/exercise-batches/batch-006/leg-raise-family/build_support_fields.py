"""One minimal C2 support construction for the settled new lying-leg poses."""
import json,sys,hashlib,time
from pathlib import Path
import numpy as np
P=Path(__file__).resolve().parent
sys.path[:0]=[str(P),str(P.parents[2]/'mannequin-mpfb-prototype/local-topology-repair/dependencies/venv/lib/python3.13/site-packages')]
from scipy import sparse
from scipy.optimize import linprog
from mathutils import Vector
import family_common as c,support_fields as fields
binding=c.initialize();a=c.a;rest=np.array([v.co[:]for v in a.body.data.vertices]);profile=c.PROFILE;neutral,_=c.sample(0,'4826');pelvic={side:min(c.MASKS['pelvic_support_'+side],key=lambda i:neutral[i,2])for side in ['L','R']};qc=sorted(set(profile['lower_midline_ids']+profile['direct_ridge_ids']));centers=sorted(set(qc+list(pelvic.values())));radii=np.array([.070,.055,.055]);distance=np.linalg.norm((rest[:,None,:]-rest[centers][None,:,:])/radii,axis=2);kernel=np.where(distance<1,(1-distance)**4*(4*distance+1),0.);ids=np.flatnonzero(np.any(kernel>1e-12,axis=1));K=kernel[ids];lookup={int(i):j for j,i in enumerate(ids)};nc=len(centers);nv=3*nc+1
(P/'support-domain.json').write_text(json.dumps({'method':'New pose-specific compact Wendland C2 source field, selected before fitting. The old bicycle targets/protected97 are not reused. Centers are frozen lower-midline/ridge IDs plus minimum vertex of each original pelvic4-ID patch at the settled neutral47degree leg pose.','source_ids':ids.tolist(),'centers':centers,'pelvic_anchors':pelvic,'radii_m':radii.tolist(),'bounds_m':{'min':rest[ids].min(axis=0).tolist(),'max':rest[ids].max(axis=0).tolist()},'source_profile_sha256':hashlib.sha256((P/'source-neutral-envelope.json').read_bytes()).hexdigest()},indent=2)+'\n')
output={'source_ids':ids.astype(np.int32),'source_basis':rest[ids].astype(np.float32)};records={}
for group,eid in [('raise','4826'),('toe','5106')]:
 up=[]
 for f in [0.,37.5,112.5]:
  c.sample(f,eid);up.append(np.array([(fields.rotation(a.body,a.rig,int(i),a.rest).inverted()@Vector((0,0,1)))[:]for i in ids]))
 up=np.array(up);matrices=[];rhs=[]
 for state in range(3):
  block=np.zeros((len(ids),nv));block[:,state*nc:(state+1)*nc]=K;block[:,-1]=-1;matrices.append(sparse.csr_matrix(block));rhs.append(np.zeros(len(ids)));negative=block.copy();negative[:,state*nc:(state+1)*nc]*=-1;matrices.append(sparse.csr_matrix(negative));rhs.append(np.zeros(len(ids)))
 outside_min=1.;baseline=[]
 for f in range(151):
  p,meta=c.sample(f,eid);outside=np.ones(len(p),bool);outside[ids]=False;outside_min=min(outside_min,float(p[outside,2].min()));assert p[outside,2].min()>=-.00025,(eid,f,'Outside compact support domain',p[outside,2].min())
  w=fields.schedule(f);sensitivity=np.empty((len(ids),3))
  for j,i in enumerate(ids):
   q=fields.rotation(a.body,a.rig,int(i),a.rest)
   for state in range(3):sensitivity[j,state]=(q@Vector(up[state,j])).z*w[state]
  B=np.hstack([K*sensitivity[:,state,None]for state in range(3)]);block=np.zeros((len(ids),nv));block[:,:-1]=-B;matrices.append(sparse.csr_matrix(block));rhs.append((p[ids,2]+.00025)*1000)
  for i in qc+list(pelvic.values()):
   d=profile['expected_neutral_groove_depth_m'].get(str(i),0.)if i in qc else 0.;lo=d-.00025;hi=d+.00175
   if i in pelvic.values():lo=.00025
   block=np.zeros((2,nv));block[0,:-1]=B[lookup[i]];block[1,:-1]=-B[lookup[i]];matrices.append(sparse.csr_matrix(block));rhs.append(np.array([(hi-p[i,2])*1000,(p[i,2]-lo)*1000]))
  baseline.append({'frame':f,**c.support_metrics(p)})
 objective=np.zeros(nv);objective[-1]=1;A=sparse.vstack(matrices,format='csr');b=np.concatenate(rhs);result=linprog(objective,A_ub=A,b_ub=b,bounds=[(-50,50)]*(nv-1)+[(0,8)],method='highs');assert result.success,(group,result.message)
 coefficients=result.x[:-1].reshape(3,nc);scalar=coefficients@K.T/1000;delta=up*scalar[:,:,None];assert np.linalg.norm(delta,axis=2).max()<=.008001;output[group+'_deltas']=delta.astype(np.float32)
 records[group]={'exercise_ids':['4826','3590','4001']if group=='raise'else['5106'],'method':'One all151-frame linear minimax C2 field with exact native unit-DQ sensitivities. New canonical source has no inherited joint/flank target. Constant root/settled pose/binding stay fixed. No per-frame position cache.','success':bool(result.success),'message':result.message,'maximum_new_rest_delta_m':float(np.linalg.norm(delta,axis=2).max()),'coefficient_mm':coefficients.tolist(),'max_constraint_excess_mm':float(np.max(A@result.x-b)),'outside_domain_min_z_m':outside_min,'baseline_metrics':baseline}
 print('SUPPORT_FIELD',group,json.dumps({k:v for k,v in records[group].items()if k not in ['coefficient_mm','baseline_metrics']}),flush=True)
np.savez_compressed(P/'support-fields.npz',**output)
(P/'support-field-receipt.json').write_text(json.dumps({'source_basis_sha256':hashlib.sha256(rest.astype(np.float32).tobytes()).hexdigest(),'binding':binding,'pose':c.posture(),'profile_sha256':hashlib.sha256((P/'source-neutral-envelope.json').read_bytes()).hexdigest(),'target_npz_sha256':hashlib.sha256((P/'support-fields.npz').read_bytes()).hexdigest(),'families':records},indent=2)+'\n')
