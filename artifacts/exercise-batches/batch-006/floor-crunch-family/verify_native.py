"""Canonical saved-action physical/native QA and source-domain references.

Both actions are evaluated over151frames with only the Armature enabled.
Temporary full-skin float32 streams feed the independent decoded-GLB comparison
and are excluded from delivery; permanent DQ references retain the required5poses.
"""
from pathlib import Path
import sys,json,math,hashlib,gzip,argparse
import bpy,numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
P=Path(__file__).resolve().parent;B=P.parent
sys.path[:0]=[str(Path.home()/'.codex/skills/blender-asset-qa/scripts'),str(B.parents[1]/'bodyweight-next-five')]
import qa_check,warning_observer
warning_observer.install(qa_check)
opts=argparse.ArgumentParser();opts.add_argument('--ids',nargs='+',choices=['0006','4354'],default=['0006','4354']);options=opts.parse_args(sys.argv[sys.argv.index('--')+1:]if'--'in sys.argv else[])
C=json.loads((P/'plantar-pad-contract.json').read_text())
FRAMES=[0,12.5,19,30,37.5,56,75,94,112.5,120,131,137.5,150]
TOL={'maximum_floor_penetration_m':.004,'support_near_band_m':.012,'minimum_support_near_fraction':.2,'loop_translation_m':.0001,'minimum_arm_hand_leg_clearance_m':.0005,'maximum_grounded_foot_joint_drift_m':.00001}
bpy.ops.wm.open_mainfile(filepath=str(P/'source.blend'));b=bpy.data.objects['SK_BlenderStudioHuman'];r=bpy.data.objects['RIG_BlenderStudioHuman'];s=bpy.context.scene;source_sha=hashlib.sha256((P/'source.blend').read_bytes()).hexdigest()
for m in b.modifiers:
 m.show_viewport=m.show_render=m.type=='ARMATURE'
 if m.type=='ARMATURE':m.use_deform_preserve_volume=True
R=np.array([v.co[:]for v in b.data.vertices]);W=[{b.vertex_groups[g.group].name:float(g.weight)for g in v.groups}for v in b.data.vertices]
receipt=json.loads((P/'binding-receipt.json').read_text());assert W==receipt['actual_weights'];assert max(map(len,W))<=4;assert max(abs(sum(row.values())-1)for row in W)<2e-6
sets=json.loads((P/'changed-candidate-check.json').read_text())['source_domains'];sets={n:set(v)for n,v in sets.items()};faces={n:[list(f.vertices)for f in b.data.polygons if all(i in ids for i in f.vertices)]for n,ids in sets.items()}
patches={}
for side,sign,suffix in [('Left',1,'L'),('Right',-1,'R')]:
 for token,cond in [('sole',(R[:,2]<.035)),('heel',(R[:,2]<.035)&(R[:,1]>.035)),('forefoot',(R[:,2]<.035)&(R[:,1]<-.065))]:
  ids=np.flatnonzero(cond&(sign*R[:,0]>.08)).tolist();assert ids;patches[token+'_'+suffix]={'indices':ids,'state':('observed'if token=='forefoot'else'supported'),'rationale':('Original239-ID broad forefoot mask, including source sidewalls; raw failed20% criterion retained diagnostically.'if token=='forefoot'else'Frozen neutral source plantar skin patch; true evaluated skin, not ankle origin.')}
 patches['plantar_pad_'+suffix]={'indices':C['plantar_pad_source_ids'][side],'state':'supported','rationale':'Frozen original Basis normalZ<−0.7 downward-facing31-ID plantar pad; never selected by deformed floor height.'}
 patches['whole_hand_'+suffix]={'indices':sorted(sets['hand'+suffix]),'state':'observed','rationale':'Full original-ID hand/finger skin; no floor-support claim.'}
 patches['foot_'+suffix]={'indices':sorted(sets['foot'+suffix]),'state':'observed','rationale':'Complete foot/toe surface, measured separately from sole patch.'}
patches['pelvic_support_L']={'indices':[8533,8585,8646,8648],'state':'supported','rationale':'Frozen original posterior pelvic patch from source anatomy.'};patches['pelvic_support_R']={'indices':[3276,3328,3388,3390],'state':'supported','rationale':'Frozen original posterior pelvic patch from source anatomy.'}
maskfile=B.parent/'batch-005/assets/5266/frozen-support-masks.json';frozen=json.loads(maskfile.read_text());patches['lumbar_arch']={'indices':frozen['patches']['lumbar_arch'],'state':'observed','rationale':'Original45 raw posterior lumbar skin vertices, reported diagnostically. Neither source requires flattening the source groove/arch.'}
upper=np.flatnonzero((R[:,2]>1.30)&(R[:,2]<1.40)&(R[:,1]>.07)&(abs(R[:,0])<.12)).tolist();assert upper;patches['upper_back']={'indices':upper,'state':'observed','rationale':'Source posterior upper-trunk skin, to show shoulders lifted; no chest-floor support claim.'}

