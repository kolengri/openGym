"""Geometric support proxy; homogeneous enclosed skin volume is not a biomechanical COM."""
import numpy as np

def hull2(points):
 p=sorted(set(map(tuple,points)))
 def cross(o,a,b):return (a[0]-o[0])*(b[1]-o[1])-(a[1]-o[1])*(b[0]-o[0])
 lo=[];up=[]
 for x in p:
  while len(lo)>1 and cross(lo[-2],lo[-1],x)<=0:lo.pop()
  lo.append(x)
 for x in reversed(p):
  while len(up)>1 and cross(up[-2],up[-1],x)<=0:up.pop()
  up.append(x)
 return np.array(lo[:-1]+up[:-1])

def measure(X,T,support_ids):
 v=np.einsum('ij,ij->i',X[T[:,0]],np.cross(X[T[:,1]],X[T[:,2]]))/6
 centroid=(v[:,None]*X[T].sum(1)/4).sum(0)/v.sum();h=hull2(X[support_ids,:2]);e=np.roll(h,-1,axis=0)-h;d=centroid[:2]-h;margin=(e[:,0]*d[:,1]-e[:,1]*d[:,0])/np.linalg.norm(e,axis=1)
 return {'method':'Homogeneous closed-skin signed-volume centroid projected into convex hull of actual frozen plantar skin. Geometric authored guard; not measured anatomical mass, force, stability or clinical evidence.','centroid_m':centroid.tolist(),'support_hull_xy_m':h.tolist(),'minimum_inward_edge_distance_m':float(margin.min()),'inside_hull':bool(margin.min()>=-.002),'signed_volume_m3':float(v.sum())}
