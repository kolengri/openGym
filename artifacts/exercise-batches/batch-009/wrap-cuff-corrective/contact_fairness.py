"""Local C1 contact fairness against exact immutable distal arm surfaces.

The harmonic ownership construction supplies the shape. This step supplies
unilateral skin clearance, leaving canonical/source channels and protected
points untouched. It is not a binding refit or global geometry fairing.
"""
import numpy as np
from scipy.sparse.linalg import spsolve
import igl

def reconstruct(target,native,triangles,domains,mask,protected,stiffness,source_ids,margin=.002,anchors=None):
 q=target.copy();N=len(q);ids=np.asarray(source_ids);idset=np.zeros(N,bool);idset[ids]=True;records=[]
 for step in range(14):
  requested={};bad_samples=0;deepest=0.
  for side,opposite in [('right_arm','left_arm'),('left_arm','right_arm'),('torso','right_arm'),('torso','left_arm')]:
   faces=domains[side];faces=faces[np.any(idset[faces],axis=1)];obstacle=domains[opposite]
   obstacle=obstacle[np.all((protected|(mask<.25))[obstacle],axis=1)]
   obstacle_points=q.copy();obstacle_points[protected]=native[protected]
   if len(faces)==0 or len(obstacle)==0:continue
   normals=np.cross(obstacle_points[obstacle[:,1]]-obstacle_points[obstacle[:,0]],obstacle_points[obstacle[:,2]]-obstacle_points[obstacle[:,0]]);normals/=np.linalg.norm(normals,axis=1)[:,None]
   bary=np.array([[i/6,j/6,(6-i-j)/6]for i in range(7)for j in range(7-i)])
   samples=np.einsum('bc,tcd->tbd',bary,q[faces]).reshape(-1,3);dist2,fi,closest=igl.point_mesh_squared_distance(samples,obstacle_points,obstacle);nn=normals[fi];signed=np.einsum('ij,ij->i',samples-closest,nn)
   # Open obstacle boundaries are distant from this local forearm contact. A
   # 40mm proximity gate avoids assigning their plane halfspace globally.
   bad=(signed<margin-1e-5)&(dist2<.04**2)
   for si in np.flatnonzero(bad):
    face=faces[si//len(bary)];bb=bary[si%len(bary)];eligible=(mask[face]>.15)&~protected[face];weight=float(bb[eligible].sum())
    if weight<1e-8:continue
    delta=nn[si]*(margin-signed[si])/weight;bad_samples+=1;deepest=max(deepest,float(margin-signed[si]))
    for vi in face[eligible]:
     correction=delta/max(float(mask[vi]),.15)
     if int(vi)not in requested or np.linalg.norm(correction)>np.linalg.norm(requested[int(vi)]):requested[int(vi)]=correction
  records.append({'iteration':step,'violating_samples':bad_samples,'maximum_contact_step_m':deepest,'constraint_source_ids':sorted(requested)})
  if not requested:break
  pins=np.array(sorted(requested),int);free=np.setdiff1d(ids,pins);u=np.zeros((N,3));u[pins]=np.array([requested[int(i)]for i in pins])
  if len(free):u[free]=spsolve(stiffness[free][:,free].tocsc(),-stiffness[free][:,pins]@u[pins])
  if anchors is not None:u=anchors.project_increment(u)
  delta=u*mask[:,None];delta[protected]=0.;q+=delta
 return q,records

class ContactAnchors:
 """Exact posed contact points and tangent planes, without triangle pinning."""
 def __init__(self,reference,target,mask,source_ids,stiffness,contact_record,skin_normals):
  self.ids=np.asarray(source_ids);self.mask=mask;self.lookup={int(i):j for j,i in enumerate(self.ids)};n=len(self.ids);rows=[];rhs=[];self.anchors=[]
  for palm in contact_record['palms']:
   hit=palm['closest'][0];tri=np.array(hit['body_source_triangle'],int);point=np.array(hit['body_point']);bary=np.linalg.lstsq(np.vstack([reference[tri].T,np.ones(3)]),np.r_[point,1.],rcond=None)[0];bary=np.maximum(bary,0.);bary/=bary.sum();point=bary@reference[tri];normal=-skin_normals[hit['palm_source_id']].copy();normal/=np.linalg.norm(normal)
   assert all(int(i)in self.lookup for i in tri),'A contact anchor lies in an exact protected domain'
   self.anchors.append({'side':palm['side'],'triangle':tri.tolist(),'barycentric':bary.tolist(),'point':point.tolist(),'normal':normal.tolist()})
   for axis in range(3):
    row=np.zeros((n,3))
    for i,w in zip(tri,bary):row[self.lookup[int(i)],axis]=w*mask[i]
    rows.append(row.ravel());rhs.append(point[axis]-float(bary@target[tri,axis]))
   for other in [1,2]:
    row=np.zeros((n,3));row[self.lookup[int(tri[0])]]=normal*mask[tri[0]];row[self.lookup[int(tri[other])]]=-normal*mask[tri[other]];rows.append(row.ravel());rhs.append(-float(normal@(target[tri[0]]-target[tri[other]])))
  self.C=np.array(rows);self.rhs=np.array(rhs);h=stiffness[self.ids][:,self.ids].tocsc();rhs_matrix=self.C.T.reshape(n,3,-1).reshape(n,-1);self.Z=spsolve(h,rhs_matrix).reshape(n*3,-1);self.M=self.C@self.Z
  assert np.linalg.matrix_rank(self.M)==len(self.M),'Contact constraints are dependent'
 def align(self,target):
  v=(self.Z@np.linalg.solve(self.M,self.rhs)).reshape(len(self.ids),3);q=target.copy();q[self.ids]+=v*self.mask[self.ids,None];return q
 def project_increment(self,u):
  v=u[self.ids].ravel();v-=self.Z@np.linalg.solve(self.M,self.C@v);q=u.copy();q[self.ids]=v.reshape(-1,3);return q
 def evidence(self,target):
  rows=[]
  for a in self.anchors:
   tri=np.array(a['triangle']);bary=np.array(a['barycentric']);point=np.array(a['point']);normal=np.array(a['normal']);rows.append({**a,'point_error_m':float(np.linalg.norm(bary@target[tri]-point)),'maximum_triangle_plane_residual_m':float(np.abs((target[tri]-point)@normal).max())})
  return rows
