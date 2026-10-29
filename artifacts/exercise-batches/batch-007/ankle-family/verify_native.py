"""Complete native cycles, source-bound supports, ankle shape and game QA."""
from pathlib import Path
import bpy,json,hashlib,gzip,sys,math
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
P=Path(__file__).resolve().parent;B=P.parent
sys.dont_write_bytecode=True;sys.path[:0]=[str(Path.home()/'.codex/skills/blender-asset-qa/scripts'),str(B.parents[1]/'bodyweight-next-five')]
import qa_check,warning_observer
warning_observer.install(qa_check)
bpy.ops.wm.open_mainfile(filepath=str(P/'source.blend'));b=bpy.data.objects['SK_BlenderStudioHuman'];r=bpy.data.objects['RIG_BlenderStudioHuman'];s=bpy.context.scene;source_sha=hashlib.sha256((P/'source.blend').read_bytes()).hexdigest()
C=json.loads((P/'pose-contract.json').read_text());receipt=json.loads((P/'binding-receipt.json').read_text());rest=np.array([v.co[:]for v in b.data.vertices]);W=[{b.vertex_groups[g.group].name:float(g.weight)for g in v.groups}for v in b.data.vertices]
assert W==receipt['actual_weights']and max(map(len,W))<=4 and max(abs(sum(row.values())-1)for row in W)<2e-6
def ids(prefixes):return {i for i,w in enumerate(W)if sum(v for k,v in w.items()if k.startswith(tuple(prefixes)))>.5}
sets={}
for side in ['Left','Right']:
 sets[side+'Arm']=ids([side+t for t in ['Arm','ForeArm','Hand','Thumb','Index','Middle','Ring','Little']]);sets[side+'Hand']=ids([side+t for t in ['Hand','Thumb','Index','Middle','Ring','Little']]);sets[side+'Leg']=ids([side+t for t in ['UpLeg','Leg','Foot','ToeBase']]);sets[side+'Foot']=ids([side+'Foot',side+'ToeBase'])
b.data.calc_loop_triangles();tri=np.array([list(t.vertices)for t in b.data.loop_triangles]);faces={name:[list(p.vertices)for p in b.data.polygons if all(i in domain for i in p.vertices)]for name,domain in sets.items()if name.endswith('Leg')}
ankle={side:[list(e.vertices)for e in b.data.edges if any(W[i].get(side+'Foot',0)>.02 and W[i].get(side+'Leg',0)>.02 for i in e.vertices)]for side in ['Left','Right']}
forefoot={side:[list(e.vertices)for e in b.data.edges if all(W[i].get(side+'Foot',0)>.999 and rest[i,2]<.035 for i in e.vertices)]for side in ['Left','Right']}
assert all(ankle.values())and all(forefoot.values())
def frame(f):s.frame_set(int(f)+1,subframe=f%1);bpy.context.view_layer.update()
def points():
 e=b.evaluated_get(bpy.context.evaluated_depsgraph_get());m=e.to_mesh();p=np.array([v.co[:]for v in m.vertices]);e.to_mesh_clear();return p
def lengths(pp,edges):ee=np.array(edges);return np.linalg.norm(pp[ee[:,0]]-pp[ee[:,1]],axis=1)
def state(id,t,side):
 if id!='1368':return 'supported'
 local=t-(0 if side=='Left'else 6)
 if local<=0 or local>=6:return 'supported'
 return 'lifted'if .5<=local<=5.5 else'initial_support_then_lifted'
