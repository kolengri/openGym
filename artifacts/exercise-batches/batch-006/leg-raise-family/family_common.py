"""Source-safe bootstrap, anatomical binding replay and native family sampler."""
import json,sys,hashlib
from pathlib import Path
import bpy,numpy as np
P=Path(__file__).resolve().parent;B=P.parent
sys.path[:0]=[str(P),str(B.parent/'batch-003')]
import authoring as a,leg_raise_pose as motion
from binding_core import ProfileBinding
PROFILE=json.loads((P/'source-neutral-envelope.json').read_text())
MASKS=json.loads((P/'source-support-masks.json').read_text())['patches']

def weights(body,index):return{body.vertex_groups[g.group].name:float(g.weight)for g in body.data.vertices[index].groups}

def initialize():
 source_binding=a.initialize();body,rig,scene=a.body,a.rig,a.scene
 for modifier in body.modifiers:
  modifier.show_viewport=modifier.show_render=modifier.type=='ARMATURE'
  if modifier.type=='ARMATURE':modifier.use_deform_preserve_volume=True
 rest=np.array([v.co[:]for v in body.data.vertices])
 core=ProfileBinding(body,rig);core_report=core.apply(.8815200062877445,.9794368639602231,details=True)
 recipe=json.loads((P/'source-glute-binding.json').read_text())
 for item in recipe['changes']:
  i=item['id'];old=weights(body,i);assert old==item['before'],('Glute replay input changed',i,old,item['before'])
  for name in old:body.vertex_groups[name].remove([i])
  for name,value in item['after'].items():body.vertex_groups[name].add([i],value,'REPLACE')
 readback=[weights(body,v.index)for v in body.data.vertices]
 assert max(map(len,readback))<=4 and max(abs(sum(w.values())-1)for w in readback)<2e-6
 assert np.array_equal(rest,np.array([v.co[:]for v in body.data.vertices]))
 return {'source_binding_sha256':source_binding,'runtime_binding_sha256':a.binding_hash(body,rig),'core':core_report,'glute_recipe_sha256':hashlib.sha256((P/'source-glute-binding.json').read_bytes()).hexdigest(),'glute_ids':[v['id']for v in recipe['changes']],'actual_max_influences':max(map(len,readback)),'actual_weight_sum_max_error':max(abs(sum(w.values())-1)for w in readback)}

def posture():return json.loads((P/'pose-parameters.json').read_text())if(P/'pose-parameters.json').exists()else dict(motion.POSTURE)

def coordinates():
 bpy.context.view_layer.update();evaluated=a.body.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=evaluated.to_mesh();points=np.empty(len(mesh.vertices)*3);mesh.vertices.foreach_get('co',points);evaluated.to_mesh_clear();return points.reshape(-1,3)

def sample(frame,exercise_id,p=None):
 assert not a.rig.animation_data or a.rig.animation_data.action is None,'Detach the rig action during manual sampling.'
 a.scene.frame_set(int(frame)+1,subframe=frame%1)
 if a.body.data.shape_keys is not None and 'SupportRaiseNeutral'in a.body.data.shape_keys.key_blocks:
  import support_fields
  support_fields.set_values(a.body,frame,exercise_id)
 desired,meta=motion.pose(a,frame,str(exercise_id),posture()if p is None else p);points=coordinates()
 error=max(float(np.max(abs(np.array(a.rig.pose.bones[n].matrix)-np.array(desired[n]))))for n in desired);assert error<2e-6,('Actual pose overwritten',exercise_id,frame,error)
 return points,{'matrix_max_error':error,'desired':desired,**meta}

def support_metrics(points):
 ids=PROFILE['lower_lumbar_ids'];mid=PROFILE['lower_midline_ids'];ridges=PROFILE['direct_ridge_ids'];depth=np.array([PROFILE['expected_neutral_groove_depth_m'][str(i)]for i in ids]);md=np.array([PROFILE['expected_neutral_groove_depth_m'][str(i)]for i in mid]);adjusted=points[ids,2]-depth
 return {'whole_body_min_z_m':float(points[:,2].min()),'whole_body_min_source_id':int(points[:,2].argmin()),'profile_min_m':float(adjusted.min()),'profile_median_m':float(np.median(adjusted)),'profile_max_m':float(adjusted.max()),'profile_fraction_within5mm':float(np.mean(abs(adjusted)<=.005)),'midline_profile_max_m':float((points[mid,2]-md).max()),'ridge_min_z_m':float(points[ridges,2].min()),'ridge_max_z_m':float(points[ridges,2].max()),'pelvic_min_m':{s:float(points[MASKS['pelvic_support_'+s],2].min())for s in ['L','R']},'raw45_z_m':{str(i):float(points[i,2])for i in MASKS['lumbar_arch']},'failed_flat19_z_m':{str(i):float(points[i,2])for i in MASKS['lumbar_midline']}}
