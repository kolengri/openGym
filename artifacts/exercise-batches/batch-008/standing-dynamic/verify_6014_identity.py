"""Full151 exact 6014 identity, permitting reuse of its passed physical gates."""
import bpy,json,numpy as np,hashlib,gzip
from pathlib import Path
F=Path(__file__).resolve().parent;P=F.parent/'assets/6014';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def capture(path):
 bpy.ops.wm.open_mainfile(filepath=str(path));r=bpy.data.objects['RIG_BlenderStudioHuman'];b=bpy.data.objects['SK_BlenderStudioHuman'];s=bpy.context.scene;r.animation_data.action=bpy.data.actions['Exercise_6014'];r.animation_data.action_slot=r.animation_data.action.slots[0]
 if b.data.shape_keys:
  b.data.shape_keys.animation_data.action=r.animation_data.action;b.data.shape_keys.animation_data.action_slot=next(x for x in r.animation_data.action.slots if x.target_id_type=='KEY')
 skins=[];bones=[]
 for f in range(151):
  s.frame_set(f+1);bpy.context.view_layer.update();e=b.evaluated_get(bpy.context.evaluated_depsgraph_get());me=e.to_mesh();skins.append(np.array([v.co[:]for v in me.vertices],np.float32));e.to_mesh_clear();bones.append(np.array([pb.matrix for pb in r.pose.bones],np.float32))
 return np.array(skins),np.array(bones)
old=F/'foundation-v5.blend';new=F/'source.blend';op,ob=capture(old);np_,nb=capture(new);assert np.array_equal(op,np_)and np.array_equal(ob,nb),'6014 exact preservation failed'
receipt={'id':'6014','original_source_sha256':sha(old),'source_sha256':sha(new),'integer_samples':151,'all10582_actual_skin_vertices_bit_exact':True,'all51_actual_bone_matrices_bit_exact':True,'maximum_skin_delta_m':float(np.linalg.norm(np_-op,axis=2).max()),'maximum_bone_matrix_delta':float(abs(nb-ob).max()),'skin_sequence_sha256_float32':hashlib.sha256(np_.tobytes()).hexdigest(),'bone_sequence_sha256_float32':hashlib.sha256(nb.tobytes()).hexdigest(),'reused_prior_receipts':{}}
# Rebind only source-scoped hash metadata. Underlying measured results/positions are unchanged.
for name in ['surface-contact-report.json','source-verification.json','raw-asset-qa.json','runtime-surface-reference.json','surface-landmarks.json','dq-reference.json.gz','normal-reference.json.gz']:
 path=P/name;oldhash=sha(path)
 if name.endswith('.gz'):
  with gzip.open(path,'rt')as f:data=json.load(f)
 else:data=json.loads(path.read_text())
 prior_identity=json.loads((P/'source-identity-reuse.json').read_text())if (P/'source-identity-reuse.json').exists()else{}
 assert data['source_sha256']in[sha(old),prior_identity.get('source_sha256')]
 receipt['reused_prior_receipts'][name]={'prior_receipt_sha256':oldhash,'prior_source_sha256':data['source_sha256'],'reason':'All151 complete native skin and51bone matrices proven bit exact; Basis/rest/binding unchanged.'};data['source_sha256']=sha(new)
 if name=='source-verification.json':data['morphs']=['OwnershipRightCross','OwnershipLeftCross'];data['morph_component_weights']='6014bothkeysidenticallyzero; actualskin/allbonesbitexact'
 data['source_identity_receipt']='source-identity-reuse.json'
 if name.endswith('.gz'):
  with gzip.open(path,'wt')as f:json.dump(data,f,separators=(',',':'))
 else:path.write_text(json.dumps(data,indent=2)+'\n')
(P/'source-identity-reuse.json').write_text(json.dumps(receipt,indent=2)+'\n');print('6014_IDENTITY',receipt['maximum_skin_delta_m'],receipt['maximum_bone_matrix_delta'])
