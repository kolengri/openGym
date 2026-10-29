"""Full151 actual native/decoded skin, support, contact and bounded invariant checks."""
import bpy,sys,json,gzip,hashlib,numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.dont_write_bytecode=True
F=Path(__file__).resolve().parent;B=F.parent;ID=sys.argv[sys.argv.index('--id')+1];P=B/'assets'/ID;sys.path[:0]=[str(F),str(B.parent/'batch-003'),str(B.parent/'batch-007/arm-circle-family')];import authoring as a
from check_motion import MotionChecks
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def signature(b,r):
 h=hashlib.sha256();h.update(np.array([v.co[:]for v in b.data.vertices],np.float32).tobytes())
 for p in b.data.polygons:h.update(np.array(p.vertices,np.int32).tobytes())
 for uv in b.data.uv_layers:h.update(uv.name.encode());h.update(np.array([v.uv[:]for v in uv.data],np.float32).tobytes())
 for bone in r.data.bones:h.update(bone.name.encode());h.update(np.array(bone.matrix_local,np.float32).tobytes())
 return h.hexdigest()
a.initialize();original=signature(a.body,a.rig);bpy.ops.wm.open_mainfile(filepath=str(P/'source.blend'));b=bpy.data.objects['SK_BlenderStudioHuman'];r=bpy.data.objects['RIG_BlenderStudioHuman'];s=bpy.context.scene;source_sha=sha(P/'source.blend');assert signature(b,r)==original;assert sorted(x.name for x in bpy.data.actions)==['Exercise_1986','Exercise_1987'];r.animation_data.action=bpy.data.actions['Exercise_'+ID];r.animation_data.action_slot=r.animation_data.action.slots[0];assert len(b.data.vertices)==10582 and len(r.data.bones)==51;assert a.binding_hash(b,r)==json.loads((F/'local-binding-report.json').read_text())['runtime_binding_sha256'];assert max(len(v.groups)for v in b.data.vertices)<=4;assert max(abs(sum(g.weight for g in v.groups)-1)for v in b.data.vertices)<2e-6;assert not b.data.shape_keys
for m in b.modifiers:assert m.show_viewport==(m.type=='ARMATURE')and m.show_render==(m.type=='ARMATURE')
assert next(m for m in b.modifiers if m.type=='ARMATURE').use_deform_preserve_volume
b.data.calc_loop_triangles();tri=np.array([t.vertices[:]for t in b.data.loop_triangles],int);R=np.array([v.co[:]for v in b.data.vertices]);N=np.array([v.normal[:]for v in b.data.vertices]);gn={g.index:g.name for g in b.vertex_groups}
def ids(prefixes,threshold=.7):return np.array([v.index for v in b.data.vertices if sum(g.weight for g in v.groups if any(gn[g.group].startswith(p)for p in prefixes))>threshold],int)
soles={side:np.array([v.index for v in b.data.vertices if v.co.z<.10 and sum(g.weight for g in v.groups if gn[g.group]in[side+'Foot',side+'ToeBase'])>.5],int)for side in['Left','Right']};arms={side:ids([side+x for x in['Arm','ForeArm','Hand','Index','Middle','Ring','Little','Thumb']],.5)for side in soles};legs={side:ids([side+x for x in['UpLeg','Leg','Foot','ToeBase']],.5)for side in soles};parts={side+'_arm':idx for side,idx in arms.items()};parts.update({side+'_leg':idx for side,idx in legs.items()})
for side,sign in [('Left',1),('Right',-1)]:
 parts[side+'_hand']=ids([side+x for x in['Hand','Index','Middle','Ring','Little','Thumb']]);parts[side+'_digits']=ids([side+x for x in['Index','Middle','Ring','Little','Thumb']]);parts[side+'_forearm']=ids([side+'ForeArm']);parts[side+'_palm']=np.array([i for i in ids([side+'Hand'],.8)if .88<R[i,2]<.94 and -sign*N[i,0]>.4],int)
