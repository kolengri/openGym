"""Bilateral, source-coordinate shoulder-only repair of diagnosed hard binding edges."""
import numpy as np

def apply(body):
 xyz=np.array([v.co[:] for v in body.data.vertices]);names=[g.name for g in body.vertex_groups]
 w=np.zeros((len(xyz),len(names)))
 for v in body.data.vertices:
  for g in v.groups:w[v.index,g.group]=g.weight
 original=w.copy()
 def smooth(v):
  v=np.clip(v,0,1);return v*v*(3-2*v)
 sx=np.abs(xyz[:,0])
 blend=smooth((sx-.09)/.05)*(1-smooth((sx-.35)/.055))*smooth((xyz[:,2]-1.16)/.055)*(1-smooth((xyz[:,2]-1.49)/.065))
 edges=np.array([e.vertices[:] for e in body.data.edges]);degree=np.bincount(edges.ravel(),minlength=len(xyz))
 selected=np.array([n in ['Spine','Spine1','Neck','LeftShoulder','RightShoulder','LeftArm','RightArm'] for n in names])
 for _ in range(18):
  total=np.zeros_like(w);np.add.at(total,edges[:,0],w[edges[:,1]]);np.add.at(total,edges[:,1],w[edges[:,0]])
  w[:,selected]+=.55*blend[:,None]*(total[:,selected]/np.maximum(degree,1)[:,None]-w[:,selected])
  w/=w.sum(1)[:,None];w[blend<=1e-8]=original[blend<=1e-8]
 ids=np.flatnonzero(blend>1e-8)
 for i in ids:
  keep=np.argsort(w[i])[-4:];w[i,np.setdiff1d(np.arange(len(names)),keep)]=0;w[i,w[i]<.001]=0;w[i]/=w[i].sum()
  old_names=[body.vertex_groups[g.group].name for g in body.data.vertices[int(i)].groups]
  for n in old_names:body.vertex_groups[n].remove([int(i)])
  for j in np.flatnonzero(w[i]):body.vertex_groups[int(j)].add([int(i)],float(w[i,j]),'REPLACE')
 actual=np.zeros_like(w)
 for v in body.data.vertices:
  for g in v.groups:actual[v.index,g.group]=g.weight
 assert np.max(abs(actual-w))<2e-6
 assert np.array_equal(actual[blend<=1e-8],original[blend<=1e-8])
 return {'purpose':'Repair both diagnosed source shoulder/trunk hard weight boundaries after elbow-plane transport correction.', 'method':'18 topology diffusion iterations, 0.55 mixing; bilateral feathered source neighborhoods abs(x)=0.09..0.405m, z=1.16..1.555m; maximum four weights.', 'affected_source_indices':ids.tolist(),'affected_vertices':len(ids),'source_bounds':[xyz[ids].min(0).tolist(),xyz[ids].max(0).tolist()],'maximum_weight_change':float(np.abs(w-original).max()),'unchanged_outside_neighborhood':True,'basis_rest_uv_topology_unchanged':True,'maximum_influences':max(len(v.groups) for v in body.data.vertices),'maximum_normalization_error':max(abs(sum(g.weight for g in v.groups)-1) for v in body.data.vertices),'edits':[{'source_index':int(i),'original':{names[j]:float(original[i,j]) for j in np.flatnonzero(original[i])},'new':{body.vertex_groups[g.group].name:float(g.weight) for g in body.data.vertices[int(i)].groups}} for i in ids]}
