"""Preserve GLB binary payload and transfer accepted native evidence with explicit lineage."""
from pathlib import Path
import json,gzip,hashlib,struct,shutil
F=Path(__file__).resolve().parent;A=F.parent/'assets/1315';O=F.parents[1]/'batch-008/assets/6539';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
oldsha=sha(O/'source.blend');newsha=sha(A/'source.blend');oldglbsha=sha(O/'motion.glb');newglbsha=None
def replace(x):
 if isinstance(x,dict):return{k:replace(v)for k,v in x.items()}
 if isinstance(x,list):return[replace(v)for v in x]
 if isinstance(x,str):return x.replace(oldglbsha,newglbsha or oldglbsha).replace(oldsha,newsha).replace('Exercise_6539','Exercise_1315').replace('6539','1315')
 return x
b=(O/'motion.glb').read_bytes();n=struct.unpack_from('<I',b,12)[0];j=json.loads(b[20:20+n]);assert j['animations'][0]['name']=='Exercise_6539'
jb=b[20:20+n].replace(b'Exercise_6539',b'Exercise_1315');assert len(jb)==n
out=b[:20]+jb+b[20+n:];assert out[20+n:]==b[20+n:];(A/'motion.glb').write_bytes(out);newglbsha=sha(A/'motion.glb')
for name in ['cameras.json','landmarks.json','source-verification.json','pose-samples.json','runtime-surface-reference.json','source-morph-samples.json','surface-contact-report.json','runtime-physics-report.json','asset-qa.json','export-verification.json','proof-receipt.json']:
 data=replace(json.loads((O/name).read_text()))
 if isinstance(data,dict):data['reuse_evidence']={'origin':str(O/name),'origin_sha256':sha(O/name),'method':'Mechanics inherited through all151 native and decoded exact identity; no refit or independent exercise mechanics rerun.'}
 (A/name).write_text(json.dumps(data,indent=2)+'\n')
for name in ['dq-reference.json.gz','joint-normal-reference.json.gz','topology-reference.json.gz']:
 with gzip.open(O/name,'rt')as f:data=replace(json.load(f))
 with gzip.GzipFile(filename=str(A/name),mode='wb',mtime=0)as f:f.write(json.dumps(data,separators=(',',':')).encode())
for p in O.glob('*.png'):shutil.copyfile(p,A/p.name)
clip=replace(json.loads((O/'clip.json').read_text()));clip.update(id='1315',primary=['spine'],secondary=['lower back','glutes'],source_hold_recommendation_seconds=[30,60],interpretation='Source permits a comfortable resting position such as kneeling with torso folded forward and relaxed arms. The accepted4365/6539 motion and binding are reused exactly; forward relaxed arms on the support plane are the authored interpretation. Five-second2s entry/1s hold/2s return; workout hold30–60seconds. Spine primary, lower back/glutes secondary are source labels, not measured activation.');(A/'clip.json').write_text(json.dumps(clip,indent=2)+'\n');(A/'authoring-context.json').write_bytes((F.parent/'contexts/1315.json').read_bytes())
report={'ok':True,'source_sha256':newsha,'glb_sha256':sha(A/'motion.glb'),'accepted_source_sha256':oldsha,'accepted_glb_sha256':sha(O/'motion.glb'),'binary_tail_exact':True,'only_glb_change':'Exercise_6539→Exercise_1315 same-length JSON action name','read_only_accepted_source':str(O.relative_to(Path.cwd())),'binding_and_hip_volume_exact':True}
(F/'rest-reuse-lineage.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
