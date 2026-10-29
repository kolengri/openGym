"""Original CC0 left ulnar-deviation stretch, with a true articulated assist."""
import argparse,json,math,sys
from pathlib import Path
import bpy,numpy as np
from mathutils import Matrix,Quaternion,Vector
P=Path(__file__).resolve().parent
sys.path.insert(0,str(P.parents[2]/'batch-003'))
import authoring as a
EXPECTED='227ede3fc31d1a2b47ff40f20a4a7288fe7bb36179add23bae953993826c8b7b'
assert a.initialize()==EXPECTED
body,rig,scene=a.body,a.rig,a.scene
REST=np.array([v.co[:] for v in body.data.vertices])
for m in body.modifiers:
 m.show_viewport=m.show_render=m.type=='ARMATURE'
 if m.type=='ARMATURE':m.use_deform_preserve_volume=False

def smooth(x):return a.ease(x)
def amounts(t):
 e=t if t<=2.5 else 5-t
 return smooth(e/1.05),smooth((e-1.05)/.95)

def apply_chain(d,side,wrist,pole):
 sh=side+'Shoulder'
 d[sh]=a.rest[sh].copy()
 shoulder=a.heads[side+'Arm']
 elbow,wrist=a.two_joint(shoulder,wrist,a.length[side+'Arm'],a.length[side+'ForeArm'],pole)
 upper,lower=side+'Arm',side+'ForeArm'
 q=a.orient(upper,elbow-shoulder)
 d[upper]=Matrix.Translation(shoulder)@q.to_matrix().to_4x4()
 base=q@a.rest[upper].to_quaternion().inverted()@a.rest[lower].to_quaternion()
 current=base@a.V((0,1,0))
 qlow=current.rotation_difference((wrist-elbow).normalized())@base
 d[lower]=Matrix.Translation(elbow)@qlow.to_matrix().to_4x4()
 return wrist

def pose(t):
 reach,tilt=amounts(t)
 d={b:a.rest[b].copy() for b in a.rest}
 # 8 degree natural elbow flexion; shoulder and trunk remain down and quiet.
 target=a.V((-.100,-.405,1.375));sh=a.heads['LeftArm']
 target=sh+(target-sh).normalized()*(a.length['LeftArm']+a.length['LeftForeArm']-.001)
 Lw=apply_chain(d,'Left',target,a.V((.22,-.20,1.29)))
 theta=math.radians(18)*tilt
 Ldir=a.V((-.04,-math.cos(theta),-math.sin(theta))).normalized()
 Lnormal=a.V((-1,0,0))
 d['LeftHand']=Matrix.Translation(Lw)@a.orient('LeftHand',Ldir,Lnormal).to_matrix().to_4x4()
 # Approach the thumb-up left hand from the assisting side, then carry its tilt.
 Rw=a.V((-.240,-.485,1.483))+a.V((-.105,.12,.045))*(1-reach)
 Rw+=a.V((0,.004,-.035))*tilt
 Rw.y+=.020*(1-tilt)*reach
 Rw.z+=.100*max(0,math.sin(math.pi*reach))**.65+.006*(1-tilt)*reach
 Rw=apply_chain(d,'Right',Rw,a.V((-.40,-.19,1.28)))
 Rdir=a.V((.80,-.60,-.05)).normalized()
 d['RightHand']=Matrix.Translation(Rw)@a.orient('RightHand',Rdir,a.V((0,0,-1))).to_matrix().to_4x4()
 for name,(h,tail,parent,digit,index) in a.finger_specs.items():
  side='Left' if name.startswith('Left') else 'Right'
  palm=a.V((-1 if side=='Left' else 1,0,0))
  axis=a.rest[name].to_3x3().inverted()@(tail-h).normalized().cross(palm).normalized()
  angles=([0,0,0] if digit!='Thumb' else [0,0,0]) if side=='Left' else ([12+28*reach,15+33*reach,8+20*reach] if digit!='Thumb' else [-15*reach,-5*reach,0])
  if side=='Right' and digit not in ['Thumb','Index']:
   factor={'Middle':.80,'Ring':.62,'Little':.45}[digit]
   angles=[v*factor for v in angles]
  d[name]=d[parent]@a.rest[parent].inverted()@a.rest[name]@Quaternion(axis,math.radians(angles[index])).to_matrix().to_4x4()
  if name=='RightThumb1':
   mat=d[name];d[name]=Matrix.Translation(mat.translation)@a.rz(15*reach).to_matrix().to_4x4()@mat.to_3x3().to_4x4()
 for pb in rig.pose.bones:
  par=pb.parent.name if pb.parent else None
  pb.matrix_basis=a.rest[pb.name].inverted()@(a.rest[par]@d[par].inverted() if par else Matrix.Identity(4))@d[pb.name]
 bpy.context.view_layer.update()
 return d

