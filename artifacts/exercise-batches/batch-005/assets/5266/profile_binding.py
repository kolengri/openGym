"""Single causal source-anatomy runtime binding family; exterior/rest stay exact."""
import json,hashlib
import numpy as np

def smooth(a,b,x):
 t=np.clip((x-a)/(b-a),0,1);return t*t*(3-2*t)

class ProfileBinding:
 def __init__(self,body,rig):
  self.body=body
  self.rest=np.array([v.co[:]for v in body.data.vertices])
  assert self.rest.shape==(10582,3)
  self.names={g.index:g.name for g in body.vertex_groups}
  self.source=[{self.names[g.group]:float(g.weight)for g in v.groups if g.weight>1e-10}for v in body.data.vertices]
  z=self.rest[:,2];x=abs(self.rest[:,0]);y=self.rest[:,1]
  self.hip_z=float(rig.data.bones['LeftUpLeg'].head_local.z)
  self.spine_z=float(rig.data.bones['Spine'].head_local.z)
  self.chest_z=float(rig.data.bones['Spine1'].head_local.z)
  # Above the true femoral pivot, progressively remove femoral skin drag.
  # The old lower-glute overlay is deliberately not imported: at/below the
  # hip pivot the complete original glute/thigh blend remains unchanged.
  self.leg_gate=smooth(self.hip_z,self.hip_z+.09,z)*(1-smooth(.195,.24,x))
  # Posterior lower lumbar follows Hips/Spine while chest twists above it.
  # The 70mm upper collar is C1 and all anterior/lateral torso stays blended.
  self.chest_gate=smooth(self.spine_z-.08,self.spine_z-.01,z)*(1-smooth(self.chest_z,self.chest_z+.07,z))*smooth(.02,.075,y)*(1-smooth(.10,.18,x))
  self.ids=[i for i,w in enumerate(self.source)if self.leg_gate[i]*(w.get('LeftUpLeg',0)+w.get('RightUpLeg',0))>1e-9 or self.chest_gate[i]*w.get('Spine1',0)>1e-9]
  self.current=None
 def apply(self,leg_amount,chest_amount,details=False):
  key=(float(leg_amount),float(chest_amount));changes=[]
  if key==self.current and not details:return
  for i in self.ids:
   old=self.source[i];new=dict(old);gain=self.leg_gate[i]*leg_amount
   removed=sum(old.get(n,0)*gain for n in ['LeftUpLeg','RightUpLeg'])
   for n in ['LeftUpLeg','RightUpLeg']:
    if n in new:new[n]*=1-gain
   total=old.get('Hips',0)+old.get('Spine',0)
   for n in ['Hips','Spine']:
    f=old.get(n,0)/total if total>1e-8 else float(n=='Hips')
    if f:new[n]=new.get(n,0)+removed*f
   chest=old.get('Spine1',0)*self.chest_gate[i]*chest_amount
   if chest:
    new['Spine1']-=chest;new['Spine']=new.get('Spine',0)+chest
   new={n:float(w)for n,w in new.items()if w>1e-8}
   assert len(new)<=4 and abs(sum(new.values())-1)<2e-6,(i,new)
   for n in set(old)|set(new):self.body.vertex_groups[n].remove([i])
   for n,w in new.items():self.body.vertex_groups[n].add([i],w,'REPLACE')
   if details and any(abs(new.get(n,0)-old.get(n,0))>1e-8 for n in set(new)|set(old)):
    changes.append({'source_id':i,'co_m':self.rest[i].tolist(),'leg_gate':float(self.leg_gate[i]),'posterior_chest_gate':float(self.chest_gate[i]),'before':old,'after':new})
  self.current=key
  if details:
   return {'method':'Single causal binding family, fitted jointly with pose. UpLeg→existingHips/Spine blend only above actual femoral headZ, C1 ramp over90mm. Regional posteriorSpine1→Spine below actualSpine1head with C1 70mm upper collar; x/y feathers preserve anterior/lateral torso. No exterior/Basis/UV/rest edit.','amounts':{'above_hip_thigh_removal':key[0],'posterior_lower_lumbar_chest_removal':key[1]},'actual_rest_landmarks_m':{'hip_z':self.hip_z,'spine_z':self.spine_z,'spine1_z':self.chest_z},'domain':{'leg_z_ramp_m':[self.hip_z,self.hip_z+.09],'leg_abs_x_feather_m':[.195,.24],'posterior_chest_lower_z_ramp_m':[self.spine_z-.08,self.spine_z-.01],'posterior_chest_upper_z_collar_m':[self.chest_z,self.chest_z+.07],'posterior_chest_y_ramp_m':[.02,.075],'posterior_chest_abs_x_feather_m':[.10,.18]},'changed_vertex_count':len(changes),'max_influences':max(len(c['after'])for c in changes)if changes else 4,'source_weights_sha256':hashlib.sha256(json.dumps(self.source,sort_keys=True).encode()).hexdigest(),'changes':changes}
