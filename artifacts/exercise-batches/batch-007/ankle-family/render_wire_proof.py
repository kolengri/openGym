"""Limited actual native neutral/peak wire evidence; no source mutation."""
from pathlib import Path
import bpy,json,hashlib
from mathutils import Vector
P=Path(__file__).resolve().parent;B=P.parent
bpy.ops.wm.open_mainfile(filepath=str(P/'source.blend'));s=bpy.context.scene;b=bpy.data.objects['SK_BlenderStudioHuman'];r=bpy.data.objects['RIG_BlenderStudioHuman'];s.render.resolution_x=1100;s.render.resolution_y=850
s.camera.location=(2.8,-4.0,1.4);s.camera.rotation_euler=(Vector((0,-.4,.4))-s.camera.location).to_track_quat('-Z','Y').to_euler();s.camera.data.ortho_scale=2.0
rows=[];line_material=bpy.data.materials.new('DiagnosticWire');line_material.diffuse_color=(.015,.02,.025,1)
for id,frame,label in [('1368',0,'neutral'),('1368',48.75,'circle'),('2761',37.5,'dorsal'),('2762',37.5,'point')]:
 r.animation_data.action=bpy.data.actions['Exercise_'+id];s.frame_set(int(frame)+1,subframe=frame%1);bpy.context.view_layer.update()
 # Workbench omits viewport wire overlays in final renders. A disposable
 # wire shell uses the actual evaluated mesh; it never enters the source.
 mesh=bpy.data.meshes.new_from_object(b.evaluated_get(bpy.context.evaluated_depsgraph_get()));mesh.materials.clear();mesh.materials.append(line_material);shell=bpy.data.objects.new('DiagnosticEvaluatedWire',mesh);s.collection.objects.link(shell);wire=shell.modifiers.new('DiagnosticWire','WIREFRAME');wire.thickness=.00065;wire.offset=1;wire.use_replace=True
 s.render.filepath=str(B/'assets'/id/f'qa-wire-{label}.png');bpy.ops.render.render(write_still=True);rows.append({'id':id,'frame':frame,'path':s.render.filepath});bpy.data.objects.remove(shell,do_unlink=True);bpy.data.meshes.remove(mesh)
(P/'wire-proof.json').write_text(json.dumps({'source_sha256':hashlib.sha256((P/'source.blend').read_bytes()).hexdigest(),'actual_saved_native_armature_DQ':True,'source_not_saved':True,'samples':rows},indent=2)+'\n')