scene.frame_start,scene.frame_end=1,151
rig.animation_data_create();act=bpy.data.actions.new('Exercise_2098');act.use_fake_user=True
rig.animation_data.action=act
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
attr.data.foreach_set('value',np.arange(len(body.data.vertices),dtype=np.float32))
assert a.binding_hash(body,rig)==EXPECTED
scene.render.engine='BLENDER_WORKBENCH';scene.render.resolution_x=800;scene.render.resolution_y=1000
scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA';scene.render.film_transparent=True
s=scene.display.shading;s.light='STUDIO';s.color_type='MATERIAL';s.show_shadows=False;s.show_cavity=False;s.show_specular_highlight=False
scene.view_settings.view_transform='Standard';scene.view_settings.look='None'
cd=bpy.data.cameras.new('ReviewCamera');cam=bpy.data.objects.new('ReviewCamera',cd);scene.collection.objects.link(cam);scene.camera=cam;cd.type='ORTHO'
CAMERAS=[{'label':'left_forearm_oblique','position':[3.1,-5.4,2.35],'target':[0,-.12,.90],'scale':2.8},{'label':'left_palm_profile','position':[-4,-.2,1.9],'target':[0,-.13,.90],'scale':2.8}]
def render(name,f,kind='oblique',wire=False):
 scene.frame_set(f+1)
 c=CAMERAS[0 if kind=='oblique' else 1];cam.location=c['position'];target=a.V(c['target']);cd.ortho_scale=2.0
 if kind=='side':cam.location=(-4,-.2,1.9)
 if kind=='rear':cam.location=(2.7,4.7,2.0)
 if kind=='hands':cam.location=(-1.8,-2.7,2.4);target=a.V((-.04,-.50,1.38));cd.ortho_scale=.43
 cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()
 ob=None
 if wire:
  ob=body.copy();ob.data=body.data.copy();scene.collection.objects.link(ob)
  mat=bpy.data.materials.new('ReviewWire');mat.diffuse_color=(.025,.025,.025,1);ob.data.materials.clear();ob.data.materials.append(mat)
  m=ob.modifiers.new('ReviewWire','WIREFRAME');m.thickness=.00055;m.offset=1
 scene.render.filepath=str(P/name);bpy.ops.render.render(write_still=True)
 if ob:
  mesh=ob.data;bpy.data.objects.remove(ob,do_unlink=True);bpy.data.meshes.remove(mesh)
for label,f in [('start',0),('entry',30),('hold',75)]:
 render('early-'+label+'-oblique.png',f)
 render('early-'+label+'-hands.png',f,'hands')
 if label!='hold':
  render('early-'+label+'-side.png',f,'side');render('early-'+label+'-rear.png',f,'rear')
render('early-hold-side.png',75,'side');render('early-hold-rear.png',75,'rear');render('early-hold-wire.png',75,'oblique',True)
scene.frame_set(1);bpy.ops.wm.save_as_mainfile(filepath=str(P/'source.blend'))
(P/'cameras.json').write_text(json.dumps(CAMERAS,indent=2)+'\n')
samples=[]
for f in [0,15,30,45,60,75,90,105,120,135,150]:
 scene.frame_set(f+1);bpy.context.view_layer.update();samples.append({'id':'2098','frame':f,'joints':{pb.name:list(rig.matrix_world@pb.head) for pb in rig.pose.bones}})
(P/'pose-samples.json').write_text(json.dumps(samples,indent=2)+'\n')
print('EARLY_PROOF_READY',P)
