"""Local copied foundation proof; never invokes author pipeline mutations."""
import sys
sys.dont_write_bytecode=True
import bpy,numpy as np,json,hashlib
from pathlib import Path
from mathutils import Vector
F=Path(__file__).resolve().parent;sys.path[:0]=[str(F),str(F.parent)]
from self_clearance import SelfClearance
import corrective
bpy.ops.wm.open_mainfile(filepath=str(F/'foundation.blend'));b=bpy.data.objects['SK_BlenderStudioHuman'];r=bpy.data.objects['RIG_BlenderStudioHuman'];s=bpy.context.scene
for m in b.modifiers:
    m.show_viewport=m.show_render=m.type=='ARMATURE'
    if m.type=='ARMATURE':m.use_deform_preserve_volume=True
clear=SelfClearance(b,r)
def points():
    bpy.context.view_layer.update();e=b.evaluated_get(bpy.context.evaluated_depsgraph_get());me=e.to_mesh();p=np.array([v.co[:]for v in me.vertices]);e.to_mesh_clear();return p
corrective.install(b,r,s);rows=[];cam=s.camera;s.render.resolution_x=s.render.resolution_y=1000
s.render.engine='BLENDER_WORKBENCH';s.render.film_transparent=True;s.display.shading.light='STUDIO';s.display.shading.color_type='MATERIAL';s.display.shading.show_shadows=False;s.display.shading.show_cavity=False;s.display.shading.show_specular_highlight=False
views=[('front-oblique',[2.3,-4,1.75],[0,-.05,1.34],1.15),('back-oblique',[2.3,4,1.7],[0,-.02,1.34],1.15)]
for f in [19,37.5,112.5]:
    corrective.select(b,r,'5172');s.frame_set(int(f)+1,subframe=f%1);p=points();m,fail=clear.sample(p)
    rows.append({'frame':f,'metrics':m,'failures':fail,'key_weights':[b.data.shape_keys.key_blocks[name].value for name,_ in corrective.STATES]})
    print('CONTACT',f,fail,flush=True)
    for label,pos,target,width in views:
        cam.location=pos;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=width;s.render.filepath=str(F/f'proof-{f:g}-{label}.png');before=points();bpy.ops.render.render(write_still=True);assert np.array_equal(points(),before)
(F/'preview-report.json').write_text(json.dumps(rows,indent=2)+'\n')
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(F/'candidate.blend'))
