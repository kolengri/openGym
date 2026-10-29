"""Source-bound invariant, full-path contact and original-index geometry checks."""
import argparse
import gzip
import hashlib
import json
import math
import sys
from pathlib import Path
import bpy
import numpy as np
from mathutils.bvhtree import BVHTree

P=Path(__file__).resolve().parent
parser=argparse.ArgumentParser()
parser.add_argument('--dense',action='store_true')
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
sys.path.insert(0,str(P.parents[2]/'batch-003'))
import authoring as a
original_hash=a.initialize()
original_xyz=np.array([v.co[:] for v in a.body.data.vertices],dtype=np.float32)
original_weights=[[(g.group,g.weight) for g in v.groups] for v in a.body.data.vertices]
original_uv=[np.array([v.uv[:] for v in uv.data],dtype=np.float32) for uv in a.body.data.uv_layers]
original_rest={b.name:np.array(b.matrix_local,dtype=np.float32) for b in a.rig.data.bones}
original_topology=[list(p.vertices) for p in a.body.data.polygons]
bpy.ops.wm.open_mainfile(filepath=str(P/'source.blend'))
body=bpy.data.objects['SK_BlenderStudioHuman'];rig=bpy.data.objects['RIG_BlenderStudioHuman'];scene=bpy.context.scene
R=np.array([v.co[:] for v in body.data.vertices],dtype=np.float32)
rest_normals=np.array([v.normal[:] for v in body.data.vertices],dtype=np.float64)
source_sha=hashlib.sha256((P/'source.blend').read_bytes()).hexdigest()
weight_report=json.loads((P/'local-weight-report.json').read_text())
changed=set(weight_report['affected_source_indices'])
assert np.array_equal(R,original_xyz)
assert original_topology==[list(p.vertices) for p in body.data.polygons]
assert all(np.array_equal(x,np.array([v.uv[:] for v in uv.data],dtype=np.float32)) for x,uv in zip(original_uv,body.data.uv_layers))
assert all(np.array_equal(original_rest[b.name],np.array(b.matrix_local,dtype=np.float32)) for b in rig.data.bones)
assert all(original_weights[v.index]==[(g.group,g.weight) for g in v.groups] for v in body.data.vertices if v.index not in changed)
assert a.binding_hash(body,rig)==weight_report['new_binding']
assert len(rig.data.bones)==51 and len(R)==10582
assert body.data.shape_keys is None
assert [x.name for x in bpy.data.actions]==['Exercise_1980']
assert all(len(v.groups)<=4 and abs(sum(g.weight for g in v.groups)-1)<1e-6 for v in body.data.vertices)
assert all(m.show_viewport==(m.type=='ARMATURE') and m.show_render==(m.type=='ARMATURE') for m in body.modifiers)
assert not next(m for m in body.modifiers if m.type=='ARMATURE').use_deform_preserve_volume
tri=np.array([t.vertices[:] for t in body.data.loop_triangles])
if not len(tri):
    body.data.calc_loop_triangles();tri=np.array([t.vertices[:] for t in body.data.loop_triangles])
region={}
for polygon,attr in zip(body.data.polygons,body.data.attributes['.sculpt_face_set'].data):
    region.setdefault(attr.value,set()).update(polygon.vertices)
def reg(*ids):
    mask=np.zeros(len(R),bool)
    mask[list(set.union(*(region[i] for i in ids)))]=True
    return mask
left_arm=(reg(21)&(R[:,0]>.22))|reg(12)
left_hand=reg(9,*[k for k in region if 64<=k<84])
right_forearm=reg(11)
right_hand=reg(10,*[k for k in region if 84<=k<104])
chest=(np.abs(R[:,0])<.145)&(R[:,2]>1.17)&(R[:,2]<1.44)&(R[:,1]<.02)
head=(R[:,2]>1.56)&(np.abs(R[:,0])<.16)
patches={}
for side,sign in [('L',1),('R',-1)]:
    sole=(sign*R[:,0]>.13)&(R[:,2]<.012)
    patches['heel_'+side]=sole&(R[:,1]>.025)
    patches['forefoot_'+side]=sole&(R[:,1]<-.025)
assert all(mask.sum()>5 for mask in patches.values())
def tree(xyz,mask):
    faces=tri[np.all(mask[tri],axis=1)]
    assert len(faces)>0
    return BVHTree.FromPolygons(xyz.tolist(),faces.tolist(),all_triangles=True)
