"""Causal upright waist/plantar repair, installed by stable group names."""
import numpy as np

def ease(t):
 t=np.clip(t,0,1);return t*t*(3-2*t)
def apply(body):
 original=[{body.vertex_groups[g.group].name:float(g.weight)for g in v.groups}for v in body.data.vertices];rest=np.array([v.co[:]for v in body.data.vertices]);rows=[]
 for i,(x,y,z)in enumerate(rest):
  old=original[i];new=dict(old);waist=float(ease((z-.93)/.15))
  moved=sum(old.get(n,0)*waist for n in ['LeftUpLeg','RightUpLeg'])
  if moved:
   for n in ['LeftUpLeg','RightUpLeg']:
    if n in new:new[n]*=1-waist
   total=old.get('Hips',0)+old.get('Spine',0)
   for n in ['Hips','Spine']:
    fraction=old.get(n,0)/total if total>1e-8 else float(n=='Hips')
    if fraction:new[n]=new.get(n,0)+moved*fraction
  side='Left'if x>0 else'Right';plantar=float((1-ease((z-.035)/.045))*ease((abs(x)-.08)/.04))
  if plantar>0:
   total=old.get(side+'Foot',0)+old.get(side+'ToeBase',0)
   target={side+'Foot':old.get(side+'Foot',0)/total if total>1e-8 else 1.,side+'ToeBase':old.get(side+'ToeBase',0)/total if total>1e-8 else 0.}
   new={n:value*(1-plantar)for n,value in new.items()}
   for n,value in target.items():new[n]=new.get(n,0)+value*plantar
  new={n:w for n,w in new.items()if w>1e-8}
  if len(new)>4:new=dict(sorted(new.items(),key=lambda item:item[1],reverse=True)[:4])
  total=sum(new.values());new={n:w/total for n,w in new.items()}
  if all(abs(old.get(n,0)-new.get(n,0))<1e-8 for n in set(old)|set(new)):continue
  for n in list(old):body.vertex_groups[n].remove([i])
  for n,w in new.items():body.vertex_groups[n].add([i],float(w),'REPLACE')
  actual={body.vertex_groups[g.group].name:float(g.weight)for g in body.data.vertices[i].groups}
  assert len(actual)<=4 and abs(sum(actual.values())-1)<2e-6
  rows.append({'id':i,'source_coordinate_m':[float(x),float(y),float(z)],'waist_gate':waist,'plantar_gate':plantar,'before':old,'after':actual})
 return {'method':'Remove diagnosed thigh drag above actual hip into the existing Hips/Spine ratio, C1 sourceZ.93..1.08m. Distal plantar sourceZ<=.035m removes shin drag into the original Foot/ToeBase ratio, C1 to.08m; preserving the toe split permits forefoot roll. Source geometry/rest/UV unchanged; no generic shoulder or seated-body overlay.','changes':rows,'maximum_influences':max(len(v.groups)for v in body.data.vertices),'maximum_actual_partition_error':max(abs(sum(g.weight for g in v.groups)-1)for v in body.data.vertices),'actual_readback_verified':True}
