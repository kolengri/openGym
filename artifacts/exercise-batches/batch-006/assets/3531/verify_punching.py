"""Actual saved native skin gates; sparse references only, no runtime cache."""
import bpy,numpy as np,json,gzip,sys,hashlib
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
P=Path(__file__).resolve().parent;F=P.parents[1]/'upright-cardio-family';ID='3531'
sys.path[:0]=[str(F),str(F.parent.parent/'batch-003')];import authoring as a
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def signature(b,r):
 h=hashlib.sha256();h.update(np.array([v.co[:]for v in b.data.vertices],np.float32).tobytes())
 for p in b.data.polygons:h.update(np.array(p.vertices,np.int32).tobytes())
 for uv in b.data.uv_layers:
  h.update(uv.name.encode());h.update(np.array([v.uv[:]for v in uv.data],np.float32).tobytes())
 for bone in r.data.bones:h.update(bone.name.encode());h.update(np.array(bone.matrix_local,np.float32).tobytes())
 return h.hexdigest()
a.initialize();original=signature(a.body,a.rig)
bpy.ops.wm.open_mainfile(filepath=str(P/'source.blend'));b=bpy.data.objects['SK_BlenderStudioHuman'];r=bpy.data.objects['RIG_BlenderStudioHuman'];s=bpy.context.scene;source_sha=sha(P/'source.blend')
assert signature(b,r)==original
assert [x.name for x in bpy.data.actions]==['Exercise_'+ID]
assert len(b.data.vertices)==10582 and len(r.data.bones)==51
assert a.binding_hash(b,r)==json.loads((P/'local-binding-report.json').read_text())['runtime_binding_sha256']
assert max(len(v.groups)for v in b.data.vertices)<=4
assert max(abs(sum(g.weight for g in v.groups)-1)for v in b.data.vertices)<2e-6
assert not b.data.shape_keys
for m in b.modifiers:assert m.show_viewport==(m.type=='ARMATURE') and m.show_render==(m.type=='ARMATURE')
assert next(m for m in b.modifiers if m.type=='ARMATURE').use_deform_preserve_volume
b.data.calc_loop_triangles();tri=np.array([t.vertices[:]for t in b.data.loop_triangles],int);rest=np.array([v.co[:]for v in b.data.vertices]);names={g.index:g.name for g in b.vertex_groups}
def ids(prefixes):return set(v.index for v in b.data.vertices if sum(g.weight for g in v.groups if any(names[g.group].startswith(p)for p in prefixes))>.5)
soles={side:np.array([v.index for v in b.data.vertices if v.co.z<.10 and sum(g.weight for g in v.groups if names[g.group]in[side+'Foot',side+'ToeBase'])>.5],int)for side in ['Left','Right']}
arms={side:ids([side+x for x in ['Arm','ForeArm','Hand','Index','Middle','Ring','Little','Thumb']])for side in soles};legs={side:ids([side+x for x in ['UpLeg','Leg','Foot','ToeBase']])for side in soles};faces={side:[list(p.vertices)for p in b.data.polygons if all(i in legs[side]for i in p.vertices)]for side in soles}
palms={side:set(v.index for v in b.data.vertices if sum(g.weight for g in v.groups if names[g.group]==side+'Hand')>.8)for side in soles};palmfaces={side:[list(p.vertices)for p in b.data.polygons if all(i in palms[side]for i in p.vertices)]for side in soles};distal={side:set(v.index for v in b.data.vertices if sum(g.weight for g in v.groups if names[g.group].startswith(side)and any(digit in names[g.group]for digit in ['Index2','Index3','Middle2','Middle3','Ring2','Ring3','Little2','Little3','Thumb2','Thumb3']))>.8)for side in soles}
# Frozen source-domain plantar posterior/anterior envelopes for roll/contact evidence.
patches={}
for side,idx in soles.items():
 q=rest[idx];patches['sole_'+side]={'indices':idx.tolist(),'rationale':'All original distal foot/toe skin IDs below sourceZ100mm with dominant Foot+ToeBase influence.'}
 # A compact floor-facing bottom envelope, retaining both heel and ball.
 bottom=idx[q[:,2]<=np.percentile(q[:,2],20)+.001]
 for part,select in [('heel',rest[bottom,1]>np.median(rest[idx,1])),('ball',rest[bottom,1]<=np.median(rest[idx,1]))]:
  chosen=bottom[select];patches[part+'_'+side]={'indices':chosen.tolist(),'rationale':'Frozen lowest20% source plantar skin, divided by source foot medianY.'}
