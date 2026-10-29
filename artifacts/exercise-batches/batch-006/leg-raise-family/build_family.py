"""Frozen four-action source; exact canonical cage plus declared sparse fields."""
import json,sys,hashlib,gzip
from pathlib import Path
import bpy,numpy as np
from mathutils import Vector
P=Path(__file__).resolve().parent;B=P.parent;sys.path.insert(0,str(P))
import family_common as c,support_fields as support,cervical_attachment as cervical
IDS=['4826','4001','3590','5106']
def invariant(b,r):
 h=hashlib.sha256()
 for v in b.data.vertices:h.update(np.array(v.co,np.float32).tobytes())
 for f in b.data.polygons:h.update(np.array(f.vertices,np.int32).tobytes())
 for uv in b.data.uv_layers:
  values=np.empty(len(uv.data)*2,np.float32);uv.data.foreach_get('uv',values);h.update(uv.name.encode()+values.tobytes())
 for bone in r.data.bones:h.update(bone.name.encode()+np.array(bone.matrix_local,np.float32).tobytes())
 return h.hexdigest()
binding=c.initialize();a=c.a;b,r,s=a.body,a.rig,a.scene;source_invariant=invariant(b,r);weights=[c.weights(b,i)for i in range(len(b.data.vertices))];support_install=support.install(b);cervical_install=cervical.install(b)
keys=b.data.shape_keys;names=[k.name for k in keys.key_blocks if k.name!='Basis'];assert len(names)==7;s.frame_start=1;s.frame_end=151;s.render.fps=30
captured={};desired={};expected_weights={};previous={}
for eid in IDS:
 captured[eid]=[];desired[eid]=[];expected_weights[eid]=[];previous={};keys.key_blocks[cervical.KEY].value=cervical.value_for(eid)
 for frame in range(151):
  points,meta=c.sample(frame,eid);desired[eid].append(np.array([meta['desired'][pb.name]for pb in r.pose.bones]));row={}
  for pb in r.pose.bones:
   q=pb.rotation_quaternion.copy()
   if pb.name in previous and q.dot(previous[pb.name])<0:q.negate()
   previous[pb.name]=q.copy();row[pb.name]=(pb.location.copy(),q.copy(),pb.scale.copy())
  captured[eid].append(row);expected_weights[eid].append({n:float(keys.key_blocks[n].value)for n in names})
# Two explicit slots per action preserve both native skeleton and KEY schedules.
r.animation_data_create();keys.animation_data_create()
for eid in IDS:
 act=bpy.data.actions.new('Exercise_'+eid);act.use_fake_user=True;oslot=act.slots.new(id_type='OBJECT',name=r.name);kslot=act.slots.new(id_type='KEY',name=keys.name)
 r.animation_data.action=act;r.animation_data.action_slot=oslot;keys.animation_data.action=act;keys.animation_data.action_slot=kslot
 for f,row in enumerate(captured[eid]):
  s.frame_set(f+1)
  for pb in r.pose.bones:
   pb.location,pb.rotation_quaternion,pb.scale=row[pb.name];pb.keyframe_insert('location',frame=f+1);pb.keyframe_insert('rotation_quaternion',frame=f+1)
  for name in names:
   key=keys.key_blocks[name];key.value=expected_weights[eid][f][name];key.keyframe_insert('value',frame=f+1)
 for layer in act.layers:
  for strip in layer.strips:
   for bag in strip.channelbags:
    for fc in bag.fcurves:
     for point in fc.keyframe_points:point.interpolation='LINEAR'
attr=b.data.attributes.get('_SOURCE_INDEX')or b.data.attributes.new(name='_SOURCE_INDEX',type='FLOAT',domain='POINT');attr.data.foreach_set('value',np.arange(10582,dtype=np.float32))
cd=bpy.data.cameras.new('ReviewCamera');cam=bpy.data.objects.new('ReviewCamera',cd);s.collection.objects.link(cam);s.camera=cam;cd.type='ORTHO';cd.ortho_scale=2.3;cam.location=(3,-3,2.5);cam.rotation_euler=(Vector((0,-.12,.4))-cam.location).to_track_quat('-Z','Y').to_euler();s.render.engine='BLENDER_WORKBENCH';s.render.resolution_x=1100;s.render.resolution_y=800;s.render.resolution_percentage=100;s.render.image_settings.file_format='PNG';s.render.film_transparent=True;s.display.shading.color_type='SINGLE';s.display.shading.single_color=(.58,.60,.63);s.display.shading.show_shadows=False;s.display.shading.show_cavity=False;s.display.shading.show_specular_highlight=False;s.view_settings.view_transform='Standard';s.view_settings.look='None'
def select(eid):
 act=bpy.data.actions['Exercise_'+eid];r.animation_data.action=act;r.animation_data.action_slot=next(slot for slot in act.slots if slot.target_id_type=='OBJECT');keys.animation_data.action=act;keys.animation_data.action_slot=next(slot for slot in act.slots if slot.target_id_type=='KEY')
