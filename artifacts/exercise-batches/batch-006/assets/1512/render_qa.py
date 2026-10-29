"""Two native wire inspections and all-frame arm/digit connection readback.

The temporary wire shell is built from the actual evaluated surface only for
inspection. It is never saved in source.blend or exported.
"""
import bpy,json,hashlib
from pathlib import Path
import numpy as np
from mathutils import Vector
P=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P/'source.blend'))
b=bpy.data.objects['SK_BlenderStudioHuman'];r=bpy.data.objects['RIG_BlenderStudioHuman'];s=bpy.context.scene
def points():
 e=b.evaluated_get(bpy.context.evaluated_depsgraph_get());m=e.to_mesh();v=np.array([x.co[:]for x in m.vertices]);e.to_mesh_clear();return v
pairs=[]
for side in ['Left','Right']:
 pairs.extend([(side+'Arm',side+'ForeArm'),(side+'ForeArm',side+'Hand')])
 for digit in ['Thumb','Index','Middle','Ring','Little']:
  pairs.extend([(side+digit+str(i),side+digit+str(i+1))for i in [1,2]])
connected=[(a,c)for a,c in pairs if(r.data.bones[a].tail_local-r.data.bones[c].head_local).length<1e-5]
rows=[]
for f in range(151):
 s.frame_set(f+1);bpy.context.view_layer.update()
 scale=max(abs(v-1)for pb in r.pose.bones for v in pb.matrix.to_scale())
 length=max(abs(pb.length-pb.bone.length)for pb in r.pose.bones)
 gaps={a+'->'+c:(r.pose.bones[a].tail-r.pose.bones[c].head).length for a,c in connected}
 assert scale<1e-5 and length<1e-6 and max(gaps.values())<1e-5,(f,scale,length,max(gaps.values()))
 rows.append({'frame':f,'maximum_bone_scale_deviation':scale,'maximum_bone_length_error_m':length,'maximum_connected_chain_gap_m':max(gaps.values())})
proofs=[]
for f,label in [(0,'neutral'),(75,'hold')]:
 s.frame_set(f+1);bpy.context.view_layer.update();before=points()
 evaluated=b.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=bpy.data.meshes.new_from_object(evaluated)
 wire=bpy.data.objects.new('TemporaryInspectionWire',mesh);s.collection.objects.link(wire);wire.matrix_world=b.matrix_world.copy()
 material=bpy.data.materials.new('InspectionWire');material.diffuse_color=(.075,.085,.095,1);wire.data.materials.clear();wire.data.materials.append(material)
 for poly in wire.data.polygons:poly.material_index=0
 modifier=wire.modifiers.new('Diagnostic wire only','WIREFRAME');modifier.thickness=.0006;modifier.use_replace=True;modifier.offset=1
 camera=s.camera;target=Vector((0,.06,.43));camera.location=(2.8,-2.3,1.55);camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.ortho_scale=1.90
 s.render.filepath=str(P/f'{label}-wire-oblique.png');bpy.ops.render.render(write_still=True)
 error=float(np.linalg.norm(points()-before,axis=1).max());assert error<1e-7
 proofs.append({'frame':f,'file':f'{label}-wire-oblique.png','native_surface_before_after_render_max_m':error})
 bpy.data.objects.remove(wire,do_unlink=True);bpy.data.meshes.remove(mesh);bpy.data.materials.remove(material)
report={'pass':True,'source_sha256':hashlib.sha256((P/'source.blend').read_bytes()).hexdigest(),'frames':151,'chain_pairs_checked':[list(x)for x in connected],'maximum_bone_scale_deviation':max(x['maximum_bone_scale_deviation']for x in rows),'maximum_bone_length_error_m':max(x['maximum_bone_length_error_m']for x in rows),'maximum_connected_chain_gap_m':max(x['maximum_connected_chain_gap_m']for x in rows),'samples':rows,'wire_proofs':proofs,'scope':'Actual saved native action; all51 bone lengths and matrix scales, anatomically connected arm/forearm/hand and digit segments. Source file never saved.'}
(P/'limb-integrity-report.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items()if k not in ['samples','chain_pairs_checked']}))
