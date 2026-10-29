"""Final-source invariants, independent key NORMAL and five full DQ references."""
from pathlib import Path
import sys
sys.dont_write_bytecode=True
import bpy,numpy as np,json,gzip,hashlib
from mathutils import Quaternion,Vector
P=Path(__file__).resolve().parent;A=P.parent/'assets/4365';sys.path.insert(0,str(P.parents[1]/'batch-003'));import authoring as a
a.initialize();OR=np.array([v.co[:]for v in a.body.data.vertices],np.float32);OU=[np.array([x.uv[:]for x in l.data],np.float32)for l in a.body.data.uv_layers];OT=[list(p.vertices)for p in a.body.data.polygons];OB={n:np.array(m,np.float32)for n,m in a.rest.items()};binding=a.binding_hash(a.body,a.rig)
bpy.ops.wm.open_mainfile(filepath=str(A/'source.blend'));b=bpy.data.objects['SK_BlenderStudioHuman'];r=bpy.data.objects['RIG_BlenderStudioHuman'];s=bpy.context.scene;R=np.array([v.co[:]for v in b.data.vertices],np.float32);source=hashlib.sha256((A/'source.blend').read_bytes()).hexdigest();key=b.data.shape_keys.key_blocks['RestingHipVolume'];rest={n:r.data.bones[n].matrix_local.copy()for n in OB}
assert a.binding_hash(b,r)==binding and np.array_equal(R,OR)and OT==[list(p.vertices)for p in b.data.polygons]
assert all(np.array_equal(x,np.array([d.uv[:]for d in l.data],np.float32))for x,l in zip(OU,b.data.uv_layers));assert all(np.array_equal(x,np.array(r.data.bones[n].matrix_local,np.float32))for n,x in OB.items())
ids=np.array([x.value for x in b.data.attributes['_SOURCE_INDEX'].data],np.float32);assert np.array_equal(ids,np.arange(10582,dtype=np.float32))
assert set(x.name for x in bpy.data.actions)=={'Exercise_4365'}and all(m.show_viewport==(m.type=='ARMATURE')and m.show_render==(m.type=='ARMATURE')for m in b.modifiers)
assert next(m for m in b.modifiers if m.type=='ARMATURE').use_deform_preserve_volume
b.data.calc_loop_triangles();T=np.array([t.vertices[:]for t in b.data.loop_triangles]);N0=np.array([v.normal[:]for v in b.data.vertices]);K=np.array([v.co[:]for v in key.data]);mesh=bpy.data.meshes.new('IndependentKeyNormals');mesh.from_pydata(K.tolist(),[],OT)
for p,original in zip(mesh.polygons,b.data.polygons):p.use_smooth=original.use_smooth
mesh.update();NK=np.array([v.normal[:]for v in mesh.vertices]);bpy.data.meshes.remove(mesh)
def xyz():
 bpy.context.view_layer.update();ev=b.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh();X=np.array([v.co[:]for v in me.vertices]);ev.to_mesh_clear();return X
s.frame_set(1);neutral=xyz();pp=neutral[T];normal=np.cross(pp[:,1]-pp[:,0],pp[:,2]-pp[:,0]);normal/=np.linalg.norm(normal,axis=1)[:,None]
reference_1512=P.parents[1]/'batch-006/assets/1512/surface-landmarks.json';frozen=json.loads(reference_1512.read_text())['patches'];patches={}
for side,sign in [('Left',1),('Right',-1)]:
 patches['knee_'+side]={'indices':frozen['knee_'+side]['indices'],'kind':'knee','state':'supported','selection':'Frozen accepted1512 actual source knee patch; independent witness0.50..1.30mm over this clip.'}
 mask=(R[:,2]<.115)&(sign*R[:,0]>.05);faces=np.flatnonzero(np.all(mask[T],axis=1)&(normal[:,2]<-.35));assert len(faces);z=pp[faces,:,2].mean(1);faces=faces[z<z.min()+.005];patches['dorsum_'+side]={'indices':np.unique(T[faces]).tolist(),'triangles':faces.tolist(),'kind':'dorsum','state':'supported','selection':'Actual neutral native-DQ floor-facing source triangles within5mm of lowest foot centroid.'}
