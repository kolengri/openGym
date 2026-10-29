"""Actual native circle direction, stationarity and relaxed-clavicle witnesses."""
import numpy as np,math
class CircleChecks:
 def __init__(self,b,r):
  self.r=r;self.soles={};self.rows=[];self.initial={};self.maximum_sole_drift=0.;self.maximum_shoulder_drift=0.;self.previous_hand={};names={g.index:g.name for g in b.vertex_groups}
  for side in ['Left','Right']:self.soles[side]=np.array([v.index for v in b.data.vertices if v.co.z<.10 and sum(g.weight for g in v.groups if names[g.group]in[side+'Foot',side+'ToeBase'])>.5],int)
 def sample(self,p,f):
  fail=[];row={'frame':f,'sides':{}}
  for side in self.soles:
   shoulder=np.array(self.r.pose.bones[side+'Arm'].head);clavicle=np.array(self.r.pose.bones[side+'Shoulder'].head);wrist=np.array(self.r.pose.bones[side+'Hand'].head);delta=wrist-shoulder;radius=float(np.linalg.norm(delta[1:]));angle=math.atan2(-delta[2],-delta[1]);ids=self.soles[side]
   if f==0:self.initial[side]={'sole':p[ids].copy(),'clavicle':clavicle.copy()}
   drift=float(np.linalg.norm(p[ids]-self.initial[side]['sole'],axis=1).max());shif=float(np.linalg.norm(clavicle-self.initial[side]['clavicle']));self.maximum_sole_drift=max(self.maximum_sole_drift,drift);self.maximum_shoulder_drift=max(self.maximum_shoulder_drift,shif)
   if drift>.0001:fail.append(f'frame{f}: {side} stationary sole skin drift {drift}')
   if shif>.0001:fail.append(f'frame{f}: {side} clavicle head drifts/shrugs {shif}')
   row['sides'][side]={'radius_m':radius,'angle_radians':angle,'sole_skin_drift_m':drift,'clavicle_head_drift_m':shif}
  self.rows.append(row);return {'actual_circle':row['sides']},fail
 def finish(self):
  fail=[];summary={'maximum_stationary_sole_skin_drift_m':self.maximum_sole_drift,'maximum_clavicle_head_drift_m':self.maximum_shoulder_drift,'sides':{},'source_repetitions_before_reverse':[10,15],'authored_demo_circles_per_direction':3}
  for side in self.soles:
   angle=np.unwrap([x['sides'][side]['angle_radians']for x in self.rows]);r=np.array([x['sides'][side]['radius_m']for x in self.rows]);forward=float((angle[120]-angle[0])/(2*math.pi));reverse=float((angle[-1]-angle[120])/(2*math.pi));fd=np.diff(angle[:121]);rd=np.diff(angle[120:]);summary['sides'][side]={'forward_turns':forward,'reverse_turns':reverse,'radius_range_m':[float(r.min()),float(r.max())],'forward_small_to_large_radius_m':[float(r[0]),float(r[120])],'maximum_angular_step_degrees':float(np.max(abs(np.diff(angle)))*180/math.pi),'minimum_forward_angular_step_radians':float(fd.min()),'maximum_reverse_angular_step_radians':float(rd.max())}
   if abs(forward-3)>1e-3 or abs(reverse+3)>1e-3:fail.append(side+' actual circle count/direction mismatch')
   if fd.min()<-.001 or rd.max()>.001:fail.append(side+' circle direction unexpectedly flips')
   if abs(r[0]-.045)>.0001 or abs(r[120]-.14)>.0001:fail.append(side+' circle radius staging mismatch')
  return summary,fail
