"""Check actual exported surfaces streamed per frame; never store a frame cache."""
from pathlib import Path
import sys,json,hashlib,struct
import bpy,numpy as np
from mathutils.bvhtree import BVHTree
P=Path(__file__).resolve().parent;bpy.ops.wm.open_mainfile(filepath=str(P/'source.blend'));b=bpy.data.objects['SK_BlenderStudioHuman'];r=bpy.data.objects['RIG_BlenderStudioHuman'];s=bpy.context.scene
assert r.animation_data.action.name=='Exercise_3948';assert b.data.shape_keys.animation_data.action.name=='Exercise_3948'
R=np.array([v.co[:] for v in b.data.vertices]);b.data.calc_loop_triangles();T=np.array([t.vertices[:] for t in b.data.loop_triangles]);restarea=np.linalg.norm(np.cross(R[T[:,1]]-R[T[:,0]],R[T[:,2]]-R[T[:,0]]),axis=1)*.5
patches=json.loads((P/'landmarks.json').read_text())['patches'];sole={n:np.array(ids,int) for n,ids in patches.items() if 'sole_' in n or n.startswith('heel_') or n.startswith('forefoot_')}
def faces(ids):mask=np.zeros(len(R),bool);mask[ids]=True;return np.flatnonzero(np.all(mask[T],axis=1))
armids=faces(patches['both_arms_hands']);legids=faces(patches['both_legs']);local={n:faces(patches[n]) for n in ['pelvis_thigh','knees','shoulders']}
def tree(X,ids):return BVHTree.FromPolygons(X.tolist(),T[ids].tolist(),all_triangles=True)
def exactread(n):
 out=bytearray()
 while len(out)<n:
  chunk=sys.stdin.buffer.read(n-len(out))
  if not chunk:raise EOFError((len(out),n))
  out.extend(chunk)
 return out
rows=[];fail=[];initial=None;centers={};maximumparity=0;witnesses={};witnesslookup={}
for expected in range(151):
 frame,count=struct.unpack('<II',exactread(8));assert frame==expected and count==10582
 X=np.frombuffer(exactread(count*12),'<f4').reshape(count,3).astype(float);N=np.frombuffer(exactread(count*12),'<f4').reshape(count,3).astype(float)
 assert np.isfinite(X).all() and np.isfinite(N).all()
 s.frame_set(frame+1);bpy.context.view_layer.update();ev=b.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh();native=np.array([ev.matrix_world@v.co for v in me.vertices]);ev.to_mesh_clear()
 parity=float(np.linalg.norm(X-native,axis=1).max());maximumparity=max(maximumparity,parity)
 if parity>1e-5:fail.append(f'{frame}: actual export/native vertex parity')
 if initial is None:initial=X.copy()
 floor=float(X[:,2].min());support={}
 if floor<-1e-6:fail.append(f'{frame}: body/floor')
 for name,ids in sole.items():
  z=X[ids,2];center=X[ids].mean(0);centers.setdefault(name,center);drift=float(np.linalg.norm(center-centers[name]));support[name]={'vertices':len(ids),'min_z':float(z.min()),'max_z':float(z.max()),'centroid_drift_m':drift}
  if z.min()<-1e-6 or z.min()>.012 or drift>.002:fail.append(f'{frame}: {name} support')
 arm,leg=tree(X,armids),tree(X,legids);intersections=len(arm.overlap(leg));distance=min(leg.find_nearest(tuple(X[i]))[3] for i in patches['both_arms_hands'])
 if intersections:fail.append(f'{frame}: whole arms/hands vs legs')
 cross=np.cross(X[T[:,1]]-X[T[:,0]],X[T[:,2]]-X[T[:,0]]);area=np.linalg.norm(cross,axis=1)*.5;regions={}
 for name,tids in local.items():
  tri=T[tids];bt=tree(X,tids);pairs=[(int(tids[i]),int(tids[j])) for i,j in bt.overlap(bt) if i<j and not set(tri[i])&set(tri[j])];refs=[]
  for a,c in pairs:
   key=f'{a}:{c}'
   if key not in witnesslookup:
    wid=len(witnesses);witnesslookup[key]=wid;ids=sorted(set(T[a])|set(T[c]));witnesses[str(wid)]={'source_triangle_ids':[a,c],'source_triangles':[T[a].tolist(),T[c].tolist()],'original_vertices':[{'id':int(i),'basis':R[i].tolist(),'weights':{b.vertex_groups[g.group].name:float(g.weight) for g in b.data.vertices[i].groups}} for i in ids],'first_frame':frame,'frames':[]}
   wid=witnesslookup[key];witnesses[str(wid)]['frames'].append(frame);refs.append(wid)
  dots=(cross[tids]*N[tri].mean(1)).sum(1);regions[name]={'triangles':len(tids),'minimum_area_m2':float(area[tids].min()),'minimum_area_ratio':float((area[tids]/restarea[tids]).min()),'maximum_area_ratio':float((area[tids]/restarea[tids]).max()),'opposed_runtime_shader_normal_faces':int((dots<=0).sum()),'disjoint_self_intersection_pairs':len(pairs),'crossing_witness_ids':refs}
  if area[tids].min()<1e-10:fail.append(f'{frame}: {name} degenerate area')
 rows.append({'frame':frame,'native_action':r.animation_data.action.name,'key_values':{k.name:k.value for k in b.data.shape_keys.key_blocks if k.name!='Basis'},'maximum_native_position_error_m':parity,'minimum_body_z':floor,'floor_plane_z':0,'sole_support':support,'whole_arms_hands_vs_legs':{'triangle_intersections':intersections,'minimum_surface_distance_m':distance},'local_faces':regions})
loop=float(np.linalg.norm(X-initial,axis=1).max())
if loop>1e-5:fail.append('loop closure')
report={'ok':not fail,'scope':'Actual project Three.js GLTFLoader+AnimationMixer+LBS/morph surface at every30Hz frame0..150, streamed directly to Blender BVHTree geometry checks. No stored runtime frame cache.','source_sha256':hashlib.sha256((P/'source.blend').read_bytes()).hexdigest(),'glb_sha256':hashlib.sha256((P/'motion.glb').read_bytes()).hexdigest(),'actual_source_action_readback':'Exercise_3948; KEY action Exercise_3948, second canonical action references exact same glTF samples.','sampling':{'frames':151,'step_frames':1,'fps':30,'native_frame_origin':1},'maximum_native_position_error_m':maximumparity,'loop_maximum_vertex_error_m':loop,'self_fold_policy':'Exact nonadjacent self-fold pairs and opposed shader normals are localized diagnostics; root accepted bounded candidate shape for user review. This is not a zero-self-collision claim. Gross visible reversal or penetration remains blocking.','candidate_approval':'Root visual review accepted corrective25 side/rear/oblique for user review; production approval not granted.','failures':fail,'samples':rows,'crossing_witnesses':witnesses}
(P/'runtime-physics-report.json').write_text(json.dumps(report,indent=2)+'\n')
print('RUNTIME_PHYSICS_JSON',json.dumps({'ok':not fail,'frames':151,'maximum_native_position_error_m':maximumparity,'minimum_body_z':min(x['minimum_body_z'] for x in rows),'minimum_arm_leg_distance_m':min(x['whole_arms_hands_vs_legs']['minimum_surface_distance_m'] for x in rows),'failures':fail[:10]}),flush=True)
if fail:raise RuntimeError(fail[:10])