def pair(xyz,A,B):
    ta,tb=tree(xyz,A),tree(xyz,B)
    intersections=ta.overlap(tb)
    nearest=[tb.find_nearest(tuple(xyz[i])) for i in np.flatnonzero(A)]
    distances=np.array([n[3] for n in nearest])
    signed=np.array([(xyz[i]-np.array(n[0])).dot(np.array(n[1])) for i,n in zip(np.flatnonzero(A),nearest)])
    distance_by_id=np.full(len(xyz),np.inf);distance_by_id[np.flatnonzero(A)]=distances
    faces=tri[np.all(A[tri],axis=1)]
    areas=np.linalg.norm(np.cross(xyz[faces[:,1]]-xyz[faces[:,0]],xyz[faces[:,2]]-xyz[faces[:,0]]),axis=1)*.5
    near_faces=np.all(distance_by_id[faces]<.012,axis=1)
    return {'triangle_intersections':len(intersections),'minimum_surface_distance_m':float(distances.min()),
        'near_12mm_vertices':int((distances<.012).sum()),'minimum_oriented_distance_m':float(signed.min()),
        'near_12mm_area_m2':float(areas[near_faces].sum()),'tested_surface_area_m2':float(areas.sum())}
frames=list(range(151)) if args.dense else list(range(0,151,5))
reference_frames=[0,15,30,45,60,75,90,105,120,135,150]
rows=[];references=[];vertexrefs=[];failures=[];centroids={};initial=None;last=None;continuity=0;prev=None
for f in frames:
    scene.frame_set(f+1);bpy.context.view_layer.update()
    ev=body.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=ev.to_mesh()
    xyz=np.array([ev.matrix_world@v.co for v in mesh.vertices]);ev.to_mesh_clear()
    assert len(xyz)==10582
    if initial is None:initial=xyz.copy()
    last=xyz.copy()
    contacts={}
    ref={'id':'1980','frame':f,'global_floor_z':float(xyz[:,2].min()),'floor_plane_z':0,'patches':{}}
    for name,mask in patches.items():
        ids=np.flatnonzero(mask);z=xyz[ids,2];center=xyz[ids].mean(axis=0)
        centroids.setdefault(name,center)
        drift=float(np.linalg.norm(center-centroids[name]))
        contacts[name]={'count':len(ids),'min_z':float(z.min()),'max_z':float(z.max()),'drift_m':drift,'near_12mm_fraction':float((np.abs(z)<.012).mean())}
        ref['patches'][name]={'indices':ids.tolist(),'min_z':float(z.min()),'max_z':float(z.max())}
        if z.min()<-.004 or z.min()>.012 or drift>.002:failures.append(f'frame {f}: {name} support')
    forearm_contact=pair(xyz,left_arm,right_forearm)
    chest_clearance=pair(xyz,left_arm|left_hand,chest)
    other_hand=pair(xyz,left_arm|left_hand,right_hand)
    hand_head=pair(xyz,left_hand|right_hand,head)
    if forearm_contact['triangle_intersections']:failures.append(f'frame {f}: active/support arm surface intersections')
    if chest_clearance['triangle_intersections']:failures.append(f'frame {f}: active arm/chest surface intersections')
    if other_hand['triangle_intersections']:failures.append(f'frame {f}: active arm/support hand surface intersections')
    if hand_head['triangle_intersections']:failures.append(f'frame {f}: hand/head surface intersections')
    if 60<=f<=90 and forearm_contact['minimum_surface_distance_m']>.012:failures.append(f'frame {f}: support forearm contact gap')
    quats={pb.name:pb.matrix.to_quaternion() for pb in rig.pose.bones}
    if prev:
        continuity=max(continuity,max(2*math.acos(min(1,abs(prev[n].dot(q)))) for n,q in quats.items()))
    prev=quats
    row={'frame':f,'global_floor_z':ref['global_floor_z'],'supports':contacts,'active_to_support_forearm':forearm_contact,
        'active_to_chest':chest_clearance,'active_to_support_hand':other_hand,'hands_to_head':hand_head,
        'bounds':[xyz.min(axis=0).tolist(),xyz.max(axis=0).tolist()],
        'left_shoulder_head':list(rig.pose.bones['LeftArm'].head),'pelvis_head':list(rig.pose.bones['Hips'].head)}
    rows.append(row)
    if f in reference_frames:
        references.append(ref)
        # Three.js skinnormal_vertex uses the same four-weight linear matrix
        # for the source normal (w=0), followed by normalization. This is
        # independent of Blender's posed geometric-normal recalculation.
        matrices={pb.name:np.array(pb.matrix@pb.bone.matrix_local.inverted(),dtype=float)[:3,:3] for pb in rig.pose.bones}
        normals=np.zeros_like(rest_normals)
        for vertex in body.data.vertices:
            for group in vertex.groups:
                normals[vertex.index]+=group.weight*(matrices[body.vertex_groups[group.group].name]@rest_normals[vertex.index])
        normals/=np.linalg.norm(normals,axis=1)[:,None]
        vertexrefs.append({'frame':f,'vertices':xyz.tolist(),'shader_normals':normals.tolist()})
