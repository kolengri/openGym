"""One source-indexed arms-forward squat shared by canonical IDs3948 and4714."""
from pathlib import Path
import sys,json,math,argparse
import bpy
import numpy as np
from mathutils import Vector,Matrix,Quaternion
P=Path(__file__).resolve().parent
sys.path.insert(0,str(P.parents[2]/'batch-003'))
import authoring as a
opts=argparse.ArgumentParser();opts.add_argument('--final',action='store_true');opts.add_argument('--no-proofs',action='store_true');o=opts.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
BINDING='227ede3fc31d1a2b47ff40f20a4a7288fe7bb36179add23bae953993826c8b7b'
assert a.initialize()==BINDING
body,rig,scene=a.body,a.rig,a.scene
sys.path.insert(0,str(P));import local_weights
weights=local_weights.apply(body);weights.update({"original_binding":BINDING,"new_binding":a.binding_hash(body,rig)})
(P/"local-weight-report.json").write_text(json.dumps(weights,indent=2)+"\n")
for m in body.modifiers:
 m.show_viewport=m.show_render=m.type=='ARMATURE'
 if m.type=='ARMATURE':m.use_deform_preserve_volume=False

def transported(name,parent,q,direction):
 base=q@a.rest[parent].to_quaternion().inverted()@a.rest[name].to_quaternion()
 return (base@Vector((0,1,0))).rotation_difference(direction.normalized())@base

def pose(t):
 q=.5-.5*math.cos(2*math.pi*t/5)
 root=Vector((0,.04+.26*q,.959-.504*q+.0002))
 d=a.torso(root,[22*q,24*q,20*q,10*q,4*q])
 for side,sign in [('Left',1),('Right',-1)]:
  # Keep the native pelvis/thigh rest frame; explicit forward pole chooses the
  # established two-joint IK branch. Knees open toward the modest toes-out.
  hip=d['Hips']@a.rest['Hips'].inverted()@a.heads[side+'UpLeg']
  fq=a.rz(-sign*8.8)
  ankle=Vector((sign*.20,.078,a.sole_height(side,fq)-.003+.0002))
  pole=hip+Vector((sign*.25,-1,0))
  knee,ankle=a.two_joint(hip,ankle,a.length[side+'UpLeg'],a.length[side+'Leg'],pole)
  uq=a.orient(side+'UpLeg',knee-hip)
  lq=transported(side+'Leg',side+'UpLeg',uq,ankle-knee)
  d[side+'UpLeg']=Matrix.Translation(hip)@uq.to_matrix().to_4x4()
  d[side+'Leg']=Matrix.Translation(knee)@lq.to_matrix().to_4x4()
  d[side+'Foot']=Matrix.Translation(ankle)@(fq@a.rest[side+'Foot'].to_quaternion()).to_matrix().to_4x4()
  d[side+'ToeBase']=d[side+'Foot']@a.rest[side+'Foot'].inverted()@a.rest[side+'ToeBase']
  sh=side+'Shoulder'
  shhead=d['Spine1']@a.rest['Spine1'].inverted()@a.heads[sh]
  # Clavicle follows chest; upper arms reach anteriorly with a small lateral
  # component. Wrist and fingers remain continuous with the forearm frame.
  d[sh]=Matrix.Translation(shhead)@(a.rx(20*q)@a.rest[sh].to_quaternion()).to_matrix().to_4x4()
  shoulder=d[sh]@a.rest[sh].inverted()@a.heads[side+'Arm']
  reach=math.sqrt(a.length[side+'Arm']**2+a.length[side+'ForeArm']**2+2*a.length[side+'Arm']*a.length[side+'ForeArm']*math.cos(math.radians(10)))
  wrist=shoulder+Vector((sign*.025,-math.cos(math.radians(30)),-math.sin(math.radians(30)))).normalized()*reach
  elbow,wrist=a.two_joint(shoulder,wrist,a.length[side+'Arm'],a.length[side+'ForeArm'],shoulder+Vector((sign*.3,0,-1)))
  aq=a.orient(side+'Arm',elbow-shoulder)
  bq=transported(side+'ForeArm',side+'Arm',aq,wrist-elbow)
  hq=bq@a.rest[side+'ForeArm'].to_quaternion().inverted()@a.rest[side+'Hand'].to_quaternion()
  d[side+'Arm']=Matrix.Translation(shoulder)@aq.to_matrix().to_4x4()
  d[side+'ForeArm']=Matrix.Translation(elbow)@bq.to_matrix().to_4x4()
  d[side+'Hand']=Matrix.Translation(wrist)@hq.to_matrix().to_4x4()
 for name,(head,tail,parent,digit,index) in a.finger_specs.items():
  sign=1 if name.startswith('Left') else -1
  axis=a.rest[name].to_3x3().inverted()@(tail-head).normalized().cross(Vector((-sign,0,0))).normalized()
  d[name]=d[parent]@a.rest[parent].inverted()@a.rest[name]@Quaternion(axis,math.radians([3,8,5][index])).to_matrix().to_4x4()
 for pb in rig.pose.bones:
  parent=pb.parent.name if pb.parent else None
  pb.matrix_basis=a.rest[pb.name].inverted()@(a.rest[parent]@d[parent].inverted() if parent else Matrix.Identity(4))@d[pb.name]
 bpy.context.view_layer.update()
 return q

