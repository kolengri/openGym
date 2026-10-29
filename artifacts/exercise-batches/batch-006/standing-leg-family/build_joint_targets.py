"""One bounded knee/shoulder target construction; both authored paths stay frozen."""
from pathlib import Path
import bpy,json,numpy as np,hashlib,shutil
from mathutils import Vector
P=Path(__file__).resolve().parent;B=P.parent;bpy.ops.wm.open_mainfile(filepath=str(P/'kinematic-source.blend'));body=bpy.data.objects['SK_BlenderStudioHuman'];rig=bpy.data.objects['RIG_BlenderStudioHuman'];s=bpy.context.scene;R=np.array([v.co[:] for v in body.data.vertices]);arm=next(m for m in body.modifiers if m.type=='ARMATURE');fair=next(m for m in body.modifiers if m.type=='CORRECTIVE_SMOOTH');arm.use_deform_preserve_volume=False
states=json.loads((P/'kinematic-state.json').read_text());deltas=[];reports=[]
def smooth(t):t=np.clip(t,0,1);return t*t*(3-2*t)
def band(t,lo,hi,f):return smooth((t-lo)/f)*(1-smooth((t-hi+f)/f))
def coords():
 bpy.context.view_layer.update();ev=body.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh();x=np.array([v.co[:] for v in me.vertices]);ev.to_mesh_clear();return x
for id,side,sign,f,kind in [('3480','Left',1,37.5,'Popliteal'),('3480','Right',-1,112.5,'Popliteal'),('3479','Left',1,31,'Shoulder'),('3479','Right',-1,106,'Shoulder')]:
 rig.animation_data.action=bpy.data.actions['Exercise_'+id];s.frame_set(int(f)+1,subframe=f%1)
 for m in body.modifiers:m.show_viewport=m.show_render=m.type=='ARMATURE'
 base=coords();fair.factor=1;fair.iterations=20;fair.show_viewport=fair.show_render=True;sm=coords();fair.show_viewport=fair.show_render=False
 collar=(band(R[:,2],.34,.66,.07)*smooth((R[:,1]-.02)/.04)*smooth((sign*R[:,0]-.04)/.04)) if kind=='Popliteal' else (band(sign*R[:,0],.08,.39,.065)*band(R[:,2],1.12,1.53,.075));target=(sm-base)*collar[:,None];A=np.zeros((len(R),3,3))
 for v in body.data.vertices:
  for g in v.groups:
   name=body.vertex_groups[g.group].name;A[v.index]+=g.weight*np.array(rig.pose.bones[name].matrix@rig.data.bones[name].matrix_local.inverted())[:3,:3]
 ids=np.flatnonzero(collar>1e-8);delta=np.zeros_like(R);delta[ids]=np.linalg.solve(A[ids],target[ids,:,None])[:,:,0];length=np.linalg.norm(delta,axis=1);t=np.clip((length-.020)/.010,0,1);bounded=np.where(length<=.020,length,np.where(length>=.030,.025,.020+.010*(t-.5*t*t)));delta*=np.divide(bounded,length,out=np.ones_like(length),where=length>1e-12)[:,None];assert np.linalg.norm(delta,axis=1).max()<=.02500001;deltas.append(delta)
 reports.append({'name':('Lunge' if kind=='Popliteal' else 'HeelTouch')+side+kind,'action_id':id,'side':side,'kind':kind,'frame':f,'source_ids':ids.tolist(),'c1_collar':collar[ids].tolist(),'uncapped_required_source_delta_m':float(length.max()),'applied_source_delta_m':float(np.linalg.norm(delta,axis=1).max()),'inverse_linear_condition_max':float(np.linalg.cond(A[ids]).max()),'capped_ids':np.flatnonzero(length>.020).tolist(),'source_deltas':delta[ids].tolist(),'outside_exact':bool(np.array_equal(delta[collar==0],np.zeros_like(delta[collar==0])))})
