"""Actual decoded GLB+Three.js surfaces streamed directly into fixed-source checks."""
from pathlib import Path
import bpy,sys,json,hashlib,struct,numpy as np
P=Path(__file__).resolve().parent;sys.path.insert(0,str(P));from geometry_checks import SurfaceChecks
id=sys.argv[-1];assert id in ['3479','3480'];out=P.parent/'assets'/id;bpy.ops.wm.open_mainfile(filepath=str(P.parent/'assets/3479/source.blend'));b=bpy.data.objects['SK_BlenderStudioHuman'];r=bpy.data.objects['RIG_BlenderStudioHuman'];s=bpy.context.scene;a=bpy.data.actions['Exercise_'+id];r.animation_data.action=a;b.data.shape_keys.animation_data.action=a;b.data.shape_keys.animation_data.action_slot=next(x for x in a.slots if x.target_id_type=='KEY');states=json.loads((P/'kinematic-state.json').read_text())[id];checks=SurfaceChecks(b,json.loads((P/'contact-landmarks.json').read_text()),json.loads((P/'joint-target-report.json').read_text()))
def read(n):
 out=bytearray()
 while len(out)<n:
  chunk=sys.stdin.buffer.read(n-len(out))
  if not chunk:raise EOFError((len(out),n))
  out.extend(chunk)
 return out
rows=[];fail=[];initial=None;maxparity=0;firstbones=None;maxbonechange=0
for expected in range(151):
 f,count=struct.unpack('<II',read(8));assert f==expected and count==10582;X=np.frombuffer(read(count*12),'<f4').reshape(count,3).astype(float);N=np.frombuffer(read(count*12),'<f4').reshape(count,3).astype(float);assert np.isfinite(X).all() and np.isfinite(N).all();s.frame_set(f+1);bpy.context.view_layer.update();ev=b.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh();native=np.array([ev.matrix_world@v.co for v in me.vertices]);ev.to_mesh_clear();parity=float(np.linalg.norm(X-native,axis=1).max());maxparity=max(maxparity,parity);bones=np.array([np.array(pb.matrix) for pb in r.pose.bones]);
 if firstbones is None:firstbones=bones.copy()
 maxbonechange=max(maxbonechange,float(abs(bones-firstbones).max()))
 if parity>1e-5:fail.append({'frame':f,'issue':'actual_export_native_parity','error':parity})
 if initial is None:initial=X.copy()
 row,issues=checks.measure(X,N,states[str(f)]);row['native_action']=r.animation_data.action.name;row['key_values']={k.name:k.value for k in b.data.shape_keys.key_blocks if k.name!='Basis'};row['maximum_native_position_error_m']=parity;rows.append(row);fail.extend({'frame':f,'issue':issue} for issue in issues)
loop=float(np.linalg.norm(X-initial,axis=1).max())
if loop>1e-5:fail.append({'issue':'loop_closure'})
assert maxbonechange>.1,'Static action sampling detected'
report={'ok':not fail,'source_sha256':hashlib.sha256((P.parent/'assets/3479/source.blend').read_bytes()).hexdigest(),'glb_sha256':hashlib.sha256((P.parent/'assets/3479/motion.glb').read_bytes()).hexdigest(),'scope':'Actual project Three.js GLTFLoader/AnimationMixer plus standard four-influence LBS and four additive POSITION/NORMAL targets. All151 surfaces streamed once in ascending time directly to native Blender BVH checks, no stored frame cache.','actual_action':a.name,'sampling':{'frames':151,'fps':30,'native_frame_origin':1},'maximum_native_position_error_m':maxparity,'maximum_native_bone_matrix_change_from_start':maxbonechange,'loop_vertex_error_m':loop,'self_fold_policy':'Localized exact nonadjacent self-fold counts and opposed shader normals are diagnostics. Root accepted bounded joint8 shape with residual joint creases; this is not a globally collision-free claim.','failures':fail,'samples':rows,'crossing_witnesses':checks.witnesses};(out/'runtime-physics-report.json').write_text(json.dumps(report,indent=2)+'\n');print('RUNTIME_PHYSICS_JSON',json.dumps({'id':id,'ok':not fail,'maximum_native_position_error_m':maxparity,'minimum_body_z':min(x['minimum_body_z'] for x in rows),'loop_vertex_error_m':loop,'failure_count':len(fail),'failures':fail[:8]}),flush=True)
if fail:raise RuntimeError(fail[:8])