scene.frame_start,scene.frame_end=1,151
rig.animation_data_create();act=bpy.data.actions.new('Exercise_3948');act.use_fake_user=True;rig.animation_data.action=act
for f in range(151):
 scene.frame_set(f+1);pose(f/30)
 for pb in rig.pose.bones:
  pb.keyframe_insert('location',frame=f+1);pb.keyframe_insert('rotation_quaternion',frame=f+1)
for layer in act.layers:
 for strip in layer.strips:
  for bag in strip.channelbags:
   for fc in bag.fcurves:
    for k in fc.keyframe_points:k.interpolation='LINEAR'
import joint_correctives
corrective_report=joint_correctives.install(body,rig,scene,act)
(P/'joint-corrective-report.json').write_text(json.dumps(corrective_report,indent=2)+'\n')
attr=body.data.attributes.get('_SOURCE_INDEX') or body.data.attributes.new('_SOURCE_INDEX','FLOAT','POINT');attr.data.foreach_set('value',np.arange(len(body.data.vertices),dtype=np.float32))
scene.render.engine='BLENDER_WORKBENCH';scene.render.resolution_x=700;scene.render.resolution_y=850;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA';scene.render.film_transparent=True
shade=scene.display.shading;shade.light='STUDIO';shade.color_type='MATERIAL';shade.show_shadows=False;shade.show_cavity=False;shade.show_specular_highlight=False
scene.view_settings.view_transform='Standard';scene.view_settings.look='None'
cd=bpy.data.cameras.new('ReviewCamera');cam=bpy.data.objects.new('ReviewCamera',cd);scene.collection.objects.link(cam);scene.camera=cam;cd.type='ORTHO'
CAMERAS=[{'label':'sagittal_90_degree','position':[5,0,1.0],'target':[0,0,1.0],'scale':2.6},{'label':'posterior_oblique_glutes','position':[3.8,5,2.0],'target':[0,0,.9],'scale':2.7}]
def render(name,f,pos,target=(0,0,.90),width=2.05,wire=False):
 scene.frame_set(f+1);cam.location=pos;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();cd.ortho_scale=width
 wo=None
 if wire:
  wo=body.copy();wo.data=body.data.copy();scene.collection.objects.link(wo);mat=bpy.data.materials.new('ReviewWire');mat.diffuse_color=(.015,.015,.015,1);wo.data.materials.clear();wo.data.materials.append(mat);wm=wo.modifiers.new('ReviewWire','WIREFRAME');wm.thickness=.00045;wm.offset=1
 scene.render.filepath=str(P/name);bpy.ops.render.render(write_still=True)
 if wo:
  me=wo.data;bpy.data.objects.remove(wo,do_unlink=True);bpy.data.meshes.remove(me)
if not o.no_proofs:
 for label,f in [('parallel',75)]:
  for v,pos in [('side',(5,0,.90)),('oblique',(3.8,-5,2)),('rear',(2.5,5,1.8))]:render('repair-low-arms-'+label+'-'+v+'.png',f,pos)
 render('parallel-wire.png',75,(3.8,-5,2),wire=True)
scene.frame_set(1);cam.location=CAMERAS[0]['position'];cam.rotation_euler=(Vector(CAMERAS[0]['target'])-cam.location).to_track_quat('-Z','Y').to_euler();cd.ortho_scale=2.05
bpy.ops.wm.save_as_mainfile(filepath=str(P/'source.blend'))
(P/'cameras.json').write_text(json.dumps(CAMERAS,indent=2)+'\n')
samples=[]
for f in [0,15,30,37,45,60,75,90,105,120,135,150]:
 scene.frame_set(f+1);bpy.context.view_layer.update();samples.append({'id':'3948','frame':f,'joints':{pb.name:list(rig.matrix_world@pb.head) for pb in rig.pose.bones}})
(P/'pose-samples.json').write_text(json.dumps(samples,indent=2)+'\n')
print('EARLY_PROOF_READY',P)
if o.final:
 scene.frame_set(1);bpy.ops.object.select_all(action='DESELECT');body.select_set(True);rig.select_set(True);bpy.context.view_layer.objects.active=rig
 result=bpy.ops.export_scene.gltf(filepath=str(P/'motion.glb'),export_format='GLB',use_selection=True,export_animations=True,export_animation_mode='ACTIONS',export_force_sampling=True,export_frame_range=True,export_frame_step=1,export_skins=True,export_all_influences=False,export_apply=False,export_attributes=True,export_materials='EXPORT',export_vertex_color='NONE',export_anim_slide_to_zero=True,export_rest_position_armature=True,export_influence_nb=4,export_cameras=False,export_lights=False,export_yup=True)
 assert result=={'FINISHED'}
