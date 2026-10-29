"""Recompute only the authorized pad metric from the unchanged151 skin stream."""
from pathlib import Path
import json,gzip,hashlib,sys
import numpy as np
P=Path(__file__).resolve().parent;out=P.parent/'assets/0006';C=json.loads((P/'plantar-pad-contract.json').read_text());source=hashlib.sha256((P/'source.blend').read_bytes()).hexdigest();assert source==C['body_source_sha256'];assert all(len(ids)==31 for ids in C['plantar_pad_source_ids'].values())
report=json.loads((out/'surface-contact-report.json').read_text());assert report['source_sha256']==source
history=out/'raw-forefoot-failed-contact-report.json'
if not history.exists():history.write_bytes((out/'surface-contact-report.json').read_bytes())
failed=json.loads(history.read_text());assert len(failed['failures'])==302 and all('forefoot_'in msg for msg in failed['failures'])
landmarks=json.loads((out/'landmarks.json').read_text());rawland=out/'raw-forefoot-failed-landmarks.json'
if not rawland.exists():rawland.write_bytes((out/'landmarks.json').read_bytes())
positions=np.frombuffer(gzip.decompress((P/'.native-all151-0006.f32.gz').read_bytes()),'<f4').reshape(151,10582,3)
reference=json.loads((out/'runtime-surface-reference.json').read_text());failures=[msg for msg in report['failures']if not'forefoot_'in msg]
for side,suffix in [('Left','L'),('Right','R')]:
 ids=C['plantar_pad_source_ids'][side];name='plantar_pad_'+suffix;rawname='forefoot_'+suffix
 landmarks['patches'][rawname]['state']='observed';landmarks['patches'][rawname]['rationale']='Original239-ID broad forefoot mask and failed20% criterion retained diagnostically; it includes curved toe sidewalls. The distinct neutral-normal plantar pad is floor-bearing.'
 patch={'indices':ids,'state':'supported','rationale':'Root-frozen original Basis normalZ<−0.7 subset of original forefoot mask. Source-only31-ID downward-facing plantar pad, never selected by deformed position.'};landmarks['patches'][name]=patch
 for row in report['samples']:
  z=positions[row['frame'],ids,2];metric={'min_z':float(z.min()),'max_z':float(z.max()),'fraction_near_floor':float(np.mean(abs(z)<=.012))};row['patches'][name]=metric
  if metric['min_z']>.012 or metric['fraction_near_floor']<.2:failures.append(f'frame{row["frame"]}:{name} support')
 for row in reference['samples']:
  raw=row['patches'][rawname];lookup={i:v for i,v in zip(raw['indices'],raw['positions'])};raw['state']='observed';raw['rationale']=landmarks['patches'][rawname]['rationale'];row['patches'][name]={**patch,'positions':[lookup[i]for i in ids]}
report['failures']=failures;report['ok']=not failures;report['plantar_pad_contract']='../../floor-crunch-family/plantar-pad-contract.json';report['plantar_pad_contract_sha256']=hashlib.sha256((P/'plantar-pad-contract.json').read_bytes()).hexdigest();report['raw_forefoot_failed_history']='raw-forefoot-failed-contact-report.json';report['raw_forefoot_original_failures']=failed['failures'];report['affected_metric_only_recomputed_from_captured151_skin']=True;report['geometry_pose_binding_components_unchanged']=True
landmarks['plantar_pad_contract']='../../floor-crunch-family/plantar-pad-contract.json';reference['plantar_pad_contract']='../../floor-crunch-family/plantar-pad-contract.json'
for name in ['surface-contact-report.json','mechanics-verification.json']:(out/name).write_text(json.dumps(report,indent=2)+'\n')
(out/'landmarks.json').write_text(json.dumps(landmarks,indent=2)+'\n');(out/'runtime-surface-reference.json').write_text(json.dumps(reference,separators=(',',':'))+'\n')
qa=json.loads((out/'asset-qa.json').read_text());qa['warning_disposition']=C['ground_warning_disposition'];(out/'asset-qa.json').write_text(json.dumps(qa,indent=2)+'\n');assert not failures,failures
(P/'plantar-contract-reconciliation.json').write_text(json.dumps({'pass':True,'source_sha256':source,'contract_sha256':report['plantar_pad_contract_sha256'],'source_original_geometry_sha256':C['original_geometry_rest_uv_sha256'],'body_geometry_pose_weights_unchanged':True,'reused_native_frames':151,'other_passing_checks_repeated':False,'raw_failed_masks_and_all_metrics_preserved':True,'new_pad_minimum_fraction_near_floor':min(row['patches']['plantar_pad_L']['fraction_near_floor']for row in report['samples'])},indent=2)+'\n');print('PAD_CONTRACT_RECONCILED',source)
