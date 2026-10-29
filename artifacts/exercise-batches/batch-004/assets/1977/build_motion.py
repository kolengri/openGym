"""Original behind-back wrist-assisted shoulder stretch. No media input."""
from pathlib import Path
import argparse,hashlib,json,math,sys
import bpy
import numpy as np
from mathutils import Matrix,Quaternion,Vector
P=Path(__file__).resolve().parent
sys.path.insert(0,str(P.parents[2]/'batch-003'))
import authoring as a
parser=argparse.ArgumentParser();parser.add_argument('--final',action='store_true');parser.add_argument('--no-proofs',action='store_true')
opts=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
BINDING='227ede3fc31d1a2b47ff40f20a4a7288fe7bb36179add23bae953993826c8b7b'
assert a.initialize()==BINDING
body,rig,scene=a.body,a.rig,a.scene
sys.path.insert(0,str(P));import local_weights
weights=local_weights.apply(body);weights.update({'original_binding':BINDING,'new_binding':a.binding_hash(body,rig)})
(P/'local-weight-report.json').write_text(json.dumps(weights,indent=2)+'\n')

def transported(name,parent,q,direction):
 base=q@a.rest[parent].to_quaternion().inverted()@a.rest[name].to_quaternion()
 return (base@Vector((0,1,0))).rotation_difference(direction.normalized())@base

def stable_pole(side,amount,wrist):
 shoulder=a.heads[side+'Arm'];axis0=(a.heads[side+'Hand']-shoulder).normalized();axis=(wrist-shoulder).normalized()
 initial=a.heads[side+'ForeArm']-shoulder;initial=(initial-axis0*initial.dot(axis0)).normalized()
 endpoint=Vector((-.055,.265,1.025)) if side=='Left' else Vector((-.125,.329,1.115))
 end_axis=(endpoint-shoulder).normalized();end_base=axis0.rotation_difference(end_axis)@initial
 goal=Vector(((.05 if side=='Left' else -.17),.20,-.27));goal=(goal-end_axis*goal.dot(end_axis)).normalized()
 twist=math.atan2(end_axis.dot(end_base.cross(goal)),end_base.dot(goal))
 # Parallel-transport the original bend plane, then gradually apply the known
 # endpoint axial twist. This never projects an interpolated point through the
 # limb axis and retains the reviewed final lowered-elbow silhouette.
 bend=Quaternion(axis,twist*amount)@(axis0.rotation_difference(axis)@initial)
 return shoulder+bend

def active_solution(tau):
 u=a.ease(tau/1.0);pull=a.ease((tau-1.5)/.5)
 wrist=a.heads['LeftHand'].lerp(Vector((.05,.265,1.025)),u)
 medial=a.ease((u-.25)/.75);wrist.x=a.heads['LeftHand'].x*(1-medial)+.05*medial-.105*pull;wrist.y+=.12*math.sin(math.pi*u)
 shoulder=a.heads['LeftArm'];pole=stable_pole('Left',u,wrist)
 elbow,wrist=a.two_joint(shoulder,wrist,a.length['LeftArm'],a.length['LeftForeArm'],pole)
 uq=a.orient('LeftArm',elbow-shoulder);lq=transported('LeftForeArm','LeftArm',uq,wrist-elbow)
 return u,shoulder,elbow,wrist,uq,lq
HOLD_LOWER=active_solution(2.5)[-1]
HAND_GOAL=a.orient('RightHand',(.13,-.012,-.085),(0,-1,0))

