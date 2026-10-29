"""Read GLB buffers directly: source IDs, normals, skin and keyed morph timing."""
import gzip,hashlib,json,math,struct
from pathlib import Path
P=Path(__file__).resolve().parent;raw=(P/'motion.glb').read_bytes();n,kind=struct.unpack_from('<II',raw,12);doc=json.loads(raw[20:20+n]);offset=20+n;binary=raw[offset+8:]
sizes={5120:('b',1),5121:('B',1),5122:('h',2),5123:('H',2),5125:('I',4),5126:('f',4)};width={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT4':16}
def unpack_view(index,component,count,w,extra=0):
 view=doc['bufferViews'][index];fmt,size=sizes[component];stride=view.get('byteStride',size*w);start=view.get('byteOffset',0)+extra
 return [list(struct.unpack_from('<'+fmt*w,binary,start+i*stride)) for i in range(count)]
def read(index):
 a=doc['accessors'][index];w=width[a['type']];values=unpack_view(a['bufferView'],a['componentType'],a['count'],w,a.get('byteOffset',0)) if 'bufferView' in a else [[0]*w for _ in range(a['count'])]
 if 'sparse' in a:
  s=a['sparse'];indices=unpack_view(s['indices']['bufferView'],s['indices']['componentType'],s['count'],1,s['indices'].get('byteOffset',0));patch=unpack_view(s['values']['bufferView'],a['componentType'],s['count'],w,s['values'].get('byteOffset',0))
  for i,v in zip(indices,patch):values[i[0]]=v
 return values
def length(v):return math.sqrt(sum(x*x for x in v))
def yup(v):return [v[0],v[2],-v[1]]
fail=[]
def check(value,reason):
 if not value:fail.append(reason)
primitives=[p for m in doc['meshes'] for p in m['primitives']];check(len(doc['meshes'])==len(doc['skins'])==len(primitives)==1,'Expected one mesh/skin/primitive');p=primitives[0];a=p['attributes']
check(len(doc['skins'][0]['joints'])==51,'Original bone count changed');check(len(read(p['indices']))//3==21160,'Triangle count changed');check(not doc.get('textures') and not doc.get('images'),'Textures present');check(len(doc['materials'])==1,'Material count changed')
ids=[round(v[0]) for v in read(a['_SOURCE_INDEX'])];check(set(ids)==set(range(10582)),'Incomplete original source IDs');check(all(abs(sum(w)-1)<1e-5 for w in read(a['WEIGHTS_0'])),'Weights not normalized')
check(all(max(j)<51 for j in read(a['JOINTS_0'])),'Skin joint out of range');check(len(p['targets'])==4 and all('POSITION' in t and 'NORMAL' in t for t in p['targets']),'Expected four POSITION/NORMAL morphs')
names=doc['meshes'][0]['extras']['targetNames'];source_sha=hashlib.sha256((P/'source.blend').read_bytes()).hexdigest()
with gzip.open(P/'ninety-normal-reference.json.gz','rt') as f:norm=json.load(f)
check(norm['source_sha256']==source_sha,'Normal reference source hash differs')
basis=read(a['NORMAL']);base_error=max(length([v[j]-yup(norm['basis'][sid])[j] for j in range(3)]) for sid,v in zip(ids,basis));normal_errors={}
for name,t in zip(names,p['targets']):
 deltas=read(t['NORMAL']);errors=[]
 for sid,b,d in zip(ids,basis,deltas):
  expected=yup(norm['targets'][name][sid]);actual=[b[j]+d[j] for j in range(3)];errors.append(length([actual[j]-expected[j] for j in range(3)]))
 normal_errors[name]=max(errors)
check(base_error<.0001 and max(normal_errors.values())<.0001,'Exported rest/morph normals differ from source')
check({v['name'] for v in doc['animations']}=={'Exercise_10565','Exercise_6560'},'Animation set differs');morph_samples=[]
for animation in doc['animations']:
 channels=[v for v in animation['channels'] if v['target']['path']=='weights'];check(len(channels)==1,'Expected one weights channel per action')
 sampler=animation['samplers'][channels[0]['sampler']];times=[v[0] for v in read(sampler['input'])];weights=[v[0] for v in read(sampler['output'])];check(abs(times[0])<1e-6 and abs(times[-1]-5)<1e-6,'Animation duration differs')
 for t in [0,1,2.5,4,5]:
  i=min(range(len(times)),key=lambda i:abs(times[i]-t));actual=weights[i*4:(i+1)*4];u=max(0,min(1,t/2 if t<2 else 1 if t<=3 else (5-t)/2));h=u*u*(3-2*u);identifier=animation['name'].removeprefix('Exercise_');expected=[(1-h if name.endswith('Upright') else h) if identifier in name else 0 for name in names];error=max(abs(x-y) for x,y in zip(actual,expected));check(error<.00001,'Morph activation differs');morph_samples.append({'action':animation['name'],'time':t,'weights':actual,'error':error})
report={'ok':not fail,'failures':fail,'source_sha256':source_sha,'glb_sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'meshes':1,'skins':1,'bones':51,'triangles':21160,'source_vertices':10582,'exported_uv_split_vertices':len(ids),'materials':1,'textures':0,'animations':[v['name'] for v in doc['animations']],'position_morphs':4,'normal_morphs':4,'target_names':names,'basis_normal_error_max':base_error,'target_normal_error_max':normal_errors,'normal_comparison_scope':'All exported UV-split vertices against source rest normal witnesses. Actual GPU DQ/morph raster appearance remains primary-owned.','morph_samples':morph_samples,'actual_threejs_visual_acceptance':False}
(P/'export-verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2));assert not fail,fail
