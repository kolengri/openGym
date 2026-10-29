"""Complete source-anatomical bilateral domains and exact near triangle distance.

The broad phase is a bounding-sphere/AABB lower bound. The narrow phase checks
all six vertex/triangle and nine edge/edge candidates, including interior line
minima. Call after an independent exact triangle-crossing check: intersecting
noncoplanar triangles can otherwise have nonzero boundary feature distances.
"""
import numpy as np

def face_sets(body):
 body.data.calc_loop_triangles();T=np.array([t.vertices[:]for t in body.data.loop_triangles]);labels=np.array([body.data.attributes['.sculpt_face_set'].data[t.polygon_index].value for t in body.data.loop_triangles]);return T,np.flatnonzero(np.isin(labels,[24,15,14,25,*range(46,64)])),np.flatnonzero(np.isin(labels,[23,16,13,*range(26,46)]))

def point_tri(P,A):
 e0=A[:,1]-A[:,0];e1=A[:,2]-A[:,0];r=P-A[:,0];aa=np.einsum('ij,ij->i',e0,e0);bb=np.einsum('ij,ij->i',e0,e1);cc=np.einsum('ij,ij->i',e1,e1);dd=np.einsum('ij,ij->i',r,e0);ee=np.einsum('ij,ij->i',r,e1);det=aa*cc-bb*bb;v=(cc*dd-bb*ee)/np.maximum(det,1e-30);w=(aa*ee-bb*dd)/np.maximum(det,1e-30);beta=np.column_stack((1-v-w,v,w));Q=np.einsum('ij,ijk->ik',beta,A);inside=(beta>=0).all(1);distance=np.einsum('ij,ij->i',P-Q,P-Q);distance[~inside]=np.inf
 for i,j in [(0,1),(1,2),(2,0)]:
  E=A[:,j]-A[:,i];t=np.clip(np.einsum('ij,ij->i',P-A[:,i],E)/np.maximum(np.einsum('ij,ij->i',E,E),1e-30),0,1);q=A[:,i]+t[:,None]*E;ds=np.einsum('ij,ij->i',P-q,P-q);use=ds<distance;distance[use]=ds[use];Q[use]=q[use];beta[use]=0;beta[use,i]=1-t[use];beta[use,j]=t[use]
 return distance,Q,beta

def near_contacts(X,T,LF,RF,margin=.003):
 from scipy.spatial import cKDTree
 L=X[T[LF]];R=X[T[RF]];lc=L.mean(1);rc=R.mean(1);lr=np.linalg.norm(L-lc[:,None],axis=2).max(1);rr=np.linalg.norm(R-rc[:,None],axis=2).max(1);lists=cKDTree(rc).query_ball_point(lc,lr+rr.max()+margin);li=np.repeat(np.arange(len(L)),[len(v)for v in lists]);ri=np.array([j for vs in lists for j in vs],dtype=int)
 if not len(li):return []
 A=L[li];B=R[ri];gap=np.maximum(np.maximum(A.min(1)-B.max(1),B.min(1)-A.max(1)),0);keep=np.linalg.norm(gap,axis=1)<margin;li=li[keep];ri=ri[keep];A=A[keep];B=B[keep]
 # A physical shared source vertex is a connected seam, not two independent
 # skin surfaces. Exclusion is identical to the explicit crossing gate.
 keep=np.array([not set(T[LF[i]])&set(T[RF[j]])for i,j in zip(li,ri)],dtype=bool);li=li[keep];ri=ri[keep];A=A[keep];B=B[keep];count=len(li)
 if not count:return []
 best=np.full(count,np.inf);PA=np.zeros((count,3));PB=PA.copy();BA=PA.copy();BB=PA.copy()
 def update(ds,pa,pb,ba,bb):
  use=ds<best;best[use]=ds[use];PA[use]=pa[use];PB[use]=pb[use];BA[use]=ba[use];BB[use]=bb[use]
 eye=np.eye(3)
 for k in range(3):
  ds,Q,beta=point_tri(A[:,k],B);update(ds,A[:,k],Q,np.tile(eye[k],(count,1)),beta)
  ds,Q,beta=point_tri(B[:,k],A);update(ds,Q,B[:,k],beta,np.tile(eye[k],(count,1)))
 for i,j in [(0,1),(1,2),(2,0)]:
  for k,l in [(0,1),(1,2),(2,0)]:
   p=A[:,i];q=B[:,k];u=A[:,j]-p;v=B[:,l]-q;r=p-q;aa=np.einsum('ij,ij->i',u,u);bb=np.einsum('ij,ij->i',u,v);cc=np.einsum('ij,ij->i',v,v);dd=np.einsum('ij,ij->i',u,r);ee=np.einsum('ij,ij->i',v,r);det=aa*cc-bb*bb;s=(bb*ee-cc*dd)/np.maximum(det,1e-30);t=(aa*ee-bb*dd)/np.maximum(det,1e-30);inside=(det>1e-25)&(s>=0)&(s<=1)&(t>=0)&(t<=1);pa=p+s[:,None]*u;pb=q+t[:,None]*v;ds=np.einsum('ij,ij->i',pa-pb,pa-pb);ds[~inside]=np.inf;ba=np.zeros((count,3));bc=ba.copy();ba[:,i]=1-s;ba[:,j]=s;bc[:,k]=1-t;bc[:,l]=t;update(ds,pa,pb,ba,bc)
 rows=[]
 for z in np.flatnonzero(best<margin**2):rows.append({'left_face':int(LF[li[z]]),'right_face':int(RF[ri[z]]),'distance_m':float(np.sqrt(best[z])),'left_position':PA[z].tolist(),'right_position':PB[z].tolist(),'left_barycentric':BA[z].tolist(),'right_barycentric':BB[z].tolist()})
 return sorted(rows,key=lambda row:row['distance_m'])
