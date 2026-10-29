"""Three compact LBS pose-space keys, source-bound native DQ hip/fairing target."""
import bpy,numpy as np,math,json
from pathlib import Path
STATES=[('SquatStanding',0),('SquatHalf',37.5),('SquatParallel',75)]
def smooth(t):t=np.clip(t,0,1);return t*t*(3-2*t)
def band(t,lo,hi,f):return smooth((t-lo)/f)*(1-smooth((t-hi+f)/f))
def set_frame(scene,f):scene.frame_set(int(f)+1,subframe=f%1);bpy.context.view_layer.update()
def coords(body):
 ev=body.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh();x=np.array([v.co[:] for v in me.vertices]);ev.to_mesh_clear();return x
def partition(f):
 q=.5-.5*math.cos(2*math.pi*f/150)
 return [max(0,1-2*q),1-abs(2*q-1),max(0,2*q-1)]
def capture(body,rig,scene):
 R=np.array([v.co[:] for v in body.data.vertices]);arm=next(m for m in body.modifiers if m.type=='ARMATURE');fair=next(m for m in body.modifiers if m.type=='CORRECTIVE_SMOOTH')
 # Source-coordinate C1 collars exclude all feet, fingers, head and distal arms.
 hip=band(R[:,2],.66,1.14,.09)*(1-smooth((abs(R[:,0])-.24)/.045))
 knee=band(R[:,2],.34,.66,.07)*smooth((R[:,1]-.02)/.04)
 shoulder=band(abs(R[:,0]),.08,.39,.065)*band(R[:,2],1.12,1.53,.075)
 fairmask=np.maximum(knee,shoulder);reports=[];deltas=[]
 for name,f in STATES:
  set_frame(scene,f)
  for m in body.modifiers:m.show_viewport=m.show_render=m.type=='ARMATURE'
  arm.use_deform_preserve_volume=False;bpy.context.view_layer.update();base=coords(body)
  arm.use_deform_preserve_volume=True;bpy.context.view_layer.update();dq=coords(body)
  arm.use_deform_preserve_volume=False
  fair.show_viewport=fair.show_render=True;fair.factor=1;fair.iterations=20;bpy.context.view_layer.update();smoothed=coords(body)
  fair.show_viewport=fair.show_render=False;bpy.context.view_layer.update()
  target=base+(dq-base)*hip[:,None]+(smoothed-base)*fairmask[:,None]
  A=np.zeros((len(R),3,3))
  for v in body.data.vertices:
   for g in v.groups:
    n=body.vertex_groups[g.group].name;M=np.array(rig.pose.bones[n].matrix@rig.data.bones[n].matrix_local.inverted())[:3,:3];A[v.index]+=g.weight*M
  changed=np.linalg.norm(target-base,axis=1)>1e-8;delta=np.zeros_like(R);delta[changed]=np.linalg.solve(A[changed],(target-base)[changed,:,None])[:,:,0];length=np.linalg.norm(delta,axis=1);i=int(length.argmax())
  ids=np.flatnonzero(changed);conditions=np.linalg.cond(A[changed]);reports.append({'name':name,'frame':f,'maximum_source_delta_m':float(length.max()),'maximum_source_id':i,'maximum_source_coordinate':R[i].tolist(),'maximum_pose_displacement_m':float(np.linalg.norm(target-base,axis=1).max()),'maximum_inverse_linear_condition':float(conditions.max()),'changed_source_ids':ids.tolist(),'source_bounds':[R[ids].min(0).tolist(),R[ids].max(0).tolist()],'hip_max_source_delta_m':float(np.linalg.norm(delta[hip>1e-8],axis=1).max()),'fairing_max_source_delta_m':float(np.linalg.norm(delta[fairmask>1e-8],axis=1).max()),'domain_maxima':{label:{'source_id':int(np.argmax(np.linalg.norm(delta,axis=1)*(mask>1e-8))),'source_coordinate':R[int(np.argmax(np.linalg.norm(delta,axis=1)*(mask>1e-8)))].tolist(),'required_source_delta_m':float((np.linalg.norm(delta,axis=1)*(mask>1e-8)).max())} for label,mask in {'hip':hip,'knee':knee,'shoulder':shoulder}.items()}})
  deltas.append(delta)
 arm.use_deform_preserve_volume=False
 for m in body.modifiers:m.show_viewport=m.show_render=m.type=='ARMATURE'
 return R,deltas,reports,{'hip':hip,'fairing':fairmask,'knee':knee,'shoulder':shoulder}
def install(body,rig,scene,action,cap=.025):
 R,deltas,reports,masks=capture(body,rig,scene)
 report={'method':'Only native DQ hip target in fixed original source hip domain, plus local native CorrectiveSmooth(20x1.0) target for diagnosed shoulder/popliteal folds. Each displacement mapped through exact inverse LBS3x3; runtime remains standard linear. Three C1-bounded source keys with piecewise-linear partition of flexion.','source_cap_m':cap,'states':reports,'protected':'Feet/ankles below0.34m, fingers/distal hands, head and all exterior vertices exactly excluded; Basis/rest/UV/topology unchanged.','cap_pass':max(x['maximum_source_delta_m'] for x in reports)<=cap}
 # Enforce the authorized25mm source cap in this single construction. The
 # C1 saturation is identity below20mm and flat at25mm from30mm, preserving
 # the already C1-zero source collar and avoiding hard radial clamp rings.
 report['uncapped_target_exceeds_cap']=not report['cap_pass']
 report['cap_pass']=True
 for index,delta in enumerate(deltas):
  length=np.linalg.norm(delta,axis=1);t=np.clip((length-.8*cap)/(.4*cap),0,1)
  bounded=np.where(length<=.8*cap,length,np.where(length>=1.2*cap,cap,.8*cap+.4*cap*(t-.5*t*t)))
  factor=np.divide(bounded,length,out=np.ones_like(length),where=length>1e-12);deltas[index]=delta*factor[:,None]
  reports[index]['applied_maximum_source_delta_m']=float(np.linalg.norm(deltas[index],axis=1).max())
  reports[index]['capped_source_ids']=np.flatnonzero(length>.8*cap).tolist()
 report['cap_method']='C1 radial source-delta saturation: exact below20mm, flat25mm above30mm; no protected/outside movement.'
 body.shape_key_add(name='Basis',from_mix=False)
 for (name,_),delta in zip(STATES,deltas):
  key=body.shape_key_add(name=name,from_mix=False);key.data.foreach_set('co',(R+delta).astype(np.float32).ravel());key.value=0
 keys=body.data.shape_keys;keys.animation_data_create();slot=action.slots.new(id_type='KEY',name='Bounded squat joint targets');keys.animation_data.action=action;keys.animation_data.action_slot=slot
 for f in range(151):
  set_frame(scene,f)
  for (name,_),value in zip(STATES,partition(f)):
   key=keys.key_blocks[name];key.value=value;key.keyframe_insert('value',frame=f+1)
 for layer in action.layers:
  for strip in layer.strips:
   for bag in strip.channelbags:
    for fc in bag.fcurves:
     for point in fc.keyframe_points:point.interpolation='LINEAR'
 set_frame(scene,0);return report
