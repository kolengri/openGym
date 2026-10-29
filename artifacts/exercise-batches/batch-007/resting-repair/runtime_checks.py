"""Actual final-source support and whole-skin checks for native/decoded DQ."""
import numpy as np
from resting_checks import measure

class SurfaceChecks:
 def __init__(self,body,landmarks):
  self.body=body;self.R=np.array([v.co[:]for v in body.data.vertices]);self.patches=landmarks['patches'];self.hold_centers={};self.fixed_centers={}
  class Source:pass
  self.motion=Source();self.motion.R=self.R;self.motion.head=np.flatnonzero(self.R[:,2]>1.55);self.motion.palm_frames={side:{'source_ids':self.patches['palm_'+side]['indices']}for side in ['Left','Right']}
 def measure(self,X,N,frame):
  row=measure(self.body,X,self.motion);row['frame']=frame;row['minimum_body_z']=float(X[:,2].min());fail=[];support={}
  if row['minimum_body_z']< -1e-6:fail.append('whole_body_floor')
  if row['minimum_triangle_area_m2']<=1e-12:fail.append('nonpositive_area')
  if row['whole_arm_hand_vs_leg_crossings']:fail.append('whole_arm_hand_vs_leg')
  for name,p in self.patches.items():
   ids=p['indices'];z=X[ids,2];kind=p['kind'];held=60<=frame<=90;supported=kind in ['knee','dorsum']or held;center=X[ids].mean(0);near=float((abs(z)<.012).mean());value={'state':'supported'if supported else'free','min_z':float(z.min()),'max_z':float(z.max()),'fraction_within12mm':near,'vertices_within5mm':int((abs(z)<.005).sum())}
   if supported:
    limit=.012 if kind in ['knee','dorsum']else .005
    if z.min()< -1e-6 or z.min()>limit:fail.append(name+'_support')
    if kind in ['knee','dorsum']and near<.2:fail.append(name+'_support_area_fraction')
    if kind=='palm'and value['vertices_within5mm']<5:fail.append(name+'_central_pad_contact')
   if kind=='dorsum':
    initial=self.fixed_centers.setdefault(name,center.copy());value['planted_skin_centroid_drift_m']=float(np.linalg.norm(center-initial))
    if value['planted_skin_centroid_drift_m']>.005:fail.append(name+'_planted_drift')
   if held and kind in ['palm','forehead']:
    initial=self.hold_centers.setdefault(name,center.copy());value['hold_skin_centroid_drift_m']=float(np.linalg.norm(center-initial))
    if value['hold_skin_centroid_drift_m']>.005:fail.append(name+'_hold_drift')
   support[name]=value
  row['supports']=support;return row,fail
