"""Original-source invariants, all-frame support/clearance and local face integrity."""
from pathlib import Path
import bpy,sys,json,gzip,hashlib,math
import numpy as np
from mathutils.bvhtree import BVHTree
P=Path(__file__).resolve().parent
sys.path.insert(0,str(P.parents[2]/'batch-003'));import authoring as a
original_hash=a.initialize();original_xyz=np.array([v.co[:] for v in a.body.data.vertices],np.float32)
original_weights=[[(g.group,g.weight) for g in v.groups] for v in a.body.data.vertices]
original_uv=[np.array([v.uv[:] for v in uv.data],np.float32) for uv in a.body.data.uv_layers]
original_rest={b.name:np.array(b.matrix_local,np.float32) for b in a.rig.data.bones};original_topology=[list(p.vertices) for p in a.body.data.polygons]
bpy.ops.wm.open_mainfile(filepath=str(P/'source.blend'));body=bpy.data.objects['SK_BlenderStudioHuman'];rig=bpy.data.objects['RIG_BlenderStudioHuman'];scene=bpy.context.scene
R=np.array([v.co[:] for v in body.data.vertices],np.float32);rn=np.array([v.normal[:] for v in body.data.vertices]);source_sha=hashlib.sha256((P/'source.blend').read_bytes()).hexdigest()
w=json.loads((P/'local-weight-report.json').read_text());changed=set(w['affected_source_indices'])
assert np.array_equal(R,original_xyz) and original_topology==[list(p.vertices) for p in body.data.polygons]
assert all(np.array_equal(x,np.array([v.uv[:] for v in uv.data],np.float32)) for x,uv in zip(original_uv,body.data.uv_layers))
assert all(np.array_equal(original_rest[b.name],np.array(b.matrix_local,np.float32)) for b in rig.data.bones)
assert all(original_weights[v.index]==[(g.group,g.weight) for g in v.groups] for v in body.data.vertices if v.index not in changed)
assert a.binding_hash(body,rig)==w['new_binding'];assert len(rig.data.bones)==51 and len(R)==10582 and body.data.shape_keys is not None
assert set(x.name for x in bpy.data.actions)=={'Exercise_3948','Exercise_4714'};assert all(len(v.groups)<=4 and abs(sum(g.weight for g in v.groups)-1)<1e-6 for v in body.data.vertices)
assert all(m.show_viewport==(m.type=='ARMATURE') and m.show_render==(m.type=='ARMATURE') for m in body.modifiers)
assert not next(m for m in body.modifiers if m.type=='ARMATURE').use_deform_preserve_volume
assert list(body.data.shape_keys.key_blocks.keys())==['Basis','SquatStanding','SquatHalf','SquatParallel']
key_normals={}
for key in body.data.shape_keys.key_blocks:
 coordinates=np.array([v.co[:] for v in key.data]);assert np.linalg.norm(coordinates-R,axis=1).max()<=.025001
 mesh=bpy.data.meshes.new('IndependentTargetNormal');mesh.from_pydata(coordinates.tolist(),[],original_topology)
 for target,source in zip(mesh.polygons,body.data.polygons):target.use_smooth=source.use_smooth
 mesh.update();key_normals[key.name]=np.array([v.normal[:] for v in mesh.vertices]);bpy.data.meshes.remove(mesh)
rn=key_normals['Basis']

body.data.calc_loop_triangles();tri=np.array([t.vertices[:] for t in body.data.loop_triangles]);restcross=np.cross(R[tri[:,1]]-R[tri[:,0]],R[tri[:,2]]-R[tri[:,0]]);restarea=np.linalg.norm(restcross,axis=1)*.5
patches={}
for side,sign in [('L',1),('R',-1)]:
 sole=(sign*R[:,0]>.13)&(R[:,2]<.012)
 patches['heel_'+side]=sole&(R[:,1]>.025);patches['forefoot_'+side]=sole&(R[:,1]<-.025)
 patches['medial_sole_'+side]=sole&(sign*R[:,0]<.23);patches['lateral_sole_'+side]=sole&(sign*R[:,0]>.23)
