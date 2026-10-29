import bpy,json,numpy as np,math
from pathlib import Path
F=Path(__file__).resolve().parent;bpy.ops.wm.open_mainfile(filepath=str(F/'source.blend'));r=bpy.data.objects['RIG_BlenderStudioHuman'];b=bpy.data.objects['SK_BlenderStudioHuman'];s=bpy.context.scene;r.animation_data.action=bpy.data.actions['Exercise_4437'];r.animation_data.action_slot=r.animation_data.action.slots[0];rows=[]
for f in [0,3,7,10,16,23,35]:
 s.frame_set(f+1);bpy.context.view_layer.update();angles={}
 for side in ['Left','Right']:
  h=r.pose.bones[side+'UpLeg'].head;k=r.pose.bones[side+'Leg'].head;a=r.pose.bones[side+'Foot'].head;angles[side]={'knee_flexion_degrees':180-(h-k).angle(a-k)*180/math.pi,'hip_knee_m':(k-h).length,'knee_ankle_m':(a-k).length,'hip':h[:],'knee':k[:],'ankle':a[:]}
 rows.append({'frame':f,'angles':angles})
rest=np.array([v.co[:]for v in b.data.vertices]);ws={}
for side,sgn in [('Left',1),('Right',-1)]:
 rows2=[]
 for v in b.data.vertices:
  if .40<v.co.z<.60 and v.co.x*sgn>0:
   w={b.vertex_groups[g.group].name:g.weight for g in v.groups};rows2.append({'id':v.index,'source_coordinate':v.co[:],'weights':w})
 ws[side]=rows2
out={'angles':rows,'source_knee_weights':ws,'leg_lengths':{side:[r.data.bones[side+x].length for x in ['UpLeg','Leg']]for side in ['Left','Right']}}
(F/'knee-diagnosis.json').write_text(json.dumps(out,indent=2));print(json.dumps({'angles':rows,'leg_lengths':out['leg_lengths']}))
