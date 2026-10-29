"""Compile one local harmonic ownership reconstruction into a bounded pose target.

Virtual influences are construction data only. The canonical binding is untouched.
"""
from pathlib import Path
import json,hashlib
import numpy as np
import scipy.sparse as sp
from scipy.sparse.linalg import spsolve
from scipy.sparse.csgraph import dijkstra
from scipy.spatial.transform import Rotation
import igl
F=Path(__file__).resolve().parent
D=np.load(F/'capture.npz');META=json.loads((F/'capture.json').read_text());R=D['rest'].astype(float);T=D['triangles'];W=D['weights'];P=D['positions'][-1];names=META['bones'];N=len(R)
assert hashlib.sha256((F/'capture.npz').read_bytes()).hexdigest()==META['capture_npz_sha256'],'Stale capture metadata/data pairing'
assert hashlib.sha256((F/'inputs-contact/source.blend').read_bytes()).hexdigest()==META['source_sha256'],'Wrong frozen source'
def smooth(t):
 t=np.clip(t,0.,1.);return t*t*(3.-2.*t)
def dq(matrices,weights):
 qr=Rotation.from_matrix(matrices[:,:3,:3]).as_quat();v=matrices[:,:3,3];qd=np.c_[(qr[:,3,None]*v+np.cross(v,qr[:,:3]))*.5,-(v*qr[:,:3]).sum(1)*.5]
 ref=qr[np.argmax(weights,axis=1)];sign=np.where(ref@qr.T<0.,-1.,1.);rr=(weights*sign)@qr;dd=(weights*sign)@qd;norm=np.linalg.norm(rr,axis=1);rr/=norm[:,None];dd/=norm[:,None]
 translation=2.*(rr[:,3,None]*dd[:,:3]-dd[:,3,None]*rr[:,:3]+np.cross(rr[:,:3],dd[:,:3]));return Rotation.from_quat(rr),translation,norm
E=np.unique(np.sort(np.concatenate([T[:,[0,1]],T[:,[1,2]],T[:,[2,0]]]),axis=1),axis=0);length=np.linalg.norm(R[E[:,0]]-R[E[:,1]],axis=1);G=sp.csr_matrix((np.r_[length,length],(np.r_[E[:,0],E[:,1]],np.r_[E[:,1],E[:,0]])),shape=(N,N));ratio=np.linalg.norm(P[E[:,0]]-P[E[:,1]],axis=1)/length;mid=R[E].mean(1);jump=np.abs(W[E[:,0]]-W[E[:,1]]).sum(1)
cliff=(ratio>2.5)&(np.linalg.norm(P[E[:,0]]-P[E[:,1]],axis=1)>.035)&(jump>.65)&(mid[:,2]>1.23)&(mid[:,2]<1.52)&(abs(mid[:,0])>.09)&(abs(mid[:,0])<.32)
seed=np.unique(E[cliff]);assert len(seed)>40,len(seed)
geodesic=dijkstra(G,directed=False,indices=seed,min_only=True)
# This compact C1 collar follows the measured source-edge ownership cliff.
mask=1.-smooth((geodesic-.015)/.135)
protected=np.zeros(N,bool)
for side in ['Left','Right']:
 armnames=[j for j,n in enumerate(names)if n.startswith(side)and any(k in n for k in ['Arm','ForeArm','Hand','Index','Middle','Ring','Little','Thumb'])]
 h=D['bone_heads'][names.index(side+'Arm')];tail=D['bone_tails'][names.index(side+'Arm')];axis=tail-h;u=(R-h)@axis/(axis@axis)
 hand=[j for j,n in enumerate(names)if n.startswith(side)and any(k in n for k in ['Hand','Index','Middle','Ring','Little','Thumb'])]
 protected|=(W[:,armnames].sum(1)>.5)&(u>.85)
 protected|=W[:,hand].sum(1)>.001
