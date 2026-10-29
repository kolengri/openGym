"""Author1843 on the exact accepted1368 seated surface and binding."""
from pathlib import Path
import bpy,sys,json,hashlib,numpy as np,argparse
from mathutils import Matrix,Vector
sys.dont_write_bytecode=True
F=Path(__file__).resolve().parent;B=F.parent;W=F.parents[3];P=B/'assets/1843';OLD=W/'artifacts/exercise-batches/batch-007/assets/1368/source.blend'
sys.path[:0]=[str(F),str(W/'artifacts/exercise-batches/batch-003')]
import authoring as a,motion
ap=argparse.ArgumentParser();ap.add_argument('--final',action='store_true');args=ap.parse_args(sys.argv[sys.argv.index('--')+1:]if'--'in sys.argv else[])
a.initialize();bpy.ops.wm.open_mainfile(filepath=str(OLD));a.body=b=bpy.data.objects['SK_BlenderStudioHuman'];a.rig=r=bpy.data.objects['RIG_BlenderStudioHuman'];a.scene=s=bpy.context.scene;r.animation_data.action=bpy.data.actions['Exercise_1368'];s.frame_set(1);bpy.context.view_layer.update();motion.install(a);binding=a.binding_hash(b,r)
r.animation_data_clear()
for act in list(bpy.data.actions):bpy.data.actions.remove(act)
act=bpy.data.actions.new('Exercise_1843');act.use_fake_user=True;r.animation_data_create();previous={};slot=None;expected={}
for f in range(151)if args.final else range(0,151,5):
 r.animation_data.action=None;s.frame_set(f+1);d=motion.pose(a,f/30)
 # Keep desired world transforms rigid before local decomposition. Repeated
 # float inverse products in digit chains can otherwise accumulate shear.
 d={n:Matrix.Translation(m.translation)@m.to_quaternion().normalized().to_matrix().to_4x4()for n,m in d.items()}
 for pb in r.pose.bones:
  par=pb.parent.name if pb.parent else None;local=np.linalg.inv(np.array(a.rest[pb.name],float))@(np.array(a.rest[par],float)@np.linalg.inv(np.array(d[par],float))if par else np.eye(4))@np.array(d[pb.name],float);basis=Matrix(local.tolist());pb.location=basis.translation;pb.rotation_quaternion=basis.to_quaternion().normalized();pb.scale=(1,1,1)
 bpy.context.view_layer.update();err=max(np.max(abs(np.array(r.pose.bones[n].matrix)-np.array(m)))for n,m in d.items());assert err<2e-6,(f,err,max(d,key=lambda n:np.max(abs(np.array(r.pose.bones[n].matrix)-np.array(d[n])))));expected[f]=np.array([pb.matrix for pb in r.pose.bones]);r.animation_data.action=act
 if slot:r.animation_data.action_slot=slot
 for pb in r.pose.bones:
  pb.rotation_mode='QUATERNION'
  if pb.name in previous and pb.rotation_quaternion.dot(previous[pb.name])<0:pb.rotation_quaternion.negate()
  previous[pb.name]=pb.rotation_quaternion.copy();pb.keyframe_insert('location',frame=f+1);pb.keyframe_insert('rotation_quaternion',frame=f+1)
 slot=r.animation_data.action_slot
for layer in act.layers:
 for strip in layer.strips:
  for bag in strip.channelbags:
   for curve in bag.fcurves:
    for key in curve.keyframe_points:key.interpolation='LINEAR'
for f,target in expected.items():s.frame_set(f+1);bpy.context.view_layer.update();assert np.max(abs(np.array([pb.matrix for pb in r.pose.bones])-target))<3e-6
s.frame_start=1;s.frame_end=151;s.render.fps=30;s.frame_set(1);bpy.context.preferences.filepaths.save_version=0
s.render.engine='BLENDER_WORKBENCH';s.render.resolution_x=800;s.render.resolution_y=800;s.render.resolution_percentage=100;s.render.film_transparent=False;s.world.color=(.09,.09,.09);s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGBA';sh=s.display.shading;sh.light='STUDIO';sh.color_type='MATERIAL';sh.show_shadows=False;sh.show_cavity=False;sh.show_specular_highlight=False;s.view_settings.view_transform='Standard';s.view_settings.look='None'
cam=s.camera
views=[{'label':'Whole-body chin oblique','position':[3.4,-4.8,2.05],'target':[0,-.32,.48],'scale':1.55},{'label':'Whole-body occiput oblique','position':[-3.5,3.6,1.9],'target':[0,-.30,.48],'scale':1.6}]
for c in views:
 cam.location=c['position'];cam.rotation_euler=(Vector(c['target'])-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=c['scale']
 for label,f in [('start',0),('turn',25),('approach',45),('held',75),('return',120)]:
  s.frame_set(f+1);s.render.filepath=str(P/f'early-{label}-{views.index(c)+1}.png');bpy.ops.render.render(write_still=True)
s.frame_set(1);bpy.ops.wm.save_as_mainfile(filepath=str(P/'source.blend'));assert a.binding_hash(b,r)==binding
(P/'cameras.json').write_text(json.dumps(views,indent=2)+'\n');(F/'keying-receipt.json').write_text(json.dumps({'source_sha256':hashlib.sha256((P/'source.blend').read_bytes()).hexdigest(),'accepted_seated_source':str(OLD.relative_to(W)),'accepted_seated_source_sha256':hashlib.sha256(OLD.read_bytes()).hexdigest(),'binding_sha256':binding,'binding_changed':False,'base_lower_body_matrices':{n:[list(row)for row in m]for n,m in motion.BASE.items()if n.startswith(('Hips','LeftUpLeg','LeftLeg','LeftFoot','LeftToeBase','RightUpLeg','RightLeg','RightFoot','RightToeBase'))},'authored_head_turn_degrees':32,'whole_cycle_keyframes':len(expected),'native_frame_origin':1},indent=2)+'\n')
