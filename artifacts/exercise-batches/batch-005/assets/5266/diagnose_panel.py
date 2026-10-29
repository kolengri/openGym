"""Causal screen-space panel sampling; no source or candidate edits."""
import bpy,json,hashlib
from pathlib import Path
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
P=Path(__file__).resolve().parent;bpy.ops.wm.open_mainfile(filepath=str(P/'source.blend'))
s=bpy.context.scene;b=bpy.data.objects['SK_BlenderStudioHuman'];r=bpy.data.objects['RIG_BlenderStudioHuman'];cam=s.camera
assert len(b.data.shape_keys.key_blocks)==4,'Rejected hip fairing must not be in canonical source'
view=json.loads((P/'cameras.json').read_text())[0];cam.location=view['position'];cam.rotation_euler=(Vector(view['target'])-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=view['scale'];s.frame_set(38,subframe=.5);bpy.context.view_layer.update()
e=b.evaluated_get(bpy.context.evaluated_depsgraph_get());m=e.to_mesh();points=[v.co.copy()for v in m.vertices];tree=BVHTree.FromPolygons(points,[list(f.vertices)for f in m.polygons]);source=np.array([v.co[:]for v in b.data.vertices])
repair=json.loads((P/'glute-binding-repair.json').read_text());repair_ids=set(repair['changed_original_vertex_ids']);fair=json.loads((P/'hip-fairing-report.json').read_text());fair_ids=set(i for row in fair['targets']for i in row['changed_original_vertex_ids']);protected=set(json.loads((P/'support-protected-domain.json').read_text())['protected_source_ids'])
rows=[];faces={}
for v in [290,305,320,335,350,365,380,395]:
 for u in range(435,486,5):
  width=cam.data.ortho_scale;height=width*650/800;origin=cam.matrix_world@Vector(((u/800-.5)*width,(.5-v/650)*height,0));direction=cam.matrix_world.to_quaternion()@Vector((0,0,-1));hit,normal,face,distance=tree.ray_cast(origin,direction)
  if face is None:continue
  ids=list(m.polygons[face].vertices);mean=source[ids].mean(axis=0)
  row={'pixel':[u,v],'polygon':face,'source_ids':ids,'source_mean':mean.tolist(),'world_hit':list(hit),'world_normal':list(normal),'repair_ids':sorted(set(ids)&repair_ids),'fairing_ids':sorted(set(ids)&fair_ids),'protected_ids':sorted(set(ids)&protected)};rows.append(row)
  faces[str(face)]={'source_ids':ids,'source_vertices':[{'id':i,'neutral_position':list(b.data.vertices[i].co),'current_weights':{b.vertex_groups[g.group].name:g.weight for g in b.data.vertices[i].groups},'repair':i in repair_ids,'fairing':i in fair_ids,'protected':i in protected}for i in ids]}
# One flat proof and one topology overlay of the SAME evaluated surface.
copy=bpy.data.meshes.new_from_object(e);o=bpy.data.objects.new('PanelActualFlat',copy);s.collection.objects.link(o)
for f in copy.polygons:f.use_smooth=False
b.hide_render=True;s.render.filepath=str(P/'panel-flat-peak.png');bpy.ops.render.render(write_still=True);b.hide_render=False;bpy.data.objects.remove(o,do_unlink=True);bpy.data.meshes.remove(copy)
copy=bpy.data.meshes.new_from_object(e);o=bpy.data.objects.new('PanelActualWire',copy);s.collection.objects.link(o);mat=bpy.data.materials.new('PanelWire');mat.diffuse_color=(.01,.01,.01,1);copy.materials.clear();copy.materials.append(mat);w=o.modifiers.new('Wire','WIREFRAME');w.thickness=.0008;w.offset=1;s.render.filepath=str(P/'panel-wire-peak.png');bpy.ops.render.render(write_still=True)
e.to_mesh_clear();(P/'panel-causal-samples.json').write_text(json.dumps({'candidate':'source.blend','frame':37.5,'camera':view,'source_sha256':hashlib.sha256((P/'source.blend').read_bytes()).hexdigest(),'fairing_domain_is_rejected_history_only':True,'samples':rows,'faces':faces},indent=2)+'\n')
for row in rows:print(row['pixel'],row['polygon'],row['source_ids'],[round(x,3)for x in row['source_mean']],'R',len(row['repair_ids']),'F',len(row['fairing_ids']))
