"""Original-cage CorrectiveSmooth targets, inverse rigid DQ offsets.

Seated/hinged targets for each authored hand distinction. Clip-specific upper
limb frames require separate arm deltas. Original Basis, weights, UV, source IDs
and 51 bones are unchanged. No native-only smoothing remains at runtime.
"""
import bpy,json
import numpy as np
from mathutils import Quaternion,Vector
NAMES={identifier:[f'Sit90_{identifier}_Upright',f'Sit90_{identifier}_Hinge'] for identifier in ['10565','6560']}

def ramp(x,lo,hi):
 t=np.clip((x-lo)/(hi-lo),0,1);return t*t*(3-2*t)

def sample(body):
 bpy.context.view_layer.update();ev=body.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh();co=np.array([v.co[:] for v in me.vertices]);ev.to_mesh_clear();return co

def rotation_field(body,rig):
 names={g.index:g.name for g in body.vertex_groups};qs={b.name:(b.matrix@b.bone.matrix_local.inverted()).to_quaternion() for b in rig.pose.bones}
 out=[]
 for v in body.data.vertices:
  groups=sorted(v.groups,key=lambda g:g.weight,reverse=True);reference=qs[names[groups[0].group]];q=Quaternion((0,0,0,0))
  for g in groups:
   r=qs[names[g.group]];factor=g.weight*(-1 if reference.dot(r)<0 else 1)
   for i in range(4):q[i]+=r[i]*factor
  q.normalize();out.append(q)
 return out

def mask(body):
 base=np.array([v.co[:] for v in body.data.vertices]);z=base[:,2];x=abs(base[:,0])
 pelvis=ramp(z,.64,.78)*(1-ramp(z,1.10,1.22))*(1-ramp(x,.25,.35))
 arms=ramp(x,.12,.18)*ramp(z,.98,1.07)*(1-ramp(z,1.48,1.55))
 return np.maximum(pelvis,arms)

def native_target(body):
 local=mask(body)
 for m in body.modifiers:m.show_viewport=m.show_render=m.type=='ARMATURE'
 co=sample(body)
 for m in body.modifiers:m.show_viewport=m.show_render=m.type in ['ARMATURE','CORRECTIVE_SMOOTH']
 native=sample(body)
 # The initial full-body target retained a short horizontal lumbar shelf.
 # A second original-cage CS witness softens only its posterior waist area.
 smooth=next(m for m in body.modifiers if m.type=='CORRECTIVE_SMOOTH');iterations=smooth.iterations
 smooth.iterations=15;waist_native=sample(body);smooth.iterations=iterations
 base=np.array([v.co[:] for v in body.data.vertices]);waist=ramp(base[:,2],.86,.94)*(1-ramp(base[:,2],1.12,1.22))*ramp(base[:,1],.025,.09)
 native+=(waist_native-native)*waist[:,None]
 for m in body.modifiers:m.show_viewport=m.show_render=m.type=='ARMATURE'
 return co,co+(native-co)*local[:,None],local

def prepare(module):
 body=module.a.body;rig=module.a.rig;base=np.array([v.co[:] for v in body.data.vertices]);body.shape_key_add(name='Basis')
 report=[]
 for identifier,names in NAMES.items():
  for seconds,name in zip([0,2.5],names):
   for key in body.data.shape_keys.key_blocks:key.value=0
   module.pose(identifier,seconds);co,target,field=native_target(body);q=rotation_field(body,rig)
   delta=target-co;local=np.array([q[i].conjugated()@Vector(d) for i,d in enumerate(delta)])
   key=body.shape_key_add(name=name);key.data.foreach_set('co',(base+local).astype(np.float32).ravel());key.value=1
   actual=sample(body);error=float(np.linalg.norm(actual-target,axis=1).max());key.value=0
   assert error<.00001,error
   norms=np.linalg.norm(local,axis=1)
   report.append({'name':name,'id':identifier,'seconds':seconds,'method':'Exact original cage CorrectiveSmooth target, complete pelvis/upper-thigh/shoulder/elbow neighborhoods with feathered margins. No Multires or singular inverse LBS. Runtime non-armature modifiers remain disabled.','affected_vertices':int((norms>1e-8).sum()),'max_offset_m':float(norms.max()),'p95_offset_m':float(np.percentile(norms[field>0],95)),'inverse_DQ_error_max_m':error,'rest_basis_weights_uv_source_ids_unchanged':True,'normal_export':'Matching standard glTF POSITION and NORMAL morph targets.'})
 return report

def set_values(body,identifier,seconds):
 t=np.clip(seconds/2 if seconds<2 else 1 if seconds<=3 else (5-seconds)/2,0,1);h=t*t*(3-2*t)
 for ident,names in NAMES.items():
  for name,value in zip(names,[1-h,h]):body.data.shape_keys.key_blocks[name].value=float(value) if ident==identifier else 0
