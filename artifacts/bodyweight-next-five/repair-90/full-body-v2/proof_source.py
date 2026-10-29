"""Curated source QA stills at four distinct acceptance poses, not a playblast."""
import bpy,json,sys,hashlib
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent;bpy.ops.wm.open_mainfile(filepath=str(P/'source.blend'))
body=bpy.data.objects['SK_BlenderStudioHuman'];rig=bpy.data.objects['RIG_BlenderStudioHuman'];keys=body.data.shape_keys;scene=bpy.context.scene
assert all(m.show_render==(m.type=='ARMATURE') for m in body.modifiers)
scene.render.engine='BLENDER_WORKBENCH';scene.render.resolution_x=900;scene.render.resolution_y=900;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.render.film_transparent=True;scene.view_settings.view_transform='Standard'
s=scene.display.shading;s.light='STUDIO';s.color_type='MATERIAL';s.show_shadows=False;s.show_cavity=False;s.show_specular_highlight=False
cd=bpy.data.cameras.new('CuratedSourceProof');cam=bpy.data.objects.new('CuratedSourceProof',cd);scene.collection.objects.link(cam);scene.camera=cam;cd.type='ORTHO'
mesh=bpy.data.meshes.new('QA_Floor');verts=[];faces=[]
for y in range(-9,10):
 for x in range(-9,10):
  i=len(verts);verts.extend([(x*.12,y*.12,-.003),((x+1)*.12,y*.12,-.003),((x+1)*.12,(y+1)*.12,-.003),(x*.12,(y+1)*.12,-.003)]);faces.append((i,i+1,i+2,i+3))
mesh.from_pydata(verts,[],faces);floor=bpy.data.objects.new('QA_Floor_Not_Exported',mesh);scene.collection.objects.link(floor)
for value in [.18,.24]:
 material=bpy.data.materials.new('QA_Floor'+str(value));material.diffuse_color=(value,value,value,1);mesh.materials.append(material)
for i,p in enumerate(mesh.polygons):p.material_index=((i//19)+(i%19))%2
out=P/'proof';out.mkdir(exist_ok=True);receipts=[]
for identifier in ['10565','6560']:
 action=bpy.data.actions['Exercise_'+identifier];rig.animation_data.action=action;rig.animation_data.action_slot=next(v for v in action.slots if v.target_id_type=='OBJECT');keys.animation_data.action=action;keys.animation_data.action_slot=next(v for v in action.slots if v.target_id_type=='KEY')
 for frame,label in [(0,'start'),(30,'entry'),(75,'hinge'),(120,'return')]:
  scene.frame_set(frame+1);bpy.context.view_layer.update()
  for view,pos in [('oblique',(-3.4,-5,2.7)),('side',(5,0,.75)),('rear',(-1.5,5,1.5))]:
   cd.ortho_scale=1.70;cam.location=pos;cam.rotation_euler=(Vector((0,-.03,.44))-cam.location).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(out/f'{identifier}-{label}-{view}.png');bpy.ops.render.render(write_still=True)
   receipts.append({'file':Path(scene.render.filepath).name,'id':identifier,'frame':frame,'view':view})
  if label in ['start','hinge']:
   cd.ortho_scale=1.03;cam.location=(1.1,-3,1.8);cam.rotation_euler=(Vector((0,-.31,.19))-cam.location).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(out/f'{identifier}-{label}-hands.png');bpy.ops.render.render(write_still=True)
  if label=='hinge':
   ev=body.evaluated_get(bpy.context.evaluated_depsgraph_get());wiremesh=bpy.data.meshes.new_from_object(ev);wire=bpy.data.objects.new('QA_Wire_Cage',wiremesh);scene.collection.objects.link(wire);wire.data.materials.clear();mat=bpy.data.materials.new('QA_Wire');mat.diffuse_color=(.025,.035,.045,1);wire.data.materials.append(mat);wm=wire.modifiers.new('QA_Wire','WIREFRAME');wm.thickness=.0007;wm.use_replace=True;body.hide_render=True
   cd.ortho_scale=1.70;cam.location=(-3.4,-5,2.7);cam.rotation_euler=(Vector((0,-.03,.44))-cam.location).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(out/f'{identifier}-hinge-wire.png');bpy.ops.render.render(write_still=True);body.hide_render=False;bpy.data.objects.remove(wire,do_unlink=True)
(out/'receipts.json').write_text(json.dumps({'source':'../source.blend','source_sha256':hashlib.sha256((P/'source.blend').read_bytes()).hexdigest(),'only_armature_and_morphs':True,'no_source_smooth_subdivision_shadows_AO':True,'floor_only_in_temporary_QA_scene':True,'stills':receipts},indent=2)+'\n')
