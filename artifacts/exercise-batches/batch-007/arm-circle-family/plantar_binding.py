"""Only the proven distal plantar recipe; all upper-body weights stay original."""
import numpy as np

def smooth(t):
 t=np.clip(t,0,1);return t*t*(3-2*t)

def apply(body):
 rows=[];oldrows=[{body.vertex_groups[g.group].name:float(g.weight)for g in v.groups}for v in body.data.vertices]
 for v,old in zip(body.data.vertices,oldrows):
  x,y,z=v.co;gate=float((1-smooth((z-.035)/.045))*smooth((abs(x)-.08)/.04))
  if gate<=1e-8:continue
  side='Left'if x>0 else'Right';total=old.get(side+'Foot',0)+old.get(side+'ToeBase',0);target={side+'Foot':old.get(side+'Foot',0)/total if total>1e-8 else 1.,side+'ToeBase':old.get(side+'ToeBase',0)/total if total>1e-8 else 0.};new={n:w*(1-gate)for n,w in old.items()}
  for n,w in target.items():new[n]=new.get(n,0)+w*gate
  new={n:w for n,w in new.items()if w>1e-8};assert len(new)<=4;total=sum(new.values());new={n:w/total for n,w in new.items()}
  if all(abs(old.get(n,0)-new.get(n,0))<1e-8 for n in set(old)|set(new)):continue
  for n in list(old):body.vertex_groups[n].remove([v.index])
  for n,w in new.items():body.vertex_groups[n].add([v.index],float(w),'REPLACE')
  actual={body.vertex_groups[g.group].name:float(g.weight)for g in body.data.vertices[v.index].groups};rows.append({'id':v.index,'source_coordinate_m':v.co[:],'gate':gate,'before':old,'after':actual})
 assert all({body.vertex_groups[g.group].name:float(g.weight)for g in v.groups}==old for v,old in zip(body.data.vertices,oldrows)if v.index not in {x['id']for x in rows})
 return {'method':'Selective reuse of original upright distal plantar sourceZ35..80mm repair, preserving Foot/ToeBase split. No waist, shoulder, arm, Neck or Head weights changed. Stable group-name install; actual readback.','changes':rows,'upper_body_original':True,'maximum_influences':max(len(v.groups)for v in body.data.vertices),'maximum_weight_sum_error':max(abs(sum(g.weight for g in v.groups)-1)for v in body.data.vertices)}
