"""Whole-cage mechanics, actual source patches and diagnostic fold localization."""
from pathlib import Path
import sys
sys.dont_write_bytecode=True
import numpy as np
import bpy
sys.path.append(str(Path(__file__).resolve().parents[3]/'mannequin-mpfb-prototype/local-topology-repair/dependencies/venv/lib/python3.13/site-packages'))
from bilateral_geometry import near_contacts
from mathutils.bvhtree import BVHTree
P=Path(__file__).resolve().parent;sys.path.insert(0,str(P.parents[1]/'batch-007/resting-repair'));from resting_checks import measure
class DataProxy:
 def __init__(self,data):self.data=data;self.shape_keys=None
 def __getattr__(self,name):return getattr(self.data,name)
class BodyProxy:
 def __init__(self,body):self.data=DataProxy(body.data)
class SurfaceChecks:
 def __init__(self,body,patches):
  self.body=body;self.R=np.array([v.co[:]for v in body.data.vertices]);self.patches=patches['patches'];self.hold={};self.fixed={};body.data.calc_loop_triangles();self.T=np.array([t.vertices[:]for t in body.data.loop_triangles]);self.motion=type('Source',(),{})();self.motion.R=self.R;self.motion.head=np.flatnonzero(self.R[:,2]>1.55);self.motion.palm_frames={'Left':{'source_ids':self.patches['palm_support']['indices']},'Right':{'source_ids':self.patches['palm_hug']['indices']}}
  knee=set(self.patches['knee_hug']['indices']);self.is_arm=np.array([any(any(k in body.vertex_groups[g.group].name for k in ['Shoulder','Arm','Hand','Thumb','Index','Middle','Ring','Little'])and g.weight>1e-8 for g in v.groups)for v in body.data.vertices]);labels=np.array([body.data.attributes['.sculpt_face_set'].data[t.polygon_index].value for t in body.data.loop_triangles]);self.bilateral_faces={'Left':np.flatnonzero(np.isin(labels,[24,15,14,25,*range(46,64)])),'Right':np.flatnonzero(np.isin(labels,[23,16,13,*range(26,46)]))}
  self.hip_mask=(self.R[:,2]>.67)&(self.R[:,2]<1.13)
  for v in body.data.vertices:
   if any(any(k in body.vertex_groups[g.group].name for k in ['Shoulder','Arm','Hand','Thumb','Index','Middle','Ring','Little'])and g.weight>1e-8 for g in v.groups):self.hip_mask[v.index]=False
  self.hip_faces=np.flatnonzero(np.all(self.hip_mask[self.T],axis=1))
  old=np.load(P/'hip-volume-component.npz');self.hip_only_coordinates=(old['source_basis']+old['position_delta']).astype(np.float32);contact=np.load(P/'thigh-contact-margin.npz');self.contact_faces=np.flatnonzero(np.any((contact['mask']>0)[self.T],axis=1))
  self.knee_faces=np.array([i for i,t in enumerate(self.T)if all(v in knee for v in t)])
 def measure(self,X,N,frame):
  row=measure(BodyProxy(self.body),X,self.motion);row['source_z_hip_ROI_including_resting_hands']=row['local']['hips'];tree=BVHTree.FromPolygons(X.tolist(),self.T[self.hip_faces].tolist(),all_triangles=True);pairs=[(int(self.hip_faces[i]),int(self.hip_faces[j]))for i,j in tree.overlap(tree)if i<j and not set(self.T[self.hip_faces[i]])&set(self.T[self.hip_faces[j]])];cross=np.cross(X[self.T[self.hip_faces,1]]-X[self.T[self.hip_faces,0]],X[self.T[self.hip_faces,2]]-X[self.T[self.hip_faces,0]]);row['local']['hips']={'nonadjacent_crossings':len(pairs),'triangle_pairs':pairs,'minimum_area_m2':float(np.linalg.norm(cross,axis=1).min()*.5),'source_mask':'sourceZ .67..1.13m excluding every source arm/hand/finger influence; old sourceZ-only ROI retained separately because source hands hang beside the pelvis.'};row['frame']=frame;row['minimum_body_z']=float(X[:,2].min());fail=[]
  if row['minimum_body_z']< -1e-6:fail.append('whole_body_floor')
  if row['minimum_triangle_area_m2']<=1e-12:fail.append('nonpositive_area')
  if row['whole_arm_hand_vs_leg_crossings']:fail.append('whole_arm_hand_vs_leg')
  trees={side:BVHTree.FromPolygons(X.tolist(),self.T[ids].tolist(),all_triangles=True)for side,ids in self.bilateral_faces.items()};pairs=[(int(self.bilateral_faces['Left'][i]),int(self.bilateral_faces['Right'][j]))for i,j in trees['Left'].overlap(trees['Right'])if not set(self.T[self.bilateral_faces['Left'][i]])&set(self.T[self.bilateral_faces['Right'][j]])];row['whole_bilateral_leg_crossings']=pairs;row['bilateral_source_semantics']='Complete original anatomical triangle face sets: L24/15/14/25/46..63, R23/16/13/26..45; only shared source-vertex topological adjacency excluded, no positional/weight proxy.'
  if pairs:fail.append('whole_bilateral_legs')
  near=near_contacts(X,self.T,self.bilateral_faces['Left'],self.bilateral_faces['Right'],.003)if not pairs else[];row['whole_bilateral_minimum_triangle_clearance_lower_bound_m']=near[0]['distance_m']if near else(0. if pairs else.003);row['bilateral_nearest_features']=near[:3]
  # Compare the amendment with the same accepted hip-only cage at identical FK
  # and scalar. This is a relative orientation test, not a rest-world normal test.
  key=self.body.data.shape_keys.key_blocks['TwistHipVolume']
  if key.value>1e-8:
   lead=self.body.data.shape_keys.key_blocks.get('ThighContactLead');lead_value=float(lead.value)if lead else 0.
   if lead:lead.value=0.
   coords=np.array([v.co[:]for v in key.data],np.float32);key.data.foreach_set('co',self.hip_only_coordinates.ravel());bpy.context.view_layer.update();ev=self.body.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=ev.to_mesh();baseline=np.array([v.co[:]for v in mesh.vertices]);ev.to_mesh_clear();key.data.foreach_set('co',coords.ravel());
   if lead:lead.value=lead_value
   bpy.context.view_layer.update();faces=self.T[self.contact_faces];c0=np.cross(baseline[faces[:,1]]-baseline[faces[:,0]],baseline[faces[:,2]]-baseline[faces[:,0]]);c1=np.cross(X[faces[:,1]]-X[faces[:,0]],X[faces[:,2]]-X[faces[:,0]]);dot=np.einsum('ij,ij->i',c0,c1);relative=dot/np.maximum(np.einsum('ij,ij->i',c0,c0),1e-30);row['contact_relative_orientation_minimum']=float(relative.min());row['contact_reversed_source_faces']=self.contact_faces[dot<=0].tolist()
   if (dot<=0).any():row['contact_relative_normal_diagnostic']='Baseline-normal direction only;17419 atf24/126 has positive material-frame determinant and area, no direct nonadjacent crossings. See face17419-diagnosis.json and accepted native proofs; compressed adjacent crease remains disclosed.'
  else:row['contact_relative_orientation_minimum']=1.;row['contact_reversed_source_faces']=[]
  supports={};held=60<=frame<=90
  for name,p in self.patches.items():
   ids=p['indices'];z=X[ids,2];kind=p['kind'];supported=kind in ['pelvis','extended_heel']or(kind=='crossed_sole'and 39<=frame<=111)or(kind=='crossed_heel'and(frame==0 or frame==150 or 39<=frame<=111))or(kind=='support_palm'and held);value={'state':'supported'if supported else'free','min_z':float(z.min()),'max_z':float(z.max()),'vertices_within5mm':int((abs(z)<.005).sum())}
   if supported and(z.min()< -1e-6 or z.min()>.005):fail.append(name+'_support')
   if supported and kind=='support_palm'and value['vertices_within5mm']<5:fail.append('central_palm_contact_area')
   center=X[ids].mean(0)
   if kind=='extended_heel':
    initial=self.fixed.setdefault(name,center.copy());value['skin_centroid_drift_m']=float(np.linalg.norm(center-initial))
    if value['skin_centroid_drift_m']>.005:fail.append('extended_heel_drift')
   if held and kind in ['support_palm','crossed_sole','pelvis']:
    initial=self.hold.setdefault(name,center.copy());value['hold_skin_centroid_drift_m']=float(np.linalg.norm(center-initial))
    if value['hold_skin_centroid_drift_m']>.005:fail.append(name+'_hold_drift')
   supports[name]=value
  if held:
   tree=BVHTree.FromPolygons(X.tolist(),self.T[self.knee_faces].tolist(),all_triangles=True);distances=[tree.find_nearest(tuple(X[i]))[3]for i in self.patches['palm_hug']['indices']];row['hug_central_palm_knee_gap_m']=min(distances);row['hug_central_pad_vertices_within12mm']=sum(v<.012 for v in distances)
   if min(distances)>.012:fail.append('floating_opposite_palm_hug')
  row['supports']=supports;return row,fail
