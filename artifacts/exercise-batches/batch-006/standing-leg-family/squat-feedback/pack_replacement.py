"""Replace only3479 animation; original3480 and physical GLB bytes stay exact."""
from pathlib import Path
import json,hashlib,struct,copy
P=Path(__file__).resolve().parent;B=P.parents[1];oldpath=B/'assets/3480/motion.glb';newpath=P/'replacement-curves.glb';sha=lambda b:hashlib.sha256(b).hexdigest()
def read(path):
 data=path.read_bytes();n=struct.unpack_from('<I',data,12)[0];doc=json.loads(data[20:20+n]);offset=20+n;count,kind=struct.unpack_from('<I4s',data,offset);assert kind==b'BIN\0';return doc,data[offset+8:offset+8+count]
old,originalbin=read(oldpath);fresh,freshbin=read(newpath);assert sha(oldpath.read_bytes())=='3fc9b638106efc8cb697fc49f5149535cb3e45d81f6d3b875788feaaa5c7c96d';doc=copy.deepcopy(old);binary=bytearray(originalbin);viewmap={};accessormap={}
def accessor(index):
 if index in accessormap:return accessormap[index]
 src=copy.deepcopy(fresh['accessors'][index]);assert 'sparse' not in src;vi=src['bufferView']
 if vi not in viewmap:
  view=copy.deepcopy(fresh['bufferViews'][vi]);start=view.get('byteOffset',0);payload=freshbin[start:start+view['byteLength']];binary.extend(b'\0'*((-len(binary))%4));view['buffer']=0;view['byteOffset']=len(binary);binary.extend(payload);viewmap[vi]=len(doc['bufferViews']);doc['bufferViews'].append(view)
 src['bufferView']=viewmap[vi];accessormap[index]=len(doc['accessors']);doc['accessors'].append(src);return accessormap[index]
replacement=copy.deepcopy(next(a for a in fresh['animations'] if a['name']=='Exercise_3479'));nodes={x['name']:i for i,x in enumerate(old['nodes']) if 'name' in x};assert len(nodes)==len(old['nodes']);assert fresh['meshes'][0]['extras']['targetNames']==old['meshes'][0]['extras']['targetNames']
for sampler in replacement['samplers']:
 sampler['input']=accessor(sampler['input']);sampler['output']=accessor(sampler['output'])
for channel in replacement['channels']:channel['target']['node']=nodes[fresh['nodes'][channel['target']['node']]['name']]
doc['animations']=[replacement if a['name']=='Exercise_3479' else a for a in doc['animations']];doc['buffers'][0]['byteLength']=len(binary);binary.extend(b'\0'*((-len(binary))%4));js=json.dumps(doc,separators=(',',':')).encode();js+=b' '*((-len(js))%4);out=B/'assets/3479/motion.glb';out.write_bytes(struct.pack('<4sII',b'glTF',2,28+len(js)+len(binary))+struct.pack('<I4s',len(js),b'JSON')+js+struct.pack('<I4s',len(binary),b'BIN\0')+binary)
assert bytes(binary[:len(originalbin)])==originalbin
assert next(a for a in old['animations'] if a['name']=='Exercise_3480')==next(a for a in doc['animations'] if a['name']=='Exercise_3480')
for key in ['meshes','skins','nodes','scenes','materials']:assert old[key]==doc[key]
report={'ok':True,'method':'Copy original complete standard GLB physical data and all original BIN bytes, append only newly exported3479 animation accessor views, replace only Exercise_3479 animation object. No runtime adapter or geometry regeneration.','baseline_glb_sha256':sha(oldpath.read_bytes()),'new_glb_sha256':sha(out.read_bytes()),'original_bin_bytes':len(originalbin),'original_bin_prefix_sha256_before':sha(originalbin),'original_bin_prefix_sha256_after':sha(bytes(binary[:len(originalbin)])),'3480_animation_json_exact':True,'3480_input_output_accessor_and_payload_bytes_exact':True,'meshes_skins_nodes_scenes_materials_exact':True,'new_animation_accessors':len(accessormap),'new_animation_views':len(viewmap),'old_3480_file_untouched':sha(oldpath.read_bytes())=='3fc9b638106efc8cb697fc49f5149535cb3e45d81f6d3b875788feaaa5c7c96d'};(P/'export-preservation-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
