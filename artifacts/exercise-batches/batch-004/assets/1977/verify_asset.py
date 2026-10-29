"""Source-bound invariants, exact-cage witnesses and behind-back contact QA."""
from pathlib import Path
import gzip,hashlib,json,math,sys
import bpy,numpy as np
from mathutils.bvhtree import BVHTree
P=Path(__file__).resolve().parent
sys.path.insert(0,str(P.parents[2]/'batch-003'));import authoring as a
original_binding=a.initialize()
R0=np.array([v.co[:] for v in a.body.data.vertices],np.float32)
W0=[[(g.group,g.weight) for g in v.groups] for v in a.body.data.vertices]
UV0=[np.array([v.uv[:] for v in uv.data],np.float32) for uv in a.body.data.uv_layers]
REST0={b.name:np.array(b.matrix_local,np.float32) for b in a.rig.data.bones}
T0=[list(p.vertices) for p in a.body.data.polygons]
bpy.ops.wm.open_mainfile(filepath=str(P/'source.blend'))
b=bpy.data.objects['SK_BlenderStudioHuman'];r=bpy.data.objects['RIG_BlenderStudioHuman'];s=bpy.context.scene
sha=hashlib.sha256((P/'source.blend').read_bytes()).hexdigest()
R=np.array([v.co[:] for v in b.data.vertices],np.float32);N=np.array([v.normal[:] for v in b.data.vertices],float)
weight=json.loads((P/'local-weight-report.json').read_text());changed=set(weight['affected_source_indices'])
assert np.array_equal(R,R0) and T0==[list(p.vertices) for p in b.data.polygons]
assert len(UV0)==len(b.data.uv_layers) and all(np.array_equal(old,np.array([v.uv[:] for v in uv.data],np.float32)) for old,uv in zip(UV0,b.data.uv_layers))
assert all(np.array_equal(REST0[v.name],np.array(v.matrix_local,np.float32)) for v in r.data.bones)
assert all(W0[v.index]==[(g.group,g.weight) for g in v.groups] for v in b.data.vertices if v.index not in changed)
assert a.binding_hash(b,r)==weight['new_binding']
assert len(R)==10582 and len(r.data.bones)==51 and b.data.shape_keys is None
assert [act.name for act in bpy.data.actions]==['Exercise_1977']
assert all(len(v.groups)<=4 and abs(sum(g.weight for g in v.groups)-1)<1e-6 for v in b.data.vertices)
assert all(m.show_viewport==(m.type=='ARMATURE') and m.show_render==(m.type=='ARMATURE') for m in b.modifiers)
assert not next(m for m in b.modifiers if m.type=='ARMATURE').use_deform_preserve_volume
assert np.array_equal(np.array([v.value for v in b.data.attributes['_SOURCE_INDEX'].data]),np.arange(10582))
b.data.calc_loop_triangles();tri=np.array([t.vertices[:] for t in b.data.loop_triangles]);assert len(tri)==21160
adj=[[] for _ in R]
for e in b.data.edges:i,j=e.vertices;adj[i].append(j);adj[j].append(i)
seen={0};stack=[0]
while stack:
 for j in adj[stack.pop()]:
  if j not in seen:seen.add(j);stack.append(j)
assert len(seen)==10582
regions={}
for p,v in zip(b.data.polygons,b.data.attributes['.sculpt_face_set'].data):regions.setdefault(v.value,set()).update(p.vertices)
def reg(*ids):return np.isin(np.arange(len(R)),sorted(set.union(*(regions[i] for i in ids))))
left_forearm=reg(12);left_hand=reg(9,*range(64,84));right_forearm=reg(11);right_hand=reg(10,*range(84,104))
active=left_forearm|left_hand;grasp=right_hand;wrist=left_forearm&(R[:,2]<1.025)
# Fixed original-coordinate masks exclude the anatomical shared shoulder seam
# while covering the rear torso/pelvis that distal arms pass behind.
trunk=(np.abs(R[:,0])<.145)&(R[:,2]>.87)&(R[:,2]<1.26)
head=(R[:,2]>1.56)&(np.abs(R[:,0])<.17)
patches={}
for label,sign in [('L',1),('R',-1)]:
 sole=(sign*R[:,0]>.13)&(R[:,2]<.012)
 patches['heel_'+label]=sole&(R[:,1]>.025);patches['forefoot_'+label]=sole&(R[:,1]<-.025)
assert all(mask.sum()>5 for mask in patches.values())
faces={}
def tree(xyz,mask):
 key=mask.tobytes()
 if key not in faces:faces[key]=tri[np.all(mask[tri],axis=1)]
 return BVHTree.FromPolygons(xyz.tolist(),faces[key].tolist(),all_triangles=True)