parts['Left_palm']=np.array(json.loads((F/'native-back-contact-solve.json').read_text())['palm_ids'],int);parts['back']=np.flatnonzero((abs(R[:,0])<.28)&(R[:,1]>.025)&(R[:,2]>1.15)&(R[:,2]<1.51));parts['head']=np.flatnonzero((R[:,2]>1.54)&(abs(R[:,0])<.17));parts['Left_wrist']=np.array([i for i in ids(['LeftForeArm'])if R[i,2]<1.025]);faces={n:tri[np.all(np.isin(tri,idx),axis=1)].tolist()for n,idx in parts.items()};patches={}
for side,idx in soles.items():
 patches['sole_'+side]={'indices':idx.tolist(),'rationale':'Frozen original distal plantar source skin below100mm, dominant Foot+ToeBase.'};bottom=idx[R[idx,2]<=np.percentile(R[idx,2],20)+.001]
 for name,sel in[('heel',R[bottom,1]>np.median(R[idx,1])),('ball',R[bottom,1]<=np.median(R[idx,1]))]:patches[name+'_'+side]={'indices':bottom[sel].tolist(),'rationale':'Frozen lowest20percent source plantar envelope separated by medianY.'}
for name in['Left_palm','Right_palm','Left_wrist']:patches[name]={'indices':parts[name].tolist(),'rationale':'Frozen original source-domain central palm or distal wrist skin, not bone endpoints.'}
checks=MotionChecks(b,r);frames=[0,15,30,45,60,75,90,105,120,135,150];dqframes=[0,30,75,120,150];decoded_path=Path(sys.argv[sys.argv.index('--decoded')+1])if'--decoded'in sys.argv else None;decoded=np.fromfile(decoded_path,dtype=np.float32).reshape(151,10582,3)if decoded_path else None;samples=[];poses=[];refs=[];dq=[];normals=[];fail=[];minimum_area=1;maximum_parity=0;previous={};maximum_joint_step=0

def pair(p,A,B):
 tree=BVHTree.FromPolygons([Vector(q)for q in p],faces[B]);rows=[]
 for i in parts[A]:
  q,n,fi,dist=tree.find_nearest(tuple(p[i]));rows.append((dist,float((p[i]-np.array(q)).dot(n)),int(i)))
 ds=np.array([x[0]for x in rows]);sg=np.array([x[1]for x in rows]);return {'minimum_distance_m':float(ds.min()),'median_distance_m':float(np.median(ds)),'minimum_signed_within40mm_m':float(sg[ds<.04].min())if np.any(ds<.04)else None,'ids_more4mm_inside_within40mm':[x[2]for x in rows if x[0]<.04 and x[1]<-.004],'near12mm_vertices':int((ds<.012).sum())}