import motion
decoded_path=Path(sys.argv[sys.argv.index('--decoded')+1])if '--decoded'in sys.argv else None
decoded=np.fromfile(decoded_path,dtype=np.float32).reshape(151,10582,3)if decoded_path else None
max_decoded_error=0
samples=[];poses=[];refs=[];dq=[];fail=[];start=None;end=None;minarea=1;maxhandinside=0
frames=[0,5,8,16,25,30,33,50,58,75,83,100,108,120,125,133,150]
# mandatory frames + distinct flight/impact/punch samples; fractional references are optional sparse reads.
allframes=sorted(set(list(range(151))+frames))
for f in allframes:
 s.frame_set(int(f)+1,subframe=f%1);bpy.context.view_layer.update();e=b.evaluated_get(bpy.context.evaluated_depsgraph_get());me=e.to_mesh();p=np.array([v.co[:]for v in me.vertices]);native_p=p.copy()
 if decoded is not None and float(f).is_integer():
  p=decoded[int(f)].astype(float);max_decoded_error=max(max_decoded_error,float(np.linalg.norm(p-native_p,axis=1).max()))
 state=motion.schedule(f,ID);z=float(p[:,2].min());area=np.linalg.norm(np.cross(p[tri[:,1]]-p[tri[:,0]],p[tri[:,2]]-p[tri[:,0]]),axis=1)/2;mina=float(area.min());minarea=min(minarea,mina)
 if z<-.00035:fail.append(f'frame{f}: floor {z}')
 if mina<=1e-12:fail.append(f'frame{f}: nonpositive triangle area {mina}')
 contacts={}
 for side,idx in soles.items():
  lo=float(p[idx,2].min());ground=side in state['grounded'];contacts[side]={'min_z_m':lo,'grounded':ground,'foot_rotation_from_rest_degrees':float(r.pose.bones[side+'Foot'].matrix.to_quaternion().rotation_difference(r.data.bones[side+'Foot'].matrix_local.to_quaternion()).angle*180/np.pi)}
  if ground and not(-.00035<=lo<=.002):fail.append(f'frame{f}: {side} sole missing support {lo}')
  if state['flight']and lo<=.0001:fail.append(f'frame{f}: {side} flight skin lacks clearance {lo}')
 vecs=[Vector(v)for v in p];trees={side:BVHTree.FromPolygons(vecs,face_list)for side,face_list in faces.items()};clearance={}
 for arm in soles:
  for leg in soles:
   signed=[];distance=[];inside=[]
   for i in arms[arm]:
    q,n,face,dist=trees[leg].find_nearest(vecs[i]);d=(vecs[i]-q).dot(n);distance.append(dist)
    if dist<.04:signed.append(d)
    if dist<.04 and d<-.004:inside.append(i)
   clearance[arm+'_arm_to_'+leg+'_leg']={'minimum_distance_m':min(distance),'minimum_close_signed_distance_m':min(signed)if signed else None,'vertices_over4mm_inside':len(inside)}
   if inside:fail.append(f'frame{f}: {arm} arm/{leg} leg {len(inside)} vertices>4mm inside')
 hand={}
 if ID=='3531':
  for side in soles:
   tree=BVHTree.FromPolygons(vecs,palmfaces[side]);inside=[];close=[]
   for i in distal[side]:
    q,n,face,dist=tree.find_nearest(vecs[i]);signed=(vecs[i]-q).dot(n)
    if dist<.025:close.append(signed)
    if dist<.025 and signed<-.004:inside.append(i)
   hand[side]={'distal_vertices_more_than4mm_inside_palm':len(inside),'minimum_close_signed_distance_m':min(close)if close else None,'diagnostic_ids':inside};maxhandinside=max(maxhandinside,len(inside))
   if inside:fail.append(f'frame{f}: {side} distal fingers penetrate palm {len(inside)}')
 elbow={};knee={}
 for side in soles:
  sh=r.pose.bones[side+'Arm'].head;el=r.pose.bones[side+'ForeArm'].head;wr=r.pose.bones[side+'Hand'].head;elbow[side]=float((sh-el).angle(wr-el)*180/np.pi);knee[side]=float(r.pose.bones[side+'Leg'].head.z-r.pose.bones['Hips'].head.z)
  if ID=='3531'and elbow[side]>165:fail.append(f'frame{f}: elbow hyperextension authoredbound {elbow[side]}')
 row={'frame':f,'phase':state,'whole_skin_min_z_m':z,'minimum_triangle_area_m2':mina,'soles':contacts,'whole_limb_clearance':clearance,'fist_palm_clearance':hand,'elbow_internal_degrees':elbow,'knee_height_above_pelvis_m':knee,'root_z_m':float(r.pose.bones['Hips'].head.z)}
 if float(f).is_integer():samples.append(row)
 if f in frames:
  poses.append({'id':ID,'frame':f,'joints':{pb.name:list(r.matrix_world@pb.head)for pb in r.pose.bones}})
  refs.append({'id':ID,'frame':f,'global_floor_z':z,'floor_plane_z':0,'phase':state,'patches':{name:{**patch,'positions':p[patch['indices']].tolist(),'min_z':float(p[patch['indices'],2].min()),'max_z':float(p[patch['indices'],2].max()),'state':'supported'if name.split('_')[-1]in state['grounded']else'flight'if state['flight']else'lifted'}for name,patch in patches.items()}})
 if f in [0,30,75,120,150]:dq.append({'id':ID,'frame':f,'positions':p.tolist()})
 if f==0:start=p.copy();startbones=np.array([pb.matrix for pb in r.pose.bones])
 if f==150:end=p.copy();endbones=np.array([pb.matrix for pb in r.pose.bones])
 e.to_mesh_clear()