def frame(f):s.frame_set(int(f)+1,subframe=f%1);bpy.context.view_layer.update()
def sample():
 e=b.evaluated_get(bpy.context.evaluated_depsgraph_get());m=e.to_mesh();m.calc_loop_triangles();p=np.array([v.co[:]for v in m.vertices]);tri=np.array([t.vertices[:]for t in m.loop_triangles]);e.to_mesh_clear();return p,tri

def physical(p,tri):
 trees={n:BVHTree.FromPolygons([Vector(v)for v in p],polys)for n,polys in faces.items()};over=trees['arms'].overlap(trees['legs']);minimum=float('inf');witness=None
 for name,other in [('arms','legs'),('legs','arms')]:
  for i in sets[name]:
   q,n,face,d=trees[other].find_nearest(Vector(p[i]))
   if d<minimum:minimum=d;witness={'region':name,'source_id':i,'opposite_polygon':face}
 areas=np.linalg.norm(np.cross(p[tri[:,1]]-p[tri[:,0]],p[tri[:,2]]-p[tri[:,0]]),axis=1)*.5
 metrics={n:{'min_z':float(p[v['indices'],2].min()),'max_z':float(p[v['indices'],2].max()),'fraction_near_floor':float(np.mean(abs(p[v['indices'],2])<=.012))}for n,v in patches.items()}
 return {'floor_min_z_m':float(p[:,2].min()),'floor_witness_source_id':int(p[:,2].argmin()),'minimum_triangle_area_m2':float(areas.min()),'nonpositive_triangles':int(np.sum(areas<=0)),'arm_hand_leg_intersections':len(over),'minimum_arm_hand_leg_clearance_m':minimum,'clearance_witness':witness,'patches':metrics}

