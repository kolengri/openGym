"""Actual native or decoded skin checks, scoped to1843's supported seated motion."""
from pathlib import Path
import bpy,sys,json,gzip,hashlib,math,numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.dont_write_bytecode=True
F=Path(__file__).resolve().parent;B=F.parent;W=F.parents[3];P=B/'assets/1843'
sys.path[:0]=[str(B.parent/'batch-003'),str(B.parent/'batch-007/upright-family')]
import authoring as a
from triangle_intersection import intersect
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
OLD=B.parent/'batch-007/assets/1368/source.blend'
bpy.ops.wm.open_mainfile(filepath=str(OLD));old=bpy.data.objects['SK_BlenderStudioHuman'];oldrig=bpy.data.objects['RIG_BlenderStudioHuman'];oldrig.animation_data.action=bpy.data.actions['Exercise_1368'];bpy.context.scene.frame_set(1);bpy.context.view_layer.update();oldbinding=a.binding_hash(old,oldrig);oldcoords=np.array([v.co[:]for v in old.data.vertices]);oldrest=np.array([bone.matrix_local for bone in oldrig.data.bones]);lowernames=['Hips']+[side+n for side in ['Left','Right']for n in['UpLeg','Leg','Foot','ToeBase']];oldlower={n:np.array(oldrig.pose.bones[n].matrix)for n in lowernames};oldshape=[(k.name,np.array([v.co[:]for v in k.data]))for k in old.data.shape_keys.key_blocks];oldpolys=[list(p.vertices)for p in old.data.polygons];olduv=[(u.name,np.array([v.uv[:]for v in u.data]))for u in old.data.uv_layers]
bpy.ops.wm.open_mainfile(filepath=str(P/'source.blend'));b=bpy.data.objects['SK_BlenderStudioHuman'];r=bpy.data.objects['RIG_BlenderStudioHuman'];s=bpy.context.scene;source_sha=sha(P/'source.blend');assert a.binding_hash(b,r)==oldbinding;assert len(b.data.vertices)==10582 and len(r.data.bones)==51;assert len(b.data.shape_keys.key_blocks)==1;assert np.array_equal(oldcoords,np.array([v.co[:]for v in b.data.vertices]));assert oldpolys==[list(p.vertices)for p in b.data.polygons];assert np.array_equal(oldrest,np.array([bone.matrix_local for bone in r.data.bones]));assert all(name==u.name and np.array_equal(arr,np.array([v.uv[:]for v in u.data]))for(name,arr),u in zip(olduv,b.data.uv_layers));assert np.array_equal(oldshape[0][1],np.array([v.co[:]for v in b.data.shape_keys.key_blocks['Basis'].data]));assert sorted(x.name for x in bpy.data.actions)==['Exercise_1843'];assert [round(v.value)for v in b.data.attributes['_SOURCE_INDEX'].data]==list(range(10582));assert all(m.show_viewport==(m.type=='ARMATURE')and m.show_render==(m.type=='ARMATURE')for m in b.modifiers);assert next(m for m in b.modifiers if m.type=='ARMATURE').use_deform_preserve_volume
r.animation_data.action=bpy.data.actions['Exercise_1843'];r.animation_data.action_slot=r.animation_data.action.slots[0]
R=np.array([v.co[:]for v in b.data.vertices]);N=np.array(b.data.shape_keys.key_blocks['Basis'].normals_vertex_get()).reshape(-1,3);b.data.calc_loop_triangles();tri=np.array([t.vertices[:]for t in b.data.loop_triangles],int);gn={g.index:g.name for g in b.vertex_groups};weight=[{gn[g.group]:g.weight for g in v.groups}for v in b.data.vertices]
def ids(prefix,threshold=.65):return np.array([i for i,row in enumerate(weight)if sum(w for n,w in row.items()if n.startswith(tuple(prefix)))>threshold],int)
parts={'head':np.flatnonzero((R[:,2]>1.545)&(abs(R[:,0])<.15)),'torso':ids(['Hips','Spine'],.8),'neck':np.flatnonzero((R[:,2]>1.42)&(R[:,2]<1.60)&(abs(R[:,0])<.14))}
for side,sign in [('Left',1),('Right',-1)]:
 for key,prefix,thresh in [('arm',['Arm','ForeArm','Hand','Thumb','Index','Middle','Ring','Little'],.65),('forearm',['ForeArm'],.8),('hand',['Hand','Thumb','Index','Middle','Ring','Little'],.7),('digits',['Thumb','Index','Middle','Ring','Little'],.7),('leg',['UpLeg','Leg','Foot','ToeBase'],.6)]:parts[side+'_'+key]=ids([side+n for n in prefix],thresh)
 parts[side+'_palm']=np.array([i for i in ids([side+'Hand'],.8)if .88<R[i,2]<.94 and -sign*N[i,0]>.4],int)
