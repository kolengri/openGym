"""Six local shoulder pose components; knee uses a static binding repair.

The source-coordinate neighborhoods and C1 cap reuse the accepted0003/2395
construction. Native smoothing only defines local deltas; the saved/exported
proof is Armature-only DQ with explicit POSITION/NORMAL targets.
"""
from pathlib import Path
import math,json,hashlib
import bpy,numpy as np
from mathutils import Quaternion,Vector
P=Path(__file__).resolve().parent
STATES=[('Center',0),('Left',37.5),('Right',112.5)]
def feather(v,a,b):
 t=np.clip((np.asarray(v)-a)/(b-a),0,1);return 1-t*t*(3-2*t)
def points(body):
 e=body.evaluated_get(bpy.context.evaluated_depsgraph_get());m=e.to_mesh();p=np.array([v.co[:]for v in m.vertices]);e.to_mesh_clear();return p
def rotation(body,rig,i):
 terms=[(g.weight,(rig.pose.bones[body.vertex_groups[g.group].name].matrix@rig.data.bones[body.vertex_groups[g.group].name].matrix_local.inverted()).to_quaternion())for g in body.data.vertices[i].groups if g.weight>1e-8];ref=max(terms,key=lambda x:x[0])[1];v=np.zeros(4)
 for w,q in terms:v+=np.array(q)*w*(-1 if q.dot(ref)<0 else 1)
 q=Quaternion(v);q.normalize();return q
def bounded_world(world,cap=.040):
 length=np.linalg.norm(world,axis=1);t=np.clip((length-.8*cap)/(.4*cap),0,1);bound=np.where(length<=.8*cap,length,np.where(length>=1.2*cap,cap,.8*cap+.4*cap*(t-.5*t*t)))
 return world*np.divide(bound,length,out=np.ones_like(length),where=length>1e-12)[:,None]
def partition(f):
 s=math.sin(2*math.pi*f/150);return[1-abs(s),max(0,s),max(0,-s)]
def install(body,rig,scene):
 R=np.array([v.co[:]for v in body.data.vertices]);knee=np.zeros(len(R));shoulder=np.zeros(len(R))
 for side in ['Left','Right']:
  c=np.array(rig.data.bones[side+'Leg'].head_local);d=R-c
  local=feather(abs(d[:,0]),.085,.125)*feather(abs(d[:,2]),.065,.150)
  # Preserve the entire opposite leg and all exterior source rings.
  local*=feather(-np.sign(c[0])*R[:,0],-.06,-.025)
  knee=np.maximum(knee,local)
  c=np.array(rig.data.bones[side+'Arm'].head_local)
  local=feather(np.linalg.norm((R-c)/np.array([.18,.18,.22]),axis=1),.45,1)*feather(-abs(R[:,0]),-.12,-.08)
  shoulder=np.maximum(shoulder,local)
 shoulder*=feather(-R[:,2],-1.31,-1.26)*.65
 assert not np.any((knee>0)&(shoulder>0))
 fair=next(m for m in body.modifiers if m.type=='CORRECTIVE_SMOOTH');deltas={};reports=[]
 def capture(mask,iterations):
  for mod in body.modifiers:mod.show_viewport=mod.show_render=mod.type=='ARMATURE'
  bpy.context.view_layer.update();base=points(body);fair.factor=1;fair.iterations=iterations;fair.show_viewport=fair.show_render=True;bpy.context.view_layer.update();smooth=points(body);fair.show_viewport=fair.show_render=False;bpy.context.view_layer.update()
  raw=(smooth-base)*mask[:,None];world=bounded_world(raw);delta=np.zeros_like(R)
  for i in np.flatnonzero(mask>0):delta[i]=rotation(body,rig,int(i)).inverted()@Vector(world[i])
  # Remove only unit-DQ float roundoff beyond the same40mm construction cap.
  length=np.linalg.norm(delta,axis=1);delta*=np.minimum(1,np.divide(.040,length,out=np.ones_like(length),where=length>1e-12))[:,None]
  return delta,float(np.linalg.norm(raw,axis=1).max())
 for id in ['0006','4354']:
  rig.animation_data.action=bpy.data.actions['Exercise_'+id]
  for name,f in STATES:
   scene.frame_set(int(f)+1,subframe=f%1);bpy.context.view_layer.update();delta,raw=capture(shoulder,30);key='Shoulder'+id+name;deltas[key]=delta;reports.append({'name':key,'frame':f,'maximum_uncapped_delta_m':raw,'maximum_source_delta_m':float(np.linalg.norm(delta,axis=1).max()),'changed_ids':np.flatnonzero(np.linalg.norm(delta,axis=1)>1e-8).tolist()})
 for name,delta in deltas.items():
  key=body.shape_key_add(name=name);key.data.foreach_set('co',(R+delta).astype(np.float32).ravel());key.value=0
 keys=body.data.shape_keys;keys.animation_data_create()
 for id in ['0006','4354']:
  action=bpy.data.actions['Exercise_'+id];slot=action.slots.new(id_type='KEY',name='Source-local joint components '+id);keys.animation_data.action=action;keys.animation_data.action_slot=slot
  rig.animation_data.action=action
  for f in range(151):
   scene.frame_set(f+1);w=partition(f)
   for name in deltas:
    key=keys.key_blocks[name];value=w[[s[0]for s in STATES].index(name.removeprefix('Shoulder'+id))]if name.startswith('Shoulder'+id)else 0;key.value=value;key.keyframe_insert('value',frame=f+1)
  for layer in action.layers:
   for strip in layer.strips:
    for bag in strip.channelbags:
     for fc in bag.fcurves:
      for point in fc.keyframe_points:point.interpolation='LINEAR'
 np.savez_compressed(P/'joint-components.npz',source_basis=R.astype(np.float32),knee_mask=knee,shoulder_mask=shoulder,**deltas)
 report={'method':'Six shoulder-only compact targets from source-local original-cage CorrectiveSmooth, inverse unit-DQ displacement, C1 source collars and radial40mm cap. KneeVolume was rejected and removed; knees use one static harmonic binding field. Three active keys interpolate per action; other3remainzero.','knee_domain':'Source knee-head neighborhoods: absX offset85..125mm and absZ offset65..150mm, smooth C1 collar; opposite-leg exclusion.','shoulder_domain':'Accepted2395 shoulder-head ellipsoid[180,180,220]mm,45..100% radius C1 feather; absX80..120mm and sourceZ1.26..1.31m collars,65% strength.','knee_mask_role':'Protected/disjoint source-domain witness only; no knee delta or key.','source_cap_m':.040,'unchanged_exterior_basis_rest_uv_ids':True,'global_smoothing_disabled':True,'states':reports,'component_archive_sha256':hashlib.sha256((P/'joint-components.npz').read_bytes()).hexdigest()}
 (P/'joint-components.json').write_text(json.dumps(report,indent=2)+'\n');return report