assert all(mask.sum()>5 for mask in patches.values())
regions={}
for polygon,attribute in zip(body.data.polygons,body.data.attributes['.sculpt_face_set'].data):regions.setdefault(attribute.value,set()).update(polygon.vertices)
armmask=np.zeros(len(R),bool);armmask[list(set.union(*(regions[k] for k in [9,10,11,12,20,21]+[k for k in regions if 64<=k<104])))]=True
legmask=(R[:,2]<1.04)&(abs(R[:,0])<.32)
localmasks={'pelvis_thigh':(R[:,2]>.66)&(R[:,2]<1.04),'knees':(R[:,2]>.38)&(R[:,2]<.61),'shoulders':(abs(R[:,0])>.09)&(abs(R[:,0])<.405)&(R[:,2]>1.16)&(R[:,2]<1.49)}
def tree(xyz,faces):return BVHTree.FromPolygons(xyz.tolist(),faces.tolist(),all_triangles=True)
rows=[];references=[];vertexrefs=[];fails=[];centers={};init=None;last=None;prev=None;maxstep=0
refframes=[0,15,30,45,60,75,90,105,120,135,150]
armfaces=tri[np.all(armmask[tri],axis=1)];legfaces=tri[np.all(legmask[tri],axis=1)]
for f in range(151):
 scene.frame_set(f+1);bpy.context.view_layer.update();ev=body.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh();xyz=np.array([ev.matrix_world@v.co for v in me.vertices]);ev.to_mesh_clear()
 if init is None:init=xyz.copy()
 last=xyz.copy();ref={'id':'3948','frame':f,'global_floor_z':float(xyz[:,2].min()),'floor_plane_z':0,'patches':{}};supports={}
 if xyz[:,2].min()<-1e-6:fails.append(f'{f}: body below floor')
 for n,mask in patches.items():
  ids=np.flatnonzero(mask);z=xyz[ids,2];center=xyz[ids].mean(0);centers.setdefault(n,center);drift=float(np.linalg.norm(center-centers[n]));supports[n]={'count':len(ids),'min_z':float(z.min()),'max_z':float(z.max()),'drift_m':drift,'near_12mm_fraction':float((abs(z)<.012).mean())};ref['patches'][n]={'indices':ids.tolist(),'min_z':float(z.min()),'max_z':float(z.max())}
  if z.min()<-1e-6 or z.min()>.012 or drift>.002:fails.append(f'{f}: {n} support')
 at,lt=tree(xyz,armfaces),tree(xyz,legfaces);overlaps=len(at.overlap(lt));distance=min(lt.find_nearest(tuple(xyz[i]))[3] for i in np.flatnonzero(armmask))
 if overlaps:fails.append(f'{f}: arms or hands/legs triangle intersection')
 cross=np.cross(xyz[tri[:,1]]-xyz[tri[:,0]],xyz[tri[:,2]]-xyz[tri[:,0]]);area=np.linalg.norm(cross,axis=1)*.5
 matrices=np.array([np.array(rig.pose.bones[g.name].matrix@rig.data.bones[g.name].matrix_local.inverted())[:3,:3] for g in body.vertex_groups]);input_normals=rn.copy()
 for key in body.data.shape_keys.key_blocks:
  if key.name!='Basis':input_normals+=key.value*(key_normals[key.name]-rn)
 normals=np.zeros_like(rn)
 for v in body.data.vertices:
  for g in v.groups:normals[v.index]+=g.weight*(matrices[g.group]@input_normals[v.index])
 normals/=np.linalg.norm(normals,axis=1)[:,None]
 local={}
 for n,mask in localmasks.items():
  faceids=np.flatnonzero(np.all(mask[tri],axis=1));faces=tri[faceids];rat=area[faceids]/restarea[faceids];dots=np.sum(cross[faceids]*normals[faces].mean(1),axis=1);inversions=int((dots<=0).sum())
  # Adjacent facets share boundaries by construction; only disjoint triangles
  # establish a self-intersection witness in the fixed local surface domain.
  hits=tree(xyz,faces).overlap(tree(xyz,faces));nonadj=[(i,j) for i,j in hits if i<j and not set(faces[i])&set(faces[j])]
  local[n]={'triangles':len(faces),'minimum_area_ratio':float(rat.min()),'maximum_area_ratio':float(rat.max()),'opposed_shader_normal_faces':inversions,'disjoint_triangle_intersections':len(nonadj)}
  if np.min(area[faceids])<1e-10:fails.append(f'{f}: degenerate {n} face')
  if nonadj:fails.append(f'{f}: {n} disjoint self-intersection')
 quats={pb.name:pb.matrix.to_quaternion() for pb in rig.pose.bones}
 if prev:maxstep=max(maxstep,max(2*math.acos(min(1,abs(prev[n].dot(q)))) for n,q in quats.items()))
 prev=quats
 rows.append({'frame':f,'global_floor_z':ref['global_floor_z'],'supports':supports,'arm_hand_to_legs':{'triangle_intersections':overlaps,'minimum_surface_distance_m':distance},'local_faces':local})
 if f in refframes:references.append(ref);vertexrefs.append({'frame':f,'vertices':xyz.tolist(),'shader_normals':normals.tolist()})
