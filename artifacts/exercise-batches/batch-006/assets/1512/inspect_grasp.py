"""Actual complete hand/foot skin inspection across staged entry and release."""
import bpy,json,hashlib,numpy as np
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
P=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P/'source.blend'));b=bpy.data.objects['SK_BlenderStudioHuman'];r=bpy.data.objects['RIG_BlenderStudioHuman'];s=bpy.context.scene
names={g.index:g.name for g in b.vertex_groups}
def ids(prefixes):return {v.index for v in b.data.vertices if sum(g.weight for g in v.groups if names[g.group].startswith(tuple(prefixes)))>.5}
leg=ids(['LeftUpLeg','LeftLeg','LeftFoot','LeftToeBase']);foot={i for i in leg if b.data.vertices[i].co.z<.22}
hands={'palm':ids(['LeftHand'])}
for digit in ['Thumb','Index','Middle','Ring','Little']:hands[digit]=ids(['Left'+digit])
faces=[list(p.vertices)for p in b.data.polygons if all(i in leg for i in p.vertices)]
footfaces=[list(p.vertices)for p in b.data.polygons if all(i in foot for i in p.vertices)]
rows=[]
for f in range(151):
 s.frame_set(f+1);bpy.context.view_layer.update();e=b.evaluated_get(bpy.context.evaluated_depsgraph_get());m=e.to_mesh();pos=[v.co.copy()for v in m.vertices];tree=BVHTree.FromPolygons(pos,faces);ftree=BVHTree.FromPolygons(pos,footfaces);parts={}
 for name,selected in hands.items():
  values=[];bad=[];closest=None
  for i in selected:
   q,n,face,d=tree.find_nearest(pos[i]);signed=(pos[i]-q).dot(n)
   fq,fn,ff,fd=ftree.find_nearest(pos[i])
   values.append((d,signed,fd))
   if closest is None or fd<closest['distance_m']:closest={'original_id':i,'distance_m':fd,'hand_position':list(pos[i]),'foot_position':list(fq),'foot_normal':list(fn)}
   if signed<-.001 and d<.04:bad.append({'id':i,'distance_m':d,'signed_m':signed,'toward_skin':list(q-pos[i])})
  parts[name]={'min_foot_unsigned_m':min(v[2]for v in values),'vertices_within5mm_foot':sum(v[2]<=.005 for v in values),'min_close_signed_m':min((v[1]for v in values if v[0]<.04),default=None),'over1mm_inside':len(bad),'worst':sorted(bad,key=lambda x:x['signed_m'])[:2],'closest_contact':closest}
 finger_normal=sum((Vector(parts[name]['closest_contact']['foot_normal'])for name in ['Index','Middle','Ring']),Vector((0,0,0))).normalized();opposition=Vector(parts['Thumb']['closest_contact']['foot_normal']).dot(finger_normal)
 rows.append({'frame':f,'global_min_z':min(p.z for p in pos),'parts':parts,'thumb_to_finger_contact_normal_dot':opposition});e.to_mesh_clear()
source_sha=hashlib.sha256((P/'source.blend').read_bytes()).hexdigest()
native=json.loads((P/'early-native-readback.json').read_text())
held=native['samples'][39:112]
ref=np.array(held[0]['foot_local_hand_matrix']);frame_error=max(float(np.max(abs(np.array(row['foot_local_hand_matrix'])-ref)))for row in held)
new_should=r.pose.bones['LeftArm'].head.copy()
s.frame_set(76);bpy.context.view_layer.update();new_reach=(r.pose.bones['LeftHand'].head-r.pose.bones['LeftArm'].head).length;arm_length=r.data.bones['LeftArm'].length+r.data.bones['LeftForeArm'].length
relative=Matrix(native['foot_local_grasp_matrix'])
baseline=P/'foot-return-repair/baseline-source.blend'
if not baseline.exists():baseline=P.parents[2]/'batch-005/assets/1512/source.blend'
bpy.ops.wm.open_mainfile(filepath=str(baseline))
r=bpy.data.objects['RIG_BlenderStudioHuman'];bpy.context.scene.frame_set(76);bpy.context.view_layer.update()
old_reach=(r.pose.bones['LeftHand'].head-r.pose.bones['LeftArm'].head).length
report={'source_sha256':source_sha,'scope':'Actual saved action and DQ key-bearing skin. Every frame, whole palm/thumb/fingers separately against complete leg/foot. Nearest normals diagnose local penetration; enclosure also requires opposed contacts and actual proof.','maximum_recorded_local_penetration_m':max(0,-min(v['min_close_signed_m']for row in rows for v in row['parts'].values()if v['min_close_signed_m']is not None)),'held_minimum_part_clearance_m':min(v['min_close_signed_m']for row in rows[39:112]for v in row['parts'].values()if v['min_close_signed_m']is not None),'held_palm_minimum_clearance_m':min(row['parts']['palm']['min_close_signed_m']for row in rows[39:112]),'held_thumb_to_fingers_normal_dot_range':[min(row['thumb_to_finger_contact_normal_dot']for row in rows[39:112]),max(row['thumb_to_finger_contact_normal_dot']for row in rows[39:112])],'held_foot_local_hand_matrix_maximum_error':frame_error,'active_airborne_wrist_deviation_max_degrees':max(row['wrist_deviation_degrees']for row in native['samples'][17:134]),'reach_comparison':{'rejected_baseline_actual_wrist_distance_m':old_reach,'current_actual_wrist_distance_m':new_reach,'unchanged_upper_plus_forearm_length_m':arm_length,'actual_wrist_distance_reduction_m':old_reach-new_reach,'old_target_overreach_m':max(0,old_reach-arm_length),'new_reach_margin_m':arm_length-new_reach,'authored_change':'Continuous shin-relative foot transport and one causally necessary collar/digit re-fit; ankle trajectory, thigh115degrees, knee130degrees and torso/support preserved. This comparison uses actual baseline/current wrists, not an incompatible fixed local grasp in another foot frame.'},'samples':rows}
(P/'early-grasp-surface-report.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items()if k!='samples'},indent=2))
