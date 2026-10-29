"""Exact canonical/existing-component invariants and declared cuff support."""
import bpy,sys,json,hashlib,numpy as np
from pathlib import Path
sys.dont_write_bytecode=True
F=Path(__file__).resolve().parent;OLD=F.parent.parent/'batch-008/standing-dynamic';sys.path[:0]=[str(F),str(F.parent.parent/'batch-003')];import authoring as a
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def snapshot(b,r):
 return {'binding':a.binding_hash(b,r),'basis':np.array([v.co[:]for v in b.data.vertices],np.float32),'faces':[list(v.vertices)for v in b.data.polygons],'uv':[(v.name,np.array([x.uv[:]for x in v.data],np.float32))for v in b.data.uv_layers],'bones':[(v.name,np.array(v.matrix_local,np.float32))for v in r.data.bones],'keys':{k.name:np.array([v.co[:]for v in k.data],np.float32)for k in b.data.shape_keys.key_blocks}}
bpy.ops.wm.open_mainfile(filepath=str(OLD/'source.blend'));base=snapshot(bpy.data.objects['SK_BlenderStudioHuman'],bpy.data.objects['RIG_BlenderStudioHuman']);bpy.ops.wm.open_mainfile(filepath=str(F/'source.blend'));b=bpy.data.objects['SK_BlenderStudioHuman'];r=bpy.data.objects['RIG_BlenderStudioHuman'];cur=snapshot(b,r)
assert cur['binding']==base['binding'];assert np.array_equal(cur['basis'],base['basis']);assert cur['faces']==base['faces'];assert len(cur['uv'])==len(base['uv'])and all(x[0]==y[0]and np.array_equal(x[1],y[1])for x,y in zip(cur['uv'],base['uv']));assert len(cur['bones'])==len(base['bones'])and all(x[0]==y[0]and np.array_equal(x[1],y[1])for x,y in zip(cur['bones'],base['bones']));assert set(base['keys']).issubset(cur['keys'])and all(np.array_equal(cur['keys'][n],base['keys'][n])for n in base['keys']);assert len(cur['basis'])==10582 and len(cur['bones'])==51
components=json.loads((F/'cuff-component-dependency.json').read_text());new_components=[components]+([components['midpoint']]if 'midpoint'in components else[]);assert set(cur['keys'])-set(base['keys'])=={c['key']for c in new_components}
def source_normals(coords):
 me=bpy.data.meshes.new('ComponentNormalInvariant');me.from_pydata(coords,[],cur['faces'])
 for face,original in zip(me.polygons,b.data.polygons):face.use_smooth=original.use_smooth
 me.update();out=np.array([v.normal[:]for v in me.vertices],np.float32);bpy.data.meshes.remove(me);return out
basis_normal=source_normals(cur['basis']);reports={};deltas={}
for dependency in new_components:
 name=dependency['key'];archive=Path(dependency['archive_path']);assert sha(archive)==dependency['archive_sha256'];data=np.load(archive);ids=data['source_ids'];delta=cur['keys'][name]-cur['basis'];deltas[name]=delta;exterior=np.ones(10582,bool);exterior[ids]=False
 assert np.array_equal(delta[exterior],np.zeros_like(delta[exterior]));assert np.array_equal(cur['basis'][ids],data['source_basis']);assert np.array_equal(cur['keys'][name][ids],(cur['basis'][ids]+data['rest_deltas']).astype(np.float32));maximum=float(np.linalg.norm(delta,axis=1).max());assert maximum<=.175+1e-7
 normal_delta=source_normals(cur['keys'][name])-basis_normal;normal_error=float(np.linalg.norm(normal_delta-data['rest_normal_deltas'],axis=1).max());assert normal_error<2e-6;normal_exterior=np.ones(10582,bool);normal_exterior[data['position_normal_union_source_ids']]=False;assert float(np.linalg.norm(normal_delta[normal_exterior],axis=1).max())<2e-6
 reports[name]={'archive_sha256':sha(archive),'declared_POSITION_source_ids':ids.tolist(),'changed_POSITION_source_ids':np.flatnonzero(np.linalg.norm(delta,axis=1)>0).tolist(),'maximum_rest_delta_m':maximum,'outside_support_POSITION_delta_m':0.,'archive_NORMAL_maximum_vector_error':normal_error,'declared_POSITION_NORMAL_union_source_ids':data['position_normal_union_source_ids'].tolist(),'outside_union_NORMAL_maximum_vector_delta':float(np.linalg.norm(normal_delta[normal_exterior],axis=1).max())}
import motion
max_blend=0.
for frame in range(151):
 values=motion.morph_values(frame,'3995');assert values[0]==values[1]==0 and min(values[2:])>=-1e-12 and sum(values[2:])<=1+1e-12;combined=sum((deltas[name]*weight for name,weight in zip(motion.MORPH_NAMES[2:],values[2:])),np.zeros_like(cur['basis']));max_blend=max(max_blend,float(np.linalg.norm(combined,axis=1).max()))
assert max_blend<=.175+1e-7;assert set(x.name for x in bpy.data.objects if x.type=='MESH')=={b.name};assert len(b.data.materials)==1
report={'ok':True,'source_sha256':sha(F/'source.blend'),'accepted_foundation_sha256':sha(OLD/'source.blend'),'runtime_binding_sha256':cur['binding'],'basis_rest_uv_topology_vertex_order_and_binding_exact':True,'existing_components_exact':list(base['keys'])[1:],'existing_component_sha256':{n:hashlib.sha256(v.tobytes()).hexdigest()for n,v in base['keys'].items()if n!='Basis'},'vertices':10582,'bones':51,'triangles':sum(len(p)-2 for p in cur['faces']),'meshes':1,'materials':1,'morph_targets':motion.MORPH_NAMES,'new_components':reports,'all151_convexity_checked':True,'maximum_all151_convex_rest_delta_m':max_blend,'source_delta_cap_m':.175,'bound_reason':'Nonnegative absolute-target coefficients sum to at most1; per-vertex unit-DQ rotation preserves the norm of the blended rest-position delta.'}
(F/'invariant-verification.json').write_text(json.dumps(report,indent=2)+'\n');print('INVARIANTS',json.dumps({k:v for k,v in report.items()if k!='new_components'}))
