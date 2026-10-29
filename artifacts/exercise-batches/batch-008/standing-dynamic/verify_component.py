"""Cheap actual-buffer/action readback of the accepted immutable component."""
import bpy,numpy as np,json,sys,hashlib
from pathlib import Path
F=Path(__file__).resolve().parent;sys.path[:0]=[str(F.parent.parent/'batch-003')];import authoring as a
S=F/'shoulder-specialist';data=np.load(S/'shoulder-ownership-target.npz');sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def tracks():
 result={}
 for action in bpy.data.actions:
  slot=next(x for x in action.slots if x.target_id_type=='OBJECT');rows=[]
  for layer in action.layers:
   for strip in layer.strips:
    for bag in strip.channelbags:
     if bag.slot_handle==slot.handle:
      for fc in bag.fcurves:rows.append([fc.data_path,fc.array_index,[(list(k.co),k.interpolation)for k in fc.keyframe_points]])
  result[action.name]=hashlib.sha256(json.dumps(sorted(rows),separators=(',',':')).encode()).hexdigest()
 return result
bpy.ops.wm.open_mainfile(filepath=str(F/'foundation-v5.blend'));b=bpy.data.objects['SK_BlenderStudioHuman'];r=bpy.data.objects['RIG_BlenderStudioHuman'];foundation=a.binding_hash(b,r);oldtracks=tracks()
bpy.ops.wm.open_mainfile(filepath=str(F/'source.blend'));b=bpy.data.objects['SK_BlenderStudioHuman'];r=bpy.data.objects['RIG_BlenderStudioHuman'];assert a.binding_hash(b,r)==foundation;assert tracks()==oldtracks;keys=b.data.shape_keys;basis=np.array([v.co[:]for v in b.data.vertices],np.float32);ids=data['source_ids'];exterior=np.setdiff1d(np.arange(10582),ids);protected=data['protected_source_ids'];rows=[]
for k,name in enumerate(['OwnershipRightCross','OwnershipLeftCross']):
 expected=basis.copy();expected[ids]+=data['rest_deltas'][k];actual=np.array([v.co[:]for v in keys.key_blocks[name].data],np.float32);assert np.array_equal(expected,actual);assert np.array_equal(actual[exterior],basis[exterior]);assert np.array_equal(actual[protected],basis[protected]);n0=np.array(keys.key_blocks['Basis'].normals_vertex_get(),np.float32).reshape(-1,3);n1=np.array(keys.key_blocks[name].normals_vertex_get(),np.float32).reshape(-1,3);normal_error=float(np.linalg.norm((n1-n0)-data['rest_normal_deltas'][k],axis=1).max());assert normal_error<2e-6;rows.append({'name':name,'actual_POSITION_buffer_sha256':hashlib.sha256(actual.tobytes()).hexdigest(),'exact_archive_composed_buffer':True,'actual_maximum_rest_delta_m':float(np.linalg.norm(actual-basis,axis=1).max()),'exterior_POSITION_maximum_m':0.,'protected_POSITION_maximum_m':0.,'full_source_native_NORMAL_archive_maximum_error':normal_error})
act=bpy.data.actions['Exercise_6014'];slot=next(x for x in act.slots if x.target_id_type=='KEY');curves=[fc for layer in act.layers for strip in layer.strips for bag in strip.channelbags if bag.slot_handle==slot.handle for fc in bag.fcurves];assert len(curves)==2 and all(len(fc.keyframe_points)==151 and all(k.co.y==0 for k in fc.keyframe_points)for fc in curves)
report={'ok':True,'source_sha256':sha(F/'source.blend'),'foundation_sha256':sha(F/'foundation-v5.blend'),'component_sha256':sha(S/'shoulder-ownership-target.npz'),'Basis_topology_UV_rest_binding_signature_unchanged':True,'all_existing_object_animation_channels_bit_exact':True,'object_animation_channel_sha256':oldtracks,'POSITION_ids':1288,'NORMAL_ids':1403,'union_ids':1472,'protected_POSITION_ids':2653,'6014_all151_scalar_keys_exact_zero':True,'states':rows};(F/'component-readback.json').write_text(json.dumps(report,indent=2)+'\n');print('COMPONENT_READBACK',[(x['name'],x['full_source_native_NORMAL_archive_maximum_error'])for x in rows])
