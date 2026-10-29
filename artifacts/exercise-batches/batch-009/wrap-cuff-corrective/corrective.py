"""Install one source-bound 3995 cuff POSITION/NORMAL pose component.

This importer does not edit binding, existing keys, action slots, or keyframes.
The standing author owns the explicit scalar animation/reset and export.
"""
from pathlib import Path
import hashlib,json,struct
import numpy as np
F=Path(__file__).resolve().parent
ARCHIVE='wrap-cuff-target.npz'
KEY='WrapRightOverCuff'
BINDING_SHA256='6c3c40b3a5ba6fcbe33e75b6599b21233b8ad03d29b0bd028e0efcff967f1b38'
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def binding_signature(body,rig):
 h=hashlib.sha256()
 for v in body.data.vertices:
  h.update(np.array(v.co,np.float32).tobytes())
  for g in v.groups:h.update(struct.pack('<If',g.group,g.weight))
 for p in body.data.polygons:h.update(np.array(p.vertices,np.int32).tobytes())
 for uv in body.data.uv_layers:
  values=np.empty(len(uv.data)*2,np.float32);uv.data.foreach_get('uv',values);h.update(uv.name.encode()+values.tobytes())
 for bone in rig.data.bones:h.update(bone.name.encode()+np.array(bone.matrix_local,np.float32).tobytes())
 return h.hexdigest()
def install(body,rig,scene=None,archive_path=None,expected_sha256=None):
 path=Path(archive_path)if archive_path else F/ARCHIVE
 if expected_sha256 is None and archive_path is None:expected_sha256=json.loads((F/'component.json').read_text())['archive_sha256']
 if expected_sha256 is not None:assert sha(path)==expected_sha256,'Cuff archive hash mismatch'
 assert binding_signature(body,rig)==BINDING_SHA256,'Canonical source geometry/binding differs'
 assert len(body.data.vertices)==10582 and len(rig.data.bones)==51
 data=np.load(path);ids=data['source_ids'];basis=np.array([v.co[:]for v in body.data.vertices],np.float32)
 assert np.array_equal(basis[ids],data['source_basis']),'Cuff source IDs/Basis differ'
 keys=body.data.shape_keys;assert keys is not None
 expected=json.loads((F/'capture.json').read_text())['old_shape_key_hashes']
 before={name:hashlib.sha256(np.array([v.co[:]for v in keys.key_blocks[name].data],np.float32).tobytes()).hexdigest()for name in expected}
 assert before==expected,'An accepted existing shoulder target changed'
 target=basis.copy();target[ids]+=data['rest_deltas']
 if KEY in keys.key_blocks:
  key=keys.key_blocks[KEY];assert np.array_equal(np.array([v.co[:]for v in key.data],np.float32),target),'A different cuff target already exists'
 else:key=body.shape_key_add(name=KEY,from_mix=False);key.data.foreach_set('co',target.ravel())
 key.relative_key=keys.key_blocks['Basis'];key.value=0.
 for name,digest in before.items():assert hashlib.sha256(np.array([v.co[:]for v in keys.key_blocks[name].data],np.float32).tobytes()).hexdigest()==digest
 assert binding_signature(body,rig)==BINDING_SHA256
 return data

def value(frame,exercise):
 """C1 suggested envelope only; author must validate the integrated trajectory."""
 if exercise!='3995':return 0.
 phase=(float(frame)%75.)/75.;p=np.sin(np.pi*phase)**2
 return float(p)