def pose(t):
 tau=min(t,5-t);u,shoulder,elbow,active,uq,lq=active_solution(tau)
 v=a.ease((tau-.65)/.85);grip=a.ease((tau-1.20)/.30);orient_amount=a.ease(v*1.7)
 d={k:m.copy() for k,m in a.rest.items()}
 d['LeftArm']=Matrix.Translation(shoulder)@uq.to_matrix().to_4x4()
 d['LeftForeArm']=Matrix.Translation(elbow)@lq.to_matrix().to_4x4()
 hq=lq@a.rest['LeftForeArm'].to_quaternion().inverted()@a.rest['LeftHand'].to_quaternion()
 d['LeftHand']=Matrix.Translation(active)@hq.to_matrix().to_4x4()
 # Once acquired, the actual grasp is transported with the active forearm.
 # The rear approach arc reaches clearance before the hand moves medially.
 relative=lq@HOLD_LOWER.inverted();target=active+relative@Vector((-.070,.064,.090))
 wrist=a.heads['RightHand'].lerp(target,v);medial=a.ease((v-.35)/.50)
 wrist.x=a.heads['RightHand'].x*(1-medial)+target.x*medial;wrist.y+=.14*math.sin(math.pi*v);wrist.z+=.18*math.sin(math.pi*v)
 shoulder=a.heads['RightArm'];pole=stable_pole('Right',v,wrist)
 elbow,wrist=a.two_joint(shoulder,wrist,a.length['RightArm'],a.length['RightForeArm'],pole)
 original_upper=a.tails['RightArm']-a.heads['RightArm'];original_lower=a.tails['RightForeArm']-a.heads['RightForeArm']
 transport=(a.frame(elbow-shoulder,(elbow-shoulder).cross(wrist-elbow))@a.frame(original_upper,original_upper.cross(original_lower)).transposed()).to_quaternion()
 uq=transport@a.rest['RightArm'].to_quaternion();lq=transported('RightForeArm','RightArm',uq,wrist-elbow)
 hq=lq@a.rest['RightForeArm'].to_quaternion().inverted()@a.rest['RightHand'].to_quaternion();hq=hq.slerp(relative@HAND_GOAL,orient_amount)
 d['RightArm']=Matrix.Translation(shoulder)@uq.to_matrix().to_4x4();d['RightForeArm']=Matrix.Translation(elbow)@lq.to_matrix().to_4x4();d['RightHand']=Matrix.Translation(wrist)@hq.to_matrix().to_4x4()
 for name,(head,tail,parent,digit,index) in a.finger_specs.items():
  sign=1 if name.startswith('Left') else -1
  axis=(tail-head).normalized().cross(Vector((-sign,0,0))).normalized();local=a.rest[name].to_3x3().inverted()@axis
  if name.startswith('Right'):
   scale={'Index':.75,'Middle':.75,'Ring':.6,'Little':.5,'Thumb':.6}[digit]
   angle=([30,45,30][index] if digit!='Thumb' else [15,24,12][index])*grip*scale
  else:angle=[6,10,7][index]*u
  q=Quaternion(local,math.radians(angle))
  if name=='RightThumb1':
   axis=a.rest[name].to_3x3().inverted()@Vector((1,0,0));q=Quaternion(axis,math.radians(-60*orient_amount))@q
  d[name]=d[parent]@a.rest[parent].inverted()@a.rest[name]@q.to_matrix().to_4x4()
 for pb in rig.pose.bones:
  parent=pb.parent.name if pb.parent else None
  pb.matrix_basis=a.rest[pb.name].inverted()@(a.rest[parent]@d[parent].inverted() if parent else Matrix.Identity(4))@d[pb.name]
 bpy.context.view_layer.update()

scene.frame_start=1;scene.frame_end=151
rig.animation_data_create();act=bpy.data.actions.new('Exercise_1977');act.use_fake_user=True;rig.animation_data.action=act
for f in range(151):
 scene.frame_set(f+1);pose(f/30)
 for pb in rig.pose.bones:
  pb.keyframe_insert('location',frame=f+1);pb.keyframe_insert('rotation_quaternion',frame=f+1)
for layer in act.layers:
 for strip in layer.strips:
  for bag in strip.channelbags:
   for fc in bag.fcurves:
    for k in fc.keyframe_points:k.interpolation='LINEAR'
attr=body.data.attributes.get('_SOURCE_INDEX') or body.data.attributes.new('_SOURCE_INDEX','FLOAT','POINT')
attr.data.foreach_set('value',np.arange(10582,dtype=np.float32))
for m in body.modifiers:
 m.show_viewport=m.show_render=m.type=='ARMATURE'
 if m.type=='ARMATURE':m.use_deform_preserve_volume=False
