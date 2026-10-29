"""Saved native ankle-frame regression, paired with actual decoded skin edges."""
from pathlib import Path
import bpy,json,hashlib,math
P=Path(__file__).resolve().parent;B=P.parent
bpy.ops.wm.open_mainfile(filepath=str(P/'source.blend'));r=bpy.data.objects['RIG_BlenderStudioHuman'];s=bpy.context.scene
reports=[]
for id,total in [('1368',360),('2761',150),('2762',150)]:
 r.animation_data.action=bpy.data.actions['Exercise_'+id];first={};previous={};rows=[]
 for f in range(total+1):
  s.frame_set(f+1);bpy.context.view_layer.update();sides={}
  for side in ['Left','Right']:
   leg=r.pose.bones[side+'Leg'].matrix.to_quaternion();foot=r.pose.bones[side+'Foot'].matrix.to_quaternion();toe=r.pose.bones[side+'ToeBase'].matrix.to_quaternion();relative=leg.inverted()@foot;toe_relative=foot.inverted()@toe
   if side not in first:first[side]=(relative.copy(),toe_relative.copy());previous[side]=(foot.copy(),relative.copy())
   angle=lambda a,b:math.degrees(a.rotation_difference(b).angle)
   # Quaternion sign has no geometric meaning; report the shortest angle.
   shortest=lambda a,b:min(angle(a,b),360-angle(a,b))
   row={'shin_relative_excursion_degrees':shortest(first[side][0],relative),'world_foot_step_degrees':shortest(previous[side][0],foot),'shin_relative_step_degrees':shortest(previous[side][1],relative),'rigid_toe_relative_error_degrees':shortest(first[side][1],toe_relative)}
   assert row['shin_relative_excursion_degrees']<35 and row['world_foot_step_degrees']<3 and row['shin_relative_step_degrees']<3 and row['rigid_toe_relative_error_degrees']<.1,(id,f,side,row)
   sides[side]=row;previous[side]=(foot.copy(),relative.copy())
  rows.append({'frame':f,'sides':sides})
 native=json.loads((B/'assets'/id/'surface-contact-report.json').read_text());decoded=json.loads((B/'assets'/id/'decoded-physical-report.json').read_text());assert native['ok']and decoded['ok']
 aggregate={k:max(row['sides'][side][k]for row in rows for side in ['Left','Right'])for k in rows[0]['sides']['Left']}
 edges={kind:{'mixed_ankle_ratio_min':min(row['internal_foot_shape'][side]['ankle_edge_ratio_min']for row in receipt['samples']for side in ['Left','Right']),'mixed_ankle_ratio_max':max(row['internal_foot_shape'][side]['ankle_edge_ratio_max']for row in receipt['samples']for side in ['Left','Right']),'rigid_forefoot_max_fractional_edge_change':max(row['internal_foot_shape'][side]['forefoot_edge_max_change']for row in receipt['samples']for side in ['Left','Right'])}for kind,receipt in [('native',native),('decoded',decoded)]}
 report={'id':id,'ok':True,'source_sha256':hashlib.sha256((P/'source.blend').read_bytes()).hexdigest(),'glb_sha256':decoded['glb_sha256'],'frames':total+1,'maximums':aggregate,'skin_edge_regression':edges,'scope':'Actual saved native shin/Foot/ToeBase frames plus all-frame native and actual decoded internal skin-edge readback. Excursion<35°, step<3° at30fps and constant Foot/ToeBase relation target the late-return hook/roll failure. Mixed ankle edge ratio[0.4,2.5] is an artifact guard, not a clinical or anatomical-quality claim. Forefoot drift<0.002.' ,'samples':rows}
 (B/'assets'/id/'foot-regression.json').write_text(json.dumps(report,indent=2)+'\n');reports.append({k:v for k,v in report.items()if k!='samples'})
(P/'foot-regression-summary.json').write_text(json.dumps(reports,indent=2)+'\n');print(json.dumps(reports,indent=2))