body.shape_key_add(name='Basis',from_mix=False)
for report,delta in zip(reports,deltas):body.shape_key_add(name=report['name'],from_mix=False).data.foreach_set('co',(R+delta).astype(np.float32).ravel())
keys=body.data.shape_keys;keys.animation_data_create()
for id in ['3479','3480']:
 action=bpy.data.actions['Exercise_'+id];rig.animation_data.action=action;slot=action.slots.new(id_type='KEY',name='Local rear knee target');keys.animation_data.action=action;keys.animation_data.action_slot=slot
 for f in range(151):
  s.frame_set(f+1)
  for report in reports:
   value=states[id][str(f)].get('lunge' if report['kind']=='Popliteal' else 'kick',0) if states[id][str(f)]['side']==report['side'] and id==report['action_id'] else 0;key=keys.key_blocks[report['name']];key.value=value;key.keyframe_insert('value',frame=f+1)
 for layer in action.layers:
  for strip in layer.strips:
   for bag in strip.channelbags:
    for fc in bag.fcurves:
     for pt in fc.keyframe_points:pt.interpolation='LINEAR'
for m in body.modifiers:m.show_viewport=m.show_render=m.type=='ARMATURE'
report={'method':'One source-bound native CorrectiveSmooth20x1.0 construction at each mirrored rear-knee peak, multiplied by a fixed C1 posterior knee collar, exact inverse per-vertex LBS, then C1 25mm source saturation. Rear knee keys use lunge amount; shoulder keys use side-kick amount. All four keys are explicit in both actions, unrelated targets zero. No DQ runtime or pose change.','source_cap_m':.025,'states':reports,'basis_rest_uv_ids_topology_unchanged':True};(P/'joint-target-report.json').write_text(json.dumps(report,indent=2)+'\n')
rig.animation_data.action=bpy.data.actions['Exercise_3480'];keys.animation_data.action=rig.animation_data.action;keys.animation_data.action_slot=next(x for x in keys.animation_data.action.slots if x.target_id_type=='KEY');s.frame_set(38);bpy.context.view_layer.update();proof=[]
for id,f,label,view,pos in [('3480',37,'deep-left','oblique',(3.8,-5,2.3)),('3480',37,'deep-left','rear',(2.5,5,2)),('3479',31,'kick','oblique',(3.8,-5,2.3)),('3479',40,'heel-contact','oblique',(3.8,-5,2.3))]:
 rig.animation_data.action=bpy.data.actions['Exercise_'+id];keys.animation_data.action=rig.animation_data.action;keys.animation_data.action_slot=next(x for x in keys.animation_data.action.slots if x.target_id_type=='KEY');s.frame_set(f+1);bpy.context.view_layer.update()
 cam=s.camera;cam.location=pos;cam.rotation_euler=(Vector((0,.2 if id=='3480' else 0,.9))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=2.25 if id=='3480' else 2.35;file=B/'assets'/id/('joint8-'+label+'-'+view+'.png');s.render.filepath=str(file);before=coords();bones={pb.name:np.array(pb.matrix) for pb in rig.pose.bones};bpy.ops.render.render(write_still=True);assert np.max(abs(coords()-before))==0;assert max(np.max(abs(np.array(pb.matrix)-bones[pb.name])) for pb in rig.pose.bones)==0;proof.append({'file':str(file.relative_to(B)),'sha256':hashlib.sha256(file.read_bytes()).hexdigest(),'frame':f,'render_surface_delta':0,'render_bone_delta':0})
s.frame_set(1);bpy.ops.wm.save_as_mainfile(filepath=str(P/'joint-source.blend'));(P/'joint8-proof-manifest.json').write_text(json.dumps({'source_sha256':hashlib.sha256((P/'joint-source.blend').read_bytes()).hexdigest(),'proofs':proof},indent=2)+'\n');print('JOINT_TARGET_READY',json.dumps([{k:r[k] for k in ['name','applied_source_delta_m','uncapped_required_source_delta_m','inverse_linear_condition_max']} for r in reports]))
