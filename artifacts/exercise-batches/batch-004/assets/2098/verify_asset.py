"""Source-bound original-index geometry, supports, grasp and pose checks."""
import hashlib,json,math,sys
from pathlib import Path
import bpy,numpy as np
from mathutils.bvhtree import BVHTree
P=Path(__file__).resolve().parent
sys.path.insert(0,str(P.parents[2]/'batch-003'));import authoring as a
bpy.ops.wm.open_mainfile(filepath=str(P/'source.blend'))
b=bpy.data.objects['SK_BlenderStudioHuman'];r=bpy.data.objects['RIG_BlenderStudioHuman'];s=bpy.context.scene
EXPECTED='227ede3fc31d1a2b47ff40f20a4a7288fe7bb36179add23bae953993826c8b7b'
assert a.binding_hash(b,r)==EXPECTED
R=np.array([v.co[:] for v in b.data.vertices]);N=len(R);labels=np.array([b.vertex_groups[max(v.groups,key=lambda g:g.weight).group].name for v in b.data.vertices])
source_sha=hashlib.sha256((P/'source.blend').read_bytes()).hexdigest()
for m in b.modifiers:
 m.show_viewport=m.show_render=m.type=='ARMATURE'
 if m.type=='ARMATURE':m.use_deform_preserve_volume=False
masks={}
for side,sign in [('L',1),('R',-1)]:
 sole=(sign*R[:,0]>.13)&(R[:,2]<.012)
 masks['heel_'+side]=sole&(R[:,1]>.025);masks['forefoot_'+side]=sole&(R[:,1]<-.035)
for side in ['Left','Right']:
 masks[side+'_hand']=np.array([n.startswith(side) and ('Hand' in n or any(k in n for k in ['Thumb','Index','Middle','Ring','Little'])) for n in labels])
 for digit in ['Thumb','Index','Middle','Ring','Little']:
  masks[side+digit+'_tip']=labels==side+digit+'3'
masks['head']=np.isin(labels,['Head','Neck'])
masks['torso']=np.isin(labels,['Hips','Spine','Spine1'])
landmarks={k:np.where(v)[0].tolist() for k,v in masks.items()}
(P/'surface-landmarks.json').write_text(json.dumps({'source_sha256':source_sha,'source_vertices':N,'definition':'Immutable original-index masks from original rest sole geometry and dominant original bone groups; no indices selected from observed results.','patches':landmarks},indent=2)+'\n')
frames=set(range(0,151,15));refs=[];fullrefs=[];rows=[];poses=[];fails=[];init={};endpoints={};prev=None;maxangle=0;maxstep=0;worst=None;neutraldir=None;neutralnormal=None
for f in range(151):
 s.frame_set(f+1);bpy.context.view_layer.update();ev=b.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh();me.calc_loop_triangles();X=np.array([ev.matrix_world@v.co for v in me.vertices]);T=np.array([t.vertices for t in me.loop_triangles]);ev.to_mesh_clear()
 assert len(X)==10582 and len(T)==21160
 def tree(mask):return BVHTree.FromPolygons(X.tolist(),T[np.all(mask[T],axis=1)].tolist(),all_triangles=True)
 L,H=tree(masks['Left_hand']),tree(masks['Right_hand']);ht=tree(masks['head']);bt=tree(masks['torso'])
 cross=len(L.overlap(H));near={}
 for d in ['Thumb','Index','Middle','Ring','Little']:
  ids=landmarks['Right'+d+'_tip'];dd=np.array([L.find_nearest(tuple(X[i]))[3] for i in ids]);near[d]={'min_m':float(dd.min()),'near_fraction_12mm':float(np.mean(dd<=.012))}
 handids=np.where(masks['Left_hand']|masks['Right_hand'])[0]
 headclear=min(ht.find_nearest(tuple(X[i]))[3] for i in handids);bodyclear=min(bt.find_nearest(tuple(X[i]))[3] for i in handids)
 support={};patches={}
 for k in ['heel_L','forefoot_L','heel_R','forefoot_R']:
  ids=landmarks[k];xx=X[ids];init.setdefault(k,xx.copy());drift=float(np.linalg.norm(xx-init[k],axis=1).max());support[k]={'min_z':float(xx[:,2].min()),'max_z':float(xx[:,2].max()),'max_drift_m':drift};patches[k]={'indices':ids,'min_z':float(xx[:,2].min()),'max_z':float(xx[:,2].max())}
  if drift>1e-6:fails.append(f'frame {f} fixed foot drift {k}')
 row={'frame':f,'global_floor_z':float(X[:,2].min()),'floor_plane_z':0,'cross_hand_triangle_intersections':cross,'right_finger_tip_proximity':near,'hand_head_clearance_m':float(headclear),'hand_torso_clearance_m':float(bodyclear),'supports':support}
 rows.append(row)
 if cross:fails.append(f'frame {f}: {cross} hand surface triangle crossings')
 if headclear<.025 or bodyclear<.025:fails.append(f'frame {f}: hand/head or hand/torso clearance <25 mm')
 if row['global_floor_z']<-.004:fails.append(f'frame {f}: floor penetration >4 mm')
 if 60<=f<=90 and sum(near[d]['min_m']<=.012 for d in ['Thumb','Index','Middle'])<3:fails.append(f'frame {f}: hold thumb/index/middle proximity >12 mm')
 current={pb.name:(pb.matrix.to_quaternion(),pb.head.copy()) for pb in r.pose.bones}
 if prev:
  for name,(q,h) in current.items():
   oq,oh=prev[name];angle=math.degrees(2*math.acos(min(1,abs(q.dot(oq)))))
   if angle>maxangle:maxangle=angle;worst={'bone':name,'frame':f}
   maxstep=max(maxstep,(h-oh).length)
 prev=current
 if f in frames:
  refs.append({'id':'2098','frame':f,'global_floor_z':float(X[:,2].min()),'floor_plane_z':0,'patches':patches});fullrefs.append({'frame':f,'vertices':X.tolist()})
  p={'frame':f,'joints':{pb.name:list(r.matrix_world@pb.head) for pb in r.pose.bones}}
  for side in ['Left','Right']:
   sh,el,wr=[r.pose.bones[side+k].head for k in ['Arm','ForeArm','Hand']];p[side+'_elbow_internal_degrees']=math.degrees((sh-el).angle(wr-el))
  direction=np.array(r.pose.bones['LeftHand'].y_axis);direction/=np.linalg.norm(direction)
  if neutraldir is None:neutraldir=direction
  p['left_hand_change_from_neutral_degrees']=math.degrees(math.acos(np.clip(np.dot(direction,neutraldir),-1,1)))
  p['left_thumb1_above_little1_m']=float(r.pose.bones['LeftThumb1'].head.z-r.pose.bones['LeftLittle1'].head.z)
  poses.append(p)
 if f in [0,150]:endpoints[f]=X
