"""Actual saved native/decoded full-cycle evidence, not a runtime cache."""
import bpy,numpy as np,json,gzip,sys,hashlib
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
F=Path(__file__).resolve().parent;ID=sys.argv[sys.argv.index('--')+1];P=F.parent/'assets'/ID
sys.path[:0]=[str(F),str(F.parent.parent/'batch-003')];import authoring as a,motion
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def signature(b,r):
 h=hashlib.sha256();h.update(np.array([v.co[:]for v in b.data.vertices],np.float32).tobytes())
 for p in b.data.polygons:h.update(np.array(p.vertices,np.int32).tobytes())
 for uv in b.data.uv_layers:h.update(uv.name.encode());h.update(np.array([v.uv[:]for v in uv.data],np.float32).tobytes())
 for bone in r.data.bones:h.update(bone.name.encode());h.update(np.array(bone.matrix_local,np.float32).tobytes())
 return h.hexdigest()
a.initialize();original=signature(a.body,a.rig)
bpy.ops.wm.open_mainfile(filepath=str(P/'source.blend'));b=bpy.data.objects['SK_BlenderStudioHuman'];r=bpy.data.objects['RIG_BlenderStudioHuman'];s=bpy.context.scene;source_sha=sha(P/'source.blend');r.animation_data.action=bpy.data.actions['Exercise_'+ID];r.animation_data.action_slot=next(x for x in r.animation_data.action.slots if x.target_id_type=='OBJECT')
assert signature(b,r)==original and len(b.data.vertices)==10582 and len(r.data.bones)==51
weights=[{b.vertex_groups[g.group].name:float(g.weight)for g in v.groups}for v in b.data.vertices];assert max(map(len,weights))<=4 and max(abs(sum(w.values())-1)for w in weights)<2e-6
assert a.binding_hash(b,r)==json.loads((P/'local-binding-report.json').read_text())['runtime_binding_sha256']
assert not b.data.shape_keys
for m in b.modifiers:assert m.show_viewport==(m.type=='ARMATURE') and m.show_render==(m.type=='ARMATURE')
assert next(m for m in b.modifiers if m.type=='ARMATURE').use_deform_preserve_volume
b.data.calc_loop_triangles();tri=np.array([t.vertices[:]for t in b.data.loop_triangles],int);rest=np.array([v.co[:]for v in b.data.vertices]);names={g.index:g.name for g in b.vertex_groups}
def ids(prefixes):return set(v.index for v in b.data.vertices if sum(g.weight for g in v.groups if any(names[g.group].startswith(p)for p in prefixes))>.5)
patches={};arms={};legs={}
for side in ['Left','Right']:
 arms[side]=ids([side+x for x in ['Arm','ForeArm','Hand','Index','Middle','Ring','Little','Thumb']]);legs[side]=ids([side+x for x in ['UpLeg','Leg','Foot','ToeBase']])
 for part,prefix in [('hand',['Hand','Index','Middle','Ring','Little','Thumb']),('foot',['Foot','ToeBase']),('shin',['Leg']),('thigh',['UpLeg'])]:patches[part+'_'+side]={'indices':sorted(ids([side+x for x in prefix])),'rationale':'Frozen original source IDs with dominant combined named deformation groups; full skin domain.'}
for side in ['Left','Right']:
 h=r.data.bones[side+'Hand'];axis=(h.tail_local-h.head_local).normalized();idx=[]
 for v in b.data.vertices:
  t=(v.co-h.head_local).dot(axis)
  if weights[v.index].get(side+'Hand',0)>.8 and .025<t<.105:idx.append(v.index)
 patches['palm_'+side]={'indices':idx,'rationale':'Frozen source heel/central palm:dominantHand>80%,25–105mm along original Hand axis from wrist. Fingers are excluded; whole-hand floor is checked separately.'}