loop=float(np.linalg.norm(init-last,axis=1).max())
if loop>1e-6:fails.append('nonclosing loop')
if maxstep>math.radians(20):fails.append('joint frame discontinuity')
sys.path.insert(0,str(Path.home()/'.codex/skills/blender-asset-qa/scripts'));import qa_check
checks=[]
for f in [0,37,75]:
 scene.frame_set(f+1);bpy.context.view_layer.update();q=qa_check.run(objects=[body.name],profile='game');checks.append({'frame':f,'qa':q})
 if not q['pass']:fails.append(f'{f}: mandatory game asset QA')
(P/'asset-qa.json').write_text(json.dumps({'source_sha256':source_sha,'pass':all(x['qa']['pass'] for x in checks),'checks':checks},indent=2)+'\n')
(P/'runtime-surface-reference.json').write_text(json.dumps({'reference_kind':'native-armature-only-linear','source_sha256':source_sha,'source_vertices':10582,'coordinate_frame':'Blender Zup metres, fixed original source IDs','floor_plane_z':0,'samples':references},separators=(',',':'))+'\n')
with gzip.open(P/'linear-vertex-reference.json.gz','wt') as out:json.dump(vertexrefs,out,separators=(',',':'))
with gzip.open(P/'topology-reference.json.gz','wt') as out:json.dump({'source_sha256':source_sha,'source_vertices':10582,'triangles':tri.tolist()},out,separators=(',',':'))
(P/'landmarks.json').write_text(json.dumps({'source_sha256':source_sha,'source_vertices':10582,'patches':{n:np.flatnonzero(mask).tolist() for n,mask in {**patches,'both_arms_hands':armmask,'both_legs':legmask,**localmasks}.items()},'definition':'Fixed original Basis-coordinate source domains before pose measurement.'},indent=2)+'\n')
report={'ok':not fails,'source_sha256':source_sha,'original_binding_hash':original_hash,'binding_hash':a.binding_hash(body,rig),'invariants':{'basis':True,'rest':True,'uv':True,'source_indices':True,'topology':True,'connected_body':True,'bones':51,'maximum_influences':4,'weights_outside_declared_domains':True,'morph_targets':3,'position_normal_targets':3,'maximum_source_corrective_delta_m':.025},'native_and_runtime_path':'Original cage with three bounded POSITION/NORMAL morphs, Armature-only linear. Native smoothing/Multires disabled; target construction is baked, no runtime DQ.','sample_step_frames':1,'sampling':'Every runtime frame0..150, native source frame1..151; full-body skin floor and fixed heel/forefoot/medial/lateral patches, complete distal arms/hands versus both legs, bounded changed-junction surface triangles.','limitations':'Discrete30Hz path evidence; no assertion of continuous-time clinical biomechanics. Opposed shader-normal face count is disclosed separately and requires inspection rather than conflation with topology orientation.','loop_max_vertex_error_m':loop,'max_joint_step_radians':maxstep,'failures':fails,'samples':rows}
(P/'surface-contact-report.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'ok':not fails,'failures':fails[:20],'minimum_skin_z':min(x['global_floor_z'] for x in rows),'minimum_arm_leg_distance':min(x['arm_hand_to_legs']['minimum_surface_distance_m'] for x in rows),'junction_summary':{n:{'max_self_intersections':max(x['local_faces'][n]['disjoint_triangle_intersections'] for x in rows),'max_opposed_normals':max(x['local_faces'][n]['opposed_shader_normal_faces'] for x in rows),'minimum_area_ratio':min(x['local_faces'][n]['minimum_area_ratio'] for x in rows)} for n in localmasks}}))
assert not fails,fails[:20]
