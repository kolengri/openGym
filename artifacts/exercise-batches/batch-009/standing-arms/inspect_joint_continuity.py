"""Bone-only sign-invariant arm continuity evidence; no skin or mesh QA."""
import bpy,sys,json,math,hashlib,numpy as np,argparse
from pathlib import Path
from mathutils import Vector
sys.dont_write_bytecode=True
F=Path(__file__).resolve().parent
parser=argparse.ArgumentParser();parser.add_argument('--source',required=True);parser.add_argument('--tag',required=True);parser.add_argument('--baseline');parser.add_argument('--id',default='3995',choices=['3995','1404','4515','1405']);args=parser.parse_args(sys.argv[sys.argv.index('--')+1:]);source=Path(args.source);bpy.ops.wm.open_mainfile(filepath=str(source));r=bpy.data.objects['RIG_BlenderStudioHuman'];s=bpy.context.scene
for ob in bpy.data.objects:
 if ob.type=='MESH':ob.hide_viewport=True
act=bpy.data.actions['Exercise_'+args.id];r.animation_data.action=act;r.animation_data.action_slot=next(x for x in act.slots if x.target_id_type=='OBJECT')
BONES=[side+part for side in ['Left','Right']for part in ['Arm','ForeArm','Hand']];rest={b.name:b.matrix_local.copy()for b in r.data.bones};frames=[];previous={};centers=[];endpoint_matrices={};endpoint_frames=[0,37,38,75,112,113,150]if args.id=='3995'else[0,60,75,90,150]
def angle(a,b):
 a=np.asarray(a,dtype=float);b=np.asarray(b,dtype=float);a/=np.linalg.norm(a);b/=np.linalg.norm(b);return math.degrees(2*math.acos(float(np.clip(abs(a@b),0,1))))
def transported(name,parent,parentq,direction):
 base=parentq@rest[parent].to_quaternion().inverted()@rest[name].to_quaternion();return(base@Vector((0,1,0))).rotation_difference(direction.normalized())@base
def axial(actual,baseline,axis):
 q=actual@baseline.inverted();q.normalize();value=2*math.atan2(Vector((q.x,q.y,q.z)).dot(axis.normalized()),q.w);return math.degrees((value+math.pi)%(2*math.pi)-math.pi)
for frame in range(151):
 s.frame_set(frame+1);bpy.context.view_layer.update();row={'frame':frame,'time_seconds':frame/30,'p':math.sin(math.pi*(frame%75)/75)**2,'bones':{}};centers.append({pb.name:list(r.matrix_world@pb.head)for pb in r.pose.bones})
 if frame in endpoint_frames:endpoint_matrices[str(frame)]={pb.name:np.array(r.matrix_world@pb.matrix).tolist()for pb in r.pose.bones}
 for side in ['Left','Right']:
  shoulder=r.pose.bones[side+'Shoulder'];arm=r.pose.bones[side+'Arm'];fore=r.pose.bones[side+'ForeArm'];hand=r.pose.bones[side+'Hand'];upper=fore.head-arm.head;lower=hand.head-fore.head;aq=transported(side+'Arm',side+'Shoulder',shoulder.matrix.to_quaternion(),upper);fq=transported(side+'ForeArm',side+'Arm',aq,lower);ru=(r.data.bones[side+'Arm'].tail_local-r.data.bones[side+'Arm'].head_local).normalized();rl=(r.data.bones[side+'ForeArm'].tail_local-r.data.bones[side+'ForeArm'].head_local).normalized();ref=ru.cross(rl).normalized();target=upper.cross(lower).normalized();pred=(aq@rest[side+'Arm'].to_quaternion().inverted())@ref;axis=upper.normalized();theta=math.degrees(math.atan2(axis.dot(pred.cross(target)),pred.dot(target)))
  for part,pb in [('Arm',arm),('ForeArm',fore),('Hand',hand)]:
   name=side+part;world=r.matrix_world@pb.matrix;local=pb.parent.matrix.inverted()@pb.matrix;g=list(world.to_quaternion());l=list(local.to_quaternion());old=previous.get(name);sample={'global_rotation_step_degrees':angle(g,old[0])if old else 0.,'parent_local_rotation_step_degrees':angle(l,old[1])if old else 0.};previous[name]=(g,l)
   if part in ['Arm','ForeArm']:sample['actual_axial_offset_from_unmodified_parent_transport_degrees']=axial(pb.matrix.to_quaternion(),aq if part=='Arm'else fq,upper if part=='Arm'else lower)
   if part=='Arm':sample['raw_atan2_hinge_degrees']=theta
   row['bones'][name]=sample
 frames.append(row)
summary={}
for name in BONES:
 out={}
 for metric in ['global_rotation_step_degrees','parent_local_rotation_step_degrees']:
  peak=max(frames[1:],key=lambda x:x['bones'][name][metric]);out[metric]={'maximum':peak['bones'][name][metric],'frame_pair':[peak['frame']-1,peak['frame']]}
 if not name.endswith('Hand'):
  metric='actual_axial_offset_from_unmodified_parent_transport_degrees';peak=max(frames,key=lambda x:abs(x['bones'][name][metric]));out[metric]={'maximum_absolute':abs(peak['bones'][name][metric]),'signed_value':peak['bones'][name][metric],'frame':peak['frame']}
 summary[name]=out
joint_steps={}
for name in BONES:
 value,frame=max((math.dist(centers[f][name],centers[f-1][name]),f)for f in range(1,151));joint_steps[name]={'maximum_m':value,'frame_pair':[frame-1,frame]}
report={'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'source_path':str(source),'action':'Exercise_'+args.id,'scope':'151 saved bone-only states. Global includes armature object transform; local is relative to posed parent. Quaternion distances use2acos(abs(dot)) after double-precision normalization. Axial offsets are measured from actual saved matrices versus parent-transported untwisted frames, not raw atan2 numbers.','summary':summary,'joint_center_step_maxima':joint_steps,'focus_frames':[x for x in frames if x['frame']in list(range(6,13))+list(range(18,22))],'all_frames':frames,'all51_joint_centers_m':centers,'accepted_endpoint_global_matrices':endpoint_matrices}
if args.baseline:
 old=json.loads(Path(args.baseline).read_text());maximum=0.;worst=None
 for frame,(a,b)in enumerate(zip(old['all51_joint_centers_m'],centers)):
  for name in a:
   error=float(np.linalg.norm(np.array(a[name])-np.array(b[name])))
   if error>maximum:maximum=error;worst={'frame':frame,'bone':name}
 endpoint=max(float(np.max(abs(np.array(old['accepted_endpoint_global_matrices'][f][name])-np.array(endpoint_matrices[f][name]))))for f in endpoint_matrices for name in endpoint_matrices[f]);report['comparison']={'baseline_source_sha256':old['source_sha256'],'maximum_all151_all51_joint_center_error_m':maximum,'joint_center_worst':worst,'maximum_accepted_endpoint_51bone_matrix_error':endpoint,'before_summary':old['summary']}
path=F/('continuity-'+args.tag+'.json');path.write_text(json.dumps(report,indent=2)+'\n');print('CONTINUITY',json.dumps({'file':str(path),'source_sha256':report['source_sha256'],'summary':summary,'comparison':report.get('comparison')}))
