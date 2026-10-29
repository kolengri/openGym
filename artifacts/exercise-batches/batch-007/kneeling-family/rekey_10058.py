"""Check/rekey the accepted editable source without historical trial dependencies.

Default is read-only comparison of the authored matrices with all241 saved poses.
An explicit --output writes a separate editable file, never the frozen inputs.
"""
from pathlib import Path
import sys
sys.dont_write_bytecode=True
import argparse,json,bpy,numpy as np
P=Path(__file__).resolve().parent;sys.path.insert(0,str(P));sys.path.insert(0,str(P.parents[1]/'batch-003'))
import authoring as a
from kneel10058_motion import KneelingMotion
parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path);args=parser.parse_args(sys.argv[sys.argv.index('--')+1:]if '--'in sys.argv else [])
source=P.parent/'assets/10058/source.blend'
if args.output:assert args.output.resolve()not in {source.resolve(),(P/'kneel10-source.blend').resolve()},'Frozen source cannot be overwritten'
a.initialize();bpy.ops.wm.open_mainfile(filepath=str(source));a.body=bpy.data.objects['SK_BlenderStudioHuman'];a.rig=bpy.data.objects['RIG_BlenderStudioHuman'];a.scene=bpy.context.scene
motion=KneelingMotion(a);states=json.loads((P/'kneel10-state.json').read_text())
for frame,st in states.items():
 rear='Right'if st['active']=='Left'else'Left';motion.knee_heights[('10058',int(frame))]=st['feet'][rear]['knee'][2]
maximum=0.;poses=[]
for frame in range(241):
 a.scene.frame_set(frame+1);bpy.context.view_layer.update();native={pb.name:np.array(pb.matrix)for pb in a.rig.pose.bones}
 desired,_,_=motion.pose('10058',frame)
 maximum=max(maximum,max(float(abs(np.array(desired[n])-native[n]).max())for n in native));poses.append({p.name:(p.location.copy(),p.rotation_quaternion.copy(),p.scale.copy())for p in a.rig.pose.bones})
assert maximum<2e-5,maximum
if args.output:
 a.rig.animation_data_clear()
 for action in list(bpy.data.actions):bpy.data.actions.remove(action)
 action=bpy.data.actions.new('Exercise_10058');action.use_fake_user=True;a.rig.animation_data_create();a.rig.animation_data.action=action;previous={}
 for frame,pose in enumerate(poses):
  a.scene.frame_set(frame+1)
  for pb in a.rig.pose.bones:
   pb.location,pb.rotation_quaternion,pb.scale=pose[pb.name]
   if pb.name in previous and pb.rotation_quaternion.dot(previous[pb.name])<0:pb.rotation_quaternion.negate()
   previous[pb.name]=pb.rotation_quaternion.copy()
   for prop in ['location','rotation_quaternion','scale']:pb.keyframe_insert(prop,frame=frame+1)
 for layer in action.layers:
  for strip in layer.strips:
   for bag in strip.channelbags:
    for curve in bag.fcurves:
     for key in curve.keyframe_points:key.interpolation='LINEAR'
 a.scene.frame_set(1);bpy.ops.wm.save_as_mainfile(filepath=str(args.output.resolve()))
report={'source':'../assets/10058/source.blend','frames':241,'maximum_authored_vs_saved_matrix_error':maximum,'default_read_only':True,'historical_trial_dependencies':False}
(P/'10058-authoring-recheck.json').write_text(json.dumps(report,indent=2)+'\n');print('AUTHORING_RECHECK',json.dumps(report))