# Source palm pad selection is the same independent geometric helper used in
# the accepted motion, and excludes fingertips as an inferred contact proxy.
from importlib.util import spec_from_file_location,module_from_spec
spec=spec_from_file_location('palm_reference',P.parent/'prone-family/palm_frame.py');palm=module_from_spec(spec);spec.loader.exec_module(palm)
class Source:pass
ref=Source();ref.body=b;ref.heads={bone.name:bone.head_local.copy()for bone in r.data.bones};ref.tails={bone.name:bone.tail_local.copy()for bone in r.data.bones};palms=palm.prepare(ref)
for side in ['Left','Right']:patches['palm_'+side]={'indices':palms[side]['source_ids'],'kind':'palm','state':'hold_supported','selection':'Original central-palm skin derived from hand axis,Hand>0.8 and source-facing normal; independently fitted palm plane.'}
forehead=np.flatnonzero((R[:,2]>1.64)&(R[:,2]<1.74)&(R[:,1]<-.06)&(N0[:,1]<-.4)).tolist();patches['forehead']={'indices':forehead,'kind':'forehead','state':'hold_supported','selection':'Original anterior forehead source skin, separate from whole-head minimum.'}
landmarks={'source_sha256':source,'source_vertices':10582,'coordinate_system':'BlenderZup','source_index_attribute':'_SOURCE_INDEX','floor_plane_z':0,'patches':patches,'reference_1512_sha256':hashlib.sha256(reference_1512.read_bytes()).hexdigest(),'tolerances':{'floor_minimum_m':-1e-6,'knee_dorsum_support_m':.012,'palm_forehead_support_m':.005,'palm_minimum_vertices_within5mm':5,'planted_hand_drift_m':.005,'planted_dorsum_drift_m':.005},'scope':'Actual source skin, not joint endpoints. Whole body and whole arm/hand versus legs are measured separately.'}
(A/'landmarks.json').write_text(json.dumps(landmarks,indent=2)+'\n')
frames=[0,22,30,35,39,40,45,46,54,60,75,90,96,104,105,111,120,128,139,150];poses=[];surfaces=[];dq=[];morph=[];full_frames={0,30,75,120,150};normal_samples=[]
for f in range(151):
 s.frame_set(f+1);bpy.context.view_layer.update();morph.append({'id':'4365','frame':f,'weights':{'RestingHipVolume':float(key.value)}})
 if f not in frames:continue
 X=xyz();poses.append({'id':'4365','frame':f,'joints':{pb.name:list(pb.head)for pb in r.pose.bones}})
 patches_frame={}
 for name,p in patches.items():
  idx=p['indices'];kind=p['kind'];supported=kind in ['knee','dorsum']or 60<=f<=90;patches_frame[name]={'indices':idx,'positions':X[idx].tolist(),'min_z':float(X[idx,2].min()),'max_z':float(X[idx,2].max()),'state':'supported'if supported else'free'}
 surfaces.append({'id':'4365','frame':f,'floor_plane_z':0,'global_floor_z':float(X[:,2].min()),'patches':patches_frame})
 if f in full_frames:
  currentN=N0+key.value*(NK-N0);worldN=np.zeros_like(currentN)
  for v in b.data.vertices:
   terms=[(g.weight,(r.pose.bones[b.vertex_groups[g.group].name].matrix@rest[b.vertex_groups[g.group].name].inverted()).to_quaternion())for g in v.groups if g.weight>1e-8];reference=max(terms,key=lambda t:t[0])[1];q=np.zeros(4)
   for weight,value in terms:q+=np.array(value)*weight*(-1 if value.dot(reference)<0 else 1)
   q=Quaternion(q);q.normalize();worldN[v.index]=q@Vector(currentN[v.index])
  worldN/=np.linalg.norm(worldN,axis=1)[:,None];dq.append({'id':'4365','frame':f,'positions':X.tolist(),'shader_normals':worldN.tolist()})
for name,data in [('pose-samples.json',poses),('runtime-surface-reference.json',{'source_sha256':source,'source_vertices':10582,'reference_kind':'native','skinning':'dualQuaternion','coordinate_frame':'Blender world metres','samples':surfaces}),('source-morph-samples.json',{'source_sha256':source,'samples':morph})]:(A/name).write_text(json.dumps(data,indent=2)+'\n')
for name,data in [('dq-reference.json.gz',{'source_sha256':source,'source_vertices':10582,'samples':dq}),('joint-normal-reference.json.gz',{'source_sha256':source,'basis':N0.tolist(),'targets':{'RestingHipVolume':NK.tolist()},'scope':'Independently calculated original-source rest/key normals. Exact DQ shader normals combine them before unit-DQ rotation; not a claim that per-face native posed normals equal this renderer transport.'}),('topology-reference.json.gz',{'source_sha256':source,'triangles':T.tolist()})]:
 with gzip.open(A/name,'wt')as fp:json.dump(data,fp)
original_delta=np.linalg.norm(K-R,axis=1);names=[g.name for g in b.vertex_groups];weight_error=max(abs(sum(g.weight for g in v.groups)-1)for v in b.data.vertices)
verify={'ok':True,'source_sha256':source,'original_source_sha256':a.SOURCE_SHA,'original_binding_sha256':binding,'invariants':{'basis':True,'rest':True,'UV':True,'topology':True,'source_ids':10582,'bones':51,'original_deform_weights_exact':True,'maximum_influences':max(len(v.groups)for v in b.data.vertices),'normalization_max_error':weight_error},'morphs':['RestingHipVolume'],'maximum_source_delta_m':float(original_delta.max()),'changed_source_ids':np.flatnonzero(original_delta>1e-8).tolist(),'other_clip_contribution':'Standalone one-action4365; no other asset or action changed.','reference_frames':sorted(full_frames),'shader_normal_reference':'Independent actual source-key normals combined before normalized native-DQ quaternion rotation.'}
(A/'source-verification.json').write_text(json.dumps(verify,indent=2)+'\n')
physical=json.loads((P/'native-loop-report.json').read_text());physical['measurement_source_sha256']=physical['source_sha256'];physical['source_sha256']=source;physical['physical_equivalence']=json.loads((P/'export-manifest.json').read_text())['physical_signature_final'];physical['status']='native_mechanics_passed_shape_accepted_for_user_review';(A/'surface-contact-report.json').write_text(json.dumps(physical,indent=2)+'\n')
print('NATIVE_REFERENCES_READY',json.dumps({'source_sha256':source,'pose_frames':frames,'full_DQ_frames':sorted(full_frames),'original_weights_exact':True,'morph_max_source_m':float(original_delta.max())}))
