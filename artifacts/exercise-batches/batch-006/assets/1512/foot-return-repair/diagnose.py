"""Read-only saved-action ankle/foot diagnosis and a few late-pose proofs."""
import bpy,json,hashlib,math,sys
from pathlib import Path
import numpy as np
from mathutils import Vector
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent;ASSET=P.parent
source=P/'baseline-source.blend'if '--baseline-source'in sys.argv else ASSET/'source.blend'
bpy.ops.wm.open_mainfile(filepath=str(source))
b=bpy.data.objects['SK_BlenderStudioHuman'];r=bpy.data.objects['RIG_BlenderStudioHuman'];s=bpy.context.scene
phase='baseline'if '--baseline-source'in sys.argv else 'repaired'
rest=np.array([v.co[:]for v in b.data.vertices]);names={g.index:g.name for g in b.vertex_groups}
w={name:np.array([sum(g.weight for g in v.groups if names[g.group]==name)for v in b.data.vertices])for name in ['LeftLeg','LeftFoot','LeftToeBase']}
foot=np.flatnonzero(w['LeftFoot']+w['LeftToeBase']>.5)
ankle=np.flatnonzero((w['LeftFoot']>.02)&(w['LeftFoot']<.98)&(w['LeftLeg']>.02))
edges=np.array([list(e.vertices)for e in b.data.edges]);ankle_set=set(ankle);foot_set=set(foot)
ae=edges[[any(int(i)in ankle_set for i in e)for e in edges]];fe=edges[[all(int(i)in foot_set for i in e)for e in edges]]
def lengths(pp,ee):return np.linalg.norm(pp[ee[:,0]]-pp[ee[:,1]],axis=1)
ae0=lengths(rest,ae);fe0=lengths(rest,fe)
def skin():
 obj=b.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=obj.to_mesh();pp=np.array([v.co[:]for v in mesh.vertices]);obj.to_mesh_clear();return pp
rows=[];last=None;initial_ankle=None;initial_foot=None
for f in range(151):
 s.frame_set(f+1);bpy.context.view_layer.update();pp=skin();qs={name:r.pose.bones[name].matrix.to_quaternion()for name in ['LeftLeg','LeftFoot','LeftToeBase']}
 local=(qs['LeftLeg'].inverted()@qs['LeftFoot']).normalized();rest_local=r.data.bones['LeftLeg'].matrix_local.to_quaternion().inverted()@r.data.bones['LeftFoot'].matrix_local.to_quaternion();delta=(local@rest_local.inverted()).normalized()
 swing,angle=delta.to_swing_twist('Y');ar=lengths(pp,ae)/ae0;fr=lengths(pp,fe)/fe0
 if initial_ankle is None:initial_ankle=lengths(pp,ae);initial_foot=lengths(pp,fe)
 row={'frame':f,'time_seconds':f/30,'leg_quaternion':list(qs['LeftLeg']),'foot_quaternion':list(qs['LeftFoot']),'toe_quaternion':list(qs['LeftToeBase']),'leg_to_foot_quaternion':list(local),'ankle_delta_angle_degrees':math.degrees(delta.angle),'ankle_swing_degrees':math.degrees(swing.angle),'ankle_twist_degrees':math.degrees(angle),'ankle_edge_ratio_min':float(ar.min()),'ankle_edge_ratio_p01':float(np.percentile(ar,1)),'ankle_edge_ratio_max':float(ar.max()),'ankle_edge_ratio_p99':float(np.percentile(ar,99)),'foot_edge_ratio_min':float(fr.min()),'foot_edge_ratio_max':float(fr.max()),'foot_bounds':{'min':pp[foot].min(axis=0).tolist(),'max':pp[foot].max(axis=0).tolist()},'bone_heads':{name:list(r.pose.bones[name].head)for name in qs}}
 row['ankle_edge_change_from_planted_max']=float(np.max(abs(lengths(pp,ae)/initial_ankle-1)))
 row['foot_edge_change_from_planted_max']=float(np.max(abs(lengths(pp,fe)/initial_foot-1)))
 if last:row['frame_rotation_delta_degrees']={name:min(math.degrees(last[name].rotation_difference(q).angle),360-math.degrees(last[name].rotation_difference(q).angle))for name,q in qs.items()}
 rows.append(row);last=qs
late=[row for row in rows if row['frame']>=105]
report={'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'phase':phase,'ankle_original_ids':ankle.tolist(),'ankle_edges':ae.tolist(),'foot_original_ids':foot.tolist(),'foot_edges':fe.tolist(),'reference':'Original rest edge lengths and actual planted-frame edge lengths; actual saved action DQ skin with current compact keys, no native smoothing.','worst_late_twist':max(late,key=lambda row:abs(row['ankle_twist_degrees'])),'worst_late_compression':min(late,key=lambda row:row['ankle_edge_ratio_min']),'worst_late_stretch':max(late,key=lambda row:row['ankle_edge_ratio_max']),'maximum_late_frame_rotation_delta_degrees':{name:max(row.get('frame_rotation_delta_degrees',{}).get(name,0)for row in late)for name in ['LeftLeg','LeftFoot','LeftToeBase']},'samples':rows}
(P/f'{phase}-native-diagnosis.json').write_text(json.dumps(report,indent=2)+'\n')
for label,f in [('release',111),('return',126),('late',132),('settled',150)]:
 s.frame_set(f+1);bpy.context.view_layer.update();pp=skin();target=Vector(pp[foot].mean(axis=0));camera=s.camera;camera.location=target+Vector((2,-.5,.3));camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.ortho_scale=.51;s.render.filepath=str(P/f'{phase}-{label}-foot.png');bpy.ops.render.render(write_still=True)
 assert float(np.linalg.norm(skin()-pp,axis=1).max())<1e-7
if phase=='repaired':
 for label,f in [('hold',75),('late-return',132)]:
  s.frame_set(f+1);bpy.context.view_layer.update();before=skin();camera=s.camera;target=Vector((0,.02,.43));camera.location=(3.6,-.05,.88);camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.ortho_scale=1.90;s.render.filepath=str(P/f'repaired-{label}-wholebody.png');bpy.ops.render.render(write_still=True);assert float(np.linalg.norm(skin()-before,axis=1).max())<1e-7
print(json.dumps({'phase':phase,'worst_late_twist':report['worst_late_twist'],'worst_late_compression':report['worst_late_compression'],'maximum_late_frame_rotation_delta_degrees':report['maximum_late_frame_rotation_delta_degrees']}))
