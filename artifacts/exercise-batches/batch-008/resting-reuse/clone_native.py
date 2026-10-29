"""Identity-only4365→6539 native action clone; no geometry or motion refit."""
from pathlib import Path
import sys
sys.dont_write_bytecode=True
import bpy,numpy as np,json,hashlib
from mathutils import Vector
P=Path(__file__).resolve().parent;A=P.parent/'assets/6539';old=P.parents[1]/'batch-007/assets/4365';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(old/'source.blend')=='85bca4ebfe5fee6a3038bee4cf39e528ffc3dd42c133888c286d960d33a92fdd'
bpy.ops.wm.open_mainfile(filepath=str(old/'source.blend'));b=bpy.data.objects['SK_BlenderStudioHuman'];r=bpy.data.objects['RIG_BlenderStudioHuman'];s=bpy.context.scene;action=bpy.data.actions['Exercise_4365'];key=b.data.shape_keys.key_blocks['RestingHipVolume']
def points():
 bpy.context.view_layer.update();ev=b.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh();x=np.array([v.co[:]for v in me.vertices],np.float32);ev.to_mesh_clear();return x
# Temporary verification memory is discarded; no frame/vertex cache is saved.
reference=[]
for f in range(151):
 s.frame_set(f+1);reference.append((points(),np.array([np.array(pb.matrix)for pb in r.pose.bones],np.float32),float(key.value)))
action.name='Exercise_6539';assert r.animation_data.action.name==b.data.shape_keys.animation_data.action.name=='Exercise_6539'
maximum=0.;matrix=0.;morph=0.
for f,(x,D,k)in enumerate(reference):
 s.frame_set(f+1);maximum=max(maximum,float(np.linalg.norm(points()-x,axis=1).max()));matrix=max(matrix,float(abs(np.array([np.array(pb.matrix)for pb in r.pose.bones],np.float32)-D).max()));morph=max(morph,abs(float(key.value)-k))
assert maximum==matrix==morph==0
reference.clear();s.frame_set(1);bpy.ops.wm.save_as_mainfile(filepath=str(A/'source.blend'));new_sha=sha(A/'source.blend')
sys.path.insert(0,str(Path.home()/'.codex/skills/blender-asset-qa/scripts'));import qa_check
qa=[];proof=[]
for f in [0,30,75,120,150]:
 s.frame_set(f+1);bpy.context.view_layer.update();result=qa_check.run(objects=[b.name],profile='game');qa.append({'frame':f,'qa':result});assert result['pass'],result['errors']
for label,f in [('start',0),('peak',75),('return',150)]:
 s.frame_set(f+1);x=points();D={p.name:np.array(p.matrix)for p in r.pose.bones}
 for view,pos,width in [('side',(5,0,1),2.5),('oblique',(3.8,-5,2.2),2.1)]:
  cam=s.camera;cam.location=pos;cam.rotation_euler=(Vector((0,.05,.65))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=width;s.render.filepath=str(A/f'neutral-{label}-{view}.png');bpy.ops.render.render(write_still=True);assert np.array_equal(x,points())and all(np.array_equal(D[p.name],np.array(p.matrix))for p in r.pose.bones);proof.append({'file':Path(s.render.filepath).name,'frame':f,'actual_action':r.animation_data.action.name,'sha256':sha(Path(s.render.filepath)),'render_skin_delta_m':0,'render_bone_delta':0})
report={'ok':True,'source_sha256':new_sha,'reused_source_sha256':sha(old/'source.blend'),'frames':151,'maximum_native_skin_identity_error_m':maximum,'maximum_native_matrix_identity_error':matrix,'maximum_native_morph_identity_error':morph,'identity_change':'Only action.name Exercise_4365→Exercise_6539; all original geometry,weights,morph coordinates/timing and all151 surfaces remain exact.','no_refit':True}
(P/'native-identity.json').write_text(json.dumps(report,indent=2)+'\n');(A/'asset-qa.json').write_text(json.dumps({'source_sha256':new_sha,'profile':'game','samples':qa},indent=2)+'\n');(A/'proof-receipt.json').write_text(json.dumps({'source_sha256':new_sha,'proofs':proof},indent=2)+'\n');print('NATIVE_IDENTITY',json.dumps(report))