for id in options.ids:
 out=B/'assets'/id;act=bpy.data.actions['Exercise_'+id];r.animation_data.action=act;b.data.shape_keys.animation_data.action=act;b.data.shape_keys.animation_data.action_slot=next(slot for slot in act.slots if slot.target_id_type=='KEY')
 failures=[];rows=[];poses=[];refs=[];dq=[];morphs=[];qareports=[];initial_joints={};joint_drift=0.;first=None;firstm=None;loop=0
 stream=gzip.open(P/f'.native-all151-{id}.f32.gz','wb',compresslevel=5)
 for f in range(151):
  frame(f);p,tri=sample();stream.write(p.astype('<f4').tobytes());q=physical(p,tri);q['frame']=f
  joint={pb.name:list(r.matrix_world@pb.head)for pb in r.pose.bones}
  for side in ['Left','Right']:
   for token in ['UpLeg','Leg','Foot','ToeBase']:
    name=side+token;v=np.array(joint[name]);initial_joints.setdefault(name,v.copy());joint_drift=max(joint_drift,float(np.linalg.norm(v-initial_joints[name])))
  q['knee_internal_degrees']={side:math.degrees((r.pose.bones[side+'UpLeg'].head-r.pose.bones[side+'Leg'].head).angle(r.pose.bones[side+'Foot'].head-r.pose.bones[side+'Leg'].head))for side in ['Left','Right']}
  if q['floor_min_z_m']<-.004:failures.append(f'frame{f}:floor penetration')
  if q['nonpositive_triangles']:failures.append(f'frame{f}:nonpositive area')
  if q['arm_hand_leg_intersections']or q['minimum_arm_hand_leg_clearance_m']<.0005:failures.append(f'frame{f}:whole arm/hand versus leg clearance')
  for n,patch in patches.items():
   m=q['patches'][n]
   if patch['state']=='supported'and(m['min_z']>.012 or m['fraction_near_floor']<.2):failures.append(f'frame{f}:{n} support')
  if first is None:first=p.copy();firstm=np.array([pb.matrix[:]for pb in r.pose.bones])
  if f==150:loop=float(np.linalg.norm(p-first,axis=1).max());matrix_loop=float(abs(np.array([pb.matrix[:]for pb in r.pose.bones])-firstm).max())
  rows.append(q);morphs.append({'frame':f,'weights':{k.name:float(k.value)for k in b.data.shape_keys.key_blocks if k.name!='Basis'}})
  if f in [0,30,75,120,150]:dq.append({'id':id,'frame':f,'positions':p.tolist()})
  if f%50==0:print('NATIVE_FRAME',id,f,flush=True)
 stream.close()
 # Subframe witnesses are explicit, especially exact left/right peaks.
 for f in FRAMES:
  frame(f);p,tri=sample();poses.append({'id':id,'frame':f,'joints':{pb.name:list(r.matrix_world@pb.head)for pb in r.pose.bones}})
  handhead={}
  if id=='4354':
   head=BVHTree.FromPolygons([Vector(v)for v in p],faces['head'])
   for side,suffix in [('Left','L'),('Right','R')]:
    signed=[]
    for i in sets['hand'+suffix]:
     near,n,face,d=head.find_nearest(Vector(p[i]));signed.append((Vector(p[i])-near).dot(n))
    wrist=r.pose.bones[side+'Hand'].head;elbow=r.pose.bones[side+'ForeArm'].head;palm=r.pose.bones[side+'Middle1'].head;angle=math.degrees((wrist-elbow).angle(palm-wrist));handhead[side]={'minimum_nearest_head_normal_signed_distance_m':min(signed),'wrist_direction_deviation_degrees':angle}
    if min(signed)<-.004 or angle>35.01:failures.append(f'frame{f}:{side} occiput hand/head clearance or wrist staging')
  refs.append({'id':id,'frame':f,'floor_plane_z':0,'global_floor_z':float(p[:,2].min()),'patches':{n:{**v,'positions':p[v['indices']].tolist()}for n,v in patches.items()},'hand_head':handhead})
  if f in [0,37.5,75,112.5]:
   qa=qa_check.run(objects=[b.name],profile='game');qareports.append({'id':id,'frame':f,'qa':qa,'warning_locations':qa_check.QA_WARNING_DETAILS})
   if not qa['pass']:failures.append(f'frame{f}:game QA errors')
 if joint_drift>1e-5 or loop>1e-4 or matrix_loop>1e-5:failures.append('Fixed leg joints or loop drift')
 (out/'pose-samples.json').write_text(json.dumps(poses,indent=2)+'\n');(out/'source-morph-samples.json').write_text(json.dumps({'source_sha256':source_sha,'samples':morphs},indent=2)+'\n')
 (out/'landmarks.json').write_text(json.dumps({'id':id,'source_sha256':source_sha,'source_vertices':10582,'coordinate_frame':'Blender Zup metres','floor':{'point':[0,0,0],'normal':[0,0,1]},'patches':patches,'tolerances':TOL,'basis':'Source anatomy masks frozen before full-cycle checking; observed lumbar arch preserves neutral source shape. Illustration contact QC, not clinical validation.'},indent=2)+'\n')
 (out/'runtime-surface-reference.json').write_text(json.dumps({'id':id,'source_sha256':source_sha,'source_vertices':10582,'source_index_attribute':'_SOURCE_INDEX','coordinate_frame':'Blender Zup metres','skinning':'dualQuaternion','reference_kind':'native-armature-only-original-cage-with-explicit-position-normal-targets','samples':refs},separators=(',',':'))+'\n')
 with gzip.open(out/'dq-reference.json.gz','wt',compresslevel=9)as stream:json.dump({'source_sha256':source_sha,'source_vertices':10582,'samples':dq},stream,separators=(',',':'))
 report={'id':id,'ok':not failures,'failures':failures,'source_sha256':source_sha,'sampled_frames':151,'maximum_fixed_leg_joint_drift_m':joint_drift,'loop_skin_error_m':loop,'loop_matrix_element_error':matrix_loop,'tolerances':TOL,'samples':rows,'minimum_arm_hand_leg_clearance_m':min(row['minimum_arm_hand_leg_clearance_m']for row in rows),'minimum_triangle_area_m2':min(row['minimum_triangle_area_m2']for row in rows),'worst_floor_min_z_m':min(row['floor_min_z_m']for row in rows),'plantar_pad_contract_sha256':hashlib.sha256((P/'plantar-pad-contract.json').read_bytes()).hexdigest(),'raw_forefoot_failed_criterion_history':{n:[{'frame':row['frame'],**row['patches'][n],'original20percent_criterion_pass':row['patches'][n]['fraction_near_floor']>=.2 and row['patches'][n]['min_z']<=.012}for row in rows]for n in ['forefoot_L','forefoot_R']},'limits':'Actual native151 sampled DQ cages, full arm/hand and lower-limb triangle/vertex witnesses. No claim of continuous-time or global zero self-collision. Native source-profile lumbar arch is observed, not flattened.'}
 (out/'surface-contact-report.json').write_text(json.dumps(report,indent=2)+'\n');(out/'mechanics-verification.json').write_text(json.dumps(report,indent=2)+'\n');(out/'asset-qa.json').write_text(json.dumps({'id':id,'source_sha256':source_sha,'pass':all(row['qa']['pass']for row in qareports),'blender':bpy.app.version_string,'samples':qareports,'warning_disposition':C['ground_warning_disposition']},indent=2)+'\n')
 print('NATIVE_RESULT',id,json.dumps({'ok':not failures,'failures':failures,'minimum_arm_leg_clearance_m':report['minimum_arm_hand_leg_clearance_m'],'loop_m':loop}),flush=True)
 assert not failures,failures
