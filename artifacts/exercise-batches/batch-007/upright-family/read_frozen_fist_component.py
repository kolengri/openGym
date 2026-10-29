"""Actual two-source key-buffer equivalence; JSON component is authoritative."""
import bpy,json,hashlib,numpy as np
from pathlib import Path
F=Path(__file__).resolve().parent;out={}
for batch,ID in [('batch-007','4437'),('batch-006','3531')]:
 P=F.parents[1]/batch/'assets'/ID;source=P/'source.blend';bpy.ops.wm.open_mainfile(filepath=str(source));b=bpy.data.objects['SK_BlenderStudioHuman'];R=np.array([v.co[:]for v in b.data.vertices]);key=np.array([v.co[:]for v in b.data.shape_keys.key_blocks['Fist_Dorsal_MCP'].data]);recipe=json.loads((F/'fist-component.json').read_text());delta=np.zeros_like(R);delta[recipe['source_ids']]=recipe['source_deltas_m'];expected=(R+delta).astype(np.float32);assert np.array_equal(key.astype(np.float32),expected);out[ID]={'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'actual_key_coordinates_sha256':hashlib.sha256(key.astype(np.float32).tobytes()).hexdigest(),'actual_exact_float32_component':True,'basis_unchanged':bool(np.array_equal(np.array([v.co[:]for v in b.data.shape_keys.key_blocks['Basis'].data]),R))}
assert out['4437']['actual_key_coordinates_sha256']==out['3531']['actual_key_coordinates_sha256'];(F/'fist-two-source-readback.json').write_text(json.dumps({'ok':True,'same_actual_key_buffer':True,'sources':out},indent=2)+'\n');print(out)
