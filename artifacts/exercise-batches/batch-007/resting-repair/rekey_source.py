"""Read-only authored/saved151-pose check; optional separate editable output.

The delivered source contains the exact original binding and frozen compact
hip component, so no rejected or historical intermediate blend is needed.
"""
from pathlib import Path
import sys
sys.dont_write_bytecode=True
import argparse,json,hashlib,gzip,bpy,numpy as np
P=Path(__file__).resolve().parent;A=P.parent/'assets/4365';sys.path.insert(0,str(P));sys.path.insert(0,str(P.parents[1]/'batch-003'))
import authoring as a
from resting_motion import KneelingMotion
parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path);args=parser.parse_args(sys.argv[sys.argv.index('--')+1:]if '--'in sys.argv else [])
if args.output:assert args.output.resolve()!=(A/'source.blend').resolve(),'Frozen source cannot be overwritten'
a.initialize();bpy.ops.wm.open_mainfile(filepath=str(A/'source.blend'));a.body=bpy.data.objects['SK_BlenderStudioHuman'];a.rig=bpy.data.objects['RIG_BlenderStudioHuman'];a.scene=bpy.context.scene
params=json.loads((P/'motion-parameters.json').read_text());contact=json.loads((P/'contact-solve.json').read_text());activation=json.loads((P/'hip-activation.json').read_text());schedule={row['frame']:row['weight']for row in activation['schedule']};motion=KneelingMotion(a);motion.child_thorax=params['child_thorax_degrees'];motion.palm_height_offset=params['palm_height_offset'];motion.clavicle_correction=params['clavicle_motion']
for row in contact['samples']:motion.knee_heights['4365',row['frame']]=row['knee_z'];motion.foot_offsets[row['frame']]=row['foot_offset']
key=a.body.data.shape_keys.key_blocks['RestingHipVolume'];maximum=0.;maximum_weight=0.;poses=[]
for f in range(151):
 a.scene.frame_set(f+1);bpy.context.view_layer.update();native={pb.name:np.array(pb.matrix)for pb in a.rig.pose.bones};maximum_weight=max(maximum_weight,abs(key.value-schedule[f]));desired,_,_=motion.pose('4365',f);maximum=max(maximum,max(float(abs(np.array(desired[n])-native[n]).max())for n in native));poses.append({pb.name:(pb.location.copy(),pb.rotation_quaternion.copy(),pb.scale.copy())for pb in a.rig.pose.bones})
assert maximum<2e-5 and maximum_weight<1e-6
if args.output:
 a.rig.animation_data_clear();a.body.data.shape_keys.animation_data_clear()
 for action in list(bpy.data.actions):bpy.data.actions.remove(action)
 action=bpy.data.actions.new('Exercise_4365');action.use_fake_user=True;a.rig.animation_data_create();a.rig.animation_data.action=action;keys=a.body.data.shape_keys;keys.animation_data_create();slot=action.slots.new(id_type='KEY',name='Resting hip volume');keys.animation_data.action=action;keys.animation_data.action_slot=slot;previous={}
 for f,pose in enumerate(poses):
  a.scene.frame_set(f+1)
  for pb in a.rig.pose.bones:
   pb.location,pb.rotation_quaternion,pb.scale=pose[pb.name]
   if pb.name in previous and pb.rotation_quaternion.dot(previous[pb.name])<0:pb.rotation_quaternion.negate()
   previous[pb.name]=pb.rotation_quaternion.copy()
   for prop in ['location','rotation_quaternion','scale']:pb.keyframe_insert(prop,frame=f+1)
  key.value=schedule[f];key.keyframe_insert('value',frame=f+1)
 for layer in action.layers:
  for strip in layer.strips:
   for bag in strip.channelbags:
    for curve in bag.fcurves:
     for point in curve.keyframe_points:point.interpolation='LINEAR'
 a.scene.frame_set(1);bpy.ops.wm.save_as_mainfile(filepath=str(args.output.resolve()))
R=np.array([v.co[:]for v in a.body.data.vertices],np.float32);K=np.array([v.co[:]for v in key.data],np.float32);position_ids=np.flatnonzero(np.any(K!=R,axis=1))
with gzip.open(A/'joint-normal-reference.json.gz','rt')as fp:normal=json.load(fp)
normal_delta=np.array(normal['targets']['RestingHipVolume'],np.float32)-np.array(normal['basis'],np.float32);normal_ids=np.flatnonzero(np.linalg.norm(normal_delta,axis=1)>1e-7)
np.savez_compressed(P/'hip-volume-final.npz',position_source_ids=position_ids.astype(np.int32),key_coordinates=K[position_ids],normal_source_ids=normal_ids.astype(np.int32),normal_deltas=normal_delta[normal_ids])
report={'ok':True,'source_sha256':hashlib.sha256((A/'source.blend').read_bytes()).hexdigest(),'frames':151,'maximum_authored_saved_matrix_error':maximum,'maximum_authored_saved_morph_weight_error':maximum_weight,'default_read_only':True,'historical_trial_dependencies':False,'compact_final_component':{'position_ids':len(position_ids),'normal_ids':len(normal_ids),'coordinates':'Exact final float32 source key coordinates, not a reconstructed approximation.'}}
(P/'authoring-recheck.json').write_text(json.dumps(report,indent=2)+'\n');print('AUTHORING_RECHECK',json.dumps(report))
