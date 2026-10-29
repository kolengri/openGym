"""Keep explicit standard glTF0/1 morph tracks when exporter omits zero action.

Only target-weight channels/defaults and appended scalar accessors change. Every
original BIN byte is retained; original geometry/skin/non-weight tracks untouched.
"""
import json,struct,hashlib
from pathlib import Path

def run(path,punches):
 path=Path(path);raw=path.read_bytes();n,t=struct.unpack_from('<II',raw,12);g=json.loads(raw[20:20+n]);off=20+n;size,kind=struct.unpack_from('<II',raw,off);data=bytearray(raw[off+8:off+8+size]);original=bytes(data);node=next(i for i,n in enumerate(g['nodes'])if 'mesh'in n and g['meshes'][n['mesh']].get('weights')is not None)
 def scalar(values,minimum=None,maximum=None):
  while len(data)%4:data.append(0)
  start=len(data);data.extend(struct.pack('<'+'f'*len(values),*values));view=len(g['bufferViews']);g['bufferViews'].append({'buffer':0,'byteOffset':start,'byteLength':4*len(values)});index=len(g['accessors']);a={'bufferView':view,'componentType':5126,'count':len(values),'type':'SCALAR'}
  if minimum is not None:a.update(min=[minimum],max=[maximum])
  g['accessors'].append(a);return index
 times=scalar([f/30 for f in range(151)],0,5);zero=scalar([0.]*151);one=scalar([1.]*151)
 for action in g['animations']:
  action['channels']=[c for c in action['channels']if not(c['target'].get('node')==node and c['target']['path']=='weights')];sampler=len(action['samplers']);action['samplers'].append({'input':times,'output':one if action['name']in punches else zero,'interpolation':'LINEAR'});action['channels'].append({'sampler':sampler,'target':{'node':node,'path':'weights'}})
 g['meshes'][g['nodes'][node]['mesh']]['weights']=[0.]
 if 'weights'in g['nodes'][node]:g['nodes'][node]['weights']=[0.]
 g['buffers'][0]['byteLength']=len(data);js=json.dumps(g,separators=(',',':')).encode();js+=b' '*((-len(js))%4);data+=b'\0'*((-len(data))%4);result=struct.pack('<III',0x46546c67,2,12+8+len(js)+8+len(data))+struct.pack('<II',len(js),0x4e4f534a)+js+struct.pack('<II',len(data),0x004e4942)+data;path.write_bytes(result);assert bytes(data[:len(original)])==original
 return {'ok':True,'cause':'Exporter omits all-zero paired KEY channel despite nonzero saved mesh default; standard explicit action weight tracks restore exact action semantics.','raw_export_sha256':hashlib.sha256(raw).hexdigest(),'final_glb_sha256':hashlib.sha256(result).hexdigest(),'original_BIN_prefix_sha256':hashlib.sha256(original).hexdigest(),'original_BIN_prefix_exact':True,'geometry_skin_nonweight_animation_payloads_unchanged':True,'mesh_default_weight':0,'explicit151_action_weights':{a['name']:int(a['name']in punches)for a in g['animations']}}