loop=float(np.linalg.norm(endpoints[0]-endpoints[150],axis=1).max())
if loop>1e-6:fails.append('endpoint skin mismatch')
if maxangle>20:fails.append('world bone rotation discontinuity >20 degrees/frame')
weights={'vertices':N,'max_influences':max(len([g for g in v.groups if g.weight>1e-8]) for v in b.data.vertices),'max_sum_error':max(abs(sum(g.weight for g in v.groups)-1) for v in b.data.vertices),'unweighted':sum(not len(v.groups) for v in b.data.vertices)}
assert weights['max_influences']<=4 and weights['max_sum_error']<1e-6 and weights['unweighted']==0
assert len(r.data.bones)==51 and [a.name for a in bpy.data.actions]==['Exercise_2098']
assert list(b.data.attributes['_SOURCE_INDEX'].data[i].value for i in range(N))==list(range(N))
sys.path.insert(0,str(Path.home()/'.codex/skills/blender-asset-qa/scripts'));import qa_check
checks=[]
for f in [0,75]:
 s.frame_set(f+1);bpy.context.view_layer.update();q=qa_check.run(objects=[b.name],profile='game');checks.append({'frame':f,'qa':q})
 if not q['pass']:fails.append(f'frame {f}: asset QA errors {q["errors"]}')
(P/'asset-qa.json').write_text(json.dumps({'source_sha256':source_sha,'pass':all(c['qa']['pass'] for c in checks),'checks':checks},indent=2)+'\n')
(P/'runtime-surface-reference.json').write_text(json.dumps({'source_sha256':source_sha,'source_vertices':N,'coordinate_frame':'Blender world metres; linear Armature only, original vertex order','samples':refs},separators=(',',':'))+'\n')
(P/'linear-vertex-reference.json').write_text(json.dumps(fullrefs,separators=(',',':'))+'\n')
(P/'pose-samples.json').write_text(json.dumps([{'id':'2098','frame':p['frame'],'joints':p['joints']} for p in poses],indent=2)+'\n')
report={'ok':not fails,'source_sha256':source_sha,'binding_hash':a.binding_hash(b,r),'original_binding_unchanged':True,'skinning':'linear','non_armature_modifiers_enabled':False,'samples_every_frame':True,'tolerances':{'near_m':.012,'floor_penetration_m':.004,'minimum_hand_head_torso_clearance_m':.025,'foot_drift_m':.000001},'tolerance_basis':'Illustration-scale diagnostic bands, no anatomical/clinical/EMG certification. No tolerances or mask IDs changed after results.','weights':weights,'loop_max_vertex_error_m':loop,'max_bone_rotation_step_degrees':maxangle,'max_bone_rotation_step_at':worst,'max_joint_step_m':maxstep,'failures':fails,'pose_measurements':poses,'samples':rows}
(P/'surface-contact-report.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'ok':not fails,'failures':fails,'max_rotation_step_degrees':maxangle,'minimum_head_clearance_m':min(x['hand_head_clearance_m'] for x in rows),'minimum_torso_clearance_m':min(x['hand_torso_clearance_m'] for x in rows),'max_crossings':max(x['cross_hand_triangle_intersections'] for x in rows),'weights':weights,'qa_pass':all(c['qa']['pass'] for c in checks)}))
