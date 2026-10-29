"""Freeze explicit delivery lists; never glob trials, logs, environments or frame caches."""
from pathlib import Path
import json,hashlib
F=Path(__file__).resolve().parent;ROOT=F.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,d):p.write_text(json.dumps(d,indent=2)+'\n')
def row(base,name):
 p=base/name;assert p.is_file(),p
 return {'path':name,'sha256':sha(p),'bytes':p.stat().st_size}
def manifest(p,data):
 data['included_files'].append({'path':'curated-files.json','self':True})
 data['self_integrity']={'algorithm':'SHA256','canonicalization':'UTF-8 compact JSON sorted keys excluding self_integrity; no newline','sha256':hashlib.sha256(json.dumps(data,sort_keys=True,separators=(',',':')).encode()).hexdigest()};write(p,data)
def dep(name,role):
 p=ROOT/name;return{'path':name,'sha256':sha(p),'role':role}
deps=[dep(name,role)for name,role in [
 ('artifacts/exercise-batches/batch-008/assets/6539/source.blend','Accepted exact native resting source; action identity only changes'),
 ('artifacts/exercise-batches/batch-008/assets/6539/motion.glb','Accepted exact resting GLB binary/samplers/morphs'),
 ('artifacts/exercise-batches/batch-008/assets/6539/delivery-report.json','Accepted resting mechanics/GPU lineage and retained fold warnings'),
 ('artifacts/exercise-batches/batch-008/resting-reuse/native-identity.json','Prior4365→6539 native exact identity receipt'),
 ('artifacts/exercise-batches/batch-008/resting-reuse/decoded-identity.json','Prior4365→6539 actual decoded identity receipt'),
 ('artifacts/exercise-batches/batch-008/assets/4935/source.blend','Accepted unchanged prone binding; old action removed'),
 ('artifacts/exercise-batches/batch-008/assets/4935/local-binding-report.json','Accepted prone binding signature'),
 ('artifacts/exercise-batches/batch-003/authoring.py','Invariant source rig math/helper extraction'),
 ('artifacts/bodyweight-five/bodyweight-five.blend','Canonical CC0 Basis/rest/UV/topology source'),
 ('artifacts/bodyweight-five/build_motion.py','Read-only rig math functions extracted by authoring helper'),
 ('artifacts/exercise-batches/batch-007/prone-family/palm_frame.py','Source-derived true palm plane frame'),
 ('artifacts/exercise-batches/dual-quaternion.js','Unchanged DQ POSITION/NORMAL shared adapter'),
 ('artifacts/exercise-batches/batch-007/resting-repair/resting_checks.py','Established source shoulder attachment ROI; diagnostic scope only'),
 ('artifacts/first-exercise-3d/runtime/package-lock.json','Existing project runtime dependency lock'),
 ('/Users/kolengri/.codex/skills/blender-asset-qa/scripts/qa_check.py','Mandatory game profile QA implementation'),
 ('/Users/kolengri/.codex/skills/blender-asset-qa/scripts/review_shots.py','Native solid/wire review implementation'),
 ('artifacts/exercise-batches/batch-009/asset-interface.json','Current asset interface'),
 ('artifacts/exercise-batches/batch-009/authoring-handoff.md','Authoring acceptance contract'),
 ('artifacts/exercise-batches/batch-009/source-resolutions.json','Source-specific staging boundary'),
 ('catalogue/exercises/1315.json','Source instruction labels/hold'),
 ('catalogue/exercises/4663.json','Source instruction labels'),
 ('artifacts/exercise-batches/batch-009/contexts/1315.json','Current intake context'),
 ('artifacts/exercise-batches/batch-009/contexts/4663.json','Current intake context')]]
