"""Complete Blender5.2's omitted second KEY action with standard glTF weights.

This writes normal glTF animation data, not a vertex cache or runtime adapter.
The source body's actual151 saved-action weights remain the sole inputs.
"""
from pathlib import Path
import json,struct,hashlib

def sha(b):return hashlib.sha256(b).hexdigest()
def complete(P):
 path=P/'motion.glb';data=path.read_bytes();magic,version,length=struct.unpack_from('<III',data);assert magic==0x46546c67 and version==2 and length==len(data)
 size,kind=struct.unpack_from('<II',data,12);assert kind==0x4e4f534a;j=json.loads(data[20:20+size]);offset=20+size;size,kind=struct.unpack_from('<II',data,offset);assert kind==0x004e4942;binary=bytearray(data[offset+8:offset+8+size]);assert len(j['buffers'])==1
 names=j['meshes'][0]['extras']['targetNames'];assert len(names)==6
 mesh_nodes=[i for i,node in enumerate(j['nodes'])if node.get('mesh')==0];assert len(mesh_nodes)==1;node=mesh_nodes[0]
 animation=next(a for a in j['animations']if a['name']=='Exercise_4354');assert not any(c['target']['path']=='weights'for c in animation['channels'])
 source_path=P.parent/'assets/4354/source-morph-samples.json';source=json.loads(source_path.read_text());assert source['source_sha256']==sha((P/'source.blend').read_bytes());assert [s['frame']for s in source['samples']]==list(range(151))
 times=[row['frame']/30 for row in source['samples']];weights=[row['weights'][name]for row in source['samples']for name in names]
 base_prefix=bytes(binary);views=[]
 def append(values,count,minimum=None,maximum=None):
  while len(binary)%4:binary.append(0)
  start=len(binary);raw=struct.pack('<'+'f'*len(values),*values);binary.extend(raw);view=len(j['bufferViews']);j['bufferViews'].append({'buffer':0,'byteOffset':start,'byteLength':len(raw)})
  accessor={'bufferView':view,'componentType':5126,'count':count,'type':'SCALAR'}
  if minimum is not None:accessor['min']=[minimum];accessor['max']=[maximum]
  index=len(j['accessors']);j['accessors'].append(accessor);views.append({'byte_offset':start,'byte_length':len(raw),'sha256':sha(raw),'accessor':index});return index
 input_index=append(times,len(times),0,5);output_index=append(weights,len(weights));sampler=len(animation['samplers']);animation['samplers'].append({'input':input_index,'output':output_index,'interpolation':'LINEAR'});animation['channels'].append({'sampler':sampler,'target':{'node':node,'path':'weights'}})
 assert bytes(binary[:len(base_prefix)])==base_prefix
 j['buffers'][0]['byteLength']=len(binary);jsonchunk=json.dumps(j,separators=(',',':')).encode();jsonchunk+=b' '*((-len(jsonchunk))%4);binary+=b'\0'*((-len(binary))%4)
 final=struct.pack('<III',0x46546c67,2,12+8+len(jsonchunk)+8+len(binary))+struct.pack('<II',len(jsonchunk),0x4e4f534a)+jsonchunk+struct.pack('<II',len(binary),0x004e4942)+binary;path.write_bytes(final)
 report={'pass':True,'method':__doc__,'source_sha256':source['source_sha256'],'native_morph_schedule_sha256':sha(source_path.read_bytes()),'exporter_glb_before_sha256':sha(data),'completed_glb_sha256':sha(final),'added_action':'Exercise_4354','added_path':'weights','target_node':node,'target_names':names,'frames':151,'interpolation':'LINEAR','existing_binary_prefix_bit_exact':True,'existing_binary_prefix_sha256':sha(base_prefix),'existing_json_preserved_except_buffers_length_accessors_views_and_added_weights_channel':True,'added_binary_views':views,'geometry_bones_position_normal_targets_changed':False,'source_changed':False,'runtime_cache_written':False}
 (P/'export-morph-channel-receipt.json').write_text(json.dumps(report,indent=2)+'\n');return report
if __name__=='__main__':print(json.dumps(complete(Path(__file__).resolve().parent)))
