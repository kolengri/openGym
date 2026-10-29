"""Immutable source, full241 native supports/skin/roll and five full references."""
from pathlib import Path
import sys
sys.dont_write_bytecode=True
import bpy,numpy as np,json,gzip,hashlib,math
from mathutils import Vector
P=Path(__file__).resolve().parent;out=P.parent/'assets/10058'
sys.path.insert(0,str(P));sys.path.insert(0,str(P.parents[1]/'batch-003'))
import authoring as a
from surface_checks_10058 import SurfaceChecks
a.initialize();OR=np.array([v.co[:]for v in a.body.data.vertices],np.float32);OU=[np.array([v.uv[:]for v in layer.data],np.float32)for layer in a.body.data.uv_layers];OT=[list(p.vertices)for p in a.body.data.polygons];OB={n:np.array(m,np.float32)for n,m in a.rest.items()};OW=[{a.body.vertex_groups[g.group].name:float(g.weight)for g in v.groups}for v in a.body.data.vertices]
bpy.ops.wm.open_mainfile(filepath=str(out/'source.blend'));body=bpy.data.objects['SK_BlenderStudioHuman'];rig=bpy.data.objects['RIG_BlenderStudioHuman'];scene=bpy.context.scene;rig.animation_data.action=bpy.data.actions['Exercise_10058'];R=np.array([v.co[:]for v in body.data.vertices],np.float32);source_sha=hashlib.sha256((out/'source.blend').read_bytes()).hexdigest()
assert np.array_equal(OR,R)and OT==[list(p.vertices)for p in body.data.polygons]
assert all(np.array_equal(old,np.array([v.uv[:]for v in layer.data],np.float32))for old,layer in zip(OU,body.data.uv_layers))
assert all(np.array_equal(OB[n],np.array(rig.data.bones[n].matrix_local,np.float32))for n in OB)
assert body.data.shape_keys is None and len(R)==10582 and len(rig.data.bones)==51
assert all(m.show_viewport==(m.type=='ARMATURE')and m.show_render==(m.type=='ARMATURE')for m in body.modifiers)
assert not next(m for m in body.modifiers if m.type=='ARMATURE').use_deform_preserve_volume
source_ids=np.empty(len(R),np.float32);body.data.attributes['_SOURCE_INDEX'].data.foreach_get('value',source_ids);assert np.array_equal(source_ids,np.arange(10582,dtype=np.float32))
W=np.zeros((len(R),len(body.vertex_groups)));names=[g.name for g in body.vertex_groups]
for v in body.data.vertices:
 for g in v.groups:W[v.index,g.group]=g.weight
assert (W>0).sum(1).max()<=4 and abs(W.sum(1)-1).max()<2e-6
changes=[]
for v in body.data.vertices:
 after={body.vertex_groups[g.group].name:float(g.weight)for g in v.groups}
 if after!=OW[v.index]:changes.append({'source_id':v.index,'before':OW[v.index],'after':after})
