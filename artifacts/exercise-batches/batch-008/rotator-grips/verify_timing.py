"""Before/after native whole-hand/forearm timing and exact unchanged spatial endpoints."""
import bpy,sys,json,math,numpy as np,hashlib,gzip
from pathlib import Path
sys.dont_write_bytecode=True
F=Path(__file__).resolve().parent;P=F.parent/'assets/1986';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def load(path):
 bpy.ops.wm.open_mainfile(filepath=str(path));r=bpy.data.objects['RIG_BlenderStudioHuman'];b=bpy.data.objects['SK_BlenderStudioHuman'];r.animation_data.action=bpy.data.actions['Exercise_1986'];r.animation_data.action_slot=r.animation_data.action.slots[0];return b,r,bpy.context.scene

def measure(path):
 b,r,s=load(path);gn={g.index:g.name for g in b.vertex_groups};parts={}
 for side in['Left','Right']:
  parts[side+'_whole_hand']=np.array([v.index for v in b.data.vertices if sum(g.weight for g in v.groups if gn[g.group].startswith(side)and any(x in gn[g.group]for x in['Hand','Thumb','Index','Middle','Ring','Little']))>.7],int);parts[side+'_forearm']=np.array([v.index for v in b.data.vertices if sum(g.weight for g in v.groups if gn[g.group]==side+'ForeArm')>.7],int)
 points=[];steps=[];previous={};entry_bones=[]
 for f in range(61):
  s.frame_set(f+1);bpy.context.view_layer.update();ev=b.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh();p=np.array([v.co[:]for v in me.vertices]);ev.to_mesh_clear();points.append({name:p[idx].mean(0).tolist()for name,idx in parts.items()});entry_bones.append(np.array([pb.matrix for pb in r.pose.bones]))
  for pb in r.pose.bones:
   q=pb.matrix.to_quaternion()
   if pb.name in previous:
    angle=math.degrees(previous[pb.name].rotation_difference(q).angle);steps.append({'frame':f,'seconds':f/30,'interval_seconds':[(f-1)/30,f/30],'joint':pb.name,'degrees':min(angle,360-angle)})
   previous[pb.name]=q.copy()
 rows=[]
 for f in range(151):
  index=f if f<=60 else 60 if f<=90 else 150-f;rows.append({'frame':f,'seconds':f/30,'centroids':points[index]})
 for f,row in enumerate(rows):
  row['speed_m_per_s']={n:float(np.linalg.norm(np.array(row['centroids'][n])-np.array(rows[f-1]['centroids'][n]))*30)for n in parts}if f else{n:0. for n in parts};row['acceleration_m_per_s2']={n:float(np.linalg.norm(np.array(row['centroids'][n])-2*np.array(rows[f-1]['centroids'][n])+np.array(rows[f-2]['centroids'][n]))*900)for n in parts}if f>1 else{n:0. for n in parts}
 maxima={}
 for name in parts:
  vs=max(rows,key=lambda x:x['speed_m_per_s'][name]);ac=max(rows,key=lambda x:x['acceleration_m_per_s2'][name]);maxima[name]={'maximum_speed_m_per_s':vs['speed_m_per_s'][name],'maximum_speed_frame':vs['frame'],'maximum_speed_interval_seconds':[(vs['frame']-1)/30,vs['frame']/30],'maximum_acceleration_m_per_s2':ac['acceleration_m_per_s2'][name],'maximum_acceleration_frame':ac['frame'],'maximum_acceleration_interval_seconds':[(ac['frame']-2)/30,ac['frame']/30]}
 return {'source_sha256':sha(path),'part_source_ids':{n:idx.tolist()for n,idx in parts.items()},'maximum_joint_step':max(steps,key=lambda x:x['degrees']),'maximum_major_joint_step':max((q for q in steps if q['joint']in['LeftArm','LeftForeArm','LeftHand','RightArm','RightForeArm','RightHand']),key=lambda x:x['degrees']),'maxima':maxima,'samples':rows},entry_bones
before,before_bones=measure(F/'timing-baseline/source.blend');after,after_bones=measure(P/'source.blend');assert before['part_source_ids']==after['part_source_ids'];hold_error=float(np.max(abs(before_bones[-1]-after_bones[-1])));assert hold_error<2e-6
#1987 action is unchanged at every integer key; no held1986 pose rerender.
def matrices(path):
 b,r,s=load(path);r.animation_data.action=bpy.data.actions['Exercise_1987'];r.animation_data.action_slot=r.animation_data.action.slots[0];out=[]
 for f in range(151):s.frame_set(f+1);bpy.context.view_layer.update();out.append(np.array([pb.matrix for pb in r.pose.bones]))
 return np.array(out)
unchanged1987=float(np.max(abs(matrices(F/'timing-baseline/source.blend')-matrices(P/'source.blend'))));assert unchanged1987<2e-6
write={'scope':'Actual native skin centroid of frozen original whole-hand/finger and forearm source domains. Entry0..60 evaluated once; exact authored hold and mirror-return derive151-state table. No unchanged hold rerender. Angular steps include all51 actual native bones.','before':before,'after':after,'maximum_held_pose_matrix_error':hold_error,'maximum_1987_all151_matrix_error':unchanged1987,'entry_clock':'entry-timing.json','baseline':'timing-baseline/manifest.json'};(F/'timing-comparison.json').write_text(json.dumps(write,indent=2)+'\n');print(json.dumps({'before':{'joint':before['maximum_joint_step'],'maxima':before['maxima']},'after':{'joint':after['maximum_joint_step'],'maxima':after['maxima']},'hold_error':hold_error,'unchanged1987':unchanged1987}))