faces={n:tri[np.all(np.isin(tri,idx),axis=1)].tolist()for n,idx in parts.items()};C=json.loads((B.parent/'batch-007/ankle-family/pose-contract.json').read_text());patches={'pelvis':{'indices':C['pelvic_original_ids'],'state':'supported'}}
for side in ['Left','Right']:
 for part,key in [('heel','heel_skin_original_ids'),('calf','calf_original_ids')]:patches[side+'_'+part]={'indices':C[key][side],'state':'supported'if part=='heel'else'free'}
 patches[side+'_palm']={'indices':parts[side+'_palm'].tolist(),'state':'free_or_light_contact'}
decoded_path=Path(sys.argv[sys.argv.index('--decoded')+1])if'--decoded'in sys.argv else None;decoded=np.fromfile(decoded_path,dtype=np.float32).reshape(151,10582,3)if decoded_path else None
quick='--quick'in sys.argv;frames=[0,15,25,35,45,55,60,75,90,105,120,135,150]if quick else range(151);rows=[];fails=[];refs=[];poses=[];dq=[];normals=[];maxlower=0.;maxparity=0.;previous={};maxstep={};first=None;last=None
pairs=[('Left_arm','head'),('Right_arm','head'),('Left_arm','neck'),('Right_arm','neck'),('Left_arm','torso'),('Right_arm','torso'),('Left_arm','Left_leg'),('Left_arm','Right_leg'),('Right_arm','Left_leg'),('Right_arm','Right_leg'),('Left_leg','Right_leg'),('Left_hand','Right_arm'),('Right_hand','Left_arm')]
for f in frames:
 s.frame_set(f+1);bpy.context.view_layer.update();e=b.evaluated_get(bpy.context.evaluated_depsgraph_get());me=e.to_mesh();native=np.array([v.co[:]for v in me.vertices]);nn=np.array([v.normal[:]for v in me.vertices]);e.to_mesh_clear();p=native if decoded is None else decoded[f].astype(float);maxparity=max(maxparity,float(np.linalg.norm(p-native,axis=1).max()));vec=[Vector(q)for q in p];trees={n:BVHTree.FromPolygons(vec,fs)for n,fs in faces.items()if fs};cross={};contact={}
 for A,T in pairs:
  count=0
  for ai,bi in trees[A].overlap(trees[T]):
   aa,bb=faces[A][ai],faces[T][bi]
   if set(aa)&set(bb):continue
   if intersect([vec[i]for i in aa],[vec[i]for i in bb]):count+=1
  cross[A+'_vs_'+T]=count
  if count:fails.append(f'{f}:{A}/{T} crossings={count}')
 for side in ['Left','Right']:
  for region in ['hand','palm','forearm','digits']:
   distances=[];signed=[];inside=[]
   for i in parts[side+'_'+region]:
    co,no,fi,dist=trees['head'].find_nearest(vec[int(i)]);sgn=(vec[int(i)]-co).dot(no);distances.append(dist);signed.append(sgn)
    if dist<.04 and sgn<-.004:inside.append(int(i))
   contact[side+'_'+region]={'minimum_distance_m':min(distances),'median_distance_m':float(np.median(distances)),'minimum_signed_normal_distance_m':min(signed),'inside_more4mm_ids':inside,'within12mm_count':sum(x<.012 for x in distances)}
   if inside:fails.append(f'{f}:{side}_{region}/head inside>4mm={len(inside)}')
 if 60<=f<=90:
  for side in ['Left','Right']:
   if contact[side+'_palm']['minimum_distance_m']>.004:fails.append(f'{f}:{side} palm gap')
 floor=float(p[:,2].min());area=float((np.linalg.norm(np.cross(p[tri[:,1]]-p[tri[:,0]],p[tri[:,2]]-p[tri[:,0]]),axis=1)*.5).min());support={n:float(p[patch['indices'],2].min())for n,patch in patches.items()if patch['state']=='supported'}
 if floor<-.00035:fails.append(f'{f}:floor={floor}')
 if area<=1e-12:fails.append(f'{f}:area={area}')
 for name,z in support.items():
  if not -.00035<=z<=.002:fails.append(f'{f}:{name} support={z}')
 for n in lowernames:maxlower=max(maxlower,float(np.max(abs(np.array(r.pose.bones[n].matrix)-oldlower[n]))))
 for pb in r.pose.bones:
  q=pb.matrix.to_quaternion()
  if pb.name in previous:
   deg=math.degrees(previous[pb.name].rotation_difference(q).angle);maxstep[pb.name]=max(maxstep.get(pb.name,0),min(deg,360-deg))
  previous[pb.name]=q.copy()
 row={'frame':f,'floor_min_z_m':floor,'support_min_z_m':support,'minimum_triangle_area_m2':area,'triangle_crossings':cross,'head_contact':contact};rows.append(row)
 if f in [0,15,30,45,60,75,90,105,120,135,150]:
  poses.append({'id':'1843','frame':f,'joints':{pb.name:list(r.matrix_world@pb.head)for pb in r.pose.bones}});refs.append({'id':'1843','frame':f,'global_floor_z':floor,'floor_plane_z':0,'patches':{n:{'indices':patch['indices'],'positions':p[patch['indices']].tolist(),'min_z':float(p[patch['indices'],2].min()),'max_z':float(p[patch['indices'],2].max()),'state':'contact'if 'palm'in n and 60<=f<=90 else patch['state']}for n,patch in patches.items()}})
 if f in [0,30,75,120,150]:
  from mathutils import Quaternion
  qmap={pb.name:(pb.matrix@pb.bone.matrix_local.inverted()).to_quaternion()for pb in r.pose.bones};dqnormals=[]
  for i,row in enumerate(weight):
   reference=qmap[next(iter(row))];q=np.zeros(4)
   for name,w in row.items():
    quat=qmap[name];q+=np.array(quat)*(w if reference.dot(quat)>=0 else-w)
   rot=Quaternion(q);rot.normalize();dqnormals.append(list(rot@Vector(N[i])))
  dq.append({'id':'1843','frame':f,'positions':p.tolist(),'normals':dqnormals});normals.append({'id':'1843','frame':f,'normals':nn.tolist()})
 if f==0:first=p.copy()
 if f==150:last=p.copy()
