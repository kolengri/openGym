"""Full241 actual decoded skin, normals and all51 joint/matrix native parity."""
from pathlib import Path
import sys
sys.dont_write_bytecode=True
import bpy,json,hashlib,struct,numpy as np
P=Path(__file__).resolve().parent;sys.path.insert(0,str(P))
from surface_checks_10058 import SurfaceChecks
out=P.parent/'assets/10058'
bpy.ops.wm.open_mainfile(filepath=str(out/'source.blend'))
b=bpy.data.objects['SK_BlenderStudioHuman'];r=bpy.data.objects['RIG_BlenderStudioHuman'];s=bpy.context.scene
r.animation_data.action=bpy.data.actions['Exercise_10058']
assert b.data.shape_keys is None
states=json.loads((P/'kneel10-state.json').read_text())
checks=SurfaceChecks(b,json.loads((out/'landmarks.json').read_text()))
metadata=json.loads(sys.stdin.buffer.readline());names=metadata['bone_names'];assert len(names)==51 and metadata['frames']==241
W=np.zeros((10582,51))
for v in b.data.vertices:
 for g in v.groups:W[v.index,names.index(b.vertex_groups[g.group].name)]=g.weight
RN=np.array([v.normal[:]for v in b.data.vertices]);inverse={n:r.data.bones[n].matrix_local.inverted()for n in names}
def read(n):
 data=bytearray()
 while len(data)<n:
  chunk=sys.stdin.buffer.read(n-len(data))
  if not chunk:raise EOFError((len(data),n))
  data.extend(chunk)
 return data
rows=[];fail=[];initial=None;firstbones=None;firstactual=None;maxchange=0;maxactualchange=0
maximum={'position_m':0.,'joint_m':0.,'deform_matrix':0.,'shader_normal_degrees':0.}
for expected in range(241):
 f,count=struct.unpack('<II',read(8));assert f==expected and count==10582
 X=np.frombuffer(read(count*12),'<f4').reshape(count,3).astype(float)
 N=np.frombuffer(read(count*12),'<f4').reshape(count,3).astype(float)
 J=np.frombuffer(read(51*12),'<f4').reshape(51,3).astype(float)
 matrices=np.frombuffer(read(51*64),'<f4').reshape(51,4,4).transpose(0,2,1).astype(float)
 assert all(np.isfinite(x).all()for x in [X,N,J,matrices])
 s.frame_set(f+1);bpy.context.view_layer.update()
 ev=b.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=ev.to_mesh();native=np.array([v.co[:]for v in mesh.vertices]);ev.to_mesh_clear()
 D=np.array([np.array(r.pose.bones[n].matrix@inverse[n])for n in names]);nativeJ=np.array([r.pose.bones[n].head[:]for n in names])
 A=np.einsum('vb,bij->vij',W,D[:,:3,:3]);nativeN=np.einsum('vij,vj->vi',A,RN);nativeN/=np.linalg.norm(nativeN,axis=1)[:,None]
 parity=float(np.linalg.norm(X-native,axis=1).max());joint=float(np.linalg.norm(J-nativeJ,axis=1).max());matrix=float(abs(matrices-D).max())
 normal=float(np.degrees(np.arccos(np.clip((N*nativeN).sum(1)/np.linalg.norm(N,axis=1),-1,1))).max())
 for key,value in [('position_m',parity),('joint_m',joint),('deform_matrix',matrix),('shader_normal_degrees',normal)]:maximum[key]=max(maximum[key],value)
 for key,value,limit in [('position_m',parity,1e-5),('joint_m',joint,1e-5),('deform_matrix',matrix,1e-5),('shader_normal_degrees',normal,.1)]:
  if value>limit:fail.append({'frame':f,'issue':'actual_decoded_native_'+key,'error':value})
 if initial is None:initial=X.copy();firstbones=D.copy();firstactual=matrices.copy()
 maxchange=max(maxchange,float(abs(D-firstbones).max()));maxactualchange=max(maxactualchange,float(abs(matrices-firstactual).max()))
 row,issues=checks.measure(X,N,states[str(f)]);row['actual_action']='Exercise_10058';row['maximum_native_position_error_m']=parity;row['maximum_native_joint_error_m']=joint;row['maximum_native_deform_matrix_error']=matrix;row['maximum_shader_normal_error_degrees']=normal
 rows.append(row);fail.extend({'frame':f,'issue':issue}for issue in issues)
loop=float(np.linalg.norm(X-initial,axis=1).max())
if loop>1e-5:fail.append({'issue':'loop_closure','m':loop})
if min(maxchange,maxactualchange)<.1:fail.append({'issue':'static_native_or_actual_animation'})
report={'ok':not fail,'source_sha256':hashlib.sha256((out/'source.blend').read_bytes()).hexdigest(),'glb_sha256':hashlib.sha256((out/'motion.glb').read_bytes()).hexdigest(),'scope':'Actual project Three.js GLTFLoader/AnimationMixer/Skeleton four-influence linear deformation. All241 30Hz full-source surfaces, exact shader normals,51 world joints and51 deformation matrices streamed once directly to source/native Blender BVH checks; no stored frame cache. Action.paused is explicitly reset before every sample.','actual_action':'Exercise_10058','sampling':{'frames':241,'fps':30,'duration_seconds':8,'native_frame_origin':1},'maximum_native_parity_error':maximum,'maximum_native_bone_matrix_change_from_start':maxchange,'maximum_actual_bone_matrix_change_from_start':maxactualchange,'loop_vertex_error_m':loop,'self_fold_policy':'Frozen source-local hip/knee/shoulder nonadjacent intersection counts are diagnostics; root accepted natural creased hip stills at peak and worst transition. This is not a globally collision-free claim.','failures':fail,'samples':rows}
(out/'runtime-physics-report.json').write_text(json.dumps(report,indent=2)+'\n')
print('RUNTIME_PHYSICS_JSON',json.dumps({'ok':not fail,'maximum_native_parity_error':maximum,'minimum_body_z':min(x['minimum_body_z']for x in rows),'loop_m':loop,'failure_count':len(fail),'failures':fail[:8]}),flush=True)
if fail:raise RuntimeError(fail[:8])
