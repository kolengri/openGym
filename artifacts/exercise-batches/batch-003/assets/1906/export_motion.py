"""Export the accepted original linear cage and exactly one named action."""
import bpy,numpy as np,json,struct,hashlib,sys
from pathlib import Path
P=Path(__file__).resolve().parent;sys.path.insert(0,str(P))
bpy.ops.wm.open_mainfile(filepath=str(P/'source.blend'))
body=bpy.data.objects['SK_BlenderStudioHuman'];rig=bpy.data.objects['RIG_BlenderStudioHuman'];scene=bpy.context.scene
assert len(bpy.data.actions)==1 and bpy.data.actions[0].name=='Exercise_1906'
for m in body.modifiers:
 m.show_viewport=m.type=='ARMATURE';m.show_render=m.type=='ARMATURE'
 if m.type=='ARMATURE':m.use_deform_preserve_volume=False
scene.frame_set(1)
bpy.ops.object.select_all(action='DESELECT');body.select_set(True);rig.select_set(True);bpy.context.view_layer.objects.active=rig
bpy.ops.export_scene.gltf(filepath=str(P/'motion.glb'),export_format='GLB',use_selection=True,export_animations=True,export_animation_mode='ACTIONS',export_force_sampling=True,export_frame_range=True,export_frame_step=1,export_skins=True,export_all_influences=False,export_apply=False,export_attributes=True,export_materials='EXPORT',export_vertex_color='NONE',export_anim_slide_to_zero=True,export_rest_position_armature=True,export_influence_nb=4,export_cameras=False,export_lights=False,export_yup=True,export_morph=True)
import patch_morph_normals
patch_morph_normals.patch(P/'motion.glb',P/'normal-patch-report.json')
b=(P/'motion.glb').read_bytes();n=struct.unpack_from('<I',b,12)[0];d=json.loads(b[20:20+n]);p=d['meshes'][0]['primitives'][0]
assert len(d['animations'])==1 and d['animations'][0]['name']=='Exercise_1906'
assert len(d['skins'])==1 and len(d['skins'][0]['joints'])==51
assert d['accessors'][p['indices']]['count']//3==21160
assert len(p.get('targets',[]))==1 and 'NORMAL' in p['targets'][0]
assert d['meshes'][0]['weights']==[0]
assert '_SOURCE_INDEX' in p['attributes'] and not d.get('images') and not d.get('textures')
(P/'export-report.json').write_text(json.dumps({'ok':True,'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b),'source_sha256':hashlib.sha256((P/'source.blend').read_bytes()).hexdigest(),'meshes':1,'skins':1,'bones':51,'triangles':21160,'materials':len(d['materials']),'textures':0,'morphs':1,'morph_default_weights':[0],'morph_normal_target':True,'animations':[x['name'] for x in d['animations']],'original_index_attribute':'_SOURCE_INDEX'},indent=2)+'\n')
