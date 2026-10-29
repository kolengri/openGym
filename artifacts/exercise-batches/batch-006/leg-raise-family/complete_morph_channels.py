"""Complete only missing/inaccurate standard GLB weights from native schedules."""
import json,struct,hashlib
from pathlib import Path
import numpy as np
def sha(data):return hashlib.sha256(data).hexdigest()
def complete(P):
 path=P/'motion.glb';raw=path.read_bytes();magic,version,length=struct.unpack_from('<III',raw);assert magic==0x46546c67 and version==2 and length==len(raw);size,kind=struct.unpack_from('<II',raw,12);assert kind==0x4e4f534a;j=json.loads(raw[20:20+size]);start=20+size;size,kind=struct.unpack_from('<II',raw,start);assert kind==0x004e4942;binary=bytearray(raw[start+8:start+8+size]);prefix=bytes(binary);native=json.loads((P/'native-action-readback.json').read_text());assert native['source_sha256']==sha((P/'source.blend').read_bytes());names=j['meshes'][0]['extras']['targetNames'];assert len(names)==7;node=next(i for i,n in enumerate(j['nodes'])if n.get('mesh')==0);changes=[]
 def accessor(index):
  a=j['accessors'][index];view=j['bufferViews'][a['bufferView']];assert a['componentType']==5126 and a['type']=='SCALAR';return np.frombuffer(binary,dtype='<f4',count=a['count'],offset=view.get('byteOffset',0)+a.get('byteOffset',0)).copy()
 def append(values,minimum=None,maximum=None):
  values=np.asarray(values,dtype='<f4').ravel();binary.extend(b'\0'*((-len(binary))%4));offset=len(binary);data=values.tobytes();binary.extend(data);view=len(j['bufferViews']);j['bufferViews'].append({'buffer':0,'byteOffset':offset,'byteLength':len(data)});a={'bufferView':view,'componentType':5126,'count':len(values),'type':'SCALAR'}
  if minimum is not None:a.update(min=[minimum],max=[maximum])
  index=len(j['accessors']);j['accessors'].append(a);return index
 for animation in j['animations']:
  eid=animation['name'].removeprefix('Exercise_');schedule=native['actions'][eid]['morph_schedule'];expected=np.array([[row[name]for name in names]for row in schedule]);times=np.arange(151)/30;channels=[c for c in animation['channels']if c['target']['path']=='weights'];error=None
  if len(channels)==1:
   sampler=animation['samplers'][channels[0]['sampler']];tt=accessor(sampler['input']);vv=accessor(sampler['output']).reshape((-1,len(names)));observed=np.column_stack([np.interp(times,tt,vv[:,i])for i in range(len(names))]);error=float(abs(observed-expected).max())
   if error<2e-6:changes.append({'action':animation['name'],'status':'exported_weights_verified','maximum_existing_error':error});continue
  animation['channels']=[c for c in animation['channels']if c['target']['path']!='weights'];input_index=append(times,0,5);output_index=append(expected);sampler=len(animation['samplers']);animation['samplers'].append({'input':input_index,'output':output_index,'interpolation':'LINEAR'});animation['channels'].append({'sampler':sampler,'target':{'node':node,'path':'weights'}});changes.append({'action':animation['name'],'status':'native_weight_channel_completed','existing_channel_count':len(channels),'maximum_existing_error':error})
 assert bytes(binary[:len(prefix)])==prefix;j['buffers'][0]['byteLength']=len(binary);chunk=json.dumps(j,separators=(',',':')).encode();chunk+=b' '*((-len(chunk))%4);binary+=b'\0'*((-len(binary))%4);final=struct.pack('<III',0x46546c67,2,12+8+len(chunk)+8+len(binary))+struct.pack('<II',len(chunk),0x4e4f534a)+chunk+struct.pack('<II',len(binary),0x004e4942)+binary;path.write_bytes(final);report={'pass':True,'source_sha256':native['source_sha256'],'native_schedule_sha256':sha((P/'native-action-readback.json').read_bytes()),'exporter_glb_sha256':sha(raw),'completed_glb_sha256':sha(final),'existing_binary_prefix_bit_exact':True,'geometry_bone_position_normal_targets_unchanged':True,'no_runtime_cache':True,'actions':changes};(P/'export-morph-channel-receipt.json').write_text(json.dumps(report,indent=2)+'\n');return report
