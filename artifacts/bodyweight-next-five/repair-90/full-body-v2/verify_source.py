"""Read-only source invariants, full-path skin/support checks and witnesses."""
import bpy,gzip,hashlib,json,math,sys
from pathlib import Path
import numpy as np
from mathutils import Vector
P=Path(__file__).resolve().parent;sys.path.insert(0,str(P));import candidate as c;import correctives as k
EXPECTED='227ede3fc31d1a2b47ff40f20a4a7288fe7bb36179add23bae953993826c8b7b'
bpy.ops.wm.open_mainfile(filepath=str(P/'source.blend'));body=bpy.data.objects['SK_BlenderStudioHuman'];rig=bpy.data.objects['RIG_BlenderStudioHuman'];scene=bpy.context.scene;keys=body.data.shape_keys
source_sha=hashlib.sha256((P/'source.blend').read_bytes()).hexdigest();base=np.array([v.co[:] for v in body.data.vertices]);failures=[]
def check(value,message):
 if not value:failures.append(message)
def select(identifier,frame):
 action=bpy.data.actions['Exercise_'+identifier];rig.animation_data.action=action;rig.animation_data.action_slot=next(s for s in action.slots if s.target_id_type=='OBJECT');keys.animation_data.action=action;keys.animation_data.action_slot=next(s for s in action.slots if s.target_id_type=='KEY');scene.frame_set(frame+1);bpy.context.view_layer.update()
check(c.a.binding_hash(body,rig)==EXPECTED,'Original binding/rest/UV hash changed')
check(len(rig.data.bones)==51,'Original bone count changed');check(len(body.data.vertices)==10582,'Source vertex count changed')
check(np.array_equal(base,np.array([v.co[:] for v in keys.key_blocks['Basis'].data])),'Basis differs from original mesh')
check(all(m.show_viewport==(m.type=='ARMATURE') and m.show_render==(m.type=='ARMATURE') for m in body.modifiers),'Runtime source enables native-only modifier')
check(next(m for m in body.modifiers if m.type=='ARMATURE').use_deform_preserve_volume,'DQ disabled')
check(all(len(v.groups)<=4 and abs(sum(g.weight for g in v.groups)-1)<1e-5 for v in body.data.vertices),'Skin weights exceed4 or are not normalized')
names={g.index:g.name for g in body.vertex_groups}
groups={name:[v.index for v in body.data.vertices if any(names[g.group]==name and g.weight>.5 for g in v.groups)] for name in ['LeftUpLeg','RightUpLeg','LeftLeg','RightLeg','LeftFoot','RightFoot','LeftHand','RightHand']}
for side in ['Left','Right']:
 groups[side+'OpenHand']=[v.index for v in body.data.vertices if any(names[g.group].startswith(side) and any(t in names[g.group] for t in ['Hand','Thumb','Index','Middle','Ring','Little']) and g.weight>.5 for g in v.groups)]
groups['Pelvis']=np.flatnonzero((base[:,2]>.82)&(base[:,2]<1.03)&(base[:,1]>.025)&(abs(base[:,0])<.19)).tolist()
select('6560',0);start=k.sample(body);select('6560',75);hinge=k.sample(body)
patchspec={'pelvic_support':'Pelvis','thigh_L':'LeftUpLeg','thigh_R':'RightUpLeg','shin_L':'LeftLeg','foot_edge_L':'LeftFoot','foot_edge_R':'RightFoot','hand_L':'LeftOpenHand','hand_R':'RightOpenHand'}
patches={}
for name,group in patchspec.items():
 ids=groups[group]
 if name.startswith('thigh'):ids=[i for i in ids if .60<base[i,2]<.87]
 near=[i for i in ids if min(start[i,2],hinge[i,2])<.012]
 if not near:near=sorted(ids,key=lambda i:min(start[i,2],hinge[i,2]))[:8]
 patches[name]={'indices':near,'source_region':group,'selection':'Full source anatomical group with actual skin within12mm of floor at either endpoint; descriptive witnesses selected after shape, never pose targets.'}