neck=[names.index(n)for n in ['Neck','Head']];lower=[j for j,n in enumerate(names)if n=='Hips' or any(k in n for k in ['UpLeg','Leg','Foot','Toe'])]
anatomical_neck=((R[:,0]/.085)**2+((R[:,1]-.025)/.085)**2<1.)&(R[:,2]>1.48)
protected|=anatomical_neck|(W[:,lower].sum(1)>.001)|(R[:,2]<1.13)|(R[:,2]>1.54)
# Preserve actual/anticipated back contact triangles, not a semantic line seam.
contact=json.loads((F/'held-contact.json').read_text());contact_seeds=set(contact['protected_body_contact_seed_source_ids'])
for palm in contact['palms']:
 for hit in palm['closest'][:8]:contact_seeds.update(hit['body_source_triangle'])
contact_seeds=np.array(sorted(contact_seeds),int)
# Keep a triangulated POSITION collar. Original quad cofaces can contribute
# legitimate geometric NORMAL-only boundary changes, recorded by finalize.py.
ring=protected.copy();touch=protected[E].any(1);ring[np.unique(E[touch])]=True
protected_geo=dijkstra(G,directed=False,indices=np.flatnonzero(ring),min_only=True)
mask*=smooth((protected_geo-.004)/.030);mask[ring]=0.;ids=np.flatnonzero(mask>1e-12);outside=np.flatnonzero(mask<=1e-12);mask[outside]=0.
# Positive cotangent screened harmonic ownership; no rest/posed geometry smoothing.
L=igl.cotmatrix(R,T).tocsr();off=L-sp.diags(L.diagonal());off.data=np.maximum(off.data,0.);A=sp.diags(np.asarray(off.sum(1)).ravel())-off;mass=igl.massmatrix(R,T,igl.MASSMATRIX_TYPE_BARYCENTRIC).diagonal();screen=mass/(.035**2);H=A+sp.diags(screen)
field=W.copy();rhs=screen[ids,None]*W[ids]-H[ids][:,outside]@W[outside];field[ids]=spsolve(H[ids][:,ids].tocsc(),rhs);field=np.maximum(field,0.);field/=field.sum(1)[:,None]
q,tr,norm=dq(D['matrices'][-1],W);base=q.apply(R)+tr;native_error=float(np.linalg.norm(base-P,axis=1).max());assert native_error<1e-5,native_error

def compile_strength(strength):
 virtual=W+(field-W)*(mask*strength)[:,None];virtual/=virtual.sum(1)[:,None];qv,tv,_=dq(D['matrices'][-1],virtual);target=qv.apply(R)+tv;target[outside]=base[outside];world=target-base;rest_delta=q.inv().apply(world);rest_delta[outside]=0.;return virtual,target,rest_delta
virtual,target,delta=compile_strength(1.);raw_bound=float(np.linalg.norm(delta,axis=1).max());strength=1.
if raw_bound>.175:
 low,high=0.,1.
 for _ in range(30):
  mid=(low+high)*.5;vv,tt,dd=compile_strength(mid)
  if np.linalg.norm(dd,axis=1).max()<=.175:low=mid
  else:high=mid
 strength=low;virtual,target,delta=compile_strength(strength)
