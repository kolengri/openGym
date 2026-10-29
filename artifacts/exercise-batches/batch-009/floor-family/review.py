"""Native peak solid/wire review and explicit common support plane evidence."""
from pathlib import Path
import sys
import bpy
from mathutils import Vector
F=Path(__file__).resolve().parent;ID=sys.argv[sys.argv.index('--')+1];P=F.parent/'assets'/ID
bpy.ops.wm.open_mainfile(filepath=str(P/'source.blend'));b=bpy.data.objects['SK_BlenderStudioHuman'];r=bpy.data.objects['RIG_BlenderStudioHuman'];s=bpy.context.scene
r.animation_data.action=bpy.data.actions['Exercise_'+ID];r.animation_data.action_slot=next(x for x in r.animation_data.action.slots if x.target_id_type=='OBJECT');s.frame_set(27);bpy.context.view_layer.update()
sys.path.insert(0,str(Path.home()/'.codex/skills/blender-asset-qa/scripts'));import review_shots
for mode in ['random','wire']:
    print(review_shots.run(objects=[b.name],out=str(P/f'qa-{mode}.png'),views=['right','top','three_quarter','bottom'],mode=mode,res=500))
if ID=='3204':
    # A transient diagnostic only: it is absent from source.blend and motion.glb.
    cam=s.camera;s.render.resolution_x=1100;s.render.resolution_y=650;s.render.film_transparent=True;s.render.engine='BLENDER_WORKBENCH';s.display.shading.light='STUDIO';s.display.shading.show_shadows=False;s.display.shading.show_cavity=False;s.display.shading.show_specular_highlight=False;s.display.shading.color_type='MATERIAL';s.display.shading.type='SOLID'
    for y in [-.8,-.6,-.4,-.2,0,.2,.4,.6,.8,1.,1.2]:
        c=bpy.data.curves.new('DiagnosticFloor','CURVE');c.dimensions='3D';c.bevel_depth=.001;c.bevel_resolution=0;sp=c.splines.new('POLY');sp.points.add(1);sp.points[0].co=(-.6,y,0,1);sp.points[1].co=(.6,y,0,1);ob=bpy.data.objects.new('DiagnosticFloor',c);s.collection.objects.link(ob)
    for x in [-.6,-.3,0,.3,.6]:
        c=bpy.data.curves.new('DiagnosticFloor','CURVE');c.dimensions='3D';c.bevel_depth=.001;c.bevel_resolution=0;sp=c.splines.new('POLY');sp.points.add(1);sp.points[0].co=(x,-.85,0,1);sp.points[1].co=(x,1.3,0,1);ob=bpy.data.objects.new('DiagnosticFloor',c);s.collection.objects.link(ob)
    for f,label in [(0,'start'),(72,'peak')]:
        s.frame_set(f+1);cam.data.type='ORTHO';cam.data.ortho_scale=2.8;cam.location=(4,.05,.90);cam.rotation_euler=(Vector((0,.05,.65))-cam.location).to_track_quat('-Z','Y').to_euler();s.render.filepath=str(P/f'support-plane-{label}.png');bpy.ops.render.render(write_still=True)
print('REVIEW_READY',ID)
