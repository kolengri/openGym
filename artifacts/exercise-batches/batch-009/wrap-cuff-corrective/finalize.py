"""Freeze the accepted POSITION target with explicit source NORMAL provenance.

Run only after root's native held-shape acceptance. Full151/runtime belongs to
standing-arms integration; this script checks the bounded component contract.
"""
import sys
sys.dont_write_bytecode=True
import bpy,numpy as np,json,hashlib
from pathlib import Path
F=Path(__file__).resolve().parent
sys.path[:0]=[str(F),str(F.parent.parent/'batch-008/standing-dynamic'),'/Users/kolengri/.codex/skills/blender-asset-qa/scripts']
import corrective,qa_check,review_shots
from self_clearance import SelfClearance
SOURCE=F/'inputs-contact/source.blend';SOURCE_SHA='88c2da9b30955e3793637fe5f8a086e0ca7339d395cf20997d6b3fdcac817c1e';POSITION_SHA='a50d65d6c27e7b18a9aeb962919f9ff196b4dae19ce295d3c6a4d7b26415d4f9'
assert corrective.sha(SOURCE)==SOURCE_SHA
assert corrective.sha(F/'accepted-position.npz')==POSITION_SHA
bpy.ops.wm.open_mainfile(filepath=str(SOURCE));b=bpy.data.objects['SK_BlenderStudioHuman'];r=bpy.data.objects['RIG_BlenderStudioHuman'];s=bpy.context.scene
for m in b.modifiers:
 m.show_viewport=m.show_render=m.type=='ARMATURE'
 if m.type=='ARMATURE':assert m.use_deform_preserve_volume
keys=b.data.shape_keys

def select(ID,frame):
 act=bpy.data.actions['Exercise_'+ID];r.animation_data.action=act;r.animation_data.action_slot=next(x for x in act.slots if x.target_id_type=='OBJECT');keys.animation_data.action=act;keys.animation_data.action_slot=next(x for x in act.slots if x.target_id_type=='KEY');s.frame_set(int(frame)+1,subframe=frame%1)

def sample():
 bpy.context.view_layer.update();e=b.evaluated_get(bpy.context.evaluated_depsgraph_get());me=e.to_mesh();p=np.array([v.co[:]for v in me.vertices],np.float32);n=np.array([v.normal[:]for v in me.vertices],np.float32);e.to_mesh_clear();return p,n,np.array([pb.matrix for pb in r.pose.bones],np.float32)

def actions_signature():
 h=hashlib.sha256()
 for act in sorted(bpy.data.actions,key=lambda a:a.name):
  h.update(act.name.encode())
  for slot in act.slots:h.update(str((slot.identifier,slot.target_id_type,slot.handle)).encode())
  for layer in act.layers:
   for strip in layer.strips:
    for bag in strip.channelbags:
     h.update(str(bag.slot_handle).encode())
     for fc in bag.fcurves:
      h.update(str((fc.data_path,fc.array_index)).encode())
      for k in fc.keyframe_points:h.update(np.array([*k.co,*k.handle_left,*k.handle_right],np.float32).tobytes()+k.interpolation.encode())
 return h.hexdigest()

binding_before=corrective.binding_signature(b,r);action_before=actions_signature();old_names=[k.name for k in keys.key_blocks];old_positions={name:np.array([v.co[:]for v in keys.key_blocks[name].data],np.float32)for name in old_names};old_normals={name:np.array(keys.key_blocks[name].normals_vertex_get(),np.float32).reshape(-1,3)for name in old_names};before={}
for ID in ['1404','1405','4515','3995']:
 for frame in [0.,37.5,150.]:
  select(ID,frame);before[(ID,frame)]=sample()
data=corrective.install(b,r,s,F/'accepted-position.npz',POSITION_SHA);keys=b.data.shape_keys;basis=old_positions['Basis'];normal0=old_normals['Basis'];normal_target=np.array(keys.key_blocks[corrective.KEY].normals_vertex_get(),np.float32).reshape(-1,3);normal_delta=normal_target-normal0
for name in old_names:
 assert np.array_equal(old_positions[name],np.array([v.co[:]for v in keys.key_blocks[name].data],np.float32)),name
 assert np.array_equal(old_normals[name],np.array(keys.key_blocks[name].normals_vertex_get(),np.float32).reshape(-1,3)),name
