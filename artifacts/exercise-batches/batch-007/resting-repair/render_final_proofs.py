"""Small solid/wire proofs from the immutable final source; no source save."""
from pathlib import Path
import bpy,numpy as np,json,hashlib
from mathutils import Vector
P=Path(__file__).resolve().parent;A=P.parent/'assets/4365';source=A/'source.blend';sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest();before_hash=sha(source)
bpy.ops.wm.open_mainfile(filepath=str(source));b=bpy.data.objects['SK_BlenderStudioHuman'];r=bpy.data.objects['RIG_BlenderStudioHuman'];s=bpy.context.scene
assert r.animation_data.action.name=='Exercise_4365'
def xyz():
 bpy.context.view_layer.update();ev=b.evaluated_get(bpy.context.evaluated_depsgraph_get());m=ev.to_mesh();x=np.array([v.co[:]for v in m.vertices]);ev.to_mesh_clear();return x
proof=[]
for label,f,wire in [('neutral-start',0,False),('neutral-peak',75,False),('neutral-return',120,False),('wire-peak',75,True)]:
 s.frame_set(f+1);x=xyz();D={p.name:np.array(p.matrix)for p in r.pose.bones};overlay=None;cam=s.camera;cam.location=(3.8,-5,2.2);cam.rotation_euler=(Vector((0,.05,.65))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=2.1;s.render.resolution_x=650;s.render.resolution_y=740
 if wire:
  overlay=b.copy();overlay.name='ProofOnlyEdges';s.collection.objects.link(overlay);overlay.color=(.02,.02,.02,1);b.color=(.65,.65,.65,1);m=overlay.modifiers.new('WireProof','WIREFRAME');m.thickness=.00065;m.offset=1;s.display.shading.color_type='OBJECT'
 s.render.filepath=str(A/(label+'.png'));bpy.ops.render.render(write_still=True);assert np.array_equal(x,xyz())and all(np.array_equal(D[p.name],np.array(p.matrix))for p in r.pose.bones)
 if overlay:bpy.data.objects.remove(overlay,do_unlink=True)
 proof.append({'file':label+'.png','frame':f,'wire_overlay':wire,'sha256':sha(Path(s.render.filepath)),'actual_action':r.animation_data.action.name,'actual_hip_key':float(b.data.shape_keys.key_blocks['RestingHipVolume'].value),'render_skin_delta_m':0,'render_bone_delta':0})
assert sha(source)==before_hash
(A/'proof-receipt.json').write_text(json.dumps({'source_sha256':before_hash,'source_unmodified':True,'proofs':proof},indent=2)+'\n')
print('FINAL_PROOFS',json.dumps(proof))
