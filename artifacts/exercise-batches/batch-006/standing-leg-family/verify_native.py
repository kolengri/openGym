"""Frozen source invariants, all151 native surfaces, five full references and game QA."""
from pathlib import Path
import bpy,sys,json,gzip,hashlib,math
import numpy as np
P=Path(__file__).resolve().parent;sys.path.insert(0,str(P));sys.path.insert(0,str(P.parents[1]/'batch-003'));import authoring as a;from geometry_checks import SurfaceChecks
a.initialize();O=np.array([v.co[:] for v in a.body.data.vertices],np.float32);OU=[np.array([v.uv[:] for v in u.data],np.float32) for u in a.body.data.uv_layers];OT=[list(p.vertices) for p in a.body.data.polygons];OR={b.name:np.array(b.matrix_local,np.float32) for b in a.rig.data.bones};OW=[{a.body.vertex_groups[g.group].name:float(g.weight) for g in v.groups} for v in a.body.data.vertices]
bpy.ops.wm.open_mainfile(filepath=str(P.parent/'assets/3479/source.blend'));body=bpy.data.objects['SK_BlenderStudioHuman'];rig=bpy.data.objects['RIG_BlenderStudioHuman'];s=bpy.context.scene;R=np.array([v.co[:] for v in body.data.vertices],np.float32);keys=body.data.shape_keys;source_sha=hashlib.sha256((P.parent/'assets/3479/source.blend').read_bytes()).hexdigest();targets=json.loads((P/'joint-target-report.json').read_text());contacts=json.loads((P/'contact-landmarks.json').read_text());states=json.loads((P/'kinematic-state.json').read_text());binding=json.loads((P/'binding-report.json').read_text())
assert np.array_equal(O,R) and OT==[list(p.vertices) for p in body.data.polygons];assert all(np.array_equal(old,np.array([v.uv[:] for v in u.data],np.float32)) for old,u in zip(OU,body.data.uv_layers));assert all(np.array_equal(OR[b.name],np.array(b.matrix_local,np.float32)) for b in rig.data.bones);assert len(rig.data.bones)==51 and len(R)==10582
assert np.array_equal(np.array([v.co[:] for v in keys.key_blocks['Basis'].data],np.float32),R);assert max(len(v.groups) for v in body.data.vertices)<=4;assert max(abs(sum(g.weight for g in v.groups)-1) for v in body.data.vertices)<2e-6;assert a.binding_hash(body,rig)==binding['binding_hash'];assert all(m.show_viewport==(m.type=='ARMATURE') and m.show_render==(m.type=='ARMATURE') for m in body.modifiers);assert not next(m for m in body.modifiers if m.type=='ARMATURE').use_deform_preserve_volume
source_indices=np.empty(len(R),np.float32);body.data.attributes['_SOURCE_INDEX'].data.foreach_get('value',source_indices);assert np.array_equal(source_indices,np.arange(10582,dtype=np.float32))
declared=set(binding['base_report']['affected_source_indices'])|{row['source_id'] for row in binding['toe_preserving_plantar_overlay']}
for v in body.data.vertices:
 if v.index not in declared:assert OW[v.index]=={body.vertex_groups[g.group].name:float(g.weight) for g in v.groups}
checks=SurfaceChecks(body,contacts,targets);T=checks.T;keynormals={}
for key in keys.key_blocks:
 xyz=np.array([v.co[:] for v in key.data]);assert np.linalg.norm(xyz-R,axis=1).max()<=.025001
 mesh=bpy.data.meshes.new('IndependentMorphNormal');mesh.from_pydata(xyz.tolist(),[],[list(p.vertices) for p in body.data.polygons]);
 for p,original in zip(mesh.polygons,body.data.polygons):p.use_smooth=original.use_smooth
 mesh.update();keynormals[key.name]=np.array([v.normal[:] for v in mesh.vertices]);bpy.data.meshes.remove(mesh)
rn=keynormals['Basis'];changed=[]
for v in body.data.vertices:
 row={body.vertex_groups[g.group].name:float(g.weight) for g in v.groups}
 if row!=OW[v.index]:changed.append({'source_id':v.index,'before':OW[v.index],'after':row})
