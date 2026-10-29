"""Reuse unchanged1987 native receipts after exact151-matrix and binding proof."""
import bpy,sys,json,gzip,hashlib
from pathlib import Path
sys.dont_write_bytecode=True
F=Path(__file__).resolve().parent;P=F.parent/'assets/1987';sys.path.insert(0,str(F.parent.parent/'batch-003'));import authoring as a
j=json.loads((F/'timing-comparison.json').read_text());assert j['maximum_1987_all151_matrix_error']<2e-6
bpy.ops.wm.open_mainfile(filepath=str(P/'source.blend'));b=bpy.data.objects['SK_BlenderStudioHuman'];r=bpy.data.objects['RIG_BlenderStudioHuman'];binding=a.binding_hash(b,r);old=json.loads((F/'timing-baseline/1987/source-verification.json').read_text());assert binding==old['runtime_binding_sha256'];assert not b.data.shape_keys
new=hashlib.sha256((P/'source.blend').read_bytes()).hexdigest();receipt={'baseline_source_sha256':old['source_sha256'],'current_source_sha256':new,'binding_sha256':binding,'all151_actual_native_bone_matrix_max_error':j['maximum_1987_all151_matrix_error'],'existing_native_matrix_tolerance':2e-6,'reason':'Only1986 time parameter changed.1987 native authored action is unchanged within the existing native matrix tolerance; Basis/rest/UV/topology/binding/sourceIDs are exact. Reuse native151 physics, source patches/joints and five diagnostic full-skin references. Actual rebuilt GLB export/decoded transport is checked separately.'}
for name in['surface-contact-report.json','raw-asset-qa.json','source-verification.json','surface-landmarks.json','runtime-surface-reference.json']:
 p=P/name;d=json.loads(p.read_text());d['source_sha256']=new;d['receipt_reuse']=receipt;p.write_text(json.dumps(d,indent=2)+'\n')
for name in['dq-reference.json.gz','normal-reference.json.gz']:
 p=P/name
 with gzip.open(p,'rt')as file:d=json.load(file)
 d['source_sha256']=new;d['receipt_reuse']=receipt
 with gzip.open(p,'wt')as file:json.dump(d,file,separators=(',',':'))
(P/'native-reuse-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