loop=float(np.linalg.norm(initial-last,axis=1).max())
if loop>1e-6:failures.append('nonclosing loop')
if continuity>math.radians(20)*(1 if args.dense else 5):failures.append('temporal joint rotation discontinuity guard')
sys.path.insert(0,str(Path.home()/'.codex/skills/blender-asset-qa/scripts'))
import qa_check
checks=[]
for f in [0,75]:
    scene.frame_set(f+1);bpy.context.view_layer.update()
    result=qa_check.run(objects=[body.name],profile='game')
    checks.append({'frame':f,'qa':result})
    if not result['pass']:failures.append(f'frame {f}: mandatory asset QA errors')
(P/'asset-qa.json').write_text(json.dumps({'source_sha256':source_sha,'pass':all(x['qa']['pass'] for x in checks),'checks':checks},indent=2)+'\n')
alpha_rows=[]
for path in sorted(P.glob('early-*.png')):
    image=bpy.data.images.load(str(path),check_existing=False)
    pixels=np.empty(len(image.pixels),np.float32);image.pixels.foreach_get(pixels)
    rgba=pixels.reshape(image.size[1],image.size[0],4)
    alpha=rgba[:,:,3];corners=[float(alpha[y,x]) for y,x in [(0,0),(0,-1),(-1,0),(-1,-1)]]
    row={'file':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'width':image.size[0],'height':image.size[1],
        'channels':image.channels,'minimum_alpha':float(alpha.min()),'maximum_alpha':float(alpha.max()),'corner_alpha':corners}
    alpha_rows.append(row);bpy.data.images.remove(image)
    if max(corners)>0 or row['channels']!=4 or row['maximum_alpha']<1:failures.append(f'{path.name}: native alpha proof')
(P/'alpha-report.json').write_text(json.dumps({'source_sha256':source_sha,'ok':all(max(x['corner_alpha'])==0 and x['channels']==4 for x in alpha_rows),
    'scope':'Native curated stills only; root owns live canvas alpha/background and playback checks.','samples':alpha_rows},indent=2)+'\n')
(P/'runtime-surface-reference.json').write_text(json.dumps({'source_sha256':source_sha,'source_vertices':10582,'coordinate_frame':'Blender world metres; original vertex IDs; Armature only linear skin','samples':references},separators=(',',':'))+'\n')
with gzip.open(P/'linear-vertex-reference.json.gz','wt') as out:json.dump(vertexrefs,out,separators=(',',':'))
with gzip.open(P/'topology-reference.json.gz','wt') as out:json.dump({'source_sha256':source_sha,'source_vertices':10582,'triangles':tri.tolist()},out,separators=(',',':'))
(P/'landmarks.json').write_text(json.dumps({'source_sha256':source_sha,'source_vertices':10582,'patches':{name:np.flatnonzero(mask).tolist() for name,mask in {**patches,'active_left_arm':left_arm,'support_right_forearm':right_forearm,'central_chest':chest}.items()},'definition':'Fixed original coordinates and authored sculpt regions before pose measurement; no pose-derived support index changes.'},indent=2)+'\n')
report={'ok':not failures,'source_sha256':source_sha,'original_binding_hash':original_hash,'binding_hash':a.binding_hash(body,rig),
    'invariants':{'basis':True,'rest':True,'uv':True,'source_indices':True,'topology':True,'connected_body':True,'bones':51,'maximum_influences':4,'weights_outside_local_shoulder':True,'morph_targets':0},
    'native_and_runtime_path':'Both original cage, Armature only, linear; native Smooth/Multires disabled and no preview-only masking.',
    'illustration_bands_m':{'proximity':.012,'penetration':.004,'support_drift':.002},
    'sampling':('Every runtime frame (1/30s)' if args.dense else 'Every 5 runtime frames (1/6s)')+' through full entry, hold and return; exact source-index export samples every 15 frames.',
    'limitations':'BVH triangle intersections and source-bound patch proximity are illustration evidence, not clinical validation or an exhaustive continuous-time collision proof. Signed nearest distances to open anatomical patches are orientation diagnostics, not solid-body penetration depths.',
    'loop_max_vertex_error_m':loop,'max_joint_step_radians':continuity,'sample_step_frames':1 if args.dense else 5,'failures':failures,'samples':rows}
(P/'surface-contact-report.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'ok':not failures,'failures':failures,'hold_contact':next(x['active_to_support_forearm'] for x in rows if x['frame']==75),'source_sha256':source_sha}))
assert not failures, failures
