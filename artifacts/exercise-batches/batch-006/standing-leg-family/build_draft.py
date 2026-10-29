"""Shared body/binding, separate text-authored trajectories and native proof isolation."""
from pathlib import Path
import bpy,sys,json,math,hashlib,importlib.util,shutil,argparse
import numpy as np
from mathutils import Vector
opts=argparse.ArgumentParser();opts.add_argument('--proof-prefix',default='early');opt=opts.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []);PREFIX=opt.proof_prefix
P=Path(__file__).resolve().parent;BATCH=P.parent;sys.path.insert(0,str(P.parents[1]/'batch-003'));sys.path.insert(0,str(P));import authoring as a;from poses import StandingLegPoses
assert a.initialize()=='227ede3fc31d1a2b47ff40f20a4a7288fe7bb36179add23bae953993826c8b7b'
body,rig,scene=a.body,a.rig,a.scene;R=np.array([v.co[:] for v in body.data.vertices]);original_weights=[{body.vertex_groups[g.group].name:float(g.weight) for g in v.groups} for v in body.data.vertices]
spec=importlib.util.spec_from_file_location('accepted_squat_binding',P.parents[1]/'batch-005/assets/3948/local_weights.py');binding=importlib.util.module_from_spec(spec);spec.loader.exec_module(binding);base_report=binding.apply(body)
foot_changes=[]
for v in body.data.vertices:
 side='Left' if v.co.x>0 else 'Right';sign=1 if side=='Left' else -1;blend=(1-binding.smooth((v.co.z-.035)/.045))*binding.smooth((sign*v.co.x-.08)/.04)
 if blend<=1e-8:continue
 before={body.vertex_groups[g.group].name:float(g.weight) for g in v.groups};orig=original_weights[v.index];den=orig.get(side+'Foot',0)+orig.get(side+'ToeBase',0);toe=orig.get(side+'ToeBase',0)/den if den>1e-12 else 0;target={side+'Foot':1-toe,side+'ToeBase':toe};row={name:(1-blend)*orig.get(name,0)+blend*target.get(name,0) for name in set(orig)|set(target)};row={n:w for n,w in row.items() if w>.001};row=dict(sorted(row.items(),key=lambda x:x[1],reverse=True)[:4]);total=sum(row.values());row={n:w/total for n,w in row.items()}
 for name in list(before):body.vertex_groups[name].remove([v.index])
 for name,value in row.items():body.vertex_groups[name].add([v.index],float(value),'REPLACE')
 foot_changes.append({'source_id':v.index,'before':before,'after':row})
assert max(len(v.groups) for v in body.data.vertices)<=4;assert max(abs(sum(g.weight for g in v.groups)-1) for v in body.data.vertices)<2e-6
for m in body.modifiers:
 m.show_viewport=m.show_render=m.type=='ARMATURE'
 if m.type=='ARMATURE':m.use_deform_preserve_volume=False
poses=StandingLegPoses(a);(P/'contact-landmarks.json').write_text(json.dumps({side:{'heel_ids':poses.heel[side]['ids'].tolist(),'heel_apex_id':poses.heel[side]['apex'],'palm_ids':poses.palm[side]['ids'].tolist(),'finger_contact_id':poses.heel[side]['finger_id']} for side in ['Left','Right']},indent=2)+'\n');scene.frame_start,scene.frame_end=1,151;scene.render.fps=30;rig.animation_data_create();intended={};states={};errors={};matrix_errors={}
for id in ['3479','3480']:
 act=bpy.data.actions.new('Exercise_'+id);act.use_fake_user=True;rig.animation_data.action=act;intended[id]={};states[id]={};errors[id]={}
 previous={}
 for f in range(151):
  scene.frame_set(f+1);d,st,err=poses.pose(id,f);bpy.context.view_layer.update();intended[id][f]={n:np.array(m) for n,m in d.items()};errors[id][f]=err
  states[id][f]={k:(list(v) if isinstance(v,Vector) else v) for k,v in st.items() if k not in ['feet']};states[id][f]['feet']={ss:{'ankle':list(fp['ankle']),'support':fp['support']} for ss,fp in st['feet'].items()}
  for pb in rig.pose.bones:
   if pb.name in previous and pb.rotation_quaternion.dot(previous[pb.name])<0:pb.rotation_quaternion.negate()
   previous[pb.name]=pb.rotation_quaternion.copy();pb.keyframe_insert('location',frame=f+1);pb.keyframe_insert('rotation_quaternion',frame=f+1)
 for layer in act.layers:
  for strip in layer.strips:
   for bag in strip.channelbags:
    for fc in bag.fcurves:
     for k in fc.keyframe_points:k.interpolation='LINEAR'
 rig.animation_data.action=act;mx=0
 for f in range(151):
  scene.frame_set(f+1);bpy.context.view_layer.update();mx=max(mx,max(float(abs(np.array(pb.matrix)-intended[id][f][pb.name]).max()) for pb in rig.pose.bones))
 matrix_errors[id]=mx;assert mx<2e-5,(id,mx)