(out/'saved-binding-provenance.json').write_text(json.dumps({'source_sha256':source_sha,'original_source_sha256':a.SOURCE_SHA,'binding_sha256':a.binding_hash(body,rig),'maximum_influences':int((W>0).sum(1).max()),'normalization_max_error':float(abs(W.sum(1)-1).max()),'changes':changes},indent=2)+'\n')
checks=SurfaceChecks(body);states=json.loads((P/'kneel10-state.json').read_text());RN=np.array([v.normal[:]for v in body.data.vertices]);rest_inverse={n:rig.data.bones[n].matrix_local.inverted()for n in names};rows=[];references=[];surfaces=[];poses=[];qa=[];fail=[];previous=None;maxstep={'degrees':0};maxskin={'m':0};maxscale=0;maxlength=0;maxhinge=0;firststep=None
sys.path.insert(0,str(Path.home()/'.codex/skills/blender-asset-qa/scripts'));import qa_check
reference_frames=[0,22,49,169,240]
pose_frames=sorted(set(reference_frames+[1,2,21,23,42,57,70,99,108,120,121,142,151,188,219]))
for frame in range(241):
 scene.frame_set(frame+1);bpy.context.view_layer.update();ev=body.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=ev.to_mesh();X=np.array([v.co[:]for v in mesh.vertices]);ev.to_mesh_clear();D=np.array([np.array(rig.pose.bones[n].matrix@rest_inverse[n])for n in names]);A=np.einsum('vb,bij->vij',W,D[:,:3,:3]);N=np.einsum('vij,vj->vi',A,RN);N/=np.linalg.norm(N,axis=1)[:,None]
 row,issues=checks.measure(X,N,states[str(frame)]);rows.append(row);fail.extend({'frame':frame,'issue':issue}for issue in issues)
 if previous is None:first=X.copy()
 q={pb.name:pb.matrix.to_quaternion()for pb in rig.pose.bones}
 if previous:
  angles={n:math.degrees(2*math.acos(min(1,abs(q[n].dot(previous['q'][n])))))for n in q};bone=max(angles,key=angles.get)
  if angles[bone]>maxstep['degrees']:maxstep={'from':frame-1,'to':frame,'bone':bone,'degrees':angles[bone]}
  displacement=np.linalg.norm(X-previous['X'],axis=1);i=int(displacement.argmax())
  if displacement[i]>maxskin['m']:maxskin={'from':frame-1,'to':frame,'source_id':i,'m':float(displacement[i])}
  if frame==1:firststep={'maximum_joint_degrees':angles[bone],'maximum_skin_step_m':float(displacement.max()),'left_knee_step_m':float((rig.pose.bones['LeftLeg'].head-previous['knee']).length)}
 previous={'q':q,'X':X,'knee':rig.pose.bones['LeftLeg'].head.copy()}
 for pb in rig.pose.bones:
  maxscale=max(maxscale,max(abs(float(v)-1)for v in pb.scale));maxlength=max(maxlength,abs((pb.tail-pb.head).length-rig.data.bones[pb.name].length))
 for side in ['Left','Right']:
  sh=rig.data.bones[side+'UpLeg'].head_local;sk=rig.data.bones[side+'Leg'].head_local;sa=rig.data.bones[side+'Foot'].head_local;sn=(sk-sh).cross(sa-sk).normalized();h=rig.pose.bones[side+'UpLeg'].head;k=rig.pose.bones[side+'Leg'].head;an=rig.pose.bones[side+'Foot'].head;tn=(k-h).cross(an-k).normalized()
  for bone in [side+'UpLeg',side+'Leg']:
   actual=(rig.pose.bones[bone].matrix@rig.data.bones[bone].matrix_local.inverted()).to_quaternion()@sn;maxhinge=max(maxhinge,float(actual.angle(tn)))
 if frame in reference_frames:
  references.append({'id':'10058','frame':frame,'vertices':X.tolist(),'shader_normals':N.tolist()});surfaces.append({'id':'10058','frame':frame,'global_floor_z':row['minimum_body_z'],'floor_plane_z':0,'patches':{name:{'indices':patch['indices'],'positions':X[patch['indices']].tolist(),'min_z':float(X[patch['indices'],2].min()),'max_z':float(X[patch['indices'],2].max())}for name,patch in checks.patches.items()}})
 if frame in pose_frames:poses.append({'id':'10058','frame':frame,'joints':{pb.name:list(pb.head)for pb in rig.pose.bones}})
 if frame in [0,22,49,151,169]:
  result=qa_check.run(objects=[body.name],profile='game');qa.append({'frame':frame,'qa':result})
  if not result['pass']:fail.append({'frame':frame,'issue':'mandatory_game_QA'})
loop=float(np.linalg.norm(X-first,axis=1).max())
if loop>1e-6:fail.append({'issue':'loop','m':loop})
if maxscale>2e-5 or maxlength>3e-6:fail.append({'issue':'bone_scale_or_length'})
report={'ok':not fail,'source_sha256':source_sha,'sampling':{'frames':241,'fps':30,'duration_seconds':8,'native_frame_origin':1},'invariants':{'basis':True,'rest':True,'uv':True,'topology':True,'source_ids':10582,'bones':51,'maximum_influences':4,'morphs':0,'skinning':'linear'},'loop_vertex_error_m':loop,'maximum_joint_step':maxstep,'maximum_skin_step':maxskin,'neutral_to_first_frame':firststep,'maximum_scale_error':maxscale,'maximum_bone_length_error_m':maxlength,'maximum_hinge_plane_error_radians':maxhinge,'self_fold_policy':'Root accepted the natural creased hip stills. Exact localized nonadjacent crossings remain diagnostic and are not a globally collision-free claim.','failures':fail,'samples':rows}
(out/'surface-contact-report.json').write_text(json.dumps(report,indent=2)+'\n');(out/'asset-qa.json').write_text(json.dumps({'source_sha256':source_sha,'profile':'game','samples':qa},indent=2)+'\n');(out/'pose-samples.json').write_text(json.dumps(poses,indent=2)+'\n');(out/'runtime-surface-reference.json').write_text(json.dumps({'source_sha256':source_sha,'reference_kind':'native-linear','source_vertices':10582,'coordinate_system':'BlenderZup','samples':surfaces},indent=2)+'\n');(out/'landmarks.json').write_text(json.dumps({'source_sha256':source_sha,'source_vertices':10582,'patches':checks.patches,'floor_plane_z':0},indent=2)+'\n')
with gzip.open(out/'linear-vertex-reference.json.gz','wt',encoding='utf8')as f:json.dump(references,f,separators=(',',':'))
with gzip.open(out/'topology-reference.json.gz','wt',encoding='utf8')as f:json.dump({'source_sha256':source_sha,'triangles':checks.T.tolist()},f,separators=(',',':'))
print('NATIVE10058',json.dumps({k:v for k,v in report.items()if k!='samples'}));assert report['ok'],fail
