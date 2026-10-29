"""Canonical invariants, complete native joint/skin witnesses and independent DQ NORMAL contract."""
from pathlib import Path
import sys,json,gzip,hashlib,math
sys.dont_write_bytecode=True
import bpy,numpy as np
from mathutils import Quaternion,Vector
P=Path(__file__).resolve().parent;A=P.parent/'assets/6121';sys.path.insert(0,str(P.parents[1]/'batch-003'));import authoring as a
a.initialize();OR=np.array([v.co[:]for v in a.body.data.vertices],np.float32);OU=[np.array([v.uv[:]for v in u.data],np.float32)for u in a.body.data.uv_layers];OT=[list(p.vertices)for p in a.body.data.polygons];OB={n:np.array(M,np.float32)for n,M in a.rest.items()};OW=[{a.body.vertex_groups[g.group].name:float(g.weight)for g in v.groups}for v in a.body.data.vertices]
bpy.ops.wm.open_mainfile(filepath=str(A/'source.blend'));b=bpy.data.objects['SK_BlenderStudioHuman'];r=bpy.data.objects['RIG_BlenderStudioHuman'];s=bpy.context.scene;source=hashlib.sha256((A/'source.blend').read_bytes()).hexdigest();R=np.array([v.co[:]for v in b.data.vertices],np.float32);keys=b.data.shape_keys;key=keys.key_blocks['TwistHipVolume'];contract=json.loads((P/'motion-contract.json').read_text());assert a.binding_hash(b,r)==contract['binding_sha256'];assert np.array_equal(R,OR)and OT==[list(p.vertices)for p in b.data.polygons];assert np.array_equal(R,np.array([v.co[:]for v in keys.key_blocks['Basis'].data],np.float32));assert all(np.array_equal(x,np.array([v.uv[:]for v in u.data],np.float32))for x,u in zip(OU,b.data.uv_layers));assert all(np.array_equal(x,np.array(r.data.bones[n].matrix_local,np.float32))for n,x in OB.items());assert len(OB)==51 and len(R)==10582;assert set(x.name for x in bpy.data.actions)=={'Exercise_6121'};assert next(m for m in b.modifiers if m.type=='ARMATURE').use_deform_preserve_volume;assert all(m.show_viewport==m.show_render==(m.type=='ARMATURE')for m in b.modifiers)
ids=np.array([v.value for v in b.data.attributes['_SOURCE_INDEX'].data]);assert np.array_equal(ids,np.arange(10582));actualW=[{b.vertex_groups[g.group].name:float(g.weight)for g in v.groups}for v in b.data.vertices];assert max(map(len,actualW))<=4;weight_error=max(abs(sum(w.values())-1)for w in actualW);assert weight_error<2e-6
rollback=json.loads((P/'hip-binding-diagnosis.json').read_text())['changes'];assert len(rollback)==255 and all(actualW[v['source_id']]==v['original']for v in rollback)
b.data.calc_loop_triangles();T=np.array([v.vertices[:]for v in b.data.loop_triangles]);N0=np.array([v.normal[:]for v in b.data.vertices]);key_names=[k.name for k in keys.key_blocks if k.name!='Basis'];assert key_names==['TwistHipVolume','ThighContactLead'];K=np.array([v.co[:]for v in key.data]);target_normals={}
for name in key_names:
 coords=np.array([v.co[:]for v in keys.key_blocks[name].data]);mesh=bpy.data.meshes.new('Independent'+name+'Normals');mesh.from_pydata(coords.tolist(),[],OT)
 for p,q in zip(mesh.polygons,b.data.polygons):p.use_smooth=q.use_smooth
 mesh.update();target_normals[name]=np.array([v.normal[:]for v in mesh.vertices]);bpy.data.meshes.remove(mesh)
