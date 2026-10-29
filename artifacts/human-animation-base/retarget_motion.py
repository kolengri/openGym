"""Retarget a real CMU capture to the CC0 Blender Studio human surface."""
import bpy,addon_utils,sys,json,math
from pathlib import Path
from mathutils import Vector,Matrix,Quaternion
P=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P/'professional-base.blend'))
body=bpy.data.objects['SK_BlenderStudioHuman']
addon_utils.enable('io_anim_bvh',default_set=False)
bpy.ops.import_anim.bvh(filepath=str(P/'13_30.bvh'),global_scale=.0564444444444,axis_forward='Z',axis_up='Y',rotate_mode='QUATERNION',update_scene_fps=True)
source=bpy.context.object;source.name='SOURCE_CMU_13_30';source.hide_render=True
start,end=1442,1712;steps=68
scene=bpy.context.scene;scene.frame_set(start);bpy.context.view_layer.update()
source_rest={b.name:(source.matrix_world@b.matrix_local) for b in source.data.bones}
def srcdir(name):
 b=source.data.bones[name];return (source.matrix_world.to_3x3()@(b.tail_local-b.head_local)).normalized()
def spos(name):return (source.matrix_world@source.pose.bones[name].matrix).translation
lateral=spos('LeftUpLeg')-spos('RightUpLeg');lateral.z=0;lateral.normalize();yaw=lateral.rotation_difference(Vector((1,0,0)))
origin=spos('Hips').copy()
# Joints fitted inside the supplied body's A-pose using its surface region bounds.
defs={'Hips':((0,.04,.96),(0,.035,1.075),None),'Spine':((0,.035,1.075),(0,.045,1.20),'Hips'),'Spine1':((0,.045,1.20),(0,.04,1.42),'Spine'),'Neck':((0,.04,1.42),(0,.02,1.555),'Spine1'),'Head':((0,.02,1.555),(0,.025,1.79),'Neck')}
for s,sign in [('Left',1),('Right',-1)]:
 def v(x,y,z):return(sign*x,y,z)
 defs.update({s+'Shoulder':((0,.04,1.42),v(.18,.035,1.43),'Spine1'),s+'Arm':(v(.18,.035,1.43),v(.325,.02,1.16),s+'Shoulder'),s+'ForeArm':(v(.325,.02,1.16),v(.397,-.027,.955),s+'Arm'),s+'Hand':(v(.397,-.027,.955),v(.448,-.085,.815),s+'ForeArm'),s+'UpLeg':(v(.105,.04,.93),v(.15,.035,.49),'Hips'),s+'Leg':(v(.15,.035,.49),v(.181,.078,.105),s+'UpLeg'),s+'Foot':(v(.181,.078,.105),v(.24,-.077,.026),s+'Leg'),s+'ToeBase':(v(.24,-.077,.026),v(.265,-.105,.015),s+'Foot')})
arm=bpy.data.armatures.new('HumanMotionSkeleton');rig=bpy.data.objects.new('RIG_BlenderStudioHuman',arm);scene.collection.objects.link(rig)
bpy.context.view_layer.objects.active=rig;rig.select_set(True);body.select_set(False);source.select_set(False);bpy.ops.object.mode_set(mode='EDIT')
for name,(a,b,parent) in defs.items():
 bone=arm.edit_bones.new(name);bone.head=a;bone.tail=b
 if parent:bone.parent=arm.edit_bones[parent]
 bone.use_connect=False
bpy.ops.object.mode_set(mode='OBJECT')
sys.path.insert(0,str(Path.home()/'.codex/skills/blender-character-rigging/scripts'));import bind_mesh
weights=bind_mesh.run(armature=rig.name,meshes=[body.name],method='auto',limit=4,clean=.005)
assert weights['meshes'][body.name]['unweighted_verts']==0,weights
# The base asset's authored region boundaries keep upper-back skin off arm bones.
regions=[set() for _ in body.data.vertices];face_set=body.data.attributes['.sculpt_face_set']
for face,region in zip(body.data.polygons,face_set.data):
 for index in face.vertices:regions[index].add(region.value)
clamped=0
for vertex,region in zip(body.data.vertices,regions):
 if 1 not in region or region.intersection({20,21}):continue
 keep={g.group:g.weight for g in vertex.groups if body.vertex_groups[g.group].name in {'Hips','Spine','Spine1','Neck','Head'}}
 if len(keep)==len(vertex.groups):continue
 if not keep:keep={body.vertex_groups['Spine1'].index:1.0}
 total=sum(keep.values())
 for index in [g.group for g in vertex.groups]:body.vertex_groups[index].remove([vertex.index])
 for index,value in keep.items():body.vertex_groups[index].add([vertex.index],value/total,'REPLACE')
 clamped+=1
