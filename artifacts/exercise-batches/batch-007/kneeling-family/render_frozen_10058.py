"""Small native/wire proofs from the immutable accepted source, without saving it."""
from pathlib import Path
import bpy,json,hashlib,numpy as np,sys
from mathutils import Vector
P=Path(__file__).resolve().parent;out=P.parent/'assets/10058';source=out/'source.blend'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();initial_sha=sha(source)
bpy.ops.wm.open_mainfile(filepath=str(source));body=bpy.data.objects['SK_BlenderStudioHuman'];rig=bpy.data.objects['RIG_BlenderStudioHuman'];scene=bpy.context.scene
rig.animation_data.action=bpy.data.actions['Exercise_10058']
def xyz():
 ev=body.evaluated_get(bpy.context.evaluated_depsgraph_get());m=ev.to_mesh();X=np.array([v.co[:]for v in m.vertices]);ev.to_mesh_clear();return X
report=P/'10058-frozen-proof-report.json'
rows=json.loads(report.read_text())['proofs'] if '--wire-only' in sys.argv else []
for label,frame,wire in [('worst-knee',130,False),('worst-hip',149,False),('neutral-wire',0,True),('half-left-wire',49,True)]:
 if '--wire-only' in sys.argv and not wire:continue
 scene.frame_set(frame+1);bpy.context.view_layer.update();X=xyz();D={p.name:np.array(p.matrix)for p in rig.pose.bones}
 cam=scene.camera;cam.location=(3.8,-5,2.2);cam.rotation_euler=(Vector((0,.05,.65))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=1.9
 scene.render.resolution_x=700;scene.render.resolution_y=700;scene.render.resolution_percentage=100
 overlay=None
 if wire:
  # Workbench does not render viewport wire overlays. Render a temporary edge
  # shell copied from the same native cage; never modify or save the body.
  overlay=body.copy();overlay.name='ProofWireOverlay';scene.collection.objects.link(overlay)
  overlay.color=(.02,.02,.02,1);body.color=(.65,.65,.65,1)
  modifier=overlay.modifiers.new('ProofEdges','WIREFRAME');modifier.thickness=.00065;modifier.offset=1
  scene.display.shading.color_type='OBJECT'
 scene.render.filepath=str(out/f'kneel10-{label}-oblique.png');bpy.ops.render.render(write_still=True)
 assert np.array_equal(X,xyz()) and all(np.array_equal(D[p.name],np.array(p.matrix))for p in rig.pose.bones)
 if overlay:bpy.data.objects.remove(overlay,do_unlink=True)
 rows=[row for row in rows if row['file']!=Path(scene.render.filepath).name]
 rows.append({'file':Path(scene.render.filepath).name,'frame':frame,'wire_overlay':wire,'sha256':sha(Path(scene.render.filepath)),'render_skin_delta_m':0,'render_bone_delta':0})
assert sha(source)==initial_sha
report.write_text(json.dumps({'source_sha256':initial_sha,'source_unmodified':True,'proofs':rows},indent=2)+'\n')
print('FROZEN_PROOFS',json.dumps(rows))
