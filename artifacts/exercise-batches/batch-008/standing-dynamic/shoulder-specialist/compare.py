"""Same-camera native baseline/corrected upper-body proofs without saved changes."""
import sys
sys.dont_write_bytecode=True
import bpy,numpy as np,json,hashlib
from pathlib import Path
from mathutils import Vector
F=Path(__file__).resolve().parent;sys.path.insert(0,str(F));import corrective
bpy.ops.wm.open_mainfile(filepath=str(F/'foundation.blend'));b=bpy.data.objects['SK_BlenderStudioHuman'];r=bpy.data.objects['RIG_BlenderStudioHuman'];s=bpy.context.scene
for m in b.modifiers:
    m.show_viewport=m.show_render=m.type=='ARMATURE'
    if m.type=='ARMATURE':m.use_deform_preserve_volume=True
cam=s.camera;s.render.resolution_x=s.render.resolution_y=1100;s.render.engine='BLENDER_WORKBENCH';s.render.film_transparent=True;s.display.shading.light='STUDIO';s.display.shading.color_type='MATERIAL';s.display.shading.show_shadows=False;s.display.shading.show_cavity=False;s.display.shading.show_specular_highlight=False
views=[('front-oblique',[2.3,-4,1.75]),('back-oblique',[2.3,4,1.7]),('side',[4,-.1,1.5])]
def points():
    bpy.context.view_layer.update();e=b.evaluated_get(bpy.context.evaluated_depsgraph_get());me=e.to_mesh();p=np.array([v.co[:]for v in me.vertices]);e.to_mesh_clear();return p
rows=[];expected={}
for condition in ['baseline-v5','corrected']:
    if condition=='corrected':corrective.install(b,r,s)
    for f in [19,37.5,112.5]:
        corrective.select(b,r,'5172');s.frame_set(int(f)+1,subframe=f%1);bpy.context.view_layer.update();m=np.array([pb.matrix for pb in r.pose.bones]);p=points()
        if condition=='baseline-v5':expected[f]=(m,p)
        else:assert np.array_equal(m,expected[f][0])
        for label,pos in views:
            cam.location=pos;cam.rotation_euler=(Vector((0,-.08,1.22))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=1.80;s.render.filepath=str(F/f'compare-{condition}-{f:g}-{label}.png');before=points();bpy.ops.render.render(write_still=True);assert np.array_equal(before,points())
            rows.append({'condition':condition,'frame':f,'view':label,'file':Path(s.render.filepath).name,'same51_bone_matrices':True,'pre_post_render_skin_delta_m':0.})
(F/'comparison-report.json').write_text(json.dumps({'foundation_sha256':hashlib.sha256((F/'foundation.blend').read_bytes()).hexdigest(),'width_m':1.8,'target':[0,-.08,1.22],'proofs':rows},indent=2)+'\n')
print('COMPARISON_READY',len(rows))