loop=float(np.max(np.linalg.norm(start-end,axis=1)));boneloop=float(np.max(abs(startbones-endbones)))
if loop>1e-5 or boneloop>1e-5:fail.append('Loop mismatch')
for name,data in ([]if decoded_path else [('runtime-surface-reference.json',{'source_sha256':source_sha,'reference_kind':'native_armature_only_DQ','source_vertices':10582,'coordinate_system':'BlenderZup meters; runtime[x,z,-y]','samples':refs}),('surface-landmarks.json',{'source_sha256':source_sha,'patches':patches,'whole_arm_ids':{k:sorted(v)for k,v in arms.items()},'whole_leg_ids':{k:sorted(v)for k,v in legs.items()},'leg_faces':faces,'palm_faces':palmfaces,'distal_finger_ids':{k:sorted(v)for k,v in distal.items()},'triangles':tri.tolist()}),('pose-samples.json',poses)]):
 (P/name).write_text(json.dumps(data,separators=(',',':'))+'\n')
with gzip.open(P/('decoded-five-reference-verification.json.gz'if decoded_path else'dq-reference.json.gz'),'wt')as out:json.dump({'source_sha256':source_sha,'source_vertices':10582,'samples':dq},out,separators=(',',':'))
with gzip.open(P/('decoded-normal-readback.json.gz'if decoded_path else'normal-reference.json.gz'),'wt')as out:json.dump({'source_sha256':source_sha,'basis':[v.normal[:]for v in b.data.vertices]},out,separators=(',',':'))
if decoded_path and max_decoded_error>.0001:fail.append('Full151 native/decoded parity exceeds100micrometers')
report={'ok':not fail,'maximum_full151_native_decoded_error_m':max_decoded_error if decoded_path else None,'source_sha256':source_sha,'native_integer_frames':151,'additional_fractional_frames':[f for f in frames if f%1],'minimum_floor_z_m':min(x['whole_skin_min_z_m']for x in samples),'minimum_triangle_area_m2':minarea,'loop_skin_error_m':loop,'loop_bone_max_element_error':boneloop,'tolerances':{'floor_penetration_m':.00035,'grounded_sole_max_gap_m':.002,'flight_sole_min_gap_m':.0001,'local_inside_m':.004,'elbow_internal_max_degrees':165},'scope':'Actual full native DQ skin; whole arms/hands/fingers versus both full legs; local nearest-normal inside only within40mm. Finger/palm diagnostic within25mm. No global self-collision or clinical claim.','failures':fail,'samples':samples};(P/('decoded-physical-report.json'if decoded_path else'surface-contact-report.json')).write_text(json.dumps(report,indent=2)+'\n')
(P/('decoded-source-readback.json'if decoded_path else'source-verification.json')).write_text(json.dumps({'ok':True,'source_sha256':source_sha,'original_source_sha256':a.SOURCE_SHA,'basis_topology_uv_bone_rest_sha256':original,'basis_topology_uv_bone_rest_unchanged':True,'runtime_binding_sha256':a.binding_hash(b,r),'maximum_influences':max(len(v.groups)for v in b.data.vertices),'maximum_weight_sum_error':max(abs(sum(g.weight for g in v.groups)-1)for v in b.data.vertices),'vertices':10582,'triangles':len(tri),'bones':51,'morphs':[],'actions':['Exercise_'+ID],'only_armature_enabled':True,'dual_quaternion':True},indent=2)+'\n')
print('NATIVE_GATES',json.dumps({'ok':not fail,'failures':fail[:20],'failure_count':len(fail),'minimum_area':minarea,'loop':loop,'maximum_finger_intrusion_count':maxhandinside}))
if '--game-qa'in sys.argv:
 sys.path.insert(0,str(Path.home()/'.codex/skills/blender-asset-qa/scripts'));import qa_check
 qa=[]
 for f in ([0,20,28,58]if ID=='4918'else[0,8,33]):
  s.frame_set(int(f)+1,subframe=f%1);bpy.context.view_layer.update();qa.append({'frame':f,'report':qa_check.run(objects=[b.name],profile='game')})
 q={'pass':all(x['report']['pass']for x in qa),'source_sha256':source_sha,'samples':qa};(P/'raw-asset-qa.json').write_text(json.dumps(q,indent=2)+'\n');assert q['pass']
if decoded_path:
 decoded_path.unlink();decoded_path.parent.rmdir();(P/'decoded-five-reference-verification.json.gz').unlink();(P/'decoded-normal-readback.json.gz').unlink();(P/'verification-exchange-path.txt').unlink()
assert not fail,fail[:20]