patches['pelvis']={'indices':np.where((rest[:,2]>.86)&(rest[:,2]<1.03)&(abs(rest[:,0])<.18))[0].tolist(),'rationale':'Source-only pelvic domain86–103cm sourceZ within18cm midline.'}
patches['lowerchest']={'indices':np.where((rest[:,2]>1.08)&(rest[:,2]<1.28)&(abs(rest[:,0])<.2))[0].tolist(),'rationale':'Source-only lowerchest108–128cm sourceZ within20cm midline.'}
faces={side:[list(p.vertices)for p in b.data.polygons if all(i in legs[side]for i in p.vertices)]for side in legs}
decoded_path=Path(sys.argv[sys.argv.index('--decoded')+1])if '--decoded'in sys.argv else None;decoded=np.fromfile(decoded_path,dtype=np.float32).reshape(151,10582,3)if decoded_path else None
samples=[];poses=[];refs=[];dq=[];fail=[];max_decoded=0.;start=None;minarea=1.;minfloor=1.;maxreach=0.;allpose=[0,15,30,45,60,75,90,105,120,135,150]
for f in range(151):
 s.frame_set(f+1);bpy.context.view_layer.update();e=b.evaluated_get(bpy.context.evaluated_depsgraph_get());me=e.to_mesh();native=np.array([v.co[:]for v in me.vertices]);e.to_mesh_clear();p=native if decoded is None else decoded[f].astype(float)
 if decoded is not None:max_decoded=max(max_decoded,float(np.linalg.norm(p-native,axis=1).max()))
 state=motion.schedule(f,ID);z=float(p[:,2].min());area=np.linalg.norm(np.cross(p[tri[:,1]]-p[tri[:,0]],p[tri[:,2]]-p[tri[:,0]]),axis=1)/2;mina=float(area.min());minarea=min(minarea,mina);minfloor=min(minfloor,z)
 if z<-.00035:fail.append(f'frame{f}: floor {z}')
 if mina<=1e-12:fail.append(f'frame{f}: nonpositive triangle area {mina}')
 contacts={name:float(p[patch['indices'],2].min())for name,patch in patches.items()}
 if ID in ['4702','4715']:
  for name,tol in [('pelvis',.004),('lowerchest',.005)]:
   if not(-.00035<=contacts[name]<=tol):fail.append(f'frame{f}: {name} support {contacts[name]}')
  for side in ['Left','Right']:
   arm_lift=state['envelope']if side==state['arm']else 0.;leg_lift=state['envelope']if side==state['leg']else 0.
   if arm_lift<1e-8 and not(-.00035<=contacts['palm_'+side]<=.002):fail.append(f'frame{f}: resting {side} hand support {contacts["palm_"+side]}')
   if leg_lift<1e-8 and not(-.00035<=contacts['foot_'+side]<=.005):fail.append(f'frame{f}: resting {side} foot support {contacts["foot_"+side]}')
 else:
  for name in ['palm_Left','palm_Right','foot_Left','foot_Right']:
   if not(-.00035<=contacts[name]<=.002):fail.append(f'frame{f}: {name} missing support {contacts[name]}')
 vec=[Vector(v)for v in p];trees={side:BVHTree.FromPolygons(vec,face_list)for side,face_list in faces.items()};clearance={}
 for arm in arms:
  for leg in legs:
   distance=[];signed=[];inside=[]
   for i in arms[arm]:
    q,n,face,dist=trees[leg].find_nearest(vec[i]);d=(vec[i]-q).dot(n);distance.append(dist)
    if dist<.04:signed.append(d)
    if dist<.04 and d<-.004:inside.append(i)
   clearance[arm+'_arm_to_'+leg+'_leg']={'minimum_distance_m':min(distance),'minimum_close_signed_distance_m':min(signed)if signed else None,'vertices_over4mm_inside':len(inside)}
   if inside:fail.append(f'frame{f}: {arm} arm/{leg} leg {len(inside)} vertices>4mm inside')
 angles={}
 for side in legs:
  for kind,chain in [('knee',['UpLeg','Leg','Foot']),('elbow',['Arm','ForeArm','Hand'])]:
   hh=[r.pose.bones[side+n].head for n in chain];angles[side+'_'+kind]=float((hh[0]-hh[1]).angle(hh[2]-hh[1])*180/np.pi)
  if ID=='3294'and angles[side+'_knee']<174:fail.append(f'frame{f}: bent plank knee {side} {angles[side+"_knee"]}')
 if ID=='3294'and state['envelope']>.999:
  far='Left'if state['load_side']=='Right'else'Right'
  if angles[far+'_elbow']<165:fail.append(f'frame{f}: extended elbow {angles[far+"_elbow"]}')
 row={'frame':f,'phase':state,'whole_skin_min_z_m':z,'minimum_triangle_area_m2':mina,'skin_patch_minima_m':contacts,'whole_limb_clearance':clearance,'internal_joint_degrees':angles};samples.append(row)
 if f in allpose:
  poses.append({'id':ID,'frame':f,'joints':{pb.name:list(r.matrix_world@pb.head)for pb in r.pose.bones}})
  refs.append({'id':ID,'frame':f,'global_floor_z':z,'floor_plane_z':0,'phase':state,'patches':{name:{**patch,'positions':p[patch['indices']].tolist(),'min_z':contacts[name],'max_z':float(p[patch['indices'],2].max())}for name,patch in patches.items()}})
 if f in [0,30,75,120,150]:dq.append({'id':ID,'frame':f,'positions':p.tolist()})
 if f==0:start=p.copy();startbones=np.array([pb.matrix for pb in r.pose.bones])
 if f==150:end=p.copy();endbones=np.array([pb.matrix for pb in r.pose.bones])
