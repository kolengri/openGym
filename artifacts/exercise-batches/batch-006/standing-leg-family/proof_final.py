"""Small final neutral/wire diagnostic stills with actual action/surface readback."""
from pathlib import Path
import bpy,json,hashlib,sys,numpy as np
from mathutils import Vector
P=Path(__file__).resolve().parent;bpy.ops.wm.open_mainfile(filepath=str(P.parent/'assets/3479/source.blend'));b=bpy.data.objects['SK_BlenderStudioHuman'];r=bpy.data.objects['RIG_BlenderStudioHuman'];s=bpy.context.scene;s.render.resolution_x=600;s.render.resolution_y=720;s.render.resolution_percentage=100;s.render.film_transparent=True;s.display.shading.show_shadows=False;s.display.shading.show_cavity=False;s.display.shading.show_specular_highlight=False
sha=hashlib.sha256((P.parent/'assets/3479/source.blend').read_bytes()).hexdigest();glbsha=hashlib.sha256((P.parent/'assets/3479/motion.glb').read_bytes()).hexdigest()
def xyz():
 bpy.context.view_layer.update();ev=b.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh();X=np.array([ev.matrix_world@v.co for v in me.vertices]);ev.to_mesh_clear();return X
specs=[('3479',[('start',0),('squat',27),('full-stand',51),('support-transfer',59),('kick',71),('heel-contact',80),('mirror-contact',200),('return',231)]),('3480',[('start',0),('deep-left',37),('deep-right',112),('return',145)])]
for id,samples in (specs[:1] if '--only-3479' in sys.argv else specs):
 out=P.parent/'assets'/id;action=bpy.data.actions['Exercise_'+id];r.animation_data.action=action;keys=b.data.shape_keys;keys.animation_data.action=action;keys.animation_data.action_slot=next(x for x in action.slots if x.target_id_type=='KEY');native=json.loads((out/'surface-contact-report.json').read_text());poses=json.loads((out/'pose-samples.json').read_text());proofs=[]
 for label,f in samples:
  s.frame_set(f+1);bpy.context.view_layer.update();expected=next(x for x in poses if x['frame']==f);assert max(np.linalg.norm(np.array(pb.head)-expected['joints'][pb.name]) for pb in r.pose.bones)<1e-7;assert all(abs(keys.key_blocks[name].value-value)<1e-7 for name,value in native['samples'][f]['key_values'].items());before=xyz();bones={pb.name:np.array(pb.matrix) for pb in r.pose.bones};cam=s.camera;cam.location=(3.8,-5,2.3);target=Vector((0,.20 if id=='3480' else 0,.9));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=2.35 if id=='3479' else 2.25
  for mode in ['neutral','wire'] if label in ['heel-contact','deep-left'] else ['neutral']:
   wire=None
   if mode=='wire':
    wire=b.copy();wire.data=b.data;s.collection.objects.link(wire);m=wire.modifiers.new('DiagnosticThinWire','WIREFRAME');m.thickness=.00045;m.use_replace=True;wire.color=(.025,.025,.025,1);b.color=(.65,.67,.69,1);s.display.shading.color_type='OBJECT'
   else:s.display.shading.color_type='MATERIAL'
   file=out/('review-'+label+'-'+mode+'.png');s.render.filepath=str(file);bpy.ops.render.render(write_still=True)
   if wire:bpy.data.objects.remove(wire,do_unlink=True)
   assert np.max(abs(xyz()-before))==0;assert max(np.max(abs(np.array(pb.matrix)-bones[pb.name])) for pb in r.pose.bones)==0
   im=bpy.data.images.load(str(file),check_existing=False);pixels=np.empty(len(im.pixels),np.float32);im.pixels.foreach_get(pixels);alpha=pixels[3::4];assert alpha.min()==0 and alpha.max()==1;assert np.count_nonzero(alpha>.99)>1000;bpy.data.images.remove(im)
   proofs.append({'frame':f,'native_action':action.name,'key_values':native['samples'][f]['key_values'],'file':file.name,'sha256':hashlib.sha256(file.read_bytes()).hexdigest(),'mode':mode,'bone_matrix_delta_after_render':0,'skin_position_delta_after_render_m':0,'alpha_min':float(alpha.min()),'alpha_max':float(alpha.max()),'opaque_pixel_fraction':float((alpha>.99).mean())})
 (out/'proof-manifest.json').write_text(json.dumps({'source_sha256':sha,'glb_sha256':glbsha,'transparent_canvas':True,'neutral_body':True,'no_AO_or_body_shadows':True,'proofs':proofs},indent=2)+'\n')
print('FINAL_PROOFS_DONE')