rest=['source.blend','motion.glb','clip.json','cameras.json','authoring-context.json','landmarks.json','pose-samples.json','runtime-surface-reference.json','source-morph-samples.json','dq-reference.json.gz','joint-normal-reference.json.gz','topology-reference.json.gz','source-verification.json','surface-contact-report.json','asset-qa.json','export-verification.json','runtime-physics-report.json','delivery-report.json','proof-receipt.json','README.md','wire-peak.png']+[f'neutral-{p}-{v}.png'for p in ['start','peak','return']for v in ['side','oblique']]
prone=['source.blend','motion.glb','clip.json','cameras.json','authoring-context.json','pose-samples.json','runtime-surface-reference.json','surface-landmarks.json','dq-reference.json.gz','normal-reference.json.gz','source-verification.json','surface-contact-report.json','raw-asset-qa.json','export-verification.json','decoded-physical-report.json','decoded-source-readback.json','delivery-report.json','local-binding-report.json','early-proof-readback.json','README.md']+[f'early-{p}-{v}_whole_body.png'for p in ['start','intermediate','peak','lower','return']for v in ['side','oblique']]+[f'qa-{mode}{suffix}.png'for mode in ['random','wire']for suffix in ['','_right','_top','_three_quarter','_bottom']]
reports=[]
for id,names in [('1315',rest),('4663',prone)]:
 A=F.parent/'assets'/id
 if id=='4663'and not(A/'delivery-report.json').exists():continue
 provenance={'id':id,'source_catalogue':next(x for x in deps if x['path']==f'catalogue/exercises/{id}.json'),'source_resolution':'../../source-resolutions.json','source_facts_vs_staging':'Source instructions and muscle roles remain in catalogue/clip; numeric demonstration timing,contact tolerance and joint angles are authored choices.','canonical_license':'CC0 Blender Studio human; original canonical source IDs/Basis/rest/UV/topology and51bones preserved.','direct_reuse':{'1315':'Accepted6539 action/binary payload exact with new identity; all151 identity receipts in family.','4663':'Accepted4935 binding only; independent keyed chest/arm path with invariant grounded legs.'}[id],'read_only_dependencies':deps,'source_sha256':sha(A/'source.blend'),'glb_sha256':sha(A/'motion.glb'),'no_restricted_visual_derivative':True,'no_runtime_vertex_frame_cache':True}
 write(A/'source-provenance.json',provenance);names=names+['source-provenance.json']
 manifest(A/'curated-files.json',{'id':id,'status':'local_native_decoded_QA_complete_primary_integration_pending','source_and_motion_frozen':True,'source_sha256':sha(A/'source.blend'),'glb_sha256':sha(A/'motion.glb'),'included_files':[row(A,n)for n in names],'read_only_dependencies':deps,'root_integration_may_update':['clip.json','cameras.json'],'excluded':['*.log','__pycache__','*.blend1','trials','temporary decoded exchanges','environments','runtime vertex/frame caches']});reports.append(json.loads((A/'delivery-report.json').read_text()))
write(F/'delivery-report.json',{'family':'batch009-floor','assets':reports,'read_only_dependencies':deps,'source_and_motion_frozen':True,'root_owned_remaining':['actual GPU integration acceptance','artistic muscle fields','camera widths','shared viewer','Git/publication'],'owned_scope':['floor-family/','assets/1315/','assets/4663/']})
names=['README.md','clone_rest.py','clone_rest_metadata.py','verify_rest_identity.mjs','rest-native-identity.json','rest-decoded-identity.json','rest-reuse-lineage.json','build.py','motion.py','export_motion.py','verify_native.py','verify_export.mjs','review.py','write_metadata.py','finalize_report.py','check-scope-reconciliation.json','package.py','delivery-report.json']
manifest(F/'curated-files.json',{'family':'batch009-floor','delivery_assets':[r['id']for r in reports],'included_files':[row(F,n)for n in names]+[row(F,'../assets/'+r['id']+'/curated-files.json')for r in reports],'read_only_dependencies':deps,'excluded':['*.log','__pycache__','inspect_support.py','trials','temporary decoded exchanges','environment','backups','runtime vertex/frame caches']})
print(json.dumps({'frozen':[{'id':r['id'],'source_sha256':r['source_sha256'],'glb_sha256':r['glb_sha256']}for r in reports]}))