armmod=next(m for m in body.modifiers if m.type=='ARMATURE');armmod.use_deform_preserve_volume=False
with bpy.context.temp_override(object=body,active_object=body):bpy.ops.object.modifier_move_to_index(modifier=armmod.name,index=0)
corrective=body.modifiers.new('JointSurfaceCorrective','CORRECTIVE_SMOOTH');corrective.factor=.5;corrective.iterations=5
with bpy.context.temp_override(object=body,active_object=body):bpy.ops.object.modifier_move_to_index(modifier=corrective.name,index=1)
rest={b.name:b.matrix_local.copy() for b in rig.data.bones};align={n:(Vector(defs[n][1])-Vector(defs[n][0])).normalized().rotation_difference(srcdir(n)) for n in defs}
source_leg=sum(source.data.bones['Left'+n].length for n in ['UpLeg','Leg']);target_leg=sum(rig.data.bones['Left'+n].length for n in ['UpLeg','Leg']);motion_scale=target_leg/source_leg
for pb in rig.pose.bones:pb.rotation_mode='QUATERNION'
scene.frame_set(end);bpy.context.view_layer.update();drift=yaw@(spos('Hips')-origin)*motion_scale;drift.z=0
footids={i for f in body.data.polygons if any(body.data.vertices[j].co.z<.10 for j in f.vertices) for i in f.vertices if body.data.vertices[i].co.z<.13}
multires=next(m for m in body.modifiers if m.type=='MULTIRES');multires.levels=0
first_rots=None;floor_shifts=[]
for i in range(steps+1):
 sf=start+i*(end-start)/steps;scene.frame_set(int(sf),subframe=sf%1);bpy.context.view_layer.update();u=i/steps;desired={};rotations={}
 for name in defs:
  sp=source.matrix_world@source.pose.bones[name].matrix
  if name=='Hips':
   leftRight=(spos('LeftUpLeg')-spos('RightUpLeg')).normalized();up=(spos('Spine')-spos('Hips')).normalized();back=up.cross(leftRight).normalized();leftRight=back.cross(up).normalized();anatomical=Matrix((leftRight,back,up)).transposed().to_quaternion();rotations[name]=yaw@anatomical@rest[name].to_quaternion()
  else:
   endpoints={'Spine':('Spine','Spine1'),'Spine1':('Spine1','Neck1'),'Neck':('Neck1','Head')}
   if name in endpoints:a,b=endpoints[name];direction=spos(b)-spos(a)
   elif name.endswith('Hand'):direction=spos(name+'Index1')-spos(name)
   else:direction=(source.matrix_world.to_3x3()@(source.pose.bones[name].tail-source.pose.bones[name].head))
   target_direction=(Vector(defs[name][1])-Vector(defs[name][0])).normalized()
   if name in {'Spine','Spine1'}:
    lateral=(spos('LeftArm')-spos('RightArm')).normalized() if name=='Spine1' else (spos('LeftUpLeg')-spos('RightUpLeg')).normalized();up=direction.normalized();back=up.cross(lateral).normalized();lateral=back.cross(up).normalized();rotations[name]=yaw@Matrix((lateral,back,up)).transposed().to_quaternion()@rest[name].to_quaternion()
   else:rotations[name]=target_direction.rotation_difference((yaw@direction).normalized())@rest[name].to_quaternion()
 if first_rots is None:first_rots={k:q.copy() for k,q in rotations.items()}
 for n in rotations:rotations[n]=first_rots[n].slerp(rotations[n],.82)
 # Match the ends of one captured repetition without changing its middle.
 blend=max(0,(u-.90)/.10);blend=blend*blend*(3-2*blend)
 for n in rotations:rotations[n]=rotations[n].slerp(first_rots[n],blend)
 root=Vector(defs['Hips'][0])+yaw@(spos('Hips')-origin)*motion_scale-drift*u
 if blend:root=root.lerp(Vector(defs['Hips'][0]),blend)
 for name in defs:
  parent=defs[name][2]
  head=root if parent is None else desired[parent]@rest[parent].inverted()@Vector(defs[name][0])
  desired[name]=Matrix.Translation(head)@rotations[name].to_matrix().to_4x4()
  basis=rest[name].inverted()@(rest[parent]@desired[parent].inverted() if parent else Matrix.Identity(4))@desired[name]
  rig.pose.bones[name].matrix_basis=basis
 bpy.context.view_layer.update();evaluated=body.evaluated_get(bpy.context.evaluated_depsgraph_get());floor=min(evaluated.data.vertices[j].co.z for j in footids)
 rig.pose.bones['Hips'].location+=rest['Hips'].to_3x3().inverted()@Vector((0,0,-floor));floor_shifts.append(float(floor))
 for pb in rig.pose.bones:pb.keyframe_insert('location',frame=i+1);pb.keyframe_insert('rotation_quaternion',frame=i+1)
rig.animation_data.action.name='CMU_13_30_Squat';source.hide_set(True);multires.levels=1;multires.render_levels=1
scene.render.fps=30;scene.frame_start=1;scene.frame_end=steps+1;scene.render.film_transparent=False;scene.display.shading.background_type='VIEWPORT';scene.display.shading.background_color=(.94,.955,.97)
scene.world.use_nodes=True;scene.world.node_tree.nodes.get('Background').inputs['Color'].default_value=(.94,.955,.97,1)
scene.camera.location=(6,0,1.0);scene.camera.rotation_euler=(Vector((0,0,.92))-scene.camera.location).to_track_quat('-Z','Y').to_euler();scene.camera.data.ortho_scale=2.15
scene.render.resolution_x=640;scene.render.resolution_y=640;scene.render.resolution_percentage=100
report={'source':'CMU subject13 capture30 / cgspeed BVH','source_frames':[start,end],'source_fps':120,'target_fps':30,'target_frames':steps+1,'motion_scale':motion_scale,'root_drift_removed_m':list(drift),'floor_shifts_m':floor_shifts,'binding':weights,'body_vertices':len(body.data.vertices),'bones':len(rig.data.bones),'upper_back_vertices_restricted_to_trunk':clamped,'source_pose':'T-pose','target_bind_pose':'A-pose','retarget':'Anatomical joint-direction retargeting with measured pelvis frame; captured joint excursion adapted to82% for this body and native linear skinning with corrective smoothing.'}
(P/'motion-build.json').write_text(json.dumps(report,indent=2));scene.frame_set(1);bpy.ops.wm.save_as_mainfile(filepath=str(P/'professional-motion.blend'))
for frame in [1,35,69]:
 scene.frame_set(frame);scene.render.filepath=str(P/f'proof-{frame:03d}.png');bpy.ops.render.render(write_still=True)
print(json.dumps({'status':'done','binding':weights,'motion_scale':motion_scale}))
