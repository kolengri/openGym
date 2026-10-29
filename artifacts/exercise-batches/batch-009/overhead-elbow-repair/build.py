"""Save a new independent1986 authoring file with unchanged accepted binding."""
import bpy,sys,json,hashlib,argparse,numpy as np
from pathlib import Path
from mathutils import Vector
sys.dont_write_bytecode=True
F=Path(__file__).resolve().parent;B=F.parent;W=F.parents[3];P=B/'assets/1986'
sys.path[:0]=[str(F),str(W/'artifacts/exercise-batches/batch-003')]
import authoring as a,motion
ap=argparse.ArgumentParser();ap.add_argument('--final',action='store_true');ap.add_argument('--dense-early',action='store_true');args=ap.parse_args(sys.argv[sys.argv.index('--')+1:]if'--'in sys.argv else[])
a.initialize();bpy.ops.wm.open_mainfile(filepath=str(W/'artifacts/exercise-batches/batch-008/assets/1986/source.blend'));a.body=b=bpy.data.objects['SK_BlenderStudioHuman'];a.rig=r=bpy.data.objects['RIG_BlenderStudioHuman'];a.scene=s=bpy.context.scene;r.animation_data_clear()
for action in list(bpy.data.actions):bpy.data.actions.remove(action)
action=bpy.data.actions.new('Exercise_1986');action.use_fake_user=True;r.animation_data_create();slot=None;previous={};witness=[];expected={};soles={side:np.array([v.index for v in b.data.vertices if v.co.z<.10 and sum(g.weight for g in v.groups if b.vertex_groups[g.group].name in[side+'Foot',side+'ToeBase'])>.5],int)for side in ['Left','Right']}
def points():
 bpy.context.view_layer.update();e=b.evaluated_get(bpy.context.evaluated_depsgraph_get());me=e.to_mesh();p=np.array([v.co[:]for v in me.vertices]);e.to_mesh_clear();return p
frames=list(range(151))if args.final or args.dense_early else list(range(0,151,5))
for f in frames:
 r.animation_data.action=None;s.frame_set(f+1);desired,state=motion.pose(a,'1986',f);p=points();offsets={side:.001-float(p[idx,2].min())for side,idx in soles.items()};desired,state=motion.pose(a,'1986',f,offsets);p=points();err=max(float(np.max(abs(np.array(r.pose.bones[n].matrix)-np.array(m))))for n,m in desired.items());assert err<2e-6,err;expected[f]=np.array([pb.matrix for pb in r.pose.bones]);state.update(ground_offsets_m=offsets,maximum_actual_matrix_error=err);witness.append(state);r.animation_data.action=action
 if slot:r.animation_data.action_slot=slot
 for pb in r.pose.bones:
  if pb.name in previous and pb.rotation_quaternion.dot(previous[pb.name])<0:pb.rotation_quaternion.negate()
  previous[pb.name]=pb.rotation_quaternion.copy();pb.keyframe_insert('location',frame=f+1);pb.keyframe_insert('rotation_quaternion',frame=f+1)
 slot=r.animation_data.action_slot
for layer in action.layers:
 for strip in layer.strips:
  for bag in strip.channelbags:
   for curve in bag.fcurves:
    for key in curve.keyframe_points:key.interpolation='LINEAR'
for f,target in expected.items():s.frame_set(f+1);bpy.context.view_layer.update();assert np.max(abs(np.array([pb.matrix for pb in r.pose.bones])-target))<3e-6
s.frame_start=1;s.frame_end=151;s.render.fps=30;bpy.context.preferences.filepaths.save_version=0;s.frame_set(1);bpy.ops.wm.save_as_mainfile(filepath=str(P/'source.blend'));(F/'native-keying-receipt.json').write_text(json.dumps({'full151':len(frames)==151,'final_gate_stage':args.final,'rows':witness,'source_sha256':hashlib.sha256((P/'source.blend').read_bytes()).hexdigest()},indent=2)+'\n')
# Review images demonstrate the actual stage order; no image/video route.
s.render.engine='BLENDER_WORKBENCH';s.render.resolution_x=600;s.render.resolution_y=800;s.render.resolution_percentage=100;s.render.film_transparent=False;s.world.color=(.1,.1,.1);s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGBA';sh=s.display.shading;sh.light='STUDIO';sh.color_type='MATERIAL';sh.show_shadows=False;sh.show_cavity=False;sh.show_specular_highlight=False;s.view_settings.view_transform='Standard';s.view_settings.look='None';cam=s.camera;cd=cam.data
views=[{'label':'back_oblique','position':[3.8,5,2.1],'target':[0,.03,1],'scale':2.05},{'label':'front_side','position':[5,-2,2.1],'target':[0,.03,1],'scale':2.05}]
for c in views:
 cam.location=c['position'];cam.rotation_euler=(Vector(c['target'])-cam.location).to_track_quat('-Z','Y').to_euler();cd.ortho_scale=c['scale']/(s.render.resolution_x/s.render.resolution_y)
 for label,f in [('start',0),('lift',20),('fold',35),('approach',48),('peak',75),('return',115)]:
  s.frame_set(f+1);s.render.filepath=str(P/f'{"proof"if args.final else"grip-settle"if args.dense_early else"staged"}-{label}-{c["label"]}.png');bpy.ops.render.render(write_still=True)
(P/'cameras.json').write_text(json.dumps(views,indent=2)+'\n')
print('EARLY_PROOFS_READY',str(P))
