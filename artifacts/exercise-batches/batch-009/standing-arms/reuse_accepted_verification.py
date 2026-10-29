"""Transfer unchanged three-action physics only after exact all151 native/DQ identity."""
from pathlib import Path
import json,gzip,hashlib,shutil
F=Path(__file__).resolve().parent;B=F.parent;OLD=F/'checkpoints/2c7213de9cff';IDS=['1404','4515','1405'];sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();read=lambda p:json.loads(p.read_text());source=sha(F/'source.blend');model=sha(F/'motion.glb');ni=read(F/'accepted-native-identity.json');di=read(F/'accepted-decoded-identity.json');oldni=read(OLD/'accepted-native-identity.json');olddi=read(OLD/'accepted-decoded-identity.json');invariants=read(F/'invariant-verification.json');assert invariants['ok']and invariants['source_sha256']==source
with gzip.open(B/'assets/3995/normal-reference.json.gz','rt')as f:normals=json.load(f)
assert normals['source_sha256']==source and len(normals['targets'])==len(invariants['morph_targets'])
for ID in IDS:
 P=B/'assets'/ID;Q=OLD/ID
 assert ni[ID]['final_source_sha256']==source and di[ID]['final_glb_sha256']==model
 for k in ['all151_native_POSITION_max_error_m','all151_native_NORMAL_max_vector_error','all151_51bone_matrix_max_element_error']:assert ni[ID][k]==oldni[ID][k]==0
 for k in ['all151_actual_Three_DQ_POSITION_max_error_m','all151_shader_equivalent_DQ_NORMAL_max_vector_error','all151_51bone_world_matrix_max_element_error']:assert di[ID][k]==olddi[ID][k]==0
 assert ni[ID]['accepted_source_sha256']==oldni[ID]['accepted_source_sha256'];assert di[ID]['accepted_glb_sha256']==olddi[ID]['accepted_glb_sha256']
 receipt={'source_sha256':source,'glb_sha256':model,'measurement_source_sha256':oldni[ID]['final_source_sha256'],'measurement_glb_sha256':olddi[ID]['final_glb_sha256'],'native_identity_receipt_sha256':sha(F/'accepted-native-identity.json'),'decoded_identity_receipt_sha256':sha(F/'accepted-decoded-identity.json'),'frozen_native_identity_receipt_sha256':sha(OLD/'accepted-native-identity.json'),'frozen_decoded_identity_receipt_sha256':sha(OLD/'accepted-decoded-identity.json'),'all151_POSITION_NORMAL_51bone_identity_error':0,'reason':'Only the3995 cuff pose components changed. This action sets every component to zero. Both old and final native/DQ skins, normals and51bone matrices are exactly identical to the same immutable accepted lineage. Prior complete151 physical and game-QA measurements transfer without re-running unchanged checks.','reused_receipts':{}}
 for name in ['surface-contact-report.json','decoded-physical-report.json','source-verification.json','decoded-source-readback.json','runtime-surface-reference.json','surface-landmarks.json','raw-asset-qa.json']:
  d=read(Q/name);assert d['source_sha256']==receipt['measurement_source_sha256'];receipt['reused_receipts'][name]=sha(Q/name);d['measurement_source_sha256']=d['source_sha256'];d['source_sha256']=source;d['identity_transfer']='verification-reuse.json'
  if name in ['decoded-physical-report.json','decoded-source-readback.json']:d['measurement_glb_sha256']=receipt['measurement_glb_sha256'];d['final_glb_sha256']=model
  if name in ['source-verification.json','decoded-source-readback.json']:d['morphs']=invariants['morph_targets']
  (P/name).write_text(json.dumps(d,indent=2)+'\n')
 with gzip.open(Q/'dq-reference.json.gz','rt')as f:d=json.load(f)
 assert d['source_sha256']==receipt['measurement_source_sha256'];d['measurement_source_sha256']=d['source_sha256'];d['source_sha256']=source;d['identity_transfer']='verification-reuse.json'
 with gzip.open(P/'dq-reference.json.gz','wt')as f:json.dump(d,f,separators=(',',':'))
 shutil.copyfile(Q/'pose-samples.json',P/'pose-samples.json');shutil.copyfile(B/'assets/3995/normal-reference.json.gz',P/'normal-reference.json.gz');(P/'verification-reuse.json').write_text(json.dumps(receipt,indent=2)+'\n');print('EXACT_PHYSICS_REUSE',ID,source,model)