(P/'saved-binding-provenance.json').write_text(json.dumps({'source_sha256':source_sha,'binding_sha256':binding['binding_hash'],'actual_saved_max_influences':max(len(v.groups) for v in body.data.vertices),'actual_changed_vertex_count':len(changed),'changes':changed},indent=2)+'\n')
sys.path.insert(0,str(Path.home()/'.codex/skills/blender-asset-qa/scripts'));import qa_check
for id in (['3479'] if '--only-3479' in sys.argv else ['3479','3480']):
 out=P.parent/'assets'/id;act=bpy.data.actions['Exercise_'+id];rig.animation_data.action=act;keys.animation_data.action=act;keys.animation_data.action_slot=next(x for x in act.slots if x.target_id_type=='KEY');checks.previous={};checks.witnesses={};checks.witnesslookup={};rows=[];refs=[];surfaces=[];samples=[];fail=[];first=None;prev=None;maxstep=0;maxstepframe=None;qa=[]
 last=round(json.loads((out/'clip.json').read_text())['duration_seconds']*30)
 reference_frames=[0,27,80,200,240] if id=='3479' and last==240 else ([0,18,40,115,150] if id=='3479' else [0,15,37,112,150]);qa_frames=[0,27,59,71,80,111,200] if id=='3479' and last==240 else ([0,18,31,40,115] if id=='3479' else [0,37,112])
 for f in range(last+1):
  s.frame_set(f+1);bpy.context.view_layer.update();ev=body.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh();X=np.array([ev.matrix_world@v.co for v in me.vertices]);ev.to_mesh_clear();matrices=np.array([np.array(rig.pose.bones[g.name].matrix@rig.data.bones[g.name].matrix_local.inverted())[:3,:3] for g in body.vertex_groups]);inputN=rn.copy()
  for key in keys.key_blocks:
   if key.name!='Basis':inputN+=key.value*(keynormals[key.name]-rn)
  N=np.zeros_like(rn)
  for v in body.data.vertices:
   for g in v.groups:N[v.index]+=g.weight*(matrices[g.group]@inputN[v.index])
  N/=np.linalg.norm(N,axis=1)[:,None];row,issues=checks.measure(X,N,states[id][str(f)]);row['key_values']={k.name:k.value for k in keys.key_blocks if k.name!='Basis'};rows.append(row);fail.extend({'frame':f,'issue':issue} for issue in issues)
  if first is None:first=X.copy()
  q={pb.name:pb.matrix.to_quaternion() for pb in rig.pose.bones}
  if prev:
   step=max(2*math.acos(min(1,abs(prev[n].dot(v)))) for n,v in q.items())
   if step>maxstep:maxstep,maxstepframe=step,f
  prev=q
  if f in reference_frames:
   refs.append({'id':id,'frame':f,'vertices':X.tolist(),'shader_normals':N.tolist()});surfaces.append({'id':id,'frame':f,'global_floor_z':row['minimum_body_z'],'floor_plane_z':0,'patches':{side+'_'+name:{'indices':ids.tolist(),'min_z':float(X[ids,2].min()),'max_z':float(X[ids,2].max())} for side,patches in checks.soles.items() for name,ids in patches.items()}})
  if f in ([0,14,27,39,51,58,59,71,80,105,111,116,120,147,171,178,179,191,200,231,240] if last==240 else [0,15,18,30,31,37,40,60,75,90,105,112,115,135,145,150]):samples.append({'id':id,'frame':f,'joints':{pb.name:list(rig.matrix_world@pb.head) for pb in rig.pose.bones}})
  if f in qa_frames:
   result=qa_check.run(objects=[body.name],profile='game');qa.append({'frame':f,'qa':result})
   if not result['pass']:fail.append({'frame':f,'issue':'mandatory_game_QA'})
 loop=float(np.linalg.norm(X-first,axis=1).max())
 if loop>1e-6:fail.append({'issue':'loop_closure'})
 report={'ok':not fail,'source_sha256':source_sha,'sampling':{'frames':last+1,'fps':30,'duration_seconds':last/30,'native_frame_origin':1},'invariants':{'original_source_sha256':a.SOURCE_SHA,'basis':True,'rest':True,'uv':True,'topology':True,'source_ids':10582,'bones':51,'maximum_weights':4,'targets':4,'maximum_source_delta_m':.025,'runtime':'standard linear; only Armature enabled'},'loop_vertex_error_m':loop,'maximum_joint_step_radians':maxstep,'maximum_joint_step_frame':maxstepframe,'self_fold_policy':'Exact nonadjacent local self-folds and opposed shader normals are localized diagnostics, not a global zero-self-collision claim. Root accepted the bounded visible joint8 candidate with residual joint crease detail.','failures':fail,'samples':rows,'crossing_witnesses':checks.witnesses}
 (out/'surface-contact-report.json').write_text(json.dumps(report,indent=2)+'\n');(out/'asset-qa.json').write_text(json.dumps({'source_sha256':source_sha,'pass':all(q['qa']['pass'] for q in qa),'checks':qa},indent=2)+'\n');(out/'pose-samples.json').write_text(json.dumps(samples,indent=2)+'\n');(out/'runtime-surface-reference.json').write_text(json.dumps({'reference_kind':'native-armature-only-standard-linear-with-four-bounded-morphs','source_sha256':source_sha,'source_vertices':10582,'coordinate_frame':'Blender Zup metres, original source IDs','floor_plane_z':0,'samples':surfaces},separators=(',',':'))+'\n')
 with gzip.open(out/'linear-vertex-reference.json.gz','wt') as stream:json.dump(refs,stream,separators=(',',':'))
 with gzip.open(out/'topology-reference.json.gz','wt') as stream:json.dump({'source_sha256':source_sha,'source_vertices':10582,'triangles':T.tolist()},stream,separators=(',',':'))
 (out/'landmarks.json').write_text(json.dumps({'source_sha256':source_sha,'source_vertices':10582,'patches':{**{side+'_'+name:ids.tolist() for side,patches in checks.soles.items() for name,ids in patches.items()},'both_arms_hands':np.flatnonzero(checks.armmask).tolist(),'both_legs':np.flatnonzero(checks.legmask).tolist()},'heel_touch_contact':contacts,'definition':'Fixed original Basis-coordinate domains, with toe-weight-defined rear toe support.'},indent=2)+'\n')
 print('NATIVE_RESULT',json.dumps({'id':id,'ok':not fail,'minimum_z':min(x['minimum_body_z'] for x in rows),'loop':loop,'maxstep_degrees':math.degrees(maxstep),'qa_errors':sum(len(q['qa']['errors']) for q in qa),'failure_count':len(fail),'failures':fail[:5]}),flush=True)
 if fail:raise RuntimeError(fail[:10])