def pair(xyz,A,B):
 ta,tb=tree(xyz,A),tree(xyz,B);nearest=[tb.find_nearest(tuple(xyz[i])) for i in np.flatnonzero(A)]
 distances=np.array([v[3] for v in nearest]);signed=np.array([(xyz[i]-np.array(v[0])).dot(v[1]) for i,v in zip(np.flatnonzero(A),nearest)])
 byid=np.full(len(R),np.inf);byid[np.flatnonzero(A)]=distances;fa=faces[A.tobytes()]
 areas=np.linalg.norm(np.cross(xyz[fa[:,1]]-xyz[fa[:,0]],xyz[fa[:,2]]-xyz[fa[:,0]]),axis=1)*.5
 return {'triangle_intersections':len(ta.overlap(tb)),'minimum_surface_distance_m':float(distances.min()),'minimum_oriented_distance_m':float(signed.min()),'near_12mm_vertices':int((distances<.012).sum()),'near_12mm_area_m2':float(areas[np.all(byid[fa]<.012,axis=1)].sum()),'tested_surface_area_m2':float(areas.sum())}
rows=[];refs=[];verts=[];fail=[];centers={};initial=None;previous=None;maxstep=0;last=None
sampleframes=[0,15,30,45,60,75,90,105,120,135,150]
for f in range(151):
 s.frame_set(f+1);bpy.context.view_layer.update();ev=b.evaluated_get(bpy.context.evaluated_depsgraph_get());m=ev.to_mesh();xyz=np.array([ev.matrix_world@v.co for v in m.vertices]);ev.to_mesh_clear()
 assert len(xyz)==10582 and np.isfinite(xyz).all()
 if initial is None:initial=xyz.copy()
 last=xyz.copy();support={};ref={'id':'1977','frame':f,'global_floor_z':float(xyz[:,2].min()),'floor_plane_z':0,'patches':{}}
 for name,mask in patches.items():
  ids=np.flatnonzero(mask);z=xyz[ids,2];center=xyz[ids].mean(0);centers.setdefault(name,center);drift=float(np.linalg.norm(center-centers[name]))
  support[name]={'count':len(ids),'min_z':float(z.min()),'max_z':float(z.max()),'drift_m':drift,'near_12mm_fraction':float((abs(z)<.012).mean())}
  ref['patches'][name]={'indices':ids.tolist(),'min_z':float(z.min()),'max_z':float(z.max())}
  if z.min()<-.004 or z.min()>.012 or drift>.002:fail.append(f'frame{f}: {name} support')
 measurements={'grasp_to_active':pair(xyz,grasp,active),'grasp_to_wrist':pair(xyz,grasp,wrist),'forearm_to_forearm':pair(xyz,left_forearm,right_forearm),'distal_arms_to_trunk':pair(xyz,active|right_forearm|right_hand,trunk),'hands_to_head':pair(xyz,left_hand|right_hand,head)}
 for label,value in measurements.items():
  if value['triangle_intersections']:fail.append(f'frame{f}: {label} triangle intersections={value["triangle_intersections"]}')
 if 60<=f<=90 and measurements['grasp_to_wrist']['minimum_surface_distance_m']>.012:fail.append(f'frame{f}: wrist grasp gap')
 shoulders={side:list(r.pose.bones[side+'Arm'].head) for side in ['Left','Right']};level=abs(shoulders['Left'][2]-shoulders['Right'][2])
 if level>1e-5:fail.append(f'frame{f}: shoulders not level')
 wrist_angles={side:math.degrees((r.pose.bones[side+'ForeArm'].tail-r.pose.bones[side+'ForeArm'].head).angle(r.pose.bones[side+'Hand'].tail-r.pose.bones[side+'Hand'].head)) for side in ['Left','Right']}
 quats={pb.name:pb.matrix.to_quaternion() for pb in r.pose.bones}
 if previous:maxstep=max(maxstep,max(2*math.acos(min(1,abs(previous[n].dot(q)))) for n,q in quats.items()))
 previous=quats
 rows.append({'frame':f,'global_floor_z':ref['global_floor_z'],'supports':support,**measurements,'shoulder_height_difference_m':level,'wrist_segment_angles_degrees_measured_unapproved':wrist_angles,'bounds':[xyz.min(0).tolist(),xyz.max(0).tolist()]})
 if f in sampleframes:
  refs.append(ref);matrices={pb.name:np.array(pb.matrix@pb.bone.matrix_local.inverted(),float)[:3,:3] for pb in r.pose.bones};normals=np.zeros_like(N)
  for vertex in b.data.vertices:
   for g in vertex.groups:normals[vertex.index]+=g.weight*(matrices[b.vertex_groups[g.group].name]@N[vertex.index])
  normals/=np.linalg.norm(normals,axis=1)[:,None];verts.append({'frame':f,'vertices':xyz.tolist(),'shader_normals':normals.tolist()})
