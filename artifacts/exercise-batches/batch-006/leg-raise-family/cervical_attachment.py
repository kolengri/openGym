"""One constant sparse additive posterior cervical attachment field."""
import hashlib,json
from pathlib import Path
import numpy as np
P=Path(__file__).resolve().parent
KEY='CervicalAttachment'
def install(body):
 data=np.load(P/'cervical-attachment.npz');ids=data['source_ids'];basis=np.array([v.co[:]for v in body.data.vertices],np.float32);assert np.array_equal(basis[ids],data['source_basis'])
 assert body.data.shape_keys is not None and KEY not in body.data.shape_keys.key_blocks
 baseline={k.name:hashlib.sha256(np.array([v.co[:]for v in k.data],np.float32).tobytes()).hexdigest()for k in body.data.shape_keys.key_blocks}
 points=basis.copy();points[ids]+=data['deltas'];key=body.shape_key_add(name=KEY,from_mix=False);key.data.foreach_set('co',points.ravel());key.value=1.
 actual=np.array([v.co[:]for v in key.data],np.float32);assert np.array_equal(actual,points)
 for name,digest in baseline.items():assert hashlib.sha256(np.array([v.co[:]for v in body.data.shape_keys.key_blocks[name].data],np.float32).tobytes()).hexdigest()==digest
 assert np.array_equal(basis,np.array([v.co[:]for v in body.data.vertices],np.float32))
 return {'key':KEY,'weight':1.,'changed_source_ids':ids.tolist(),'actual_maximum_rest_delta_m':float(np.linalg.norm(actual[ids]-basis[ids],axis=1).max()),'target_sha256_float32':hashlib.sha256(actual.tobytes()).hexdigest(),'prior_key_hashes_unchanged':baseline,'composition':'Exact canonical Basis plus only declared sparse cervical delta; independently additive to the unchanged six lumbar/pelvis support fields.'}

def value_for(exercise_id):
 return json.loads((P/'cervical-action-weights.json').read_text())['weights'][str(exercise_id)]
