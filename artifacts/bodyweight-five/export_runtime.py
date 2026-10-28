"""Export a small web skeleton with five actions and original-vertex atlas lookup."""
import bpy,sys,json,numpy as np
from pathlib import Path
P=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P/'runtime-source.blend'))
body=bpy.data.objects['SK_BlenderStudioHuman'];rig=bpy.data.objects['RIG_BlenderStudioHuman']
bpy.context.scene.render.fps=30;bpy.context.scene.render.fps_base=1.0
# Web textures keep the sharp role states without uploading six 4k images.
web=P/'web-textures';web.mkdir(exist_ok=True)
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
texture_source=Path(args[args.index('--texture-source')+1]) if '--texture-source' in args else P
for identifier in ['neutral','5965','5915','5887','0001','9066']:
    image=bpy.data.images.load(str(texture_source/f'texture-{identifier}.png'),check_existing=False)
    image.scale(2048,1024);image.file_format='PNG';image.filepath_raw=str(web/f'{identifier}.png');image.save()
    bpy.data.images.remove(image)
sys.path.insert(0,str(P.parent/'mannequin-muscle-atlas'));import muscle_atlas as atlas
weights=atlas.prepare(body)
regions={name:{'indices':np.flatnonzero(w>.001).tolist(),'weights':np.round(w[w>.001],4).tolist()} for name,w in weights.items()}
mapping=json.loads((P.parent/'mannequin-muscle-atlas/region-map.json').read_text())
(P/'runtime-muscles.json').write_text(json.dumps({'source_vertices':len(body.data.vertices),'source_index_attribute':'_SOURCE_INDEX','regions':regions,'mappings':mapping['mappings'],'notice':'Illustrative rest-vertex masks. Sharp render boundaries use the prepared texture atlas; vertex-only shading has lower spatial resolution.'},separators=(',',':'))+'\n')
attribute=body.data.attributes.get('_SOURCE_INDEX') or body.data.attributes.new(name='_SOURCE_INDEX',type='FLOAT',domain='POINT')
attribute.data.foreach_set('value',np.arange(len(body.data.vertices),dtype=np.float32))
# Export the original quad cage; 21,160 triangles, not the 84k render subdivision.
for modifier in body.modifiers:
    if modifier.type!='ARMATURE':modifier.show_viewport=False;modifier.show_render=False
rig.data.pose_position='REST';bpy.context.view_layer.update()
for image in bpy.data.images:
    if image.name.startswith('MuscleAtlas_'):
        image.scale(2048,1024);image.pack()
sys.path.insert(0,str(Path.home()/'.codex/skills/blender-asset-qa/scripts'));import qa_check
qa=qa_check.run(objects=[body.name],profile='game');assert qa['pass'],qa
(P/'runtime-asset-qa.json').write_text(json.dumps(qa,indent=2)+'\n')
sys.path.insert(0,str(Path.home()/'.codex/skills/blender-game-optimization/scripts'));import mesh_stats
stats=mesh_stats.run(objects=[body.name],budget='web')
(P/'runtime-budget.json').write_text(json.dumps(stats,indent=2)+'\n')
rig.data.pose_position='POSE';bpy.context.view_layer.update()
bpy.ops.object.select_all(action='DESELECT');body.select_set(True);rig.select_set(True);bpy.context.view_layer.objects.active=rig
bpy.ops.export_scene.gltf(filepath=str(P/'bodyweight-five.glb'),export_format='GLB',use_selection=True,
    export_yup=True,export_apply=False,export_texcoords=True,export_normals=True,
    export_materials='EXPORT',export_image_format='AUTO',export_vertex_color='NONE',export_attributes=True,
    export_animations=True,export_animation_mode='ACTIONS',export_force_sampling=True,
    export_frame_range=False,export_frame_step=1,export_anim_slide_to_zero=True,export_skins=True,export_influence_nb=4,
    export_def_bones=True,export_leaf_bone=False,export_rest_position_armature=True,
    export_extras=True,export_cameras=False,export_lights=False)
sys.path.insert(0,str(Path.home()/'.codex/skills/blender-export-pipelines/scripts'));import export_asset
summary=export_asset.glb_summary(str(P/'bodyweight-five.glb'))
assert summary['animations']==5,summary
assert summary['skins']==1 and summary['meshes']==1 and summary['tris']==21160,summary
summary['bytes']=(P/'bodyweight-five.glb').stat().st_size;summary['bone_count']=len(rig.data.bones)
(P/'runtime-export.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary))
