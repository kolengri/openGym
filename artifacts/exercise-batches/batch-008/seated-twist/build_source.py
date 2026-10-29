"""Final151 native mechanics, editable one-action source and actual saved-action readback."""
from pathlib import Path
import sys,json,hashlib,math,gzip
sys.dont_write_bytecode=True
import bpy,numpy as np
from mathutils import Matrix,Quaternion,Vector
P=Path(__file__).resolve().parent;A=P.parent/'assets/6121';sys.path.insert(0,str(P));import twist_motion as m
from prepare_landmarks import landmarks
from native_checks import SurfaceChecks
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
a=m.prepare();contacts=m.CONTACT.copy();drive={k:v.tolist()for k,v in m.DRIVE.items()};lm=landmarks(m);checks=SurfaceChecks(a.body,lm);s=a.scene;b=a.body;r=a.rig;s.frame_start=1;s.frame_end=151;s.render.fps=30
poses=[];skins=[];rows=[];morphs=[];fail=[];max_joint={'degrees':0};max_skin={'m':0};previous={};lastX=None;max_hinge=0.;min_pole=1.;minimum_areas=1.;R=np.array([v.co[:]for v in b.data.vertices]);binding=m.a.binding_hash(b,r);key=b.data.shape_keys.key_blocks['TwistHipVolume'];lead=b.data.shape_keys.key_blocks['ThighContactLead']
for f in range(151):
 d,params=m.pose(f/30);X=m.points();row,issues=checks.measure(X,None,f);k=float(key.value);row['component_weight']=k;row['contact_lead_weight']=float(lead.value);row['root_delta_m']=params['root_delta'];rows.append(row);fail.extend({'frame':f,'issue':issue}for issue in issues)
 pose={}
 for pb in r.pose.bones:
  q=pb.rotation_quaternion.copy()
  if pb.name in previous:
   angle=math.degrees(q.rotation_difference(previous[pb.name]).angle);angle=min(angle,360-angle)
   if angle>max_joint['degrees']:max_joint={'from':f-1,'to':f,'bone':pb.name,'degrees':angle}
  previous[pb.name]=q.copy();pose[pb.name]=(pb.location.copy(),q,pb.scale.copy(),pb.matrix.copy())
 if lastX is not None:
  step=np.linalg.norm(X-lastX,axis=1);i=int(step.argmax())
  if step[i]>max_skin['m']:max_skin={'from':f-1,'to':f,'source_id':i,'m':float(step[i])}
 lastX=X.copy();poses.append(pose);skins.append(X.astype(np.float32));morphs.append((k,float(lead.value)))
 for side in ['Left','Right']:
  for chain in [['UpLeg','Leg','Foot'],['Arm','ForeArm','Hand']]:
   H,K,W=[d[side+n].translation for n in chain];N=(K-H).cross(W-K).normalized();SN=(a.heads[side+chain[1]]-a.heads[side+chain[0]]).cross(a.heads[side+chain[2]]-a.heads[side+chain[1]]).normalized()
   for name in chain[:2]:
    moved=(d[side+name].to_quaternion()@a.rest[side+name].to_quaternion().inverted())@SN;max_hinge=max(max_hinge,math.degrees(moved.angle(N)))
 if f%30==0:print('NATIVE151',f,'issues',len(fail),'floor',row['minimum_body_z'],flush=True)
loop=float(np.linalg.norm(skins[-1]-skins[0],axis=1).max());assert loop<1e-6
report={'ok':not fail,'frames':151,'fps':30,'duration_seconds':5,'native_frame_origin':1,'maximum_native_joint_step':max_joint,'maximum_native_skin_step':max_skin,'maximum_actual_source_hinge_plane_error_degrees':max_hinge,'loop_skin_error_m':loop,'minimum_body_z':min(x['minimum_body_z']for x in rows),'minimum_triangle_area_m2':min(x['minimum_triangle_area_m2']for x in rows),'minimum_hold_hug_gap_m':min(x.get('hug_central_palm_knee_gap_m',1e9)for x in rows),'maximum_hold_hug_gap_m':max(x.get('hug_central_palm_knee_gap_m',0)for x in rows),'contacts':contacts,'component_drive':drive,'failures':fail,'samples':rows,'fold_policy':'Localized nonadjacent source-ROI crossings are diagnostic warnings with exact frame/face pairs. Shoulder/hip silhouettes are primary-reviewed; no global collision-free claim. Semantic hip ROI excludes source hanging hands; older sourceZ-only metric remains separately named.'}
(P/'native-loop-report.json').write_text(json.dumps(report,indent=2)+'\n');assert not fail,fail[:12]
# Bake native51-joint TRS plus one explicit scalar on one slotted/layered action.
action=bpy.data.actions.new('Exercise_6121');action.use_fake_user=True;r.animation_data_create();r.animation_data.action=action;keys=b.data.shape_keys;keys.animation_data_create();slot=action.slots.new(id_type='KEY',name='Seated twist hip volume');keys.animation_data.action=action;keys.animation_data.action_slot=slot;previous={}
for f,pose in enumerate(poses):
 s.frame_set(f+1)
 for pb in r.pose.bones:
  pb.location,pb.rotation_quaternion,pb.scale=pose[pb.name][:3]
  if pb.name in previous and pb.rotation_quaternion.dot(previous[pb.name])<0:pb.rotation_quaternion.negate()
  previous[pb.name]=pb.rotation_quaternion.copy()
  for prop in ['location','rotation_quaternion','scale']:pb.keyframe_insert(prop,frame=f+1)
 key.value,lead.value=morphs[f];key.keyframe_insert('value',frame=f+1);lead.keyframe_insert('value',frame=f+1)