preservation=[]
for(ID,frame),previous in before.items():
 select(ID,frame);keys.key_blocks[corrective.KEY].value=0.;now=sample()
 assert all(np.array_equal(a,z)for a,z in zip(previous,now)),(ID,frame)
 preservation.append({'exercise':ID,'frame':frame,'component_weight':0.,'skin_POSITION_bit_exact':True,'skin_geometric_NORMAL_bit_exact':True,'all51_bone_matrices_bit_exact':True})
assert binding_before==corrective.binding_signature(b,r)==corrective.BINDING_SHA256
assert action_before==actions_signature()
protected=data['protected_source_ids'];protected_normal_ids=protected[np.linalg.norm(normal_delta[protected],axis=1)>0.]
normal_ids=np.flatnonzero(np.linalg.norm(normal_delta,axis=1)>0.);union=np.union1d(data['source_ids'],normal_ids);exterior=np.setdiff1d(np.arange(len(basis)),union);assert np.max(np.abs(normal_delta[exterior]))==0.
payload={name:data[name]for name in data.files};payload.update(rest_basis_normals=normal0,rest_normal_deltas=normal_delta,normal_source_ids=np.arange(len(basis),dtype=np.int32),normal_changed_source_ids=normal_ids.astype(np.int32),position_normal_union_source_ids=union.astype(np.int32))
np.savez_compressed(F/corrective.ARCHIVE,**payload);archive_sha=corrective.sha(F/corrective.ARCHIVE)
select('3995',37.5);keys.key_blocks[corrective.KEY].value=0.;p0,n0,m0=sample();keys.key_blocks[corrective.KEY].value=1.;p,n,m=sample();assert np.array_equal(m0,m);assert np.array_equal(p0[protected],p[protected]);assert np.array_equal(p0[np.setdiff1d(np.arange(len(p)),data['source_ids'])],p[np.setdiff1d(np.arange(len(p)),data['source_ids'])])
b.data.calc_loop_triangles();T=np.array([t.vertices[:]for t in b.data.loop_triangles],int);areas=np.linalg.norm(np.cross(p[T[:,1]]-p[T[:,0]],p[T[:,2]]-p[T[:,0]]),axis=1)*.5;assert areas.min()>1e-10,float(areas.min())
clear=SelfClearance(b,r);metrics,issues=clear.sample(p)
# Keep local attachment intersections explicit, with source ownership and bounds.
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from triangle_intersection import intersect
names={g.index:g.name for g in b.vertex_groups};owners=[names[max(v.groups,key=lambda g:g.weight).group]for v in b.data.vertices];v=[Vector(x)for x in p];attachment=[];hard=[]
for label,AA,BB in [('arms',clear.arm['Left'],clear.arm['Right']),('Ltorso',clear.distal['Left'],clear.torso),('Rtorso',clear.distal['Right'],clear.torso)]:
 at=BVHTree.FromPolygons(v,AA,all_triangles=True);bt=BVHTree.FromPolygons(v,BB,all_triangles=True)
 for ai,bi in at.overlap(bt):
  a,bb=AA[ai],BB[bi]
  if set(a)&set(bb)or not intersect([v[i]for i in a],[v[i]for i in bb]):continue
  pair={'label':label,'a':a,'b':bb,'owners_a':[owners[i]for i in a],'owners_b':[owners[i]for i in bb]};local=label!='arms'and all(owners[i].endswith('Arm')and not owners[i].endswith('ForeArm')for i in a)and all(owners[i]in ['Spine','Spine1']for i in bb)
  (attachment if local else hard).append(pair)
assert not hard,hard[:5]
attach_ids=np.array(sorted(set(i for pair in attachment for tri in [pair['a'],pair['b']]for i in tri)),int);attach_bounds=[p[attach_ids].min(0).tolist(),p[attach_ids].max(0).tolist()]if len(attach_ids)else None
qa=[]
for frame in [0.,37.5]:
 select('3995',frame);keys.key_blocks[corrective.KEY].value=0. if frame==0 else 1.;q=qa_check.run(objects=[b.name],profile='game');qa.append({'frame':frame,'component_weight':keys.key_blocks[corrective.KEY].value,'report':q});print('GAME_QA',frame,len(q['errors']),len(q['warnings']),flush=True)
 assert q['pass'],q['errors']
