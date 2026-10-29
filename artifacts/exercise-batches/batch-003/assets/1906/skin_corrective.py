"""One bounded left hip/knee pose corrective; Basis and original weights unchanged."""
import bpy,json,math
import numpy as np
from mathutils import Matrix

def smoothstep(x):
 x=np.clip(x,0,1);return x*x*(3-2*x)
def window(x,a,b,c,d):return smoothstep((x-a)/(b-a))*(1-smoothstep((x-c)/(d-c)))
def apply(body,rig,scene,report_path):
 assert body.data.shape_keys is None,'Refuse to stack or overwrite existing correctives'
 N=len(body.data.vertices);R=np.array([v.co for v in body.data.vertices],float)
 before={m.name:(m.show_viewport,m.show_render) for m in body.modifiers}
 smooth=next(m for m in body.modifiers if m.type=='CORRECTIVE_SMOOTH');oldfactor,olditers=smooth.factor,smooth.iterations
 def positions():
  bpy.context.view_layer.update();ob=body.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ob.to_mesh();p=np.array([v.co for v in me.vertices],float);ob.to_mesh_clear();assert len(p)==N;return p
 scene.frame_set(76)
 for m in body.modifiers:m.show_viewport=m.type=='ARMATURE';m.show_render=m.type=='ARMATURE'
 linear=positions()
 smooth.show_viewport=True;smooth.factor=.5;smooth.iterations=5
 desired=positions()
 for m in body.modifiers:m.show_viewport=m.type=='ARMATURE'
 smooth.factor,smooth.iterations=oldfactor,olditers
 # Feathered anatomical neighborhoods; no opposite-side or distal-leg correction.
 hip=window(R[:,2],.73,.79,.99,1.05)*window(R[:,0],-.025,.025,.23,.29)
 knee=window(R[:,2],.36,.42,.56,.62)*window(R[:,0],.025,.065,.23,.28)
 mask=np.maximum(hip,knee)
 world_delta=(desired-linear)*mask[:,None]
 skin={pb.name:np.array(pb.matrix@pb.bone.matrix_local.inverted(),float) for pb in rig.pose.bones}
 delta=np.zeros_like(R);conditions=[]
 for v in body.data.vertices:
  if mask[v.index]<1e-8:continue
  M=sum((g.weight*skin[body.vertex_groups[g.group].name] for g in v.groups),np.zeros((4,4)))
  cond=float(np.linalg.cond(M[:3,:3]));conditions.append(cond)
  assert cond<5,'Unstable inverse linear skin matrix'
  delta[v.index]=np.linalg.solve(M[:3,:3],world_delta[v.index])
 maxdelta=float(np.linalg.norm(delta,axis=1).max())
 print('CORRECTIVE_BOUND',maxdelta,max(conditions),flush=True)
 assert maxdelta<.025,'Reject large rest-space offset'
 basis=body.shape_key_add(name='Basis',from_mix=False)
 key=body.shape_key_add(name='LeftHipKnee_Soften',from_mix=False)
 key.data.foreach_set('co',(R+delta).astype(np.float32).ravel())
 keys=body.data.shape_keys;keys.animation_data_create();act=rig.animation_data.action;keys.animation_data.action=act
 slot=act.slots.new(id_type='KEY',name=keys.name);keys.animation_data.action_slot=slot
 for f in range(151):
  t=min(f/30,5-f/30)
  # Compression starts with knee flexion; full correction before the hold.
  w=float(smoothstep(t/1.55))
  key.value=w;key.keyframe_insert('value',frame=f+1)
 for layer in act.layers:
  for strip in layer.strips:
   for bag in strip.channelbags:
    for fc in bag.fcurves:
     for k in fc.keyframe_points:k.interpolation='LINEAR'
 for m in body.modifiers:m.show_viewport,m.show_render=before[m.name]
 assert np.array_equal(np.array([v.co for v in body.data.vertices]),R.astype(np.float32))
 assert len(bpy.data.actions)==1 and act.name=='Exercise_1906'
 scene.frame_set(1)
 report={'morph':'LeftHipKnee_Soften','count':1,'basis_rest_unchanged':True,'weights_unchanged':True,'rig_bones':len(rig.data.bones),'affected_vertices':int(np.count_nonzero(np.linalg.norm(delta,axis=1)>1e-7)),'max_rest_offset_m':maxdelta,'p99_nonzero_rest_offset_m':float(np.quantile(np.linalg.norm(delta,axis=1)[mask>1e-8],.99)),'max_inverse_lbs_condition_number':max(conditions),'max_posed_target_displacement_m':float(np.linalg.norm(world_delta,axis=1).max()),'target':'Localized existing native CorrectiveSmooth cage, originalfactor0.5/5iterations, feathered to selected hip and knee only. Original native modifier settings restored.','activation':'0atstart/end; smooth flexion-entry weighting, full before hold; one shared action with Key slot.'}
 report_path.write_text(json.dumps(report,indent=2)+'\n');return report
