"""Apply the ONE frozen proximal-glute candidate; primary shape review owns use.

No fitting or parameter selection occurs here. The JSON stores the exact source
IDs and before/after weights from the harmonic reconstruction in5266.
"""
import hashlib,json
from pathlib import Path
import numpy as np
P=Path(__file__).resolve().parent

def install(body):
 path=P/'glute-binding-repair.json';recipe=json.loads(path.read_text())
 assert len(body.data.vertices)==10582
 protected=json.loads((P/'support-protected-domain.json').read_text())['protected_source_ids']
 def vertex_weights(i):return{body.vertex_groups[g.group].name:float(g.weight)for g in body.data.vertices[i].groups}
 frozen={i:vertex_weights(i)for i in protected}
 basis=np.array([v.co[:]for v in body.data.vertices],np.float32)
 targets={k.name:np.array([v.co[:]for v in k.data],np.float32)for k in body.data.shape_keys.key_blocks}
 changed=[]
 for item in recipe['changes']:
  i=item['id'];assert i not in frozen
  current=vertex_weights(i);assert current==item['before'],('Unexpected glute binding input',i,current,item['before'])
  for name in current:body.vertex_groups[name].remove([i])
  for name,value in item['after'].items():body.vertex_groups[name].add([i],value,'REPLACE')
  changed.append(i)
 assert frozen=={i:vertex_weights(i)for i in protected}
 assert np.array_equal(basis,np.array([v.co[:]for v in body.data.vertices],np.float32))
 assert all(np.array_equal(value,np.array([v.co[:]for v in body.data.shape_keys.key_blocks[name].data],np.float32))for name,value in targets.items())
 assert max(len(v.groups)for v in body.data.vertices)<=4
 assert max(abs(sum(g.weight for g in body.data.vertices[i].groups)-1)for i in changed)<2e-6
 return {'method':recipe['method'],'recipe_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'changed_original_vertex_ids':changed,'protected97_weights_exact':True,'all_existing_target_buffers_exact':True,'basis_exact':True,'maximum_influences':4,'refit_performed':False}
