"""Full151 streamed decoded DQ positions/NORMAL plus all51 native joints/matrices."""
from pathlib import Path
import sys
sys.dont_write_bytecode=True
import bpy,json,hashlib,gzip,struct,numpy as np
P=Path(__file__).resolve().parent;sys.path.insert(0,str(P));sys.path.insert(0,str(P.parents[1]/'batch-007/resting-repair'));from runtime_checks import SurfaceChecks
A=P.parent/'assets/6539';bpy.ops.wm.open_mainfile(filepath=str(A/'source.blend'));b=bpy.data.objects['SK_BlenderStudioHuman'];r=bpy.data.objects['RIG_BlenderStudioHuman'];s=bpy.context.scene
assert r.animation_data.action.name=='Exercise_6539';metadata=json.loads(sys.stdin.buffer.readline());names=metadata['bone_names'];assert len(names)==51 and metadata['frames']==151
checks=SurfaceChecks(b,json.loads((A/'landmarks.json').read_text()));inverse={n:r.data.bones[n].matrix_local.inverted()for n in names}
with gzip.open(A/'joint-normal-reference.json.gz','rt')as fp:normals=json.load(fp)
N0=np.array(normals['basis']);NK=np.array(normals['targets']['RestingHipVolume']);indices=np.zeros((10582,4),int);weights=np.zeros((10582,4))
for v in b.data.vertices:
 for k,g in enumerate(v.groups):indices[v.index,k]=names.index(b.vertex_groups[g.group].name);weights[v.index,k]=g.weight
reference_slot=np.argmax(weights,axis=1);reference_joint=indices[np.arange(10582),reference_slot]
def read(n):
 data=bytearray()
 while len(data)<n:
  chunk=sys.stdin.buffer.read(n-len(data))
  if not chunk:raise EOFError((len(data),n))
  data.extend(chunk)
 return data
rows=[];fail=[];maximum={'position_m':0.,'joint_m':0.,'deformation_matrix':0.,'shader_normal_degrees':0.,'morph_weight':0.};first=None;first_matrix=None;first_native=None;matrix_change=0.;native_change=0.;minimum_source_normal_length=1.
for frame in range(151):
 f,count=struct.unpack('<II',read(8));assert f==frame and count==10582
 X=np.frombuffer(read(count*12),'<f4').reshape(count,3).astype(float);N=np.frombuffer(read(count*12),'<f4').reshape(count,3).astype(float);J=np.frombuffer(read(51*12),'<f4').reshape(51,3).astype(float);D=np.frombuffer(read(51*64),'<f4').reshape(51,4,4).transpose(0,2,1).astype(float);morph=struct.unpack('<f',read(4))[0];assert all(np.isfinite(v).all()for v in [X,N,J,D])
 s.frame_set(f+1);bpy.context.view_layer.update();ev=b.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh();native=np.array([v.co[:]for v in me.vertices]);ev.to_mesh_clear();nativeD=np.array([np.array(r.pose.bones[n].matrix@inverse[n])for n in names]);nativeJ=np.array([r.pose.bones[n].head[:]for n in names]);nativeMorph=float(b.data.shape_keys.key_blocks['RestingHipVolume'].value)
 Q=np.array([(r.pose.bones[n].matrix@inverse[n]).to_quaternion()[:]for n in names]);Q/=np.linalg.norm(Q,axis=1)[:,None];terms=Q[indices];reference=Q[reference_joint];sign=np.where((terms*reference[:,None,:]).sum(2)<0,-1.,1.);blend=(terms*weights[:,:,None]*sign[:,:,None]).sum(1);blend/=np.linalg.norm(blend,axis=1)[:,None]
 sourceN=N0+nativeMorph*(NK-N0);minimum_source_normal_length=min(minimum_source_normal_length,float(np.linalg.norm(sourceN,axis=1).min()));v=blend[:,1:];nativeN=sourceN+2*np.cross(v,np.cross(v,sourceN)+blend[:,:1]*sourceN);nativeN/=np.linalg.norm(nativeN,axis=1)[:,None]
 errors={'position_m':float(np.linalg.norm(X-native,axis=1).max()),'joint_m':float(np.linalg.norm(J-nativeJ,axis=1).max()),'deformation_matrix':float(abs(D-nativeD).max()),'shader_normal_degrees':float(np.degrees(np.arccos(np.clip((N*nativeN).sum(1)/np.linalg.norm(N,axis=1),-1,1))).max()),'morph_weight':abs(morph-nativeMorph)}
 for name,value in errors.items():
  maximum[name]=max(maximum[name],value)
  if value>(.1 if name=='shader_normal_degrees'else 1e-5):fail.append({'frame':f,'issue':'decoded_native_'+name,'value':value})
 if first is None:first=X.copy();first_matrix=D.copy();first_native=nativeD.copy()
 matrix_change=max(matrix_change,float(abs(D-first_matrix).max()));native_change=max(native_change,float(abs(nativeD-first_native).max()));row,issues=checks.measure(X,N,f);row['native_parity_errors']=errors;row['actual_morph_weight']=morph;rows.append(row);fail.extend({'frame':f,'issue':issue}for issue in issues)
loop=float(np.linalg.norm(X-first,axis=1).max())
if loop>1e-5:fail.append({'issue':'loop','m':loop})
if min(matrix_change,native_change)<.1:fail.append({'issue':'static_actual_or_native_animation'})
report={'ok':not fail,'source_sha256':hashlib.sha256((A/'source.blend').read_bytes()).hexdigest(),'glb_sha256':hashlib.sha256((A/'motion.glb').read_bytes()).hexdigest(),'runtime_adapter_sha256':hashlib.sha256((P.parents[1]/'dual-quaternion.js').read_bytes()).hexdigest(),'sampling':{'frames':151,'fps':30,'duration_seconds':5,'native_frame_origin':1},'method':'Actual project GLTFLoader/AnimationMixer with the exact unchanged shared optional DQ adapter; all151 complete surfaces, exact shaderNORMAL,51joints and51deformation matrices streamed directly to native Blender/source BVH checks. Action.paused explicitly reset before each sample; no stored runtime frame cache.','maximum_native_parity_error':maximum,'maximum_actual_deformation_matrix_change_from_start':matrix_change,'maximum_native_deformation_matrix_change_from_start':native_change,'minimum_source_morph_normal_length':minimum_source_normal_length,'loop_vertex_error_m':loop,'self_fold_policy':'Exact frozen-source ROI crossings remain diagnostic with frame/triangle localization; native silhouettes at intermediate/peak/worst poses were accepted for user review. This is not a globally collision-free claim.','failures':fail,'samples':rows}
(A/'runtime-physics-report.json').write_text(json.dumps(report,indent=2)+'\n');print('RUNTIME151',json.dumps({'ok':not fail,'maximum_native_parity_error':maximum,'minimum_body_z':min(x['minimum_body_z']for x in rows),'minimum_source_normal_length':minimum_source_normal_length,'loop_m':loop,'failure_count':len(fail),'failures':fail[:10]}),flush=True)
if fail:raise RuntimeError(fail[:10])
