import bpy,json,sys,numpy as np
from pathlib import Path
P=Path(__file__).resolve().parent
sys.path.insert(0,'/Users/kolengri/.codex/skills/blender-asset-qa/scripts')
import qa_check,review_shots
body=bpy.data.objects['SK_BlenderStudioHuman']
r=qa_check.run(objects=[body.name],profile='render',no_modifiers=True)
# Attribute-only atlas does not change the source's UVs/geometry; source original
# UVMap is UDIM and the atlas adds one ordinary normalized render UV map.
r['accepted_warnings']={}
for warning in r.get('warnings',[]):
 if 'UV' in warning or 'uv' in warning:r['accepted_warnings'][warning]='The preserved original UVMap is a 9x4 UDIM layout; MuscleAtlasUV is the normalized render map.'
(P/'asset-qa.json').write_text(json.dumps(r,indent=2))
image=next(i for i in bpy.data.images if i.name.startswith('MuscleAtlas_SK'))
assert image.packed_file is not None
assert tuple(image.size)==(4096,2048)
assert body.data.uv_layers.get('UVMap') and body.data.uv_layers.get('MuscleAtlasUV')
assert len(body.data.vertices)==10582
pixels=np.empty(len(image.pixels),np.float32);image.pixels.foreach_get(pixels)
assert np.all(pixels.reshape(-1,4)[:,:3]==pixels[:3])
colors=np.empty((len(body.data.vertices),4),np.float32)
body.data.color_attributes['MuscleAtlas'].data.foreach_get('color',colors.ravel())
assert np.all(colors[:,:3]==colors[0,:3])
assert not any(n.type=='BUMP' for m in body.data.materials if m and m.node_tree for n in m.node_tree.nodes)
del pixels,colors
report={'packed_texture':True,'texture_size':list(image.size),'base_vertices':len(body.data.vertices),'polygons':len(body.data.polygons),'material_count':len(body.data.materials),'object_dimensions':list(body.dimensions),'uv_maps':[u.name for u in body.data.uv_layers],'qa_pass':r['pass']}
report.update({'neutral_packed_texture_uniform':True,'neutral_vertex_colors_uniform':True,'global_shader_bump':False})
(P/'readback.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
review_shots.run(objects=[body.name],out=str(P/'wire-review.png'),views=['front','right','back'],mode='wire',res=384)
