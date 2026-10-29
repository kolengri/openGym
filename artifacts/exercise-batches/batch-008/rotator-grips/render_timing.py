"""New timing-transition proofs only; accepted held poses are not rerendered."""
import bpy,sys,json,hashlib,numpy as np,math
from pathlib import Path
from mathutils import Vector
sys.dont_write_bytecode=True
F=Path(__file__).resolve().parent;P=F.parent/'assets/1986';bpy.ops.wm.open_mainfile(filepath=str(P/'source.blend'));b=bpy.data.objects['SK_BlenderStudioHuman'];r=bpy.data.objects['RIG_BlenderStudioHuman'];s=bpy.context.scene;r.animation_data.action=bpy.data.actions['Exercise_1986'];r.animation_data.action_slot=r.animation_data.action.slots[0];comparison=json.loads((F/'timing-comparison.json').read_text());after=comparison['after'];frames=sorted({after['maximum_major_joint_step']['frame'],after['maximum_joint_step']['frame'],after['maxima']['Left_whole_hand']['maximum_speed_frame'],after['maxima']['Right_whole_hand']['maximum_speed_frame'],46,47});views=json.loads((P/'cameras.json').read_text());s.render.engine='BLENDER_WORKBENCH';s.render.resolution_x=700;s.render.resolution_y=840;s.render.resolution_percentage=100;s.render.film_transparent=True;s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGBA';shade=s.display.shading;shade.light='STUDIO';shade.color_type='MATERIAL';shade.show_shadows=False;shade.show_cavity=False;shade.show_specular_highlight=False;cam=s.camera;cam.data.type='ORTHO';proofs=[]
def points():
 bpy.context.view_layer.update();e=b.evaluated_get(bpy.context.evaluated_depsgraph_get());me=e.to_mesh();p=np.array([v.co[:]for v in me.vertices]);e.to_mesh_clear();return p
for f in frames+[120]:
 s.frame_set(f+1);bpy.context.view_layer.update()
 for view in views:
  cam.location=view['position'];cam.rotation_euler=(Vector(view['target'])-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=view['scale']/(700/840);before=points();bones=np.array([pb.matrix for pb in r.pose.bones]);name=f'timing-f{f:03}-{view["label"]}.png'if f!=120 else'early-release-'+view['label']+'.png';s.render.filepath=str(P/name);bpy.ops.render.render(write_still=True);assert np.array_equal(before,points());assert np.array_equal(bones,np.array([pb.matrix for pb in r.pose.bones]));proofs.append({'frame':f,'seconds':f/30,'file':name,'sha256':hashlib.sha256((P/name).read_bytes()).hexdigest(),'pre_post_skin_delta_m':0})
f=after['maximum_joint_step']['frame'];finger=[];previous={};gn={g.index:g.name for g in b.vertex_groups};idx=np.array([v.index for v in b.data.vertices if sum(g.weight for g in v.groups if gn[g.group]=='RightLittle3')>.95],int)
for frame in range(f-2,f+2):
 s.frame_set(frame+1);bpy.context.view_layer.update();p=points();row={'frame':frame,'seconds':frame/30,'actual_right_little3_skin_centroid':p[idx].mean(0).tolist(),'head':list(r.pose.bones['RightLittle3'].head),'tail':list(r.pose.bones['RightLittle3'].tail),'local_step_degrees':{}}
 for name in['RightHand','RightLittle1','RightLittle2','RightLittle3']:
  q=r.pose.bones[name].rotation_quaternion.copy()
  if name in previous:
   angle=math.degrees(previous[name].rotation_difference(q).angle);row['local_step_degrees'][name]=min(angle,360-angle)
  previous[name]=q
 finger.append(row)
s.frame_set(f+1);cam.location=(1.2,4,1.9);target=(r.pose.bones['RightHand'].head+r.pose.bones['LeftForeArm'].head)/2;cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=.58/(700/840);before=points();name=f'timing-f{f:03}-finger-detail.png';s.render.filepath=str(P/name);bpy.ops.render.render(write_still=True);assert np.array_equal(before,points());proofs.append({'frame':f,'seconds':f/30,'file':name,'sha256':hashlib.sha256((P/name).read_bytes()).hexdigest(),'pre_post_skin_delta_m':0});report={'source_sha256':hashlib.sha256((P/'source.blend').read_bytes()).hexdigest(),'scope':'Only newly timed critical transitions plus updated release. Held/start poses unchanged and not rerendered.','proofs':proofs,'distal_finger_diagnostic':finger,'recommended_entry_gpu_frames':sorted(set(frames+[x-1 for x in frames])),'recommended_return_gpu_frames':sorted({150-x for x in frames}|{151-x for x in frames})};(P/'timing-proof-receipt.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