attr=body.data.attributes.get('_SOURCE_INDEX') or body.data.attributes.new('_SOURCE_INDEX','FLOAT','POINT');attr.data.foreach_set('value',np.arange(10582,dtype=np.float32))
scene.render.engine='BLENDER_WORKBENCH';scene.render.resolution_x=760;scene.render.resolution_y=900;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA';scene.render.film_transparent=True
sh=scene.display.shading;sh.light='STUDIO';sh.color_type='MATERIAL';sh.show_shadows=False;sh.show_cavity=False;sh.show_specular_highlight=False;scene.view_settings.view_transform='Standard';scene.view_settings.look='None'
cd=bpy.data.cameras.new('ReviewCamera');cam=bpy.data.objects.new('ReviewCamera',cd);scene.collection.objects.link(cam);scene.camera=cam;cd.type='ORTHO'
def coordinates():
 ev=body.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh();X=np.array([ev.matrix_world@v.co for v in me.vertices]);ev.to_mesh_clear();return X
proof=[]
for id,frames in [('3479',[('start',0),('squat',18),('kick',31),('heel-contact',40),('mirror-contact',115)]),('3480',[('start',0),('deep-left',37),('deep-right',112),('return',145)])]:
 out=BATCH/'assets'/id;out.mkdir(exist_ok=True);rig.animation_data.action=bpy.data.actions['Exercise_'+id]
 for label,f in frames:
  scene.frame_set(f+1);bpy.context.view_layer.update();before=coordinates();beforebones={pb.name:np.array(pb.matrix) for pb in rig.pose.bones};assert max(float(abs(beforebones[n]-intended[id][f][n]).max()) for n in beforebones)<2e-5
  views=[('oblique',(3.8,-5,2.3))]
  if label in ['heel-contact','deep-left']:views += [('side',(5,0,1)),('rear',(2.5,5,2))]
  for view,pos in views:
   cam.location=pos;target=Vector((0,.20 if id=='3480' else 0,.90));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cd.ortho_scale=2.35 if id=='3479' else 2.25;file=out/f'{PREFIX}-{label}-{view}.png';scene.render.filepath=str(file);bpy.ops.render.render(write_still=True);after=coordinates();delta=float(np.linalg.norm(after-before,axis=1).max());bone_delta=max(float(abs(np.array(pb.matrix)-beforebones[pb.name]).max()) for pb in rig.pose.bones);assert delta<1e-7 and bone_delta<1e-7
   proof.append({'id':id,'frame':f,'file':str(file.relative_to(P.parent)),'sha256':hashlib.sha256(file.read_bytes()).hexdigest(),'render_surface_delta_m':delta,'render_bone_matrix_delta':bone_delta,'minimum_full_skin_z':float(after[:,2].min())})
 samples=[]
 for f in [0,15,18,30,31,37,40,60,75,90,105,112,115,135,145,150]:
  scene.frame_set(f+1);bpy.context.view_layer.update();samples.append({'id':id,'frame':f,'joints':{pb.name:list(rig.matrix_world@pb.head) for pb in rig.pose.bones}})
 (out/'pose-samples.json').write_text(json.dumps(samples,indent=2)+'\n');shutil.copyfile(BATCH/'contexts'/(id+'.json'),out/'authoring-context.json')
rig.animation_data.action=bpy.data.actions['Exercise_3479'];scene.frame_set(1);bpy.ops.wm.save_as_mainfile(filepath=str(P/'kinematic-source.blend'))
(P/'binding-report.json').write_text(json.dumps({'base_recipe':'batch005/assets/3948/local_weights.py','base_recipe_sha256':hashlib.sha256((P.parents[1]/'batch-005/assets/3948/local_weights.py').read_bytes()).hexdigest(),'base_report':base_report,'toe_preserving_plantar_overlay':foot_changes,'binding_hash':a.binding_hash(body,rig),'max_weight_error':max(abs(sum(g.weight for g in v.groups)-1) for v in body.data.vertices),'max_influences':max(len(v.groups) for v in body.data.vertices),'basis_rest_uv_source_ids_unchanged':True},indent=2)+'\n')
(P/'kinematic-state.json').write_text(json.dumps(states,indent=2)+'\n');(P/'target-errors.json').write_text(json.dumps({'maximum_native_matrix_errors':matrix_errors,'target_errors_by_frame':errors},indent=2)+'\n');(P/(PREFIX+'-proof-manifest.json')).write_text(json.dumps({'source_sha256':hashlib.sha256((P/'kinematic-source.blend').read_bytes()).hexdigest(),'proofs':proof},indent=2)+'\n')
print('EARLY_PROOF_READY',matrix_errors)