for layer in action.layers:
 for strip in layer.strips:
  for bag in strip.channelbags:
   for curve in bag.fcurves:
    for point in curve.keyframe_points:point.interpolation='LINEAR'
s.frame_set(1);bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(A/'source.blend'));source_sha=sha(A/'source.blend')
bpy.ops.wm.open_mainfile(filepath=str(A/'source.blend'));m.a.body=b=bpy.data.objects['SK_BlenderStudioHuman'];m.a.rig=r=bpy.data.objects['RIG_BlenderStudioHuman'];m.a.scene=s=bpy.context.scene;key=b.data.shape_keys.key_blocks['TwistHipVolume'];lead=b.data.shape_keys.key_blocks['ThighContactLead'];max_skin_error=0.;max_matrix_error=0.;max_weight_error=0.
for f in range(151):
 s.frame_set(f+1);bpy.context.view_layer.update();X=m.points();max_skin_error=max(max_skin_error,float(np.linalg.norm(X-skins[f],axis=1).max()));max_matrix_error=max(max_matrix_error,max(float(abs(np.array(pb.matrix)-np.array(poses[f][pb.name][3])).max())for pb in r.pose.bones));max_weight_error=max(max_weight_error,max(abs(float(key.value)-morphs[f][0]),abs(float(lead.value)-morphs[f][1])))
assert max_skin_error<1e-5 and max_matrix_error<1e-5 and max_weight_error<1e-6
lm['source_sha256']=source_sha;(A/'landmarks.json').write_text(json.dumps(lm,indent=2)+'\n');report.update(source_sha256=source_sha,saved_source_parity={'skin_m':max_skin_error,'matrix':max_matrix_error,'morph':max_weight_error});(P/'native-loop-report.json').write_text(json.dumps(report,indent=2)+'\n');(A/'surface-contact-report.json').write_text(json.dumps(report,indent=2)+'\n');(P/'motion-contract.json').write_text(json.dumps({'contacts':contacts,'drive':drive,'component_names':['TwistHipVolume','ThighContactLead'],'contact_interpolation':'sqrt(k)-k entry lead of the same frozen contactvector; zero neutral/held; totalcontactamplitude sqrt(k)<=1. Foot-only swing lift12mm*sin(pi*quinticLegProgress)^2, zero endpoints.','binding_sha256':binding,'neutral_key':0,'peak_key':1,'other_actions':'Standalone single-action asset; no other action contribution. Key is explicit at every frame including neutral0.','source_sha256':source_sha},indent=2)+'\n')
# Mandatory raw game QA and actual saved-source material/wire stills.
sys.path.insert(0,str(Path.home()/'.codex/skills/blender-asset-qa/scripts'));import qa_check
qa=[];proof=[]
for f in sorted(set([0,9,22,30,45,60,75,90,105,120,128,141,150,max_joint['to'],max_skin['to']])):
 s.frame_set(f+1);result=qa_check.run(objects=[b.name],profile='game');qa.append({'frame':f,'qa':result});assert result['pass'],result['errors']
for label,f in [('start',0),('peak',75),('return',150)]:
 s.frame_set(f+1);X=m.points();D={p.name:np.array(p.matrix)for p in r.pose.bones}
 for view,pos in [('side',(3.8,-.2,1)),('oblique',(3.3,-4.5,2))]:
  cam=s.camera;cam.location=pos;cam.rotation_euler=(Vector((0,-.35,.4))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=2.05;s.render.filepath=str(A/f'neutral-{label}-{view}.png');bpy.ops.render.render(write_still=True);assert np.array_equal(X,m.points())and all(np.array_equal(D[p.name],np.array(p.matrix))for p in r.pose.bones);proof.append({'file':Path(s.render.filepath).name,'frame':f,'action':r.animation_data.action.name,'sha256':sha(Path(s.render.filepath)),'render_skin_delta_m':0,'render_bone_delta':0})
s.frame_set(76);b.show_wire=True;b.show_all_edges=True;s.render.filepath=str(A/'wire-peak.png');bpy.ops.render.render(write_still=True);b.show_wire=False
(A/'asset-qa.json').write_text(json.dumps({'source_sha256':source_sha,'profile':'game','samples':qa},indent=2)+'\n');(A/'proof-receipt.json').write_text(json.dumps({'source_sha256':source_sha,'proofs':proof},indent=2)+'\n');print('SOURCE_FROZEN',source_sha,'max_joint',max_joint,'max_skin',max_skin,'hinge',max_hinge,flush=True)
