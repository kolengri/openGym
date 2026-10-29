"""Append explicit standard glTF 151-key morph tracks for every action."""
import json,struct,hashlib,sys
from pathlib import Path
sys.dont_write_bytecode=True
F=Path(__file__).resolve().parent;sys.path.insert(0,str(F));import motion

def run(path):
 path=Path(path);raw=path.read_bytes();n,_=struct.unpack_from('<II',raw,12);g=json.loads(raw[20:20+n]);off=20+n;size,_=struct.unpack_from('<II',raw,off);data=bytearray(raw[off+8:off+8+size]);original=bytes(data);node=next(i for i,n in enumerate(g['nodes'])if 'mesh'in n and g['meshes'][n['mesh']].get('weights')is not None)
 def scalar(vals,bounds=None):
  while len(data)%4:data.append(0)
  start=len(data);data.extend(struct.pack('<'+'f'*len(vals),*vals));view=len(g['bufferViews']);g['bufferViews'].append({'buffer':0,'byteOffset':start,'byteLength':4*len(vals)});index=len(g['accessors']);a={'bufferView':view,'componentType':5126,'count':len(vals),'type':'SCALAR'}
  if bounds:a.update(min=[bounds[0]],max=[bounds[1]])
  g['accessors'].append(a);return index
 count=len(g['meshes'][g['nodes'][node]['mesh']]['weights']);times=scalar([f/30 for f in range(151)],(0,5));summary={}
 for action in g['animations']:
  ID=action['name'].split('_')[-1];vals=[v for f in range(151)for v in motion.morph_values(f,ID)];assert len(vals)==151*count;output=scalar(vals);action['channels']=[c for c in action['channels']if not(c['target'].get('node')==node and c['target']['path']=='weights')];sampler=len(action['samplers']);action['samplers'].append({'input':times,'output':output,'interpolation':'LINEAR'});action['channels'].append({'sampler':sampler,'target':{'node':node,'path':'weights'}});summary[action['name']]={'targets':count,'keys':151,'minimum':min(vals),'maximum':max(vals),'all_zero':all(v==0 for v in vals)}
 g['meshes'][g['nodes'][node]['mesh']]['weights']=[0.]*count
 if 'weights'in g['nodes'][node]:g['nodes'][node]['weights']=[0.]*count
 g['buffers'][0]['byteLength']=len(data);js=json.dumps(g,separators=(',',':')).encode();js+=b' '*((-len(js))%4);data+=b'\0'*((-len(data))%4);result=struct.pack('<III',0x46546c67,2,12+8+len(js)+8+len(data))+struct.pack('<II',len(js),0x4e4f534a)+js+struct.pack('<II',len(data),0x004e4942)+data;path.write_bytes(result);assert bytes(data[:len(original)])==original
 return {'ok':True,'semantics':'Explicit standard scalar tracks for every morph target in every action, with neutral mesh/node defaults. No runtime reset workaround.','original_BIN_prefix_exact':True,'original_BIN_prefix_sha256':hashlib.sha256(original).hexdigest(),'raw_export_sha256':hashlib.sha256(raw).hexdigest(),'final_glb_sha256':hashlib.sha256(result).hexdigest(),'actions':summary}