select('3995',37.5);keys.key_blocks[corrective.KEY].value=1.
review=review_shots.run(objects=[b.name],out=str(F/'qa-wire.png'),views=['front','right','back'],mode='wire',res=600)
select('3995',0.);keys.key_blocks[corrective.KEY].value=0.;bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(F/'component-source.blend'))
construction=json.loads((F/'accepted-construction.json').read_text());position_deltas=np.zeros_like(basis);position_deltas[data['source_ids']]=data['rest_deltas']
outer_chest=(abs(basis[:,0])<.10)&(basis[:,2]>1.17)&(basis[:,2]<1.43);outer_deltoid=(abs(basis[:,0])>.25)&(basis[:,2]>1.33)&(basis[:,2]<1.53)
report={'source_sha256':SOURCE_SHA,'accepted_POSITION_archive_sha256':POSITION_SHA,'archive':corrective.ARCHIVE,'archive_sha256':archive_sha,'key':corrective.KEY,'native_held_shape_accepted_by_root':True,'native_shape_proof_tag':'a50d65d6c27e','integration_status':'Component packet only; writer owns C1p151 keys/reset/export/native-decoded and other-action151 preservation; root owns final GLB GPU acceptance.','vertices':len(basis),'triangles':len(T),'bones':len(r.data.bones),'existing_keys_exact':old_names,'source_Basis_rest_topology_UV_weights_signature':binding_before,'all_existing_actions_sha256':action_before,'canonical_binding_exact':True,'existing_key_POSITION_NORMAL_exact':True,'actions_exact':True,'position_source_count':len(data['source_ids']),'normal_source_count':len(normal_ids),'position_normal_union_source_count':len(union),'normal_only_source_ids':np.setdiff1d(normal_ids,data['source_ids']).tolist(),'protected_source_count':len(protected),'protected_source_ids':protected.tolist(),'protected_POSITION_component_delta_m':0.,'protected_source_NORMAL_maximum_vector_delta':float(np.linalg.norm(normal_delta[protected],axis=1).max()),'protected_POSITION_with_geometric_NORMAL_boundary_source_ids':protected_normal_ids.tolist(),'protected_native_held_POSITION_bit_exact':True,'protected_native_held_geometric_NORMAL_maximum_vector_difference':float(np.linalg.norm(n[protected]-n0[protected],axis=1).max()),'exterior_POSITION_component_delta_m':0.,'exterior_POSITION_NORMAL_union_delta':0.,'maximum_source_POSITION_delta_m':float(np.linalg.norm(position_deltas,axis=1).max()),'maximum_native_held_POSITION_delta_m':float(np.linalg.norm(p-p0,axis=1).max()),'maximum_source_NORMAL_vector_delta':float(np.linalg.norm(normal_delta,axis=1).max()),'minimum_held_triangle_area_m2':float(areas.min()),'nonpositive_area_triangles':int((areas<=0.).sum()),'hard_crossing_pairs':hard,'attachment_crossing_pairs':attachment,'attachment_pair_count':len(attachment),'attachment_source_ids':attach_ids.tolist(),'attachment_posed_bounds_m':attach_bounds,'attachment_note':'Root accepted localized connected cuff/pectoral compression folds as explicit diagnostics. Raw Arm/Spine1 attached-face pairs are not hidden or reclassified as distal clearance. No ForeArm/Hand/head/other-arm hard pairs remain at the held pose.','contact_anchor_evidence':construction['contact_anchor_evidence'],'outer_chest_source_region_count':int(outer_chest.sum()),'outer_chest_maximum_source_delta_m':float(np.linalg.norm(position_deltas[outer_chest],axis=1).max()),'outer_deltoid_source_region_count':int(outer_deltoid.sum()),'outer_deltoid_maximum_source_delta_m':float(np.linalg.norm(position_deltas[outer_deltoid],axis=1).max()),'NORMAL_provenance':'Full source-indexed Blender5.2 ShapeKey.normals_vertex_get target minus immutable Basis normals. Native source geometric NORMAL targets match standard glTF exporter semantics; inverse-native-unit-DQ applies to POSITION compilation. Runtime NORMAL transport/parity belongs to standing integration. Protected physical domains have exact zero POSITION deltas. True original-polygon-coface geometric NORMAL boundary deltas are retained, including six unchanged neck POSITION vertices; no artificial NORMAL pinning. All component channels reset0 for neutral/otheractions.','temporal_contract':'3995 only; p=sin²(pi*((runtime_frame%75)/75)), component scalar=p; two sameRightOver repeats, exact0 neutral/other3actions and scalar velocity0 at neutral/held/repetition/loop boundaries. Writer owns all151 explicit standard weights/reset.','native_preservation_samples':preservation,'game_qa':qa,'wire_review':review}
(F/'component.json').write_text(json.dumps(report,indent=2)+'\n');print('COMPONENT_READY',archive_sha,len(data['source_ids']),len(normal_ids),float(areas.min()),len(attachment),flush=True)
