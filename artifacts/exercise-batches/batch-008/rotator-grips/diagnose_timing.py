"""Diagnose the exact motion interval without rerunning unchanged hold poses."""
import bpy,sys,json,math,hashlib,numpy as np
from pathlib import Path
from mathutils import Vector
sys.dont_write_bytecode=True
F=Path(__file__).resolve().parent;P=F/'timing-baseline'if'--baseline'in sys.argv else F.parent/'assets/1986';bpy.ops.wm.open_mainfile(filepath=str(P/'source.blend'));r=bpy.data.objects['RIG_BlenderStudioHuman'];b=bpy.data.objects['SK_BlenderStudioHuman'];s=bpy.context.scene;r.animation_data.action=bpy.data.actions['Exercise_1986'];r.animation_data.action_slot=r.animation_data.action.slots[0];previous={};rows=[];joint=[];names=['LeftArm','LeftForeArm','LeftHand','RightArm','RightForeArm','RightHand']
for f in range(151):
 s.frame_set(f+1);bpy.context.view_layer.update();row={'frame':f,'seconds':f/30,'joints':{n:{'head':list(r.pose.bones[n].head),'tail':list(r.pose.bones[n].tail)}for n in names}};joint.append(row)
 for pb in r.pose.bones:
  q=pb.matrix.to_quaternion()
  if pb.name in previous:
   angle=math.degrees(previous[pb.name].rotation_difference(q).angle);rows.append({'frame':f,'interval_seconds':[(f-1)/30,f/30],'joint':pb.name,'angular_step_degrees':min(angle,360-angle)})
  previous[pb.name]=q.copy()
rows.sort(key=lambda q:q['angular_step_degrees'],reverse=True);worst=rows[0];f0=worst['frame'];gn={g.index:g.name for g in b.vertex_groups};parts={name:np.array([v.index for v in b.data.vertices if sum(g.weight for g in v.groups if gn[g.group].startswith(name))>.7],int)for name in['LeftHand','LeftForeArm','RightHand','RightForeArm']};surface=[]
for f in range(max(0,f0-4),min(151,f0+5)):
 s.frame_set(f+1);bpy.context.view_layer.update();e=b.evaluated_get(bpy.context.evaluated_depsgraph_get());me=e.to_mesh();p=np.array([v.co[:]for v in me.vertices]);e.to_mesh_clear();surface.append({'frame':f,'seconds':f/30,'centroids':{n:p[ids].mean(0).tolist()for n,ids in parts.items()},'joints':joint[f]['joints']})
for i,row in enumerate(surface):
 row['linear_speed_m_per_s']={n:float(np.linalg.norm(np.array(row['centroids'][n])-np.array(surface[i-1]['centroids'][n]))*30)for n in parts}if i else{}
 row['linear_acceleration_m_per_s2']={n:float(np.linalg.norm(np.array(row['centroids'][n])-2*np.array(surface[i-1]['centroids'][n])+np.array(surface[i-2]['centroids'][n]))*900)for n in parts}if i>1 else{}
report={'source_sha256':hashlib.sha256((P/'source.blend').read_bytes()).hexdigest(),'glb_sha256':hashlib.sha256((P/'motion.glb').read_bytes()).hexdigest(),'worst':worst,'worst24':rows[:24],'actual_native_surface_interval':surface,'all151_joint_heads_tails':joint,'scope':'Native51-joint angular steps plus actual native hand/forearm surface centroids only around worst transition; no unchanged hold reevaluation.'};(F/('timing-diagnosis.json'if'--baseline'in sys.argv else'current-timing-diagnosis.json')).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'worst':worst,'worst_relevant':next(q for q in rows if q['joint']in names),'interval':surface}))
