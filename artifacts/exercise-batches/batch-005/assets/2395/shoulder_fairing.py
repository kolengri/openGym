"""One bounded additive shoulder component; preserve source/support components."""
import hashlib,json
from pathlib import Path
import bpy,numpy as np
from mathutils import Quaternion,Vector
STATES=[('JointNeutral',0),('JointRightCross',37.5),('JointLeftCross',112.5)]
P=Path(__file__).resolve().parent

def feather(value,inner,outer):
 t=np.clip((np.asarray(value)-inner)/(outer-inner),0,1)
 return 1-t*t*(3-2*t)

def points(body):
 evaluated=body.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=evaluated.to_mesh()
 value=np.array([v.co[:]for v in mesh.vertices]);evaluated.to_mesh_clear();return value

def dq_rotation(body,rig,index):
 terms=[]
 for group in body.data.vertices[index].groups:
  if group.weight<=1e-8:continue
  name=body.vertex_groups[group.group].name
  q=(rig.pose.bones[name].matrix@rig.data.bones[name].matrix_local.inverted()).to_quaternion()
  terms.append((group.weight,q))
 reference=max(terms,key=lambda row:row[0])[1];value=np.zeros(4)
 for weight,q in terms:value+=np.array(q)*weight*(-1 if q.dot(reference)<0 else 1)
 q=Quaternion(value);q.normalize();return q

def install(body,rig,scene,component_name='shoulder-additive-component'):
 """Capture once on the settled hip/body, then add to the existing three keys."""
 original=np.array([v.co[:]for v in body.data.vertices]);foundation={n:np.array([v.co[:]for v in body.data.shape_keys.key_blocks[n].data])for n,_ in STATES}
 protected=set(json.loads((P/'support-protected-domain.json').read_text())['protected_source_ids'])
 mask=np.zeros(len(original))
 for side in ['Left','Right']:
  centre=np.array(rig.data.bones[side+'Arm'].head_local)
  local=feather(np.linalg.norm((original-centre)/np.array([.18,.18,.22]),axis=1),.45,1)
  local*=feather(-abs(original[:,0]),-.12,-.08)
  mask=np.maximum(mask,local)
 mask*=feather(-original[:,2],-1.31,-1.26)*.65
 ids=np.flatnonzero(mask>0);assert not(set(ids)&protected),'Shoulder domain overlaps frozen support'
 fair=next(m for m in body.modifiers if m.type=='CORRECTIVE_SMOOTH')
 reports=[];deltas=[]
 for name,frame in STATES:
  scene.frame_set(int(frame)+1,subframe=frame%1);bpy.context.view_layer.update()
  for m in body.modifiers:m.show_viewport=m.show_render=m.type=='ARMATURE'
  arm=next(m for m in body.modifiers if m.type=='ARMATURE');arm.use_deform_preserve_volume=True
  bpy.context.view_layer.update();base=points(body)
  fair.factor=1;fair.iterations=30;fair.show_viewport=fair.show_render=True
  bpy.context.view_layer.update();target=points(body)
  fair.show_viewport=fair.show_render=False;bpy.context.view_layer.update()
  world=(target-base)*mask[:,None];raw=np.linalg.norm(world,axis=1)
  # Squat's C1 saturation: identity through20mm; flat25mm from30mm.
  cap=.025;t=np.clip((raw-.8*cap)/(.4*cap),0,1)
  bounded=np.where(raw<=.8*cap,raw,np.where(raw>=1.2*cap,cap,.8*cap+.4*cap*(t-.5*t*t)))
  world*=np.divide(bounded,raw,out=np.ones_like(raw),where=raw>1e-12)[:,None]
  delta=np.zeros_like(original)
  for index in ids:delta[index]=dq_rotation(body,rig,int(index)).inverted()@Vector(world[index])
  lengths=np.linalg.norm(delta,axis=1)
  # Unit-DQ float32 rotation can add nanometers to a saturated25mm vector.
  # Enforce the same construction cap after that numerical transport.
  numerical_excess=float(max(0,lengths.max()-cap));assert numerical_excess<1e-7
  delta*=np.minimum(1,np.divide(cap,lengths,out=np.ones_like(lengths),where=lengths>1e-12))[:,None]
  assert np.linalg.norm(delta,axis=1).max()<=cap+1e-12
  assert np.all(delta[list(protected)]==0)
  deltas.append(delta)
  reports.append({'key':name,'frame':frame,'maximum_uncapped_diagnostic_displacement_m':float(raw.max()),'unit_DQ_float32_cap_roundoff_removed_m':numerical_excess,'maximum_additive_rest_delta_m':float(np.linalg.norm(delta,axis=1).max()),'changed_source_ids':np.flatnonzero(np.linalg.norm(delta,axis=1)>1e-8).tolist(),'foundation_sha256_float32':hashlib.sha256(foundation[name].astype(np.float32).tobytes()).hexdigest()})
 # No original component is removed. The separate archive carries exactly this
 # shoulder-only addition, not a replacement key or inverse-LBS projection.
 for (name,_),delta in zip(STATES,deltas):
  body.data.shape_keys.key_blocks[name].data.foreach_set('co',(foundation[name]+delta).astype(np.float32).ravel())
 np.savez_compressed(P/(component_name+'.npz'),source_ids=ids.astype(np.int32),source_basis=original[ids].astype(np.float32),deltas=np.array(deltas)[:,ids],foundation_buffers=np.array([foundation[n]for n,_ in STATES]).astype(np.float32))
 report={'method':'One native CorrectiveSmooth diagnostic, factor1/30iterations, restricted to C1 ellipsoidal source shoulder neighborhoods;65% strength; inverse unit-DQ rotation; squat C1 source cap25mm. Additive to the exact existing three composed buffers, with original151weights.','analogues':['../1512/local_correctives.py','../3948/joint_correctives.py'],'domain':'Source Arm-head ellipsoids radii[180,180,220]mm; shoulder central|X|<=80mm excluded, feather80..120mm; inner45% plateau/outer100% zero. SourceZ<=1.26m excluded with a C1 collar to1.31m, separating the shared posterior support domain. No hip, knee, head, hand, floor or root edits.','mask_source_ids':ids.tolist(),'protected_shared_support_ids':sorted(protected),'protected_maximum_additive_delta_m':0.,'outside_mask_maximum_additive_delta_m':0.,'new_component_cap_m':.025,'states':reports,'component_archive':component_name+'.npz','component_archive_sha256':hashlib.sha256((P/(component_name+'.npz')).read_bytes()).hexdigest(),'original_buffers_preserved_as_components':True,'global_corrective_smooth_disabled':True}
 (P/(component_name+'.json')).write_text(json.dumps(report,indent=2)+'\n')
 for m in body.modifiers:m.show_viewport=m.show_render=m.type=='ARMATURE'
 scene.frame_set(1);bpy.context.view_layer.update()
 return report
