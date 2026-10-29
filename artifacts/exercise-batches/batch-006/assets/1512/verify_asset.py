"""Immutable-source skin supports, full limbs and native DQ references."""
import bpy,json,sys,hashlib,gzip
sys.dont_write_bytecode=True
from pathlib import Path
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
P=Path(__file__).resolve().parent
SHA=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(P/'source.blend'))
b=bpy.data.objects['SK_BlenderStudioHuman'];r=bpy.data.objects['RIG_BlenderStudioHuman'];s=bpy.context.scene
for mod in b.modifiers:
 mod.show_viewport=mod.show_render=mod.type=='ARMATURE'
 if mod.type=='ARMATURE':mod.use_deform_preserve_volume=True
source_sha=SHA(P/'source.blend');rest=np.array([v.co[:]for v in b.data.vertices]);names={g.index:g.name for g in b.vertex_groups}
weights={name:np.array([sum(g.weight for g in v.groups if names[g.group]==name)for v in b.data.vertices])for name in names.values()}
def ids(prefixes):return set(v.index for v in b.data.vertices if sum(g.weight for g in v.groups if any(names[g.group].startswith(p)for p in prefixes))>.5)
def sample(f):
 s.frame_set(f+1);bpy.context.view_layer.update();e=b.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=e.to_mesh();points=np.array([v.co[:]for v in mesh.vertices]);return e,mesh,points
e,mesh,start=sample(0)
patches={}
def patch(name,candidate,rationale,state):
 faces=[]
 for face in mesh.polygons:
  if not all(candidate[i]for i in face.vertices):continue
  pp=start[list(face.vertices)];normal=np.cross(pp[1]-pp[0],pp[2]-pp[0]);normal/=max(np.linalg.norm(normal),1e-12)
  if normal[2]<-.35:faces.append((face.index,float(pp[:,2].mean()),list(face.vertices)))
 assert faces,name
 low=min(v[1]for v in faces);chosen=[v for v in faces if v[1]<low+.005]
 patches[name]={'indices':sorted({i for _,_,vs in chosen for i in vs}),'polygons':[i for i,_,_ in chosen],'rationale':rationale,'state':state,'selection':'Actual floor-facing original skin faces within5mm of local lowest face centroid, frozen IDs.'}
for side,sign in [('Left',1),('Right',-1)]:
 state='supported'if side=='Right'else'initial_support_then_lifted'
 patch('palm_'+side,weights[side+'Hand']>.8,'Actual palmar heel, independent of finger or wrist joints.',state)
 patch('knee_'+side,(rest[:,0]*sign>0)&(rest[:,2]>.445)&(rest[:,2]<.525),'Anterior knee skin under hip; not a joint proxy.',state)
 patch('foot_'+side,(weights[side+'Foot']+weights[side+'ToeBase'])>.8,'Resting dorsal/toe surface of trailing foot.',state)
e.to_mesh_clear()
# Whole arms include all finger surfaces. Legs include thigh, calf and foot;
# source-Z ankle subset is retained separately for the intended left grip.
arms={side:ids([side+x for x in ['Arm','ForeArm','Hand','Index','Middle','Ring','Little','Thumb']])for side in ['Left','Right']}
hands={side:ids([side+x for x in ['Hand','Index','Middle','Ring','Little','Thumb']])for side in ['Left','Right']}
legs={side:ids([side+x for x in ['UpLeg','Leg','Foot','ToeBase']])for side in ['Left','Right']}
ankle={i for i in legs['Left']if rest[i,2]<.22}
faces={side:[list(p.vertices)for p in b.data.polygons if all(i in legs[side]for i in p.vertices)]for side in ['Left','Right']}
ankle_faces=[list(p.vertices)for p in b.data.polygons if all(i in ankle for i in p.vertices)]
b.data.calc_loop_triangles();triangles=np.array([list(t.vertices)for t in b.data.loop_triangles])
samples=[];refs=[];dq=[];poses=[];morphs=[];failures=[];initial=None;last=None
frames=[0,15,25,30,39,40,45,60,75,90,105,111,115,120,135,150]
for f in range(151):
 e,mesh,pos=sample(f)
 if f==0:initial=pos.copy()
 if f==150:last=pos.copy()
 contacts={}
 for name,p in patches.items():
  pp=pos[p['indices']];z=pp[:,2];near=float(np.mean(abs(z)<=.012));drift=float(np.max(np.linalg.norm(pp[:,:2]-start[p['indices'],:2],axis=1)))
  contacts[name]={'min_z':float(z.min()),'max_z':float(z.max()),'fraction_near_floor':near,'maximum_tangential_drift_m':drift}
  if p['state']=='supported'and(z.min()>.012 or near<.2):failures.append(f'frame{f}: {name} lacks skin support')
  if name=='palm_Right'and drift>.005:failures.append(f'frame{f}: supporting palm drift')
 if pos[:,2].min()<-.004:failures.append(f'frame{f}: floor penetration')
 pp=pos[triangles];minimum_area=float((.5*np.linalg.norm(np.cross(pp[:,1]-pp[:,0],pp[:,2]-pp[:,0]),axis=1)).min())
 if minimum_area<=1e-12:failures.append(f'frame{f}: nonpositive triangle area')
 trees={side:BVHTree.FromPolygons([Vector(p)for p in pos],face_list)for side,face_list in faces.items()}
 limb_metrics={}
 for arm_side in ['Left','Right']:
  for leg_side in ['Left','Right']:
   tree=trees[leg_side];distances=[];inside=[];signed_close=[]
   for i in arms[arm_side]:
    nearest,normal,face,distance=tree.find_nearest(Vector(pos[i]));signed=(Vector(pos[i])-nearest).dot(normal)
    distances.append(distance)
    if distance<.04:signed_close.append(signed)
    if signed<-.004 and distance<.04:inside.append(i)
   key=arm_side+'_arm_to_'+leg_side+'_leg'
   limb_metrics[key]={'minimum_distance_m':min(distances),'minimum_close_signed_distance_m':min(signed_close)if signed_close else None,'vertices_over4mm_inside':len(inside)}
   if inside:failures.append(f'frame{f}: {key} has{len(inside)} skin vertices inside')
 tree=BVHTree.FromPolygons([Vector(p)for p in pos],ankle_faces)
 grip_distances=[tree.find_nearest(Vector(pos[i]))[3]for i in hands['Left']]
 grip={'minimum_distance_m':min(grip_distances),'hand_vertices_within5mm':sum(v<=.005 for v in grip_distances)}
 if 39<=f<=111 and not(grip['minimum_distance_m']<.005 and grip['hand_vertices_within5mm']>=3):failures.append(f'frame{f}: missing ankle grip')
 row={'frame':f,'global_floor_z':float(pos[:,2].min()),'floor_plane_z':0,'minimum_triangle_area_m2':minimum_area,'contacts':contacts,'whole_limb_clearance':limb_metrics,'ankle_grip':grip}
 samples.append(row)
 if f in frames:
  poses.append({'id':'1512','frame':f,'joints':{pb.name:list(r.matrix_world@pb.head)for pb in r.pose.bones}})
  morphs.append({'frame':f,'weights':{k.name:float(k.value)for k in b.data.shape_keys.key_blocks if k.name!='Basis'}})
  refs.append({'id':'1512','frame':f,'global_floor_z':float(pos[:,2].min()),'floor_plane_z':0,'patches':{name:{'indices':p['indices'],'positions':pos[p['indices']].tolist(),'min_z':contacts[name]['min_z'],'max_z':contacts[name]['max_z'],'state':p['state']}for name,p in patches.items()}})
 if f in [0,30,75,120,150]:dq.append({'id':'1512','frame':f,'positions':pos.tolist()})
 e.to_mesh_clear()