for f in range(151):
 s.frame_set(f+1);bpy.context.view_layer.update();ev=b.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh();native_p=np.array([v.co[:]for v in me.vertices]);pn=np.array([v.normal[:]for v in me.vertices]);p=native_p if decoded is None else decoded[f].astype(float);maximum_parity=max(maximum_parity,float(np.linalg.norm(p-native_p,axis=1).max()));ev.to_mesh_clear();z=float(p[:,2].min());area=float((np.linalg.norm(np.cross(p[tri[:,1]]-p[tri[:,0]],p[tri[:,2]]-p[tri[:,0]]),axis=1)*.5).min());minimum_area=min(minimum_area,area)
 if z<-.00035:fail.append(f'frame{f}: floor penetration {z}')
 if area<=1e-12:fail.append(f'frame{f}: nonpositive triangle area {area}')
 support={side:float(p[idx,2].min())for side,idx in soles.items()}
 for side,lo in support.items():
  if not -.00035<=lo<=.002:fail.append(f'frame{f}: {side} sole unsupported {lo}')
 extra,issues=checks.sample(p,f,ID,native_p=native_p);fail.extend(issues);contact={};pairs=[('Left_digits','Left_forearm'),('Right_digits','Right_forearm'),('Left_hand','Right_arm'),('Left_hand','head'),('Right_hand','head'),('Right_hand','Left_arm'),('Right_palm','Left_arm'),('Right_digits','Left_arm')]
 if ID=='1986':pairs += [('Left_hand','back'),('Left_palm','back'),('Left_digits','back')]
 for A,Bb in pairs:
  value=pair(p,A,Bb);contact[A+'_to_'+Bb]=value
  # Distal hand self-contact is authored; independent torso/head penetration stays bounded.
  if value['ids_more4mm_inside_within40mm']:fail.append(f'frame{f}: {A}/{Bb} {len(value["ids_more4mm_inside_within40mm"])} vertices>4mm inside')
 if 60<=f<=90:
  if contact['Right_palm_to_Left_arm']['minimum_distance_m']>.012:fail.append(f'frame{f}: assisting palm contact gap')
  if contact['Right_digits_to_Left_arm']['minimum_distance_m']>.012:fail.append(f'frame{f}: assisting finger contact gap')
  if ID=='1986'and contact['Left_palm_to_back']['median_distance_m']>.008:fail.append(f'frame{f}: upperback central palm median gap')
 for pb in r.pose.bones:
  q=pb.matrix.to_quaternion()
  if pb.name in previous:
   deg=np.degrees(previous[pb.name].rotation_difference(q).angle);maximum_joint_step=max(maximum_joint_step,min(deg,360-deg))
  previous[pb.name]=q.copy()
 row={'frame':f,'time':f/30,'phase':'Enter'if f<60 else'Hold'if f<=90 else'Return','whole_skin_min_z_m':z,'minimum_triangle_area_m2':area,'sole_min_z_m':support,'contact':contact,**extra};samples.append(row)
 if f in frames:
  poses.append({'id':ID,'frame':f,'joints':{pb.name:list(r.matrix_world@pb.head)for pb in r.pose.bones}});refs.append({'id':ID,'frame':f,'global_floor_z':z,'floor_plane_z':0,'patches':{name:{**patch,'positions':p[patch['indices']].tolist(),'min_z':float(p[patch['indices'],2].min()),'max_z':float(p[patch['indices'],2].max()),'state':'supported'if name.startswith(('sole_','heel_','ball_'))else'contact'if 60<=f<=90 and(name=='Right_palm'or(ID=='1986'and name=='Left_palm')or(ID=='1987'and name=='Left_wrist'))else'free'}for name,patch in patches.items()}})
 if f in dqframes:dq.append({'id':ID,'frame':f,'positions':p.tolist()});normals.append({'id':ID,'frame':f,'normals':pn.tolist()})
 if f==0:start=p.copy();startbones=np.array([pb.matrix for pb in r.pose.bones])
 if f==150:end=p.copy();endbones=np.array([pb.matrix for pb in r.pose.bones])
loop=float(np.linalg.norm(start-end,axis=1).max());boneloop=float(np.max(abs(startbones-endbones)))
if loop>1e-5 or boneloop>1e-5:fail.append('Loop mismatch')
if decoded is not None and maximum_parity>.0001:fail.append('Actual decoded native full151 parity>100micrometers')
if maximum_joint_step>45:fail.append(f'Joint step above45degrees {maximum_joint_step}')
if decoded is None:
 for name,data in [('runtime-surface-reference.json',{'source_sha256':source_sha,'reference_kind':'native_armature_only_DQ','source_vertices':10582,'coordinate_system':'BlenderZup meters; runtime[x,z,-y]','samples':refs}),('surface-landmarks.json',{'source_sha256':source_sha,'patches':patches,'parts':{k:v.tolist()for k,v in parts.items()},'triangles':tri.tolist()}),('pose-samples.json',poses)]: (P/name).write_text(json.dumps(data,separators=(',',':'))+'\n')
 for name,data in [('dq-reference.json.gz',{'source_sha256':source_sha,'source_vertices':10582,'samples':dq}),('normal-reference.json.gz',{'source_sha256':source_sha,'source_vertices':10582,'basis':N.tolist(),'native_reference_kind':'Evaluated geometric vertex normals; basis normal parity is transport contract. Posed geometric normals are diagnostic and not asserted equal to rotated source normal shader.','samples':normals})]:
  with gzip.open(P/name,'wt')as out:json.dump(data,out,separators=(',',':'))