loop=float(np.linalg.norm(initial-last,axis=1).max())
if loop>1e-6:fail.append('loop does not close')
if maxstep>math.radians(20):fail.append('20degree/frame discontinuity diagnostic exceeded')
sys.path.insert(0,str(Path.home()/'.codex/skills/blender-asset-qa/scripts'));import qa_check
checks=[]
for f in [0,30,75]:
 s.frame_set(f+1);bpy.context.view_layer.update();qa=qa_check.run(objects=[b.name],profile='game');checks.append({'frame':f,'qa':qa})
 if not qa['pass']:fail.append(f'frame{f}: standard assetQA errors')
(P/'asset-qa.json').write_text(json.dumps({'source_sha256':sha,'pass':all(x['qa']['pass'] for x in checks),'checks':checks},indent=2)+'\n')
if (P/'native-proof-reference.json').exists():
 proof=json.loads((P/'native-proof-reference.json').read_text());assert proof['source_sha256']==sha
 alpha=[]
 for name,expected in proof['files'].items():
  path=P/name;assert hashlib.sha256(path.read_bytes()).hexdigest()==expected
  image=bpy.data.images.load(str(path),check_existing=False);pixels=np.empty(len(image.pixels),np.float32);image.pixels.foreach_get(pixels);rgba=pixels.reshape(image.size[1],image.size[0],4)
  corners=[float(rgba[y,x,3]) for y,x in [(0,0),(0,-1),(-1,0),(-1,-1)]]
  alpha.append({'file':name,'sha256':expected,'size':list(image.size),'channels':image.channels,'corner_alpha':corners,'maximum_alpha':float(rgba[:,:,3].max())});bpy.data.images.remove(image)
  if max(corners)>0 or alpha[-1]['maximum_alpha']<1:fail.append(name+': native alpha')
 (P/'alpha-report.json').write_text(json.dumps({'source_sha256':sha,'ok':all(max(x['corner_alpha'])==0 and x['channels']==4 for x in alpha),'scope':'Native curated stills only; root owns live canvas alpha.','samples':alpha},indent=2)+'\n')
(P/'runtime-surface-reference.json').write_text(json.dumps({'source_sha256':sha,'source_vertices':10582,'coordinate_frame':'Blender metres, original IDs, Armature-only linear skin','samples':refs},separators=(',',':'))+'\n')
with gzip.open(P/'linear-vertex-reference.json.gz','wt') as out:json.dump(verts,out,separators=(',',':'))
with gzip.open(P/'topology-reference.json.gz','wt') as out:json.dump({'source_sha256':sha,'source_vertices':10582,'triangles':tri.tolist()},out,separators=(',',':'))
(P/'landmarks.json').write_text(json.dumps({'source_sha256':sha,'source_vertices':10582,'definition':'Fixed original source coordinates and sculpt regions, selected before measurement; original IDs unchanged.','patches':{name:np.flatnonzero(mask).tolist() for name,mask in {**patches,'active_left_distal_arm':active,'active_left_wrist':wrist,'assisting_right_hand':grasp,'rear_trunk':trunk}.items()}},indent=2)+'\n')
report={'ok':not fail,'source_sha256':sha,'original_binding_hash':original_binding,'binding_hash':a.binding_hash(b,r),'invariants':{'basis':True,'rest':True,'uv':True,'source_indices':True,'topology':True,'connected_body':True,'vertices':10582,'triangles':21160,'bones':51,'maximum_influences':4,'weights_outside_declared_ids_unchanged':True,'morph_targets':0},'native_and_runtime_path':'Original cage; Armature only, linear; Smooth/Multires disabled.','sampling':'Every runtime frame0..150 at30fps through full entry/hold/return; exact original-ID position and shader-normal witnesses every15frames.','illustration_bands_m':{'proximity':.012,'penetration':.004,'support_drift':.002},'source_vs_staging':'Level shoulders and wrist grasp are source constraints. Standing neutral lower-body setup, one left side, hand orientation, path and numerical joint values are reversible illustration choices.','limitations':'Triangle intersections/proximity are sampled illustration evidence, not clinical limits or exhaustive continuous collision proof. Oriented nearest distance to an open anatomical patch is a diagnostic, not a solid penetration depth. Root owns browser/runtime interactions and final visual acceptance.','loop_max_vertex_error_m':loop,'max_joint_step_radians':maxstep,'failures':fail,'samples':rows}
(P/'surface-contact-report.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'ok':not fail,'failures':fail,'hold':rows[75],'source_sha256':sha}))
assert not fail,fail
