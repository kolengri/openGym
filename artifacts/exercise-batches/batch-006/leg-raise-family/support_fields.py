"""Compact pose-specific DQ support fields for straight-leg and toe-reach actions."""
import math,json,hashlib
from pathlib import Path
import numpy as np
from mathutils import Quaternion,Vector
P=Path(__file__).resolve().parent
GROUP_KEYS={'raise':['SupportRaiseNeutral','SupportRaiseLeft','SupportRaiseRight'],'toe':['SupportToeNeutral','SupportToeLeft','SupportToeRight']}

def family(exercise_id):return'toe'if str(exercise_id)=='5106'else'raise'

def schedule(frame):
 s=max(-1.,min(1.,math.sin(2*math.pi*frame/150)))
 return np.array([1-abs(s),max(0,s),max(0,-s)])

def rotation(body,rig,index,rest):
 terms=[(g.weight,(rig.pose.bones[body.vertex_groups[g.group].name].matrix@rest[body.vertex_groups[g.group].name].inverted()).to_quaternion())for g in body.data.vertices[index].groups if g.weight>1e-8]
 reference=max(terms,key=lambda t:t[0])[1];value=np.zeros(4)
 for weight,q in terms:value+=np.array(q)*weight*(-1 if q.dot(reference)<0 else 1)
 q=Quaternion(value);q.normalize();return q

def install(body):
 data=np.load(P/'support-fields.npz');ids=data['source_ids'];basis=np.array([v.co[:]for v in body.data.vertices],np.float32);assert np.array_equal(basis[ids],data['source_basis'])
 assert body.data.shape_keys is None,'New canonical foundation must have no inherited pose targets.'
 body.shape_key_add(name='Basis',from_mix=False);receipt=[]
 for group,names in GROUP_KEYS.items():
  for state,name in enumerate(names):
   delta=data[group+'_deltas'][state];points=basis.copy();points[ids]+=delta;key=body.shape_key_add(name=name,from_mix=False);key.data.foreach_set('co',points.ravel());key.value=0
   actual=np.array([v.co[:]for v in key.data],np.float32);assert np.array_equal(actual,points)
   receipt.append({'key':name,'maximum_rest_delta_m':float(np.linalg.norm(delta,axis=1).max()),'changed_source_ids':ids[np.linalg.norm(delta,axis=1)>1e-8].tolist(),'target_sha256_float32':hashlib.sha256(actual.tobytes()).hexdigest(),'composition':'Canonical unchanged Basis + declared sparse pose-specific support delta. No original pose target exists in this canonical foundation.'})
 assert np.array_equal(basis,np.array([v.co[:]for v in body.data.vertices],np.float32));return receipt

def set_values(body,frame,exercise_id):
 active=family(exercise_id);w=schedule(frame)
 for group,names in GROUP_KEYS.items():
  for index,name in enumerate(names):body.data.shape_keys.key_blocks[name].value=float(w[index])if group==active else 0.
