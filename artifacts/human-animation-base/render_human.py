"""Render a continuous professional human with surface muscle colors, not SVG body parts."""
import bpy,math,json,sys
import numpy as np
from pathlib import Path
P=Path(__file__).resolve().parent;bpy.ops.wm.open_mainfile(filepath=str(P/'professional-motion.blend'))
body=bpy.data.objects['SK_BlenderStudioHuman'];rig=bpy.data.objects['RIG_BlenderStudioHuman'];scene=bpy.context.scene
coords=np.asarray([v.co[:] for v in body.data.vertices]);x=np.abs(coords[:,0]);y=coords[:,1];z=coords[:,2]
def ell(cx,cy,cz,rx,ry,rz):return np.exp(-2*(((x-cx)/rx)**2+((y-cy)/ry)**2+((z-cz)/rz)**2))
quad=np.maximum.reduce([ell(.15,-.050,.69,.075,.080,.16),ell(.19,.005,.69,.05,.07,.14),ell(.09,-.035,.56,.045,.06,.065)])
glute=ell(.115,.115,.925,.105,.075,.11)
core=ell(0,-.105,1.19,.13,.065,.16)
calf=ell(.18,.12,.28,.075,.075,.17)*.3
quad*=((z>.51)&(z<.875)&(y<.045))
glute*=((z>.83)&(z<1.015)&(y>.075))
oblique=.9*ell(.135,-.005,1.165,.065,.085,.145)
primary=np.maximum(quad,glute);secondary=np.maximum.reduce([core,oblique,calf])
def smooth_mask(values,lo,hi):
 t=np.clip((values-lo)/(hi-lo),0,1);return t*t*(3-2*t)
primary=smooth_mask(primary,.10,.42);secondary=smooth_mask(secondary,.08,.44)
base=np.tile(np.array([.55,.63,.70]),(len(coords),1));arm_region=(x>.22)&(z>.78)&(z<1.48);base[arm_region]=[.72,.79,.84]
attribute=body.data.color_attributes.get('WorkingMuscles') or body.data.color_attributes.new(name='WorkingMuscles',type='FLOAT_COLOR',domain='POINT');body.data.color_attributes.active_color=attribute
scene.display.shading.color_type='VERTEX';scene.display.shading.light='STUDIO';scene.display.shading.show_shadows=True;scene.display.shading.cavity_type='BOTH';scene.display.shading.curvature_ridge_factor=1.0;scene.display.shading.curvature_valley_factor=.8;scene.display.shading.show_specular_highlight=False
scene.render.film_transparent=False;scene.view_settings.view_transform='Standard';scene.view_settings.look='None';scene.view_settings.exposure=0;scene.view_settings.gamma=1
# Use the requested strict profile, with a stable orthographic camera.
scene.camera.location=(6,0,1.0);scene.camera.data.ortho_scale=2.05
out=P/'human-frames';out.mkdir(exist_ok=True)
frames=scene.frame_end-scene.frame_start
for frame in range(scene.frame_start,scene.frame_end):
 scene.frame_set(frame);phase=(frame-scene.frame_start)/frames;load=.72+.23*math.sin(math.pi*phase)**2
 colors=base.copy();w=np.clip(secondary*.95,0,1)[:,None];colors=colors*(1-w)+np.array([.91,.57,.13])*w
 w=np.clip(primary*load*1.10,0,.98)[:,None];colors=colors*(1-w)+np.array([.87,.12,.07])*w
 rgba=np.column_stack([colors,np.ones(len(colors))]).astype(np.float32);attribute.data.foreach_set('color',rgba.ravel());body.data.update()
 scene.render.filepath=str(out/f'{frame-1:04d}.png');bpy.ops.render.render(write_still=True)
 if frame in [1,35]:
  bpy.data.images['Render Result'].save_render(str(P/f'highlight-{frame:03d}.png'))
scene.frame_set(1);bpy.ops.wm.save_as_mainfile(filepath=str(P/'human-highlight.blend'))
(P/'render-report.json').write_text(json.dumps({'renderer':'Blender Workbench','frames':frames,'fps':30,'duration':frames/30,'width':640,'height':640,'camera':'strict sagittal orthographic','body':'Blender Studio Human Base Meshes realistic male / CC0','motion':'CMU13_30,12.0–14.25s,retargeted; joint excursion adapted to82%','highlight':'Illustrative surface color fields on the continuous mesh, with source sculpted muscle anatomy retained.'},indent=2))