loop=float(np.linalg.norm(start-end,axis=1).max());boneloop=float(abs(startbones-endbones).max())
if loop>1e-5 or boneloop>1e-5:fail.append('Loop mismatch')
if decoded is not None and max_decoded>.0001:fail.append('151native/decoded parity exceeds100micrometers')
if decoded is None:
 for name,data in [('runtime-surface-reference.json',{'source_sha256':source_sha,'reference_kind':'native_armature_only_DQ','source_vertices':10582,'coordinate_system':'BlenderZup meters; runtime[x,z,-y]','samples':refs}),('surface-landmarks.json',{'source_sha256':source_sha,'patches':patches,'whole_arm_ids':{k:sorted(v)for k,v in arms.items()},'whole_leg_ids':{k:sorted(v)for k,v in legs.items()},'leg_faces':faces,'triangles':tri.tolist()}),('pose-samples.json',poses)]:
  (P/name).write_text(json.dumps(data,separators=(',',':'))+'\n')
 with gzip.open(P/'dq-reference.json.gz','wt')as out:json.dump({'source_sha256':source_sha,'source_vertices':10582,'samples':dq},out,separators=(',',':'))
 with gzip.open(P/'normal-reference.json.gz','wt')as out:json.dump({'source_sha256':source_sha,'basis':[v.normal[:]for v in b.data.vertices]},out,separators=(',',':'))
report={'ok':not fail,'source_sha256':source_sha,'native_integer_frames':151,'maximum_full151_native_decoded_error_m':max_decoded if decoded is not None else None,'minimum_floor_z_m':minfloor,'minimum_triangle_area_m2':minarea,'loop_skin_error_m':loop,'loop_bone_max_element_error':boneloop,'tolerances':{'floor_penetration_m':.00035,'support_hand_foot_gap_m':.002,'prone_pelvis_gap_m':.004,'prone_lowerchest_foot_gap_m':.005,'local_inside_m':.004,'archer_knee_min_internal_degrees':174,'peak_extended_elbow_min_degrees':165},'scope':'Actual full native DQ skin; whole arms/hands/fingers versus both full legs. Local nearest-normal inside diagnostic only within40mm. No global collision-free or clinical claim.','failures':fail,'samples':samples}
(P/('decoded-physical-report.json'if decoded is not None else'surface-contact-report.json')).write_text(json.dumps(report,indent=2)+'\n')
(P/('decoded-source-readback.json'if decoded is not None else'source-verification.json')).write_text(json.dumps({'ok':True,'source_sha256':source_sha,'original_source_sha256':a.SOURCE_SHA,'basis_topology_uv_bone_rest_sha256':original,'basis_topology_uv_bone_rest_unchanged':True,'runtime_binding_sha256':a.binding_hash(b,r),'maximum_influences':max(map(len,weights)),'maximum_weight_sum_error':max(abs(sum(w.values())-1)for w in weights),'vertices':10582,'triangles':len(tri),'bones':51,'morphs':[],'actions':[x.name for x in bpy.data.actions],'active_action':'Exercise_'+ID,'only_armature_enabled':True,'dual_quaternion':True,'actual_saved_weights_by_name':weights},indent=2)+'\n')
print('GATES',json.dumps({'ok':not fail,'failure_count':len(fail),'failures':fail[:12],'floor':minfloor,'area':minarea,'loop':loop,'max_decoded':max_decoded}),flush=True)
if '--game-qa'in sys.argv:
 sys.path.insert(0,str(Path.home()/'.codex/skills/blender-asset-qa/scripts'));import qa_check
 qa=[]
 for f in [0,30,105]:s.frame_set(f+1);bpy.context.view_layer.update();qa.append({'frame':f,'report':qa_check.run(objects=[b.name],profile='game')})
 q={'pass':all(x['report']['pass']for x in qa),'source_sha256':source_sha,'samples':qa};(P/'raw-asset-qa.json').write_text(json.dumps(q,indent=2)+'\n');assert q['pass']
if decoded_path:decoded_path.unlink();decoded_path.parent.rmdir();(P/'verification-exchange-path.txt').unlink()
assert not fail,fail[:15]