summaries=[]
for id,total in [('1368',360),('2761',150),('2762',150)]:
 out=B/'assets'/id;out.mkdir(parents=True,exist_ok=True);r.animation_data.action=bpy.data.actions['Exercise_'+id];frame(0);first=points();firstm=np.array([pb.matrix[:]for pb in r.pose.bones]);base_lengths={side:{'ankle':lengths(first,ankle[side]),'forefoot':lengths(first,forefoot[side])}for side in ['Left','Right']}
 # Freeze actual floor-facing skin IDs in the complete anatomical domains.
 patches={'pelvic_support':{'indices':[i for i in C['pelvic_original_ids']if first[i,2]<.0135],'state':'supported','rationale':'Actual posterior pelvic skin frozen in the seated neutral, not a bone proxy.'}}
 for side in ['Left','Right']:
  patches['heel_'+side]={'indices':[i for i in C['heel_skin_original_ids'][side]if first[i,2]<.0135],'state':'supported','rationale':'Actual heel skin within12mm of the support plane at neutral; frozen source IDs.'}
  patches['whole_hand_'+side]={'indices':sorted(sets[side+'Hand']),'state':'observed','rationale':'Whole hand/finger skin resting on upper thigh; no floor claim.'}
 assert all(p['indices']for p in patches.values())
 rows=[];joints=[];failures=[];dq=[];poses=[];refs=[];qas=[]
 samples=sorted(set([0,15,30,37.5,60,75,90,112.5,120,135,150]if total==150 else[0,15,30,48.75,60,82.5,90,120,135,165,180,210,228.75,270,300,315,345,360]))
 full=[0,30,75,120,150]if total==150 else[0,90,180,270,360]
 for f in range(total+1):
  frame(f);p=points();areas=.5*np.linalg.norm(np.cross(p[tri[:,1]]-p[tri[:,0]],p[tri[:,2]]-p[tri[:,0]]),axis=1);trees={side:BVHTree.FromPolygons([Vector(x)for x in p],faces[side+'Leg'])for side in ['Left','Right']};limbs={}
  for arm_side in ['Left','Right']:
   for leg_side in ['Left','Right']:
    signed=[];distance=[]
    for i in sets[arm_side+'Arm']:
     q,n,_,d=trees[leg_side].find_nearest(Vector(p[i]));distance.append(d)
     if d<.04:signed.append((Vector(p[i])-q).dot(n))
    metric={'minimum_distance_m':min(distance),'minimum_close_signed_m':min(signed)if signed else None};limbs[arm_side+'_to_'+leg_side]=metric
    if signed and min(signed)<-.001:failures.append(f'frame{f}: {arm_side} arm/hand penetrates {leg_side} leg')
  footshape={}
  for side in ['Left','Right']:
   ar=lengths(p,ankle[side])/base_lengths[side]['ankle'];fr=lengths(p,forefoot[side])/base_lengths[side]['forefoot'];footshape[side]={'ankle_edge_ratio_min':float(ar.min()),'ankle_edge_ratio_max':float(ar.max()),'forefoot_edge_max_change':float(abs(fr-1).max())}
   if ar.min()<.4 or ar.max()>2.5 or abs(fr-1).max()>.002:failures.append(f'frame{f}: {side} internal ankle/forefoot deformation')
  support={name:{'min_z':float(p[patch['indices'],2].min()),'max_z':float(p[patch['indices'],2].max()),'fraction_near_floor':float(np.mean(abs(p[patch['indices'],2])<=.012))}for name,patch in patches.items()}
  for name in ['pelvic_support','heel_Left','heel_Right']:
   metric=support[name];supported=name=='pelvic_support'or state(id,f/30,name.split('_')[-1])=='supported'
   if supported and(metric['min_z']>.012 or metric['fraction_near_floor']<.2):failures.append(f'frame{f}: {name} skin support')
  heel_min={side:float(p[C['heel_skin_original_ids'][side],2].min())for side in ['Left','Right']};calf_min={side:float(p[C['calf_original_ids'][side],2].min())for side in ['Left','Right']}
  for side in ['Left','Right']:
   if state(id,f/30,side)=='lifted'and(heel_min[side]<.025 or calf_min[side]<.015):failures.append(f'frame{f}: {side} circle leg not clearly lifted')
  wrist={side:math.degrees((r.pose.bones[side+'Hand'].head-r.pose.bones[side+'ForeArm'].head).angle(r.pose.bones[side+'Middle1'].head-r.pose.bones[side+'Hand'].head))for side in ['Left','Right']}
  scales=max(abs(x-1)for pb in r.pose.bones for x in pb.matrix.to_scale());length_error=max(abs(pb.length-pb.bone.length)for pb in r.pose.bones);gap=max((r.pose.bones[side+'ForeArm'].head-r.pose.bones[side+'Arm'].tail).length for side in ['Left','Right']);gap=max(gap,*(float((r.pose.bones[side+'Hand'].head-r.pose.bones[side+'ForeArm'].tail).length)for side in ['Left','Right']))
  if max(wrist.values())>45 or scales>1e-5 or length_error>1e-6 or gap>1e-5:failures.append(f'frame{f}: wrist or connected fixed-length arm integrity')
  row={'frame':f,'floor_min_z_m':float(p[:,2].min()),'minimum_triangle_area_m2':float(areas.min()),'patches':support,'heel_skin_min_z_m':heel_min,'calf_skin_min_z_m':calf_min,'whole_arm_hand_leg':limbs,'internal_foot_shape':footshape,'wrist_deviation_degrees':wrist,'maximum_bone_scale_error':scales,'maximum_bone_length_error_m':length_error,'maximum_arm_chain_gap_m':gap};rows.append(row);joints.append({'id':id,'frame':f,'joints':{pb.name:list(r.matrix_world@pb.head)for pb in r.pose.bones}})
  if p[:,2].min()<-.004 or areas.min()<=1e-12:failures.append(f'frame{f}: floor or positive areas')
  if f in full:dq.append({'id':id,'frame':f,'positions':p.tolist()})
 last=p.copy();loop=float(np.linalg.norm(last-first,axis=1).max());matrix_loop=float(abs(np.array([pb.matrix[:]for pb in r.pose.bones])-firstm).max())
 if loop>1e-4 or matrix_loop>1e-5:failures.append('Loop closure')
 for f in samples:
  frame(f);p=points();poses.append({'id':id,'frame':f,'joints':{pb.name:list(r.matrix_world@pb.head)for pb in r.pose.bones}});refs.append({'id':id,'frame':f,'global_floor_z':float(p[:,2].min()),'floor_plane_z':0,'patches':{name:{**patch,'state':state(id,f/30,name[5:])if name.startswith('heel_')else patch['state'],'positions':p[patch['indices']].tolist()}for name,patch in patches.items()}})
 for f in ([0,37.5,112.5,150]if total==150 else[0,48.75,135,228.75,315,360]):
  frame(f);qa=qa_check.run(objects=[b.name],profile='game');qas.append({'frame':f,'report':qa,'warning_locations':qa_check.QA_WARNING_DETAILS})
  if not qa['pass']:failures.append(f'frame{f}: mandatory game errors')
 landmarks={'source_sha256':source_sha,'source_vertices':10582,'patches':patches,'whole_heel_original_ids':C['heel_skin_original_ids'],'calf_original_ids':C['calf_original_ids'],'ankle_edges':ankle,'forefoot_edges':forefoot,'domains':{name:sorted(v)for name,v in sets.items()},'floor_plane_z':0}
 (out/'landmarks.json').write_text(json.dumps(landmarks,indent=2)+'\n');(out/'pose-samples.json').write_text(json.dumps(poses,indent=2)+'\n');(out/'native-joint-readback.json').write_text(json.dumps({'source_sha256':source_sha,'samples':joints},separators=(',',':'))+'\n');(out/'source-morph-samples.json').write_text(json.dumps({'source_sha256':source_sha,'samples':[{'frame':f,'weights':{}}for f in samples]})+'\n')
 (out/'runtime-surface-reference.json').write_text(json.dumps({'source_sha256':source_sha,'source_vertices':10582,'reference_kind':'native_armature_only_DQ_original_body_no_corrective_keys','samples':refs},separators=(',',':'))+'\n')
 with gzip.open(out/'dq-reference.json.gz','wt')as handle:json.dump({'source_sha256':source_sha,'source_vertices':10582,'samples':dq},handle,separators=(',',':'))
 report={'id':id,'ok':not failures,'source_sha256':source_sha,'frames':total+1,'duration_seconds':total/30,'failures':failures,'loop_skin_error_m':loop,'loop_matrix_error':matrix_loop,'minimum_floor_z_m':min(row['floor_min_z_m']for row in rows),'samples':rows,'scope':'Complete native saved-action DQ cycle. Local nearest-normal diagnostics, discrete skin support/areas/internal edges and all51 native joint heads; actual decoded triangle crossings remain a separate gate.'}
 (out/'surface-contact-report.json').write_text(json.dumps(report,indent=2)+'\n');(out/'asset-qa.json').write_text(json.dumps({'id':id,'source_sha256':source_sha,'pass':all(row['report']['pass']for row in qas),'samples':qas},indent=2)+'\n');summaries.append({'id':id,'ok':report['ok'],'failures':failures[:10],'minimum_floor_z_m':report['minimum_floor_z_m'],'loop_skin_error_m':loop});print(json.dumps(summaries[-1]),flush=True)
 (P/'native-summary.json').write_text(json.dumps(summaries,indent=2)+'\n')
 assert not failures,failures[:12]