assert a.binding_hash(body,rig)==weights['new_binding']
scene.render.engine='BLENDER_WORKBENCH';scene.render.resolution_x=700;scene.render.resolution_y=840;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA';scene.render.film_transparent=True
shade=scene.display.shading;shade.light='STUDIO';shade.color_type='MATERIAL';shade.show_shadows=False;shade.show_cavity=False;shade.show_specular_highlight=False
scene.view_settings.view_transform='Standard';scene.view_settings.look='None'
CAMERAS=[{'label':'posterior_wrist_grasp','position':[2.3,5,2.0],'target':[0,.06,.88],'scale':2.15}, {'label':'left_side_shoulder_extension','position':[5,.9,1.7],'target':[0,.06,.88],'scale':2.15}]
cams=[]
for i,spec in enumerate(CAMERAS):
 cd=bpy.data.cameras.new(spec['label']);c=bpy.data.objects.new(spec['label'],cd);scene.collection.objects.link(c);cd.type='ORTHO';cd.ortho_scale=spec['scale']/(scene.render.resolution_x/scene.render.resolution_y)
 c.location=spec['position'];c.rotation_euler=(Vector(spec['target'])-c.location).to_track_quat('-Z','Y').to_euler();cams.append(c)
scene.camera=cams[0]
def render(name,f,pos,target=(0,.06,.89),width=1.80,wire=False):
 scene.frame_set(f+1);cam=cams[0];cam.location=pos;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=width/(scene.render.resolution_x/scene.render.resolution_y)
 wo=None
 if wire:
  wo=body.copy();wo.data=body.data.copy();scene.collection.objects.link(wo);mat=bpy.data.materials.new('Proof_wire');mat.diffuse_color=(.02,.02,.02,1);wo.data.materials.clear();wo.data.materials.append(mat);mod=wo.modifiers.new('Proof_wire','WIREFRAME');mod.thickness=.0004;mod.offset=1
 scene.render.filepath=str(P/name);bpy.ops.render.render(write_still=True)
 if wo:
  mesh=wo.data;bpy.data.objects.remove(wo,do_unlink=True);bpy.data.meshes.remove(mesh)
if not opts.no_proofs:
 for phase,f in [('start',0),('entry',30),('hold',75)]:
  for label,pos in [('side',(5,0,1.6)),('oblique',(3.8,4,1.8)),('rear',(0,5,1.6))]:render(f'early-{phase}-{label}.png',f,pos)
 render('hold-grasp.png',75,(.8,5,1.5),(-.03,.24,1.10),.62)
 if opts.final:render('hold-wire.png',75,(3.8,4,1.8),wire=True)
for cam,spec in zip(cams,CAMERAS):
 cam.location=spec['position'];cam.rotation_euler=(Vector(spec['target'])-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=spec['scale']/(scene.render.resolution_x/scene.render.resolution_y)
scene.frame_set(1);scene.camera=cams[0];scene.render.fps=30
bpy.ops.wm.save_as_mainfile(filepath=str(P/'source.blend'))
if not opts.no_proofs:
 proof_files=sorted(P.glob('early-*.png'))+[P/'hold-grasp.png']+([P/'hold-wire.png'] if opts.final else [])
 (P/'native-proof-reference.json').write_text(json.dumps({'source_sha256':hashlib.sha256((P/'source.blend').read_bytes()).hexdigest(),'path':'Native Armature-only linear cage; no Smooth/Multires','files':{path.name:hashlib.sha256(path.read_bytes()).hexdigest() for path in proof_files}},indent=2)+'\n')
(P/'cameras.json').write_text(json.dumps(CAMERAS,indent=2)+'\n')
samples=[]
for f in [0,15,30,45,60,75,90,105,120,135,150]:
 scene.frame_set(f+1);bpy.context.view_layer.update();samples.append({'id':'1977','frame':f,'joints':{pb.name:list(rig.matrix_world@pb.head) for pb in rig.pose.bones}})
(P/'pose-samples.json').write_text(json.dumps(samples,indent=2)+'\n')
print('EARLY_PROOF_READY')
if opts.final:
 scene.frame_set(1);bpy.ops.object.select_all(action='DESELECT');body.select_set(True);rig.select_set(True);bpy.context.view_layer.objects.active=rig
 assert bpy.ops.export_scene.gltf(filepath=str(P/'motion.glb'),export_format='GLB',use_selection=True,export_animations=True,export_animation_mode='ACTIONS',export_force_sampling=True,export_frame_range=True,export_frame_step=1,export_skins=True,export_all_influences=False,export_apply=False,export_attributes=True,export_materials='EXPORT',export_vertex_color='NONE',export_anim_slide_to_zero=True,export_rest_position_armature=True,export_influence_nb=4,export_cameras=False,export_lights=False,export_yup=True)=={'FINISHED'}
