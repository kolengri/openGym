"""Lightweight final saved-source invariant and declared-exterior receipt."""
from pathlib import Path
import bpy,sys,json,hashlib,numpy as np
P=Path(__file__).resolve().parent;sys.path.insert(0,str(P.parents[1]/'batch-003'));import authoring as a
a.initialize();R=np.array([v.co[:] for v in a.body.data.vertices],np.float32);U=[np.array([v.uv[:] for v in u.data],np.float32) for u in a.body.data.uv_layers];T=[list(p.vertices) for p in a.body.data.polygons];B={b.name:np.array(b.matrix_local,np.float32) for b in a.rig.data.bones};W=[{a.body.vertex_groups[g.group].name:float(g.weight) for g in v.groups} for v in a.body.data.vertices]
f=P.parent/'assets/3479/source.blend';bpy.ops.wm.open_mainfile(filepath=str(f));b=bpy.data.objects['SK_BlenderStudioHuman'];r=bpy.data.objects['RIG_BlenderStudioHuman'];report=json.loads((P/'binding-report.json').read_text());declared=set(report['base_report']['affected_source_indices'])|{x['source_id'] for x in report['toe_preserving_plantar_overlay']}
assert np.array_equal(R,np.array([v.co[:] for v in b.data.vertices],np.float32));assert T==[list(p.vertices) for p in b.data.polygons];assert len(U)==len(b.data.uv_layers) and all(np.array_equal(x,np.array([v.uv[:] for v in u.data],np.float32)) for x,u in zip(U,b.data.uv_layers));assert all(np.array_equal(B[bone.name],np.array(bone.matrix_local,np.float32)) for bone in r.data.bones)
indices=np.empty(len(R),np.float32);b.data.attributes['_SOURCE_INDEX'].data.foreach_get('value',indices);assert np.array_equal(indices,np.arange(10582,dtype=np.float32));assert np.array_equal(R,np.array([v.co[:] for v in b.data.shape_keys.key_blocks['Basis'].data],np.float32));changed=[]
for v in b.data.vertices:
 row={b.vertex_groups[g.group].name:float(g.weight) for g in v.groups};assert len(row)<=4 and abs(sum(row.values())-1)<2e-6
 if row!=W[v.index]:assert v.index in declared;changed.append(v.index)
maxdelta=0
for state in json.loads((P/'joint-target-report.json').read_text())['states']:
 X=np.array([v.co[:] for v in b.data.shape_keys.key_blocks[state['name']].data],np.float32);mask=np.zeros(len(R),bool);mask[state['source_ids']]=True;assert np.array_equal(X[~mask],R[~mask]);delta=float(np.linalg.norm(X-R,axis=1).max());assert delta<=.025001;maxdelta=max(maxdelta,delta)
assert all(t.mute for t in b.data.shape_keys.animation_data.nla_tracks) and not b.data.shape_keys.animation_data.use_nla
out={'ok':True,'source_sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'basis_exact':True,'rest_exact':True,'uv_exact':True,'topology_exact':True,'source_ids_exact':True,'bones':len(r.data.bones),'source_vertices':len(R),'triangles':sum(len(p.vertices)-2 for p in b.data.polygons),'maximum_influences':max(len(v.groups) for v in b.data.vertices),'actual_changed_binding_vertices':len(changed),'declared_binding_vertices':len(declared),'binding_exterior_exact':True,'corrective_exteriors_exact':True,'maximum_saved_source_target_delta_m':maxdelta,'nla_discovery':'Inactive KEY association3480 is explicitly muted with use_nla=False; only the selected active action evaluates natively.'};(P/'invariant-report.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