select('4826');s.frame_set(1);bpy.context.preferences.filepaths.save_version=0;assert invariant(b,r)==source_invariant;bpy.ops.wm.save_as_mainfile(filepath=str(P/'source.blend'))
# Saved-action readback is authoritative; the renderer cannot replace it with an
# inherited action, and every native matrix/morph schedule is checked all151.
bpy.ops.wm.open_mainfile(filepath=str(P/'source.blend'));b=bpy.data.objects['SK_BlenderStudioHuman'];r=bpy.data.objects['RIG_BlenderStudioHuman'];s=bpy.context.scene;keys=b.data.shape_keys;assert invariant(b,r)==source_invariant;assert weights==[{b.vertex_groups[g.group].name:float(g.weight)for g in v.groups}for v in b.data.vertices]
readbacks={};source_sha=hashlib.sha256((P/'source.blend').read_bytes()).hexdigest()
for eid in IDS:
 select(eid);maxmatrix=0.;maxmorph=0.;jointrows=[]
 for f in range(151):
  s.frame_set(f+1);bpy.context.view_layer.update();error=float(abs(np.array([pb.matrix[:]for pb in r.pose.bones])-desired[eid][f]).max());maxmatrix=max(maxmatrix,error);assert error<2e-6
  maxmorph=max(maxmorph,max(abs(keys.key_blocks[n].value-expected_weights[eid][f][n])for n in names));jointrows.append({'frame':f,'joints':{pb.name:list(r.matrix_world@pb.head)for pb in r.pose.bones}})
 assert maxmorph<1e-6;readbacks[eid]={'maximum_saved_matrix_error':maxmatrix,'maximum_saved_morph_error':maxmorph,'all151_joints':jointrows,'morph_schedule':expected_weights[eid]}
(P/'native-action-readback.json').write_text(json.dumps({'source_sha256':source_sha,'actions':readbacks},separators=(',',':'))+'\n')
normal={'source_sha256':source_sha,'basis':np.array(keys.key_blocks['Basis'].normals_vertex_get()).reshape((-1,3)).tolist(),'targets':{n:np.array(keys.key_blocks[n].normals_vertex_get()).reshape((-1,3)).tolist()for n in names},'coordinate_frame':'Original Blender Zup rest normals'}
with gzip.open(P/'morph-normal-reference.json.gz','wt',compresslevel=9)as stream:json.dump(normal,stream,separators=(',',':'))
report={'source_sha256':source_sha,'canonical_source_sha256':a.SOURCE_SHA,'basis_rest_uv_topology_invariant_sha256':source_invariant,'source_vertices':10582,'triangles':21160,'bones':51,'actions':['Exercise_'+i for i in IDS],'binding':binding,'actual_weights':weights,'support_targets':support_install,'cervical_target':cervical_install,'cervical_action_weights':{eid:cervical.value_for(eid)for eid in IDS},'actual_maximum_influences':max(map(len,weights)),'actual_maximum_weight_sum_error':max(abs(sum(w.values())-1)for w in weights),'source_rest_and_basis_preserved':True,'source_render_accepted':'Native early/final supported proofs accepted by root; remaining small cervical crease disclosed.','source_not_resaved_after_readback':True,'all151_action_readback':{i:{k:v for k,v in q.items()if k not in ['all151_joints','morph_schedule']}for i,q in readbacks.items()}}
(P/'source-build-receipt.json').write_text(json.dumps(report,indent=2)+'\n')
for eid in IDS:
 out=B/'assets'/eid;clip=json.loads((out/'clip.json').read_text());clip.update(asset='leg-raise-family',physical_source='../../leg-raise-family/source.blend',shared_physical_resource={'motion':'../../leg-raise-family/motion.glb','source':'../../leg-raise-family/source.blend','action_identity':'Exercise_'+eid,'identical_leg_action_as':['4826','3590']if eid in ['4826','3590']else[]},review_status='source_cue_and_shape_accepted_final_checks_pending',cervical_attachment={'maximum_source_delta_m':.008,'weight':cervical.value_for(eid),'remaining_small_contour_crease':'Disclosed and accepted for this user-review illustration batch.'});(out/'clip.json').write_text(json.dumps(clip,indent=2)+'\n')
print('FROZEN_SOURCE_READY',source_sha,json.dumps(report['all151_action_readback']),flush=True)