loop=float(np.linalg.norm(initial-last,axis=1).max())
if loop>.0001:failures.append('Skin loop mismatch')
surface={'source_sha256':source_sha,'reference_kind':'native_armature_only_DQ_with_explicit_compact_keys','source_vertices':10582,'coordinate_system':'Blender Z-up meters; runtime[x,z,-y]','samples':refs}
(P/'runtime-surface-reference.json').write_text(json.dumps(surface,separators=(',',':'))+'\n')
with gzip.open(P/'dq-reference.json.gz','wt')as handle:json.dump({'source_sha256':source_sha,'source_vertices':10582,'samples':dq},handle,separators=(',',':'))
(P/'surface-landmarks.json').write_text(json.dumps({'source_sha256':source_sha,'source_vertices':10582,'patches':patches,'ankle_grip_original_ids':sorted(ankle),'scope':'Actual original10582vertex domain, all indices frozen to the source cage.'},indent=2)+'\n')
(P/'pose-samples.json').write_text(json.dumps(poses,indent=2)+'\n')
(P/'source-morph-samples.json').write_text(json.dumps({'source_sha256':source_sha,'samples':morphs},indent=2)+'\n')
report={'ok':not failures,'source_sha256':source_sha,'skinning':'dualQuaternion','frames':151,'floor_plane_z':0,'minimum_global_z':min(x['global_floor_z']for x in samples),'maximum_global_min_z':max(x['global_floor_z']for x in samples),'loop_skin_error_m':loop,'support_tolerance':{'band_m':.012,'minimum_patch_fraction':.2,'maximum_floor_penetration_m':.004,'maximum_palm_drift_m':.005},'clearance_tolerance':'Every whole arm,hand,finger vs both whole legs; nearest-normal inside check within40mm,4mm tolerance. Intended ankle grip requires>=3hand vertices within5mm throughout hold. No bone-only skin inference.','failures':failures,'samples':samples}
(P/'surface-contact-report.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'ok':report['ok'],'failures':failures[:15],'minimum_global_z':report['minimum_global_z'],'loop_skin_error_m':loop,'support_patches':{k:len(v['indices'])for k,v in patches.items()},'hold_contacts':samples[75]['contacts'],'hold_grip':samples[75]['ankle_grip']},indent=2))
assert not failures,failures[:15]

if '--game-qa'in sys.argv:
 sys.path.insert(0,'/Users/kolengri/.codex/skills/blender-asset-qa/scripts');import qa_check
 qa=[]
 for f in [0,25,40,75,115]:
  s.frame_set(f+1);bpy.context.view_layer.update();result=qa_check.run(objects=[b.name],profile='game')
  qa.append({'frame':f,'report':result,'warning_locations':getattr(qa_check,'QA_WARNING_DETAILS',{}),'checker_detail_availability':'Installed checker has no QA_WARNING_DETAILS export; complete ordinary metrics and warnings retained.'})
 data={'pass':all(x['report']['pass']for x in qa),'source_sha256':source_sha,'samples':qa}
 (P/'asset-qa.json').write_text(json.dumps(data,indent=2)+'\n')
 print('GAME_QA',json.dumps({'pass':data['pass'],'results':[{'frame':x['frame'],'errors':x['report']['errors'],'warnings':x['report']['warnings']}for x in qa]}))
 assert data['pass']