(P/'ninety-landmarks.json').write_text(json.dumps({'schema_version':'2.0','source_sha256':source_sha,'source_vertices':10582,'source_index_attribute':'_SOURCE_INDEX','coordinate_frame':'Blender world metres','floor':{'point':[0,0,0],'normal':[0,0,1]},'patches':patches,'old_artist_contact_indices_reused':False},indent=2)+'\n')
samples=[];pose_samples=[];surface_samples=[];allrows=[];errors=[];endpoints={}
for identifier in ['10565','6560']:
 for frame in range(151):
  select(identifier,frame);co=k.sample(body)
  check(np.isfinite(co).all(),f'{identifier}:{frame} nonfinite skin')
  row={'id':identifier,'frame':frame,'global_floor_z':float(co[:,2].min()),'parts':{name:{'min_z':float(co[ids,2].min()),'max_z':float(co[ids,2].max())} for name,ids in groups.items()},'wrist_directions':{}}
  for side in ['Left','Right']:
   fore=rig.pose.bones[side+'Hand'].head-rig.pose.bones[side+'ForeArm'].head;finger=rig.pose.bones[side+'Middle1'].tail-rig.pose.bones[side+'Middle1'].head
   row['wrist_directions'][side]={'forearm_to_middle_proximal_degrees':math.degrees(fore.angle(finger)),'forearm':list(fore.normalized()),'proximal_middle':list(finger.normalized())}
  check(row['global_floor_z']>=-.004,f'{identifier}:{frame} skin below floor by{-row["global_floor_z"]:.6f}m')
  for b in rig.pose.bones:check(max(abs(s-1) for s in b.scale)<1e-5,f'{identifier}:{frame} nonunit bone scale {b.name}')
  allrows.append(row)
  if frame in [0,150]:endpoints[(identifier,frame)]=co.copy()
  if frame%15==0:
   samples.append({'id':identifier,'frame':frame,'positions':co.tolist(),'morph_weights':{name:float(keys.key_blocks[name].value) for name in sum(k.NAMES.values(),[])}})
   pose_samples.append({'id':identifier,'frame':frame,'joints':{b.name:list(b.head) for b in rig.pose.bones}})
   surface_samples.append({'id':identifier,'frame':frame,'global_floor_z':row['global_floor_z'],'patches':{name:{'indices':p['indices'],'min_z':float(co[p['indices'],2].min()),'max_z':float(co[p['indices'],2].max())} for name,p in patches.items()}})
  if frame in [0,15,30,45,60,75,90,105,120,135,150]:
   saved=[key.value for key in keys.key_blocks]
   for key in keys.key_blocks:key.value=0
   raw,target,field=k.native_target(body)
   for key,value in zip(keys.key_blocks,saved):key.value=value
   delta=np.linalg.norm(co-target,axis=1);errors.append({'id':identifier,'frame':frame,'local_target_error_max_m':float(delta.max()),'local_target_error_p95_m':float(np.percentile(delta[field>0],95))})
 for name in ['Left','Right']:
  angles=[r['wrist_directions'][name]['forearm_to_middle_proximal_degrees'] for r in allrows if r['id']==identifier]
  check(max(angles)<115,f'{identifier} {name} severe folded wrist direction {max(angles):.1f}deg')
 check(float(np.linalg.norm(endpoints[(identifier,0)]-endpoints[(identifier,150)],axis=1).max())<1e-5,f'{identifier} loop skin differs')
with gzip.open(P/'ninety-dq-reference.json.gz','wt',compresslevel=9) as stream:json.dump({'source_sha256':source_sha,'source_vertices':10582,'skinning':'dualQuaternion','coordinate_frame':'Blender world metres, original source IDs, Armature plus four local morphs; all non-Armature modifiers disabled','samples':samples},stream,separators=(',',':'))
(P/'ninety-pose-samples.json').write_text(json.dumps(pose_samples,separators=(',',':'))+'\n')
(P/'ninety-runtime-surface-reference.json').write_text(json.dumps({'source_sha256':source_sha,'coordinate_frame':'Blender world metres','source_index_attribute':'_SOURCE_INDEX','source_vertices':10582,'samples':surface_samples},separators=(',',':'))+'\n')
normal_reference={'source_sha256':source_sha,'coordinate_frame':'Original Blender mesh rest normals, Z up','basis':np.array(keys.key_blocks['Basis'].normals_vertex_get()).reshape((-1,3)).tolist(),'targets':{name:np.array(keys.key_blocks[name].normals_vertex_get()).reshape((-1,3)).tolist() for name in sum(k.NAMES.values(),[])}}
with gzip.open(P/'ninety-normal-reference.json.gz','wt',compresslevel=9) as stream:json.dump(normal_reference,stream,separators=(',',':'))
select('6560',75);sys.path.insert(0,'/Users/kolengri/.codex/skills/blender-asset-qa/scripts');import qa_check
qa=qa_check.run(objects=[body.name],profile='game');(P/'asset-qa.json').write_text(json.dumps(qa,indent=2)+'\n')
check(qa['pass'],'Asset QA errors: '+str(qa.get('errors')))
report={'ok':not failures,'failures':failures,'source_sha256':source_sha,'binding_rest_uv_sha256':EXPECTED,'original_basis_weights_uv_source_ids_unchanged':True,'vertices':10582,'triangles':sum(len(p.vertices)-2 for p in body.data.polygons),'bones':51,'actions':['Exercise_10565','Exercise_6560'],'morphs':sum(k.NAMES.values(),[]),'all_non_armature_modifiers_disabled':True,'preview_seconds':5,'preview_hold_seconds':1,'source_workout_hold_seconds':[20,30],'samples_checked':302,'all_skin_min_z_m':min(r['global_floor_z'] for r in allrows),'loop_skin_error_max_m':max(float(np.linalg.norm(endpoints[(i,0)]-endpoints[(i,150)],axis=1).max()) for i in ['10565','6560']),'wrist_direction_ranges_degrees':{i:{side:[min(r['wrist_directions'][side]['forearm_to_middle_proximal_degrees'] for r in allrows if r['id']==i),max(r['wrist_directions'][side]['forearm_to_middle_proximal_degrees'] for r in allrows if r['id']==i)] for side in ['Left','Right']} for i in ['10565','6560']},'native_target_error_samples':errors,'asset_qa_warnings':qa.get('warnings',[]),'visual_status':'Primary approved early full-body shape only; final source stills and actual Three.js DQ+morph/normal appearance require review.'}
(P/'source-verification.json').write_text(json.dumps(report,indent=2)+'\n');(P/'full-path-measurements.json').write_text(json.dumps(allrows,separators=(',',':'))+'\n');print(json.dumps(report,indent=2))
