"""Shared deterministic invariant hashing; no Blender mutations."""
import hashlib,numpy as np
def weights(body):return[{body.vertex_groups[g.group].name:float(g.weight)for g in v.groups}for v in body.data.vertices]
def invariant(body,rig):
 h=hashlib.sha256()
 for v in body.data.vertices:h.update(np.array(v.co,np.float32).tobytes())
 for f in body.data.polygons:h.update(np.array(f.vertices,np.int32).tobytes())
 for uv in body.data.uv_layers:
  values=np.empty(len(uv.data)*2,np.float32);uv.data.foreach_get('uv',values);h.update(uv.name.encode()+values.tobytes())
 for bone in rig.data.bones:h.update(bone.name.encode()+np.array(bone.matrix_local,np.float32).tobytes())
 return h.hexdigest()
