"""Fixed original-source surface domains and discrete contact diagnostics."""
import numpy as np
from mathutils.bvhtree import BVHTree
class SurfaceChecks:
 def __init__(self,body,contact,target_report):
  self.body=body;self.contact=contact;self.R=np.array([v.co[:] for v in body.data.vertices]);R=self.R;body.data.calc_loop_triangles();self.T=np.array([t.vertices[:] for t in body.data.loop_triangles]);T=self.T;self.restarea=np.linalg.norm(np.cross(R[T[:,1]]-R[T[:,0]],R[T[:,2]]-R[T[:,0]]),axis=1)*.5;regions={}
  for p,a in zip(body.data.polygons,body.data.attributes['.sculpt_face_set'].data):regions.setdefault(a.value,set()).update(p.vertices)
  self.patches={};self.soles={};self.hand={};self.heel={};self.previous={};self.witnesses={};self.witnesslookup={}
  def mask(ids):m=np.zeros(len(R),bool);m[list(ids)]=True;return m
  self.armmask=mask(set.union(*(regions[k] for k in [9,10,11,12,20,21]+[k for k in regions if 64<=k<104])));self.legmask=(R[:,2]<1.04)&(abs(R[:,0])<.32);self.armfaces=np.flatnonzero(np.all(self.armmask[T],axis=1));self.legfaces=np.flatnonzero(np.all(self.legmask[T],axis=1))
  for side,sgn in [('Left',1),('Right',-1)]:
   low=(sgn*R[:,0]>.12)&(R[:,2]<.012);gi=body.vertex_groups[side+'ToeBase'].index;share=np.array([sum(g.weight for g in v.groups if g.group==gi) for v in body.data.vertices]);self.soles[side]={'heel':np.flatnonzero(low&(R[:,1]>.025)),'forefoot':np.flatnonzero(low&(R[:,1]<-.025)),'rear_toes':np.flatnonzero(low&(R[:,1]<0)&(share>.7))};self.hand[side]=np.flatnonzero(self.armmask&(R[:,2]<1.0)&(sgn*R[:,0]>.3));self.heel[side]=np.flatnonzero((sgn*R[:,0]>.12)&(R[:,1]>.09)&(R[:,2]<.105));assert all(len(x)>5 for x in self.soles[side].values())
  self.local={'pelvis_thigh':np.flatnonzero(np.all(((R[:,2]>.66)&(R[:,2]<1.14))[T],axis=1)),'knees':np.flatnonzero(np.all(((R[:,2]>.34)&(R[:,2]<.66))[T],axis=1)),'shoulders':np.flatnonzero(np.all(((abs(R[:,0])>.08)&(abs(R[:,0])<.40)&(R[:,2]>1.12)&(R[:,2]<1.53))[T],axis=1))}
  for x in target_report['states']:
   m=mask(x['source_ids']);self.local[x['name']+'_affected_star']=np.flatnonzero(np.any(m[T],axis=1))
 def tree(self,X,ids):return BVHTree.FromPolygons(X.tolist(),self.T[ids].tolist(),all_triangles=True)
 def measure(self,X,N,st):
  T=self.T;f=st['frame'];id=st['id'];fail=[];floor=float(X[:,2].min());supports={}
  if floor<-1e-6:fail.append('body_floor')
  for side in ['Left','Right']:
   kind=st['feet'][side]['support'];names=['heel','forefoot'] if kind=='whole_sole' else (['rear_toes'] if kind=='rear_toes' else [])
   if not names:self.previous.pop(side,None)
   for name in names:
    ids=self.soles[side][name];center=X[ids].mean(0);initial=self.previous.setdefault(side,{}).setdefault(name,center);drift=float(np.linalg.norm(center-initial));z=X[ids,2];supports[side+'_'+name]={'kind':kind,'count':len(ids),'minimum_z':float(z.min()),'maximum_z':float(z.max()),'near_12mm_fraction':float((abs(z)<.012).mean()),'centroid_drift_m':drift}
    if z.min()<-1e-6 or z.min()>.012 or drift>.002:fail.append(side+'_'+name+'_support')
  arm,leg=self.tree(X,self.armfaces),self.tree(X,self.legfaces);pairs=arm.overlap(leg);armgap=float(min(leg.find_nearest(tuple(X[i]))[3] for i in np.flatnonzero(self.armmask)));unintended=[]
  for i,j in pairs:unintended.append({'arm_triangle_id':int(self.armfaces[i]),'leg_triangle_id':int(self.legfaces[j]),'arm_source_ids':T[self.armfaces[i]].tolist(),'leg_source_ids':T[self.legfaces[j]].tolist()})
  if unintended:fail.append('whole_arm_hand_vs_leg')
  contact={}
  if id=='3479':
   side=st['side'];info=self.contact[side];tip=info['finger_contact_id'];heel=info['heel_apex_id'];hf=np.flatnonzero(np.all(np.isin(T,self.heel[side]),axis=1));ht=self.tree(X,hf);near=[ht.find_nearest(tuple(X[i]))[3] for i in self.hand[side]];gap=float(np.linalg.norm(X[tip]-X[heel]));contact={'side':side,'weight':st['contact'],'source_finger_id':tip,'source_heel_id':heel,'finger_to_heel_point_m':gap,'whole_hand_to_heel_surface_minimum_m':float(min(near)),'heel_prediction_error_m':float(np.linalg.norm(X[heel]-st['heel_contact_point']))}
   if st['contact']>1-1e-7 and not (.001-2e-6<=gap<=.005+2e-6):fail.append('heel_touch_point_gap')
  cross=np.cross(X[T[:,1]]-X[T[:,0]],X[T[:,2]]-X[T[:,0]]);area=np.linalg.norm(cross,axis=1)*.5;local={}
  if area.min()<=1e-12:fail.append('nonpositive_or_degenerate_area')
  for name,ids in self.local.items():
   tri=T[ids];bt=self.tree(X,ids);pairs=[(int(ids[i]),int(ids[j])) for i,j in bt.overlap(bt) if i<j and not set(tri[i])&set(tri[j])];refs=[]
   for a,b in pairs:
    key=f'{a}:{b}'
    if key not in self.witnesslookup:
     wid=len(self.witnesses);self.witnesslookup[key]=wid;self.witnesses[str(wid)]={'source_triangle_ids':[a,b],'source_triangles':[T[a].tolist(),T[b].tolist()],'original_vertices':[{'id':int(i),'basis':self.R[i].tolist(),'weights':{self.body.vertex_groups[g.group].name:float(g.weight) for g in self.body.data.vertices[int(i)].groups}} for i in sorted(set(T[a])|set(T[b]))],'frames':[]}
    wid=self.witnesslookup[key];tag=[id,f]
    if tag not in self.witnesses[str(wid)]['frames']:self.witnesses[str(wid)]['frames'].append(tag)
    refs.append(wid)
   dots=(cross[ids]*N[tri].mean(1)).sum(1);local[name]={'triangles':len(ids),'minimum_area_m2':float(area[ids].min()),'minimum_area_ratio':float((area[ids]/self.restarea[ids]).min()),'maximum_area_ratio':float((area[ids]/self.restarea[ids]).max()),'opposed_shader_normal_faces':int((dots<=0).sum()),'disjoint_self_intersection_pairs':len(pairs),'crossing_witness_ids':refs}
  return {'frame':f,'minimum_body_z':floor,'minimum_triangle_area_m2':float(area.min()),'minimum_knee_skin_z':float(X[(self.R[:,2]>.38)&(self.R[:,2]<.61),2].min()),'supports':supports,'heel_contact':contact,'arm_hand_vs_leg':{'triangle_intersections':len(unintended),'minimum_surface_distance_m':armgap,'unintended_pairs':unintended},'local_faces':local},fail
