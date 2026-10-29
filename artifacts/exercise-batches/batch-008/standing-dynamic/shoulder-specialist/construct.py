"""Pose-only shoulder ownership field; no smoothing of rest or posed geometry."""
from pathlib import Path
import numpy as np,json,hashlib
import scipy.sparse as sp
from scipy.sparse.linalg import spsolve
from scipy.spatial.transform import Rotation
from scipy.sparse.csgraph import dijkstra
import igl
F=Path(__file__).resolve().parent;D=np.load(F/'capture.npz');R=D['rest'];W=D['weights'];T=D['triangles'];names=json.loads((F/'capture.json').read_text())['bones']
def smooth(x):
    x=np.clip(x,0,1);return x*x*(3-2*x)
def feather(x,a,b):return 1-smooth((x-a)/(b-a))
mask=np.zeros(len(R))
for side in ['Left','Right']:
    head=D['bone_heads'][names.index(side+'Arm')]
    rho=np.linalg.norm((R-head)/[.33,.27,.32],axis=1)
    mask=np.maximum(mask,feather(rho,.52,1))
mask*=smooth((R[:,2]-1.14)/.10)*feather(R[:,2],1.51,1.60)
fixed_arm=np.zeros(len(R),bool)
for side in ['Left','Right']:
    arm=W[:,[j for j,n in enumerate(names)if n.startswith(side)and any(k in n for k in ['Arm','ForeArm','Hand','Index','Middle','Ring','Little','Thumb'])]].sum(1)
    radius=np.linalg.norm(R-D['bone_heads'][names.index(side+'Arm')],axis=1)
    fixed_arm|=(arm>.5)&(radius>.08)
# Freeze the native lower-axilla/contact patch plus a broad25mm source-surface
# collar. A60mm geodesic C1 transition restores the upper crest/scapular field.
E=np.unique(np.sort(np.concatenate([T[:,[0,1]],T[:,[1,2]],T[:,[2,0]]]),axis=1),axis=0)
lengths=np.linalg.norm(R[E[:,0]]-R[E[:,1]],axis=1)
G=sp.csr_matrix((np.r_[lengths,lengths],(np.r_[E[:,0],E[:,1]],np.r_[E[:,1],E[:,0]])),shape=(len(R),len(R)))
contact=np.load(F/'native-contact-domain.npz');seed=contact['seed_source_ids'];geodesic=dijkstra(G,directed=False,indices=seed,min_only=True)
geodesic_mask=smooth((geodesic-.025)/.060);mask*=geodesic_mask
protected=(geodesic<=.025)|fixed_arm
# Native distal surfaces are immutable clearance handles, not a new skin seam.
domain=(mask>0)&~fixed_arm;ids=np.flatnonzero(domain);outside=np.flatnonzero(~domain)
L=igl.cotmatrix(R,T).tocsr();off=L-sp.diags(L.diagonal());off.data=np.maximum(off.data,0);A=sp.diags(np.asarray(off.sum(1)).ravel())-off
# Screened harmonic influence ownership. 65mm surface diffusion length resolves
# the measured 5–15mm source assignment jumps without moving source geometry.
M=igl.massmatrix(R,T,igl.MASSMATRIX_TYPE_BARYCENTRIC).diagonal()
screen=M/(.065**2);H=A+sp.diags(screen)
rhs=screen[ids,None]*W[ids]-H[ids][:,outside]@W[outside]
field=W.copy();field[ids]=spsolve(H[ids][:,ids].tocsc(),rhs)
field=np.maximum(field,0);field/=field.sum(1)[:,None]
virtual=W+(field-W)*mask[:,None];virtual[fixed_arm]=W[fixed_arm];virtual/=virtual.sum(1)[:,None]
def dq(mats,weights):
    qr=Rotation.from_matrix(mats[:,:3,:3]).as_quat();qd=np.zeros_like(qr);v=mats[:,:3,3];qd[:,:3]=(qr[:,3,None]*v+np.cross(v,qr[:,:3]))*.5;qd[:,3]=-(v*qr[:,:3]).sum(1)*.5
    ref=qr[np.argmax(weights,axis=1)];sign=np.where(ref@qr.T<0,-1,1);rr=(weights*sign)@qr;dd=(weights*sign)@qd;length=np.linalg.norm(rr,axis=1);rr/=length[:,None];dd/=length[:,None]
    translation=2*(rr[:,3,None]*dd[:,:3]-dd[:,3,None]*rr[:,:3]+np.cross(rr[:,:3],dd[:,:3]))
    return Rotation.from_quat(rr),translation,length
targets=[];deltas=[];reports=[]
for state,j in enumerate([2,6]):
    q,tr,length=dq(D['matrices'][j],W);base=q.apply(R)+tr
    error=float(np.linalg.norm(base-D['positions'][j],axis=1).max());assert error<1e-5,error
    qv,tv,_=dq(D['matrices'][j],virtual);target=qv.apply(R)+tv
    target[~domain]=base[~domain]
    world=target-base;delta=q.inv().apply(world);delta[~domain]=0
    targets.append(target);deltas.append(delta)
    reports.append({'frame':float(D['frames'][j]),'baseline_DQ_native_max_error_m':error,'maximum_world_delta_m':float(np.linalg.norm(world,axis=1).max()),'minimum_native_blend_norm':float(length[ids].min()),'rotation_condition_number':1.,'exterior_max_delta_m':float(np.linalg.norm(world[~domain],axis=1).max()),'distal_arm_max_delta_m':float(np.linalg.norm(world[fixed_arm],axis=1).max()),'protected_lower_axilla_collar_max_delta_m':float(np.linalg.norm(world[protected],axis=1).max())})
delta=np.array(deltas).astype(np.float32)
assert np.linalg.norm(delta,axis=2).max()<.058,'Frozen ownership component exceeded its accepted58mm construction bound'
np.savez_compressed(F/'target.npz',source_ids=ids.astype(np.int32),source_basis=R[ids].astype(np.float32),rest_deltas=delta[:,ids],world_targets=np.array(targets)[:,ids],mask=mask[ids].astype(np.float32),protected_source_ids=np.flatnonzero(protected).astype(np.int32),geodesic_distance_m=geodesic[ids].astype(np.float32),virtual_weights=virtual[ids].astype(np.float32))
report={'method':'Screened harmonic virtual influence ownership on original source surface;65mm diffusion length; immutable native distal-arm/lower-axilla handles,25mm exact geodesic collar and60mm C1 surface-distance transition. Virtual influences compile into two5172-only inverse-unit-DQ POSITION targets. No source binding, geometry or posed/rest smoothing.','source_domain':'Union Arm-head ellipsoids radii330/270/320mm, plateau52%; sourceZ lower feather1140–1240mm, upper1510–1600mm. Distal arm/finger skin with original combinedArm>50% and source Arm-head radius>80mm is exact immutable.','protected_native_lower_axilla_and_collar_ids':np.flatnonzero(protected).tolist(),'native_contact_seed_source_ids':seed.tolist(),'geodesic_exact_collar_m':.025,'geodesic_C1_transition_m':[.025,.085],'domain_source_ids':ids.tolist(),'fixed_distal_arm_ids':np.flatnonzero(fixed_arm).tolist(),'source_vertex_count':len(R),'states':reports,'maximum_rest_delta_m':float(np.linalg.norm(delta,axis=2).max()),'exact_zero_exterior':True,'virtual_binding_only':True,'target_archive_sha256':hashlib.sha256((F/'target.npz').read_bytes()).hexdigest()}
(F/'construction.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(reports,indent=2))