# Reconstruct transported rest-edge differentials, rather than shrinking the
# posed surface. This removes residual translation cliffs while retaining
# intrinsic shoulder/chest edge scale and the virtual anatomical rotation field.
qv,tv,_=dq(D['matrices'][-1],virtual);edge_rotation=(qv[E[:,0]].apply(R[E[:,0]]-R[E[:,1]])+qv[E[:,1]].apply(R[E[:,0]]-R[E[:,1]]))*.5
edge_weight=np.asarray(off[E[:,0],E[:,1]]).ravel();divergence=np.zeros_like(R);np.add.at(divergence,E[:,0],edge_rotation*edge_weight[:,None]);np.add.at(divergence,E[:,1],-edge_rotation*edge_weight[:,None]);differential_H=A+sp.diags(mass/(.055**2));fair_delta=np.zeros_like(R);fair_delta[ids]=spsolve(differential_H[ids][:,ids].tocsc(),(divergence-A@target)[ids]);target+=fair_delta*mask[:,None]
# Add unilateral contact fairness only against exact protected distal skin.
from contact_fairness import reconstruct,ContactAnchors
C=np.load(F/'clearance-domains.npz');domains={key:C[key]for key in C.files};contact_stiffness=A+sp.diags(mass/(.025**2));unconstrained_target=target.copy();anchors=ContactAnchors(P,target,mask,ids,contact_stiffness,contact,D['normals'][-1]);target=anchors.align(target);target,contact_iterations=reconstruct(target,base,T,domains,mask,protected,contact_stiffness,ids,anchors=anchors);anchor_evidence=anchors.evidence(target);delta=q.inv().apply(target-base);delta[outside]=0.
assert np.linalg.norm(delta,axis=1).max()<=.175000001,('Contact target exceeds authorized175mm',float(np.linalg.norm(delta,axis=1).max()))
np.savez_compressed(F/'target-position.npz',source_ids=ids.astype(np.int32),source_basis=R[ids].astype(np.float32),rest_deltas=delta[ids].astype(np.float32),posed_target=target[ids].astype(np.float32),mask=mask[ids].astype(np.float32),virtual_weights=virtual[ids].astype(np.float32),protected_source_ids=np.flatnonzero(protected).astype(np.int32),protected_normal_ring_source_ids=np.flatnonzero(ring).astype(np.int32),contact_source_ids=contact_seeds.astype(np.int32),contact_anchor_source_triangles=np.array([a['triangle']for a in anchors.anchors],np.int32),contact_anchor_barycentric=np.array([a['barycentric']for a in anchors.anchors]),contact_anchor_world_points=np.array([a['point']for a in anchors.anchors]),contact_anchor_world_normals=np.array([a['normal']for a in anchors.anchors]),ownership_cliff_seed_source_ids=seed.astype(np.int32),source_geodesic_m=geodesic[ids].astype(np.float32))
# Keep all tests explicit: support is allowed to repair cuffs, not hands/limbs.
assert np.max(np.linalg.norm(delta[protected],axis=1))==0.
report={'source_sha256':META['source_sha256'],'transported_rest_edge_fairness_maximum_delta_m':float(np.linalg.norm(fair_delta*mask[:,None],axis=1).max()),'contact_anchor_evidence':anchor_evidence,'contact_fairness_iterations':contact_iterations,'contact_fairness_maximum_added_delta_m':float(np.linalg.norm(target-unconstrained_target,axis=1).max()),'method':'Local positive-cotangent screened harmonic VIRTUAL influence reconstruction (35mm length), compact C1 graph-geodesic collar (15..150mm) around measured ownership-cliff edges; immutable protected/contact handles and topological NORMAL ring, C1 protected-distance feather4..34mm. Compile changed DQ deformation into a pose-only inverse-native-unit-DQ POSITION target. Canonical weights and geometry remain exact. No geometric shrink/smoothing/caps or global field.','seed_edges':int(cliff.sum()),'seed_source_ids':seed.tolist(),'cliff_edge_stretch_before_max':float(ratio[cliff].max()),'position_source_ids':ids.tolist(),'position_source_count':len(ids),'protected_source_ids':np.flatnonzero(protected).tolist(),'protected_normal_ring_source_ids':np.flatnonzero(ring).tolist(),'contact_source_ids':contact_seeds.tolist(),'full_strength_needed_max_delta_m':raw_bound,'construction_strength':strength,'maximum_rest_delta_m':float(np.linalg.norm(delta,axis=1).max()),'maximum_world_delta_m':float(np.linalg.norm(target-base,axis=1).max()),'source_delta_budget_m':.175,'native_DQ_forward_maximum_error_m':native_error,'minimum_native_DQ_blend_norm':float(norm[ids].min()),'inverse_rotation_condition_number':1.,'protected_position_delta_m':0.,'exterior_position_delta_m':0.,'archive_sha256':hashlib.sha256((F/'target-position.npz').read_bytes()).hexdigest()}
(F/'construction.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items()if not isinstance(v,list)},indent=2))
