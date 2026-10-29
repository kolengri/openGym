"""Final source inventory for exact camera, render and material acceptance."""
from pathlib import Path
import bpy,hashlib,json,sys
P=Path(__file__).resolve().parent;bpy.ops.wm.open_mainfile(filepath=str(P/'source.blend'))
s=bpy.context.scene;s.frame_set(1);bpy.context.view_layer.update();body=bpy.data.objects['SK_BlenderStudioHuman'];rig=bpy.data.objects['RIG_BlenderStudioHuman']
specs=json.loads((P/'cameras.json').read_text());cameras=[o for o in s.objects if o.type=='CAMERA']
assert len(specs)==len(cameras)==2 and all(c.data.type=='ORTHO' for c in cameras)
assert len([o for o in s.objects if o.type=='MESH'])==1 and len([o for o in s.objects if o.type=='ARMATURE'])==1
assert len(body.data.materials)==1 and len(bpy.data.actions)==1
assert not any(n.type=='TEX_IMAGE' for mat in body.data.materials for n in mat.node_tree.nodes)
assert s.render.film_transparent and not s.display.shading.show_shadows and not s.display.shading.show_cavity and not s.display.shading.show_specular_highlight
assert all(m.show_viewport==(m.type=='ARMATURE') for m in body.modifiers)
for spec in specs:
 cam=bpy.data.objects[spec['label']];assert max(abs(float(x)-y) for x,y in zip(cam.location,spec['position']))<1e-6
report={'ok':True,'source_sha256':hashlib.sha256((P/'source.blend').read_bytes()).hexdigest(),'blender_version':bpy.app.version_string,'platform':sys.platform,'objects':{kind:len([o for o in s.objects if o.type==kind]) for kind in ['MESH','ARMATURE','CAMERA']},'bones':len(rig.data.bones),'actions':[a.name for a in bpy.data.actions],'dimensions_m_at_start':list(body.dimensions),'units':{'scale_length':s.unit_settings.scale_length,'system':s.unit_settings.system},'native_frames':[s.frame_start,s.frame_end],'fps':s.render.fps,'material_count':len(body.data.materials),'body_image_texture_nodes':0,'cameras':[{'name':c.name,'type':c.data.type,'position':list(c.location),'native_ortho_vertical_scale':c.data.ortho_scale} for c in cameras],'cameras_json_scale':'horizontal world width; root fits final viewport width','render':{'engine':s.render.engine,'film_transparent':s.render.film_transparent,'shadows':s.display.shading.show_shadows,'cavity_ao':s.display.shading.show_cavity,'specular_overlay':s.display.shading.show_specular_highlight},'modifiers':[{'name':m.name,'type':m.type,'viewport':m.show_viewport,'render':m.show_render} for m in body.modifiers]}
(P/'native-inventory.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
