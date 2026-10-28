"""Sample our existing independent motion rig for an SVG-only runtime."""
import bpy,json
from pathlib import Path
P=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P.parent/'athlete-clean-v2/athlete-motion.blend'))
rig=bpy.data.objects['RIG_Athlete']
names=['Hips','Spine','neck','Head','head_end','LeftArm','LeftForeArm','LeftHand','RightArm','RightForeArm','RightHand','LeftUpLeg','LeftLeg','LeftFoot','LeftToeBase','RightUpLeg','RightLeg','RightFoot','RightToeBase']
clips={}
for action in list(bpy.data.actions):
    rig.animation_data.action=action
    if len(action.slots):rig.animation_data.action_slot=action.slots[0]
    end=int(action.frame_range[1]);frames=[]
    for frame in range(1,end+1,2):
        bpy.context.scene.frame_set(frame);bpy.context.view_layer.update()
        frames.append([[round(v,5) for v in (rig.matrix_world@rig.pose.bones[name].head)] for name in names])
    if (end-1)%2:
        bpy.context.scene.frame_set(end);bpy.context.view_layer.update()
        frames.append([[round(v,5) for v in (rig.matrix_world@rig.pose.bones[name].head)] for name in names])
    clips[action.name]={'duration':round((end-1)/30,3),'frames':frames}
(P/'poses.json').write_text(json.dumps({'joints':names,'fps':15,'clips':clips},separators=(',',':')))
print({name:len(clip['frames']) for name,clip in clips.items()})
