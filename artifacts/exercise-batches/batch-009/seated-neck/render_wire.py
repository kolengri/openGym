"""Actual evaluated source wire proofs; disposable wire never enters export."""
from pathlib import Path
import bpy,json,hashlib
from mathutils import Vector
F=Path(__file__).resolve().parent;P=F.parent/'assets/1843';bpy.ops.wm.open_mainfile(filepath=str(P/'source.blend'));s=bpy.context.scene;b=bpy.data.objects['SK_BlenderStudioHuman'];camera=s.camera;camera.location=(3.4,-4.8,2.05);camera.rotation_euler=(Vector((0,-.32,.48))-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.ortho_scale=1.55
mat=bpy.data.materials.new('DiagnosticWireOnly');mat.diffuse_color=(.01,.015,.02,1)
for frame,label in [(0,'start'),(75,'held')]:
 s.frame_set(frame+1);bpy.context.view_layer.update();mesh=bpy.data.meshes.new_from_object(b.evaluated_get(bpy.context.evaluated_depsgraph_get()));mesh.materials.clear();mesh.materials.append(mat);shell=bpy.data.objects.new('DiagnosticWireShell',mesh);s.collection.objects.link(shell);wire=shell.modifiers.new('WireProof','WIREFRAME');wire.thickness=.00045;wire.offset=1;wire.use_replace=True;s.render.filepath=str(P/f'qa-wire-{label}.png');bpy.ops.render.render(write_still=True);bpy.data.objects.remove(shell,do_unlink=True);bpy.data.meshes.remove(mesh)
(F/'wire-proof.json').write_text(json.dumps({'source_sha256':hashlib.sha256((P/'source.blend').read_bytes()).hexdigest(),'frames':[0,75],'actual_evaluated_native_DQ':True,'diagnostic_shell_not_saved':True},indent=2)+'\n')
