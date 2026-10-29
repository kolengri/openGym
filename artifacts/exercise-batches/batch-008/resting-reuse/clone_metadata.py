"""Identity-only GLB/receipt lineage for accepted4365→6539 reuse."""
from pathlib import Path
import json,gzip,hashlib,struct,copy
P=Path(__file__).resolve().parent;A=P.parent/'assets/6539';OLD=P.parents[1]/'batch-007/assets/4365'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
oldsha=sha(OLD/'source.blend');newsha=sha(A/'source.blend')
def replace(x):
 if isinstance(x,dict):return {k:replace(v) for k,v in x.items()}
 if isinstance(x,list):return [replace(v) for v in x]
 if isinstance(x,str):return x.replace(oldsha,newsha).replace('Exercise_4365','Exercise_6539').replace('4365','6539')
 return x
# Same-length JSON identity rename leaves every binary accessor byte untouched.
b=(OLD/'motion.glb').read_bytes();n=struct.unpack_from('<I',b,12)[0];j=json.loads(b[20:20+n]);assert len(j['animations'])==1 and j['animations'][0]['name']=='Exercise_4365'
newj=b[20:20+n].replace(b'Exercise_4365',b'Exercise_6539');assert len(newj)==n
out=b[:20]+newj+b[20+n:];(A/'motion.glb').write_bytes(out);jj=json.loads(newj);jj['animations'][0]['name']='Exercise_4365';assert jj==j and out[20+n:]==b[20+n:]
for name in ['cameras.json','landmarks.json','source-verification.json','pose-samples.json','runtime-surface-reference.json','source-morph-samples.json']:
 (A/name).write_text(json.dumps(replace(json.loads((OLD/name).read_text())),indent=2)+'\n')
for name in ['dq-reference.json.gz','joint-normal-reference.json.gz','topology-reference.json.gz']:
 with gzip.open(OLD/name,'rt')as f:data=replace(json.load(f))
 with gzip.GzipFile(filename=str(A/name),mode='wb',mtime=0)as f:f.write(json.dumps(data,separators=(',',':')).encode())
clip=replace(json.loads((OLD/'clip.json').read_text()));clip.update(id='6539',primary=['lats'],secondary=['shoulders','lower back'],source_hold_recommendation_seconds=[20,30],interpretation='The title says armless, while the explicit source instructions require both arms reaching forward. Follow the instructions: kneel, sit toward heels, reach forward and lower the chest with forehead near the floor. Exact accepted4365 motion is reused without refitting; five seconds demonstrate2s entry/1s hold/2s return. Workout hold20–30seconds.');(A/'clip.json').write_text(json.dumps(clip,indent=2)+'\n')
(A/'authoring-context.json').write_bytes((P.parent/'contexts/6539.json').read_bytes())
for name in ['verify_export.mjs','verify_runtime.mjs','verify_runtime.py']:
 text=(P.parents[1]/'batch-007/resting-repair'/name).read_text().replace('4365','6539')
 if name.endswith('.py'):text=text.replace('from runtime_checks import SurfaceChecks',"sys.path.insert(0,str(P.parents[1]/'batch-007/resting-repair'));from runtime_checks import SurfaceChecks")
 (P/name).write_text(text)
report={'ok':True,'new_source_sha256':newsha,'new_glb_sha256':sha(A/'motion.glb'),'reused_source_sha256':oldsha,'reused_glb_sha256':sha(OLD/'motion.glb'),'binary_tail_sha256':hashlib.sha256(b[20+n:]).hexdigest(),'binary_geometry_weights_morphs_animation_samplers_exact':True,'glb_json_equal_except_action_name':True,'native_identity_receipt':'native-identity.json','source_changed_only_action_identity':True,'reference_lineage':'Native refs cloned by exact151 skin/matrix/morph identity; actual decoded151 identity independently measured next. No geometry, weight, posture, support, morph or timing fit.','source_hold_recommendation_seconds':[20,30],'primary':['lats']}
(P/'reuse-lineage.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