loop=float(np.linalg.norm(first-last,axis=1).max());assert maxlower<2e-6,maxlower
if loop>1e-5:fails.append('loop mismatch')
if decoded is not None and maxparity>.0001:fails.append('native decoded parity')
report={'ok':not fails,'source_sha256':source_sha,'frames':len(rows),'native_frame_origin':1,'source_vertices':10582,'triangles':len(tri),'bones':51,'source_and_binding_exact_to_accepted1368':True,'maximum_lower_body_matrix_delta':maxlower,'maximum_native_decoded_skin_error_m':maxparity if decoded is not None else None,'loop_error_m':loop,'maximum_bone_step_degrees':maxstep,'minimum_triangle_area_m2':min(x['minimum_triangle_area_m2']for x in rows),'failures':fails,'samples':rows,'limitations':'Discrete triangle crossing and local signed-nearest diagnostics, not a global enclosed-volume/continuous collision certificate. Contact proximity alone does not establish visual believability.'}
(P/('early-contact-report.json'if quick else'decoded-physical-report.json'if decoded_path else'surface-contact-report.json')).write_text(json.dumps(report,indent=2)+'\n')
if not quick and decoded is None:
 for name,data in [('pose-samples.json',poses),('runtime-surface-reference.json',{'source_sha256':source_sha,'source_vertices':10582,'reference_kind':'native_armature_only_DQ','samples':refs}),('surface-landmarks.json',{'source_sha256':source_sha,'parts':{n:i.tolist()for n,i in parts.items()},'patches':patches,'triangles':tri.tolist()})]:(P/name).write_text(json.dumps(data,separators=(',',':'))+'\n')
 for name,data in [('dq-reference.json.gz',{'source_sha256':source_sha,'source_vertices':10582,'samples':dq}),('normal-reference.json.gz',{'source_sha256':source_sha,'source_vertices':10582,'basis':N.tolist(),'posed_normals_kind':'Native geometric normals; rotated source normal shader parity is evaluated separately.','samples':normals})]:
  with gzip.open(P/name,'wt')as out:json.dump(data,out,separators=(',',':'))
 (P/'source-verification.json').write_text(json.dumps({'ok':True,'source_sha256':source_sha,'accepted_seated_source_sha256':sha(OLD),'canonical_original_source_sha256':a.SOURCE_SHA,'basis_rest_uv_topology_source_ids_unchanged':True,'binding_exact_to_accepted1368':True,'runtime_binding_sha256':oldbinding,'maximum_influences':max(map(len,weight)),'maximum_weight_sum_error':max(abs(sum(row.values())-1)for row in weight),'morph_targets':[],'explicit_morph_reset':'No morph targets exist; no corrective reset is needed.','lower_body_exact':maxlower<2e-6},indent=2)+'\n')
if '--game-qa'in sys.argv:
 sys.path.insert(0,str(Path.home()/'.codex/skills/blender-asset-qa/scripts'));import qa_check;qa=[]
 for f in [0,30,75,120]:
  s.frame_set(f+1);bpy.context.view_layer.update();qa.append({'frame':f,'report':qa_check.run(objects=[b.name],profile='game')})
 (P/'asset-qa.json').write_text(json.dumps({'pass':all(x['report']['pass']for x in qa),'source_sha256':source_sha,'samples':qa},indent=2)+'\n')
print(json.dumps({'ok':not fails,'samples':len(rows),'failures':fails[:35],'failure_count':len(fails),'maxlower':maxlower,'loop':loop}))
if decoded_path:decoded_path.unlink();decoded_path.parent.rmdir();(P/'verification-exchange-path.txt').unlink()
assert not fails,fails[:30]
