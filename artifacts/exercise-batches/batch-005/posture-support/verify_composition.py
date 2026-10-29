"""Readback proof of original3 + declared support3 under identical weights."""
import json,sys,hashlib
from pathlib import Path
import bpy,numpy as np
P=Path(__file__).resolve().parent;B=P.parent;S=B.parent/'batch-004/assets/0003'
sys.path[:0]=[str(P),str(B.parent/'batch-003'),str(S)]
import authoring as a,support_sampler as sampler
contract=json.loads((P/'support-contract.json').read_text());records=[];inputs={}
for family in ['2395','5266']:
 a.initialize();bpy.ops.wm.open_mainfile(filepath=str(S/'source.blend'));a.body=bpy.data.objects['SK_BlenderStudioHuman'];a.rig=bpy.data.objects['RIG_BlenderStudioHuman'];a.scene=bpy.context.scene;a.rig.animation_data_clear()
 if family=='2395':
  for name in sampler.KEY_NAMES:
   values=np.array([v.co[:]for v in a.body.data.shape_keys.key_blocks[name].data],dtype=np.float32);assert hashlib.sha256(values.tobytes()).hexdigest()==contract['foundation']['key_coordinate_sha256_float32'][name];inputs[name]=values
  inputs['weight_schedule151']=np.array(contract['foundation']['original151_weight_schedule'],dtype=np.float32)
  np.savez_compressed(P/'support-foundation-keys.npz',**inputs)
 binding=sampler.apply_binding(a.body,a.rig);installed=sampler.install_support(a.body,family);schedule=[]
 for frame in range(151):
  a.scene.frame_set(frame+1);schedule.append([float(a.body.data.shape_keys.key_blocks[n].value)for n in sampler.KEY_NAMES])
 assert schedule==contract['foundation']['original151_weight_schedule']
 assert all(r['composition']['original_input_full_sha256_float32']==contract['foundation']['key_coordinate_sha256_float32'][r['key']]for r in installed['targets'])
 records.append({'family':family,'original151_schedule_exact':True,'support_composition':installed['targets']})
 if family=='2395':(P/'support-binding-authoritative.json').write_text(json.dumps(binding,indent=2)+'\n')
receipt={'method':'Actual complete coordinate readback: delivered3 target buffers equal float32(original3 input + declared sparse additive support3) point by point. Original buffers are retained independently with SHA256. Under the unchanged original weight schedule this equals6 additive components sharing3 weights. Final target hashes intentionally differ from original.','original_source_blend_sha256':contract['source_blend_sha256'],'original_inputs':'support-foundation-keys.npz','original_inputs_sha256':hashlib.sha256((P/'support-foundation-keys.npz').read_bytes()).hexdigest(),'families':records,'ok':True}
(P/'support-composition.json').write_text(json.dumps(receipt,indent=2)+'\n')
contract['foundation']['retained_original_target_components']='support-foundation-keys.npz';contract['foundation']['retained_original_target_components_sha256']=receipt['original_inputs_sha256'];contract['composition']='support-composition.json';contract['composition_sha256']=hashlib.sha256((P/'support-composition.json').read_bytes()).hexdigest();contract['native_sampler']='support_sampler.py';contract['native_sampler_sha256']=hashlib.sha256((P/'support_sampler.py').read_bytes()).hexdigest();contract['authoritative_binding_receipt']='support-binding-authoritative.json';(P/'support-contract.json').write_text(json.dumps(contract,indent=2)+'\n')
print('COMPOSITION_PASS',json.dumps({'families':[r['family']for r in records],'schedule_exact':True,'retained_original_input_sha256':receipt['original_inputs_sha256']}))