report={'ok':not fail,'source_sha256':source_sha,'native_integer_frames':151,'minimum_floor_z_m':min(v['whole_skin_min_z_m']for v in samples),'minimum_triangle_area_m2':minimum_area,'loop_skin_error_m':loop,'loop_bone_max_element_error':boneloop,'maximum_full_cycle_native_decoded_error_m':maximum_parity if decoded is not None else None,'maximum_joint_step_degrees':maximum_joint_step,'maximum_leg_foot_orientation_step_degrees':checks.maximum_step,'forefoot_edge_ratio_range':checks.edge_range,'mixed_ankle_edge_ratio_range':checks.ankle_range,'maximum_forefoot_relative_matrix_error':checks.maximum_toe_error,'triangle_crossings':checks.crossings,'tolerances':{'floor_penetration_m':.00035,'sole_max_gap_m':.002,'local_inside_within40mm_m':.004,'assisting_palm_and_finger_hold_max_gap_m':.012,'upperback_central_palm_hold_median_max_gap_m':.008},'scope':'Actual full skin; whole arms/hands/fingers versus both complete legs; explicit palm/finger contacts, wholehand/head and upperback local signed diagnostic. No global self-collision/clinical claim.','failures':fail,'samples':samples};(P/('decoded-physical-report.json'if decoded is not None else'surface-contact-report.json')).write_text(json.dumps(report,indent=2)+'\n')
if decoded is None:
 (P/'source-verification.json').write_text(json.dumps({'ok':True,'source_sha256':source_sha,'original_source_sha256':a.SOURCE_SHA,'basis_topology_uv_bone_rest_sha256':original,'basis_topology_uv_bone_rest_unchanged':True,'runtime_binding_sha256':a.binding_hash(b,r),'maximum_influences':max(len(v.groups)for v in b.data.vertices),'maximum_weight_sum_error':max(abs(sum(g.weight for g in v.groups)-1)for v in b.data.vertices),'vertices':10582,'triangles':len(tri),'bones':51,'morphs':[],'actions':['Exercise_1986','Exercise_1987'],'selected_action':'Exercise_'+ID,'only_armature_enabled':True,'dual_quaternion':True},indent=2)+'\n')
print('NATIVE_GATES',json.dumps({'id':ID,'ok':not fail,'failures':fail[:25],'failure_count':len(fail),'minimum_area':minimum_area,'loop':loop}))
if '--game-qa'in sys.argv:
 sys.path.insert(0,str(Path.home()/'.codex/skills/blender-asset-qa/scripts'));import qa_check;qa=[]
 for f in[0,30,75,120]:
  if f==75 and '--reuse-held-qa'in sys.argv:
   timing=json.loads((F/'timing-comparison.json').read_text());assert timing['maximum_held_pose_matrix_error']<2e-6;baseline=json.loads((F/'timing-baseline'/ID/'raw-asset-qa.json').read_text());old=next(q for q in baseline['samples']if q['frame']==75);qa.append({**old,'receipt_reuse':'Same authored held pose within existing2e-6 native matrix tolerance and exact binding; no hold QA rerun.','maximum_held_pose_matrix_error':timing['maximum_held_pose_matrix_error'],'baseline_source_sha256':baseline['source_sha256']})
  else:s.frame_set(f+1);bpy.context.view_layer.update();qa.append({'frame':f,'report':qa_check.run(objects=[b.name],profile='game')})
 q={'pass':all(x['report']['pass']for x in qa),'source_sha256':source_sha,'samples':qa};(P/'raw-asset-qa.json').write_text(json.dumps(q,indent=2)+'\n');assert q['pass']
if decoded_path:decoded_path.unlink();decoded_path.parent.rmdir();(P/'verification-exchange-path.txt').unlink()
assert not fail,fail[:25]