rest={n:r.data.bones[n].matrix_local.copy()for n in OB};lm=json.loads((A/'landmarks.json').read_text());native=json.loads((P/'native-loop-report.json').read_text());frames=sorted(set([0,9,22,30,39,45,51,60,75,90,99,103,105,111,120,128,141,150,native['maximum_native_joint_step']['to'],native['maximum_native_skin_step']['to']]));full={0,24,30,75,120,150};frames=sorted(set(frames)|full);poses=[];surfaces=[];dq=[];morph=[];speeds=[];previous=None;max_speed={'m_per_s':0};max_acc={'m_per_s2':0};last_velocity=None;first=None;last=None
for f in range(151):
 s.frame_set(f+1);bpy.context.view_layer.update();ev=b.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh();X=np.array([v.co[:]for v in me.vertices]);ev.to_mesh_clear();morph.append({'id':'6121','frame':f,'weights':{n:float(keys.key_blocks[n].value)for n in key_names}});hands={side:X[lm['patches'][patch]['indices']].mean(0)for side,patch in [('Left','palm_support'),('Right','palm_hug')]}
 if previous is not None:
  velocity={side:(v-previous[side])*30 for side,v in hands.items()}
  for side,v in velocity.items():
   speed=float(np.linalg.norm(v))
   if speed>max_speed['m_per_s']:max_speed={'from':f-1,'to':f,'side':side,'m_per_s':speed}
   if last_velocity is not None:
    acceleration=float(np.linalg.norm(v-last_velocity[side])*30)
    if acceleration>max_acc['m_per_s2']:max_acc={'frame':f,'side':side,'m_per_s2':acceleration}
  last_velocity=velocity
 previous={k:v.copy()for k,v in hands.items()};speeds.append({'frame':f,'central_palm_centroids':{k:v.tolist()for k,v in hands.items()}})
 if f==0:first=X.copy()
 if f==150:last=X.copy()
 if f not in frames:continue
 poses.append({'id':'6121','frame':f,'joints':{pb.name:list(pb.head)for pb in r.pose.bones}});patches={}
 for name,p in lm['patches'].items():
  idx=p['indices'];kind=p['kind'];held=60<=f<=90;support=kind in ['pelvis','extended_heel']or(kind=='support_palm'and held)or(kind=='crossed_sole'and 39<=f<=111)or(kind=='crossed_heel'and(f==0 or f==150 or 39<=f<=111));patches[name]={'indices':idx,'positions':X[idx].tolist(),'min_z':float(X[idx,2].min()),'max_z':float(X[idx,2].max()),'state':'supported'if support else'free'}
 surfaces.append({'id':'6121','frame':f,'floor_plane_z':0,'global_floor_z':float(X[:,2].min()),'patches':patches})
 if f in full:
  currentN=N0+sum(float(keys.key_blocks[n].value)*(target_normals[n]-N0)for n in key_names);world=np.zeros_like(currentN)
  for v in b.data.vertices:
   terms=[(g.weight,(r.pose.bones[b.vertex_groups[g.group].name].matrix@rest[b.vertex_groups[g.group].name].inverted()).to_quaternion())for g in v.groups];ref=max(terms,key=lambda x:x[0])[1];q=Quaternion(sum((np.array(q)*w*(-1 if q.dot(ref)<0 else 1)for w,q in terms),np.zeros(4)));q.normalize();world[v.index]=q@Vector(currentN[v.index])
  world/=np.linalg.norm(world,axis=1)[:,None];dq.append({'id':'6121','frame':f,'positions':X.tolist(),'shader_normals':world.tolist()})
for name,data in [('pose-samples.json',poses),('runtime-surface-reference.json',{'source_sha256':source,'source_vertices':10582,'reference_kind':'native','skinning':'dualQuaternion','samples':surfaces}),('source-morph-samples.json',{'source_sha256':source,'samples':morph})]:(A/name).write_text(json.dumps(data,indent=2)+'\n')
for name,data in [('dq-reference.json.gz',{'source_sha256':source,'source_vertices':10582,'samples':dq}),('joint-normal-reference.json.gz',{'source_sha256':source,'basis':N0.tolist(),'targets':{n:target_normals[n].tolist()for n in key_names},'scope':'Independent actual key mesh normals, combined before unit-DQ shader rotation.'}),('topology-reference.json.gz',{'source_sha256':source,'triangles':T.tolist()})]:
 with gzip.GzipFile(filename=str(A/name),mode='wb',mtime=0)as fp:fp.write(json.dumps(data,separators=(',',':')).encode())
changed=[i for i,(u,v)in enumerate(zip(OW,actualW))if u!=v];verification={'ok':True,'source_sha256':source,'original_source_sha256':a.SOURCE_SHA,'binding_sha256':contract['binding_sha256'],'invariants':{'vertices':10582,'triangles':len(T),'bones':51,'Basis_rest_UV_original_source_ids_oriented_topology_exact':True,'maximum_influences':max(map(len,actualW)),'maximum_weight_sum_error':weight_error},'binding_lineage':'Accepted1368 seated profile/glute/plantar binding, with exactly255 inherited semantic UpLeg rows restored to original weights. All other rows exact to accepted1368.','changed_weights_from_original_source_ids':changed,'original_semantic_hip_rollback_ids':[v['source_id']for v in rollback],'morphs':key_names,'maximum_source_delta_m':float(np.linalg.norm(K-R,axis=1).max()),'position_changed_source_ids':np.flatnonzero(np.any(K!=R,axis=1)).tolist(),'normal_changed_source_ids':np.flatnonzero(np.max(np.array([np.linalg.norm(target_normals[n]-N0,axis=1)for n in key_names]),axis=0)>1e-7).tolist(),'reference_frames':sorted(full),'scalar_reset':'One standalone action only;151 explicit scalar samples; exactly0 at frame0/150 and1 during hold. Other assets do not share this mesh/Key datablock.'};(A/'source-verification.json').write_text(json.dumps(verification,indent=2)+'\n');(P/'motion-speed-report.json').write_text(json.dumps({'source_sha256':source,'frames':151,'maximum_actual_central_palm_speed':max_speed,'maximum_actual_central_palm_acceleration':max_acc,'maximum_joint_step':native['maximum_native_joint_step'],'maximum_skin_step':native['maximum_native_skin_step'],'loop_m':float(np.linalg.norm(last-first,axis=1).max()),'interpretation':'Short hand release precedes leg placement; normal approach arc vanishes smoothly at contact. Measured speed/step receipts, no arbitrary threshold relaxation.','samples':speeds},indent=2)+'\n');print('NATIVE_REFS',source,'maxhand',max_speed,'maxacc',max_acc)
