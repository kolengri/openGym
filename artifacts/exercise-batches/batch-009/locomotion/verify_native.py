"""Verify actual saved native or decoded DQ skin over all151 states."""
import bpy,numpy as np,json,gzip,sys,hashlib,math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
F=Path(__file__).resolve().parent;B=F.parent;ID=sys.argv[sys.argv.index('--id')+1];P=B/'assets'/ID
sys.path[:0]=[str(F),str(B.parent/'batch-003'),str(B.parent/'batch-008/standing-dynamic')]
import authoring as a,motion
from check_motion import MotionChecks
from self_clearance import SelfClearance
from triangle_intersection import intersect
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def signature(b,r):
    h=hashlib.sha256();h.update(np.array([v.co[:] for v in b.data.vertices],np.float32).tobytes())
    for p in b.data.polygons:h.update(np.array(p.vertices,np.int32).tobytes())
    for uv in b.data.uv_layers:h.update(uv.name.encode());h.update(np.array([v.uv[:] for v in uv.data],np.float32).tobytes())
    for bone in r.data.bones:h.update(bone.name.encode());h.update(np.array(bone.matrix_local,np.float32).tobytes())
    return h.hexdigest()
assert bpy.app.version[:3]==(5,2,3)
a.initialize();original=signature(a.body,a.rig);original_weights=[{a.body.vertex_groups[g.group].name:g.weight for g in v.groups} for v in a.body.data.vertices]
bpy.ops.wm.open_mainfile(filepath=str(P/'source.blend'));b=bpy.data.objects['SK_BlenderStudioHuman'];r=bpy.data.objects['RIG_BlenderStudioHuman'];s=bpy.context.scene;source_sha=sha(P/'source.blend')
assert signature(b,r)==original
assert sorted(x.name for x in bpy.data.actions)==['Exercise_'+i for i in motion.IDS]
r.animation_data.action=bpy.data.actions['Exercise_'+ID];r.animation_data.action_slot=r.animation_data.action.slots[0]
assert len(b.data.vertices)==10582 and len(r.data.bones)==51 and b.data.shape_keys is None
assert a.binding_hash(b,r)==json.loads((P/'local-binding-report.json').read_text())['runtime_binding_sha256']
assert all({b.vertex_groups[g.group].name:g.weight for g in v.groups}==old for v,old in zip(b.data.vertices,original_weights) if v.co.z>=.08)
assert max(len(v.groups) for v in b.data.vertices)<=4
assert max(abs(sum(g.weight for g in v.groups)-1) for v in b.data.vertices)<2e-6
for m in b.modifiers:assert m.show_viewport==(m.type=='ARMATURE') and m.show_render==(m.type=='ARMATURE')
assert next(m for m in b.modifiers if m.type=='ARMATURE').use_deform_preserve_volume
b.data.calc_loop_triangles();tri=np.array([t.vertices[:] for t in b.data.loop_triangles],int);rest=np.array([v.co[:] for v in b.data.vertices]);names={g.index:g.name for g in b.vertex_groups}
def ids(prefixes):return set(v.index for v in b.data.vertices if sum(g.weight for g in v.groups if any(names[g.group].startswith(p) for p in prefixes))>.5)
soles={side:np.array([v.index for v in b.data.vertices if v.co.z<.10 and sum(g.weight for g in v.groups if names[g.group] in [side+'Foot',side+'ToeBase'])>.5],int) for side in ['Left','Right']}
arms={side:ids([side+x for x in ['Arm','ForeArm','Hand','Index','Middle','Ring','Little','Thumb']]) for side in soles}
legs={side:ids([side+x for x in ['UpLeg','Leg','Foot','ToeBase']]) for side in soles}
faces={side:[list(p.vertices) for p in b.data.polygons if all(i in legs[side] for i in p.vertices)] for side in soles}
legtri={side:tri[np.all(np.isin(tri,list(legs[side])),axis=1)].tolist() for side in soles}
palms={side:set(v.index for v in b.data.vertices if sum(g.weight for g in v.groups if names[g.group]==side+'Hand')>.8) for side in soles}
palmfaces={side:[list(p.vertices) for p in b.data.polygons if all(i in palms[side] for i in p.vertices)] for side in soles}
distal={side:ids([side+x for x in ['Index2','Index3','Middle2','Middle3','Ring2','Ring3','Little2','Little3','Thumb2','Thumb3']]) for side in soles}
patches={}
for side,idx in soles.items():
    patches['sole_'+side]={'indices':idx.tolist(),'rationale':'Complete original distal Foot/ToeBase-dominant skin below sourceZ100mm.'}
    q=rest[idx];bottom=idx[q[:,2]<=np.percentile(q[:,2],20)+.001]
    for part,select in [('heel',rest[bottom,1]>np.median(rest[idx,1])),('ball',rest[bottom,1]<=np.median(rest[idx,1]))]:
        patches[part+'_'+side]={'indices':bottom[select].tolist(),'rationale':'Lowest20percent original plantar envelope split at median sourceY.'}
def source_normals():
    mesh=bpy.data.meshes.new('TemporaryNormalWitness');mesh.from_pydata([v.co[:] for v in b.data.vertices],[],[list(p.vertices) for p in b.data.polygons])
    for face,old in zip(mesh.polygons,b.data.polygons):face.use_smooth=old.use_smooth
    mesh.update();normal=np.array([v.normal[:] for v in mesh.vertices]);bpy.data.meshes.remove(mesh);return normal
basis_normal=source_normals();bone_names=[pb.name for pb in r.pose.bones];bone_number={name:i for i,name in enumerate(bone_names)}
weight_indices=np.zeros((10582,4),int);weight_values=np.zeros((10582,4))
for v in b.data.vertices:
    for k,g in enumerate(v.groups):weight_indices[v.index,k]=bone_number[names[g.group]];weight_values[v.index,k]=g.weight
def shader_normals():
    # Independent native pose/bind quaternion equation, matching the shared DQ shader.
    q=np.array([(r.pose.bones[name].matrix@r.data.bones[name].matrix_local.inverted()).to_quaternion()[:] for name in bone_names])
    influence=q[weight_indices];sign=np.where(np.sum(influence*influence[:,:1,:],axis=2)<0,-1.,1.)
    blend=np.sum(influence*(weight_values*sign)[:,:,None],axis=1);blend/=np.linalg.norm(blend,axis=1)[:,None]
    xyz=blend[:,1:];twice=2*np.cross(xyz,basis_normal);normal=basis_normal+blend[:,:1]*twice+np.cross(xyz,twice)
    normal/=np.linalg.norm(normal,axis=1)[:,None];return normal.tolist()
checks=MotionChecks(b,r);selfclear=SelfClearance(b,r)
decoded_path=Path(sys.argv[sys.argv.index('--decoded')+1]) if '--decoded' in sys.argv else None
decoded=np.fromfile(decoded_path,dtype=np.float32).reshape(151,10582,3) if decoded_path else None
samples=[];poses=[];refs=[];dq=[];normal_samples=[];fail=[];max_decoded=0.;minarea=1.;first=last=None;previous_support={};maximum_support_drift=0.;bilateral_total=0
frames=sorted(set([0,30,75,120,150]+[x['frame'] for x in json.loads((P/'early-report.json').read_text())['proofs']]))
for f in range(151):
    s.frame_set(f+1);bpy.context.view_layer.update();e=b.evaluated_get(bpy.context.evaluated_depsgraph_get());me=e.to_mesh();native=np.array([v.co[:] for v in me.vertices]);p=decoded[f].astype(float) if decoded is not None else native
    max_decoded=max(max_decoded,float(np.linalg.norm(p-native,axis=1).max()));st=motion.state(f,ID);z=float(p[:,2].min());area=np.linalg.norm(np.cross(p[tri[:,1]]-p[tri[:,0]],p[tri[:,2]]-p[tri[:,0]]),axis=1)/2;mina=float(area.min());minarea=min(minarea,mina)
    if z<-.00035:fail.append(f'frame{f}: floor {z}')
    if mina<=1e-12:fail.append(f'frame{f}: nonpositive triangle area {mina}')
    vec=[Vector(v) for v in p];trees={side:BVHTree.FromPolygons(vec,face) for side,face in faces.items()};contacts={};clearance={};hand={};elbows={}
    for side,idx in soles.items():
        lo=float(p[idx,2].min());ground=side in st['grounded'];heel_pitch=st.get('rear_heel_lift_degrees',0) if side!=st.get('moving_side') else 0
        heel_z=float(p[patches['heel_'+side]['indices'],2].min());ball_z=float(p[patches['ball_'+side]['indices'],2].min())
        contacts[side]={'min_z_m':lo,'grounded':ground,'rear_heel_lift_degrees':heel_pitch,'heel_min_z_m':heel_z,'ball_min_z_m':ball_z,'support_region':'forefoot' if ground and heel_pitch>1e-6 else 'heel_and_ball' if ground else 'free'}
        if ground and not(-.00035<=lo<=.002):fail.append(f'frame{f}: {side} sole missing support {lo}')
        if ground and not(-.00035<=ball_z<=.002):fail.append(f'frame{f}: {side} actual ball skin lacks support {ball_z}')
        if ground and heel_pitch<=1e-6 and not(-.00035<=heel_z<=.002):fail.append(f'frame{f}: {side} actual heel skin lacks support {heel_z}')
        if st['flight'] and lo<=.0001:fail.append(f'frame{f}: {side} flight lacks skin clearance {lo}')
        # The fixed toe joint is a transport witness; separate actual skin minima above prove support.
        anchor=np.array(r.pose.bones[side+'ToeBase'].head)[:2]
        if ground and side in previous_support:
            drift=float(np.linalg.norm(anchor-previous_support[side]));maximum_support_drift=max(maximum_support_drift,drift)
            if drift>.0005:fail.append(f'frame{f}: {side} planted toe transport drift {drift}')
        if ground:previous_support[side]=anchor
        elif side in previous_support:del previous_support[side]
        for leg in soles:
            inside=[];distance=[]
            for i in arms[side]:
                q,n,face,dist=trees[leg].find_nearest(vec[i]);distance.append(dist)
                if dist<.04 and (vec[i]-q).dot(n)<-.004:inside.append(i)
            clearance[side+'_arm_to_'+leg+'_leg']={'minimum_distance_m':min(distance),'vertices_more_than4mm_inside':len(inside)}
            if inside:fail.append(f'frame{f}: {side} arm/{leg} leg intrusion {len(inside)}')
        palm=BVHTree.FromPolygons(vec,palmfaces[side]);inside=[]
        for i in distal[side]:
            q,n,face,dist=palm.find_nearest(vec[i])
            if dist<.025 and (vec[i]-q).dot(n)<-.004:inside.append(i)
        hand[side]={'distal_finger_vertices_more_than4mm_inside_palm':len(inside),'source_ids':inside}
        if inside:fail.append(f'frame{f}: {side} finger/palm intrusion {len(inside)}')
        sh=r.pose.bones[side+'Arm'].head;el=r.pose.bones[side+'ForeArm'].head;wr=r.pose.bones[side+'Hand'].head;elbows[side]=float((sh-el).angle(wr-el)*180/np.pi)
        if elbows[side]>175:fail.append(f'frame{f}: {side} elbow internal angle {elbows[side]}')
    left=BVHTree.FromPolygons(vec,legtri['Left'],all_triangles=True);right=BVHTree.FromPolygons(vec,legtri['Right'],all_triangles=True);crossings=0
    for li,ri in left.overlap(right):
        lt,rt=legtri['Left'][li],legtri['Right'][ri]
        if set(lt)&set(rt):continue
        if intersect([vec[i] for i in lt],[vec[i] for i in rt]):crossings+=1
    bilateral_total+=crossings
    if crossings:fail.append(f'frame{f}: bilateral leg triangle crossings {crossings}')
    extra,issues=checks.sample(p,f,ID,native_p=native);fail.extend(issues)
    clear,issues=selfclear.sample(p);fail.extend(f'frame{f}: '+issue for issue in issues)
    samples.append(dict(frame=f,phase=st,whole_skin_min_z_m=z,minimum_triangle_area_m2=mina,soles=contacts,whole_arm_leg_clearance=clearance,relaxed_finger_palm_clearance=hand,elbow_internal_degrees=elbows,bilateral_leg_triangle_crossings=crossings,arm_self_clearance=clear,**extra))
    if f in frames:
        poses.append(dict(id=ID,frame=f,joints={pb.name:list(r.matrix_world@pb.head) for pb in r.pose.bones}))
        def patch_state(name):
            side=name.split('_')[-1]
            if st['flight']:return 'flight'
            if side not in st['grounded']:return 'lifted'
            if name.startswith('heel_') and contacts[side]['rear_heel_lift_degrees']>1e-6:return 'lifted'
            return 'supported'
        refs.append(dict(id=ID,frame=f,global_floor_z=z,floor_plane_z=0,phase=st,patches={name:dict(**patch,positions=p[patch['indices']].tolist(),min_z=float(p[patch['indices'],2].min()),max_z=float(p[patch['indices'],2].max()),state=patch_state(name)) for name,patch in patches.items()}))
    if f in [0,30,75,120,150]:
        dq.append(dict(id=ID,frame=f,positions=p.tolist()));normal_samples.append(dict(id=ID,frame=f,normals=shader_normals()))
    if f==0:first=p.copy();firstbones=np.array([pb.matrix for pb in r.pose.bones])
    if f==150:last=p.copy();lastbones=np.array([pb.matrix for pb in r.pose.bones])
    e.to_mesh_clear()
loop=float(np.linalg.norm(first-last,axis=1).max());boneloop=float(np.max(abs(firstbones-lastbones)))
if loop>1e-5 or boneloop>1e-5:fail.append('Loop mismatch')
if decoded_path and max_decoded>.0001:fail.append('Decoded/native full151 parity exceeds100micrometers')
if not decoded_path:
    for name,data in [('runtime-surface-reference.json',dict(source_sha256=source_sha,reference_kind='native_DQ_Armature_only_no_correctives',source_vertices=10582,coordinate_system='BlenderZup meters; runtime[x,z,-y]',samples=refs)),('surface-landmarks.json',dict(source_sha256=source_sha,patches=patches,whole_arm_ids={k:sorted(v) for k,v in arms.items()},whole_leg_ids={k:sorted(v) for k,v in legs.items()},leg_faces=faces,palm_faces=palmfaces,distal_finger_ids={k:sorted(v) for k,v in distal.items()},triangles=tri.tolist())),('pose-samples.json',poses)]:
        (P/name).write_text(json.dumps(data,separators=(',',':'))+'\n')
    with gzip.open(P/'dq-reference.json.gz','wt') as out:json.dump(dict(source_sha256=source_sha,source_vertices=10582,samples=dq),out,separators=(',',':'))
    with gzip.open(P/'normal-reference.json.gz','wt') as out:json.dump(dict(source_sha256=source_sha,basis=basis_normal.tolist(),targets={},samples=normal_samples),out,separators=(',',':'))
report=dict(ok=not fail,source_sha256=source_sha,native_integer_frames=151,maximum_full_cycle_native_decoded_error_m=max_decoded if decoded_path else None,minimum_floor_z_m=min(x['whole_skin_min_z_m'] for x in samples),minimum_triangle_area_m2=minarea,loop_skin_error_m=loop,loop_bone_max_element_error=boneloop,maximum_grounded_toe_anchor_step_m=maximum_support_drift,maximum_leg_foot_orientation_step_degrees=checks.maximum_step,forefoot_edge_ratio_range=checks.edge_range,mixed_ankle_edge_ratio_range=checks.ankle_range,maximum_forefoot_relative_matrix_error=checks.maximum_toe_error,arm_leg_triangle_crossings=checks.crossings,arm_self_triangle_crossings=selfclear.crossings,bilateral_leg_triangle_crossings=bilateral_total,tolerances=dict(floor_penetration_m=.00035,grounded_sole_max_gap_m=.002,flight_sole_min_gap_m=.0001,local_intrusion_m=.004,elbow_internal_max_degrees=175,forefoot_edge_ratio=[.85,1.15],mixed_ankle_edge_ratio=[.65,1.35],planted_toe_anchor_step_m=.0005),scope='Complete arms/hands/fingers versus both full legs; opposite leg triangles; distal arms versus torso/head and mutual arm triangles. Local nearest-normal intrusion gates are limited to40mm. No global self-collision or clinical claim.',failures=fail,samples=samples)
(P/('decoded-physical-report.json' if decoded_path else 'surface-contact-report.json')).write_text(json.dumps(report,indent=2)+'\n')
(P/('decoded-source-readback.json' if decoded_path else 'source-verification.json')).write_text(json.dumps(dict(ok=True,source_sha256=source_sha,original_source_sha256=a.SOURCE_SHA,basis_topology_uv_bone_rest_sha256=original,basis_topology_uv_bone_rest_unchanged=True,original_weights_above_sourceZ80mm_exact=True,runtime_binding_sha256=a.binding_hash(b,r),maximum_influences=max(len(v.groups) for v in b.data.vertices),maximum_weight_sum_error=max(abs(sum(g.weight for g in v.groups)-1) for v in b.data.vertices),vertices=10582,triangles=len(tri),bones=51,morphs=[],corrective_track_reset='Not applicable: no morph targets or corrective tracks.',actions=['Exercise_'+i for i in motion.IDS],selected_action='Exercise_'+ID,only_armature_enabled=True,dual_quaternion=True),indent=2)+'\n')
print('PHYSICAL_GATES',json.dumps(dict(id=ID,ok=not fail,failure_count=len(fail),failures=fail[:20],minimum_area=minarea,loop=loop,max_decoded_error=max_decoded)))
if '--game-qa' in sys.argv:
    sys.path.insert(0,str(Path.home()/'.codex/skills/blender-asset-qa/scripts'));import qa_check
    qa=[]
    for f in {'3220':[0,15,36,54],'3672':[0,35,112],'6097':[0,19,56]}[ID]:
        s.frame_set(f+1);bpy.context.view_layer.update();qa.append(dict(frame=f,report=qa_check.run(objects=[b.name],profile='game')))
    q=dict(pass_=all(x['report']['pass'] for x in qa),source_sha256=source_sha,samples=qa);q['pass']=q.pop('pass_');(P/'raw-asset-qa.json').write_text(json.dumps(q,indent=2)+'\n');assert q['pass']
    sys.path.insert(0,str(Path.home()/'.codex/skills/blender-core/scripts'));import env_report
    (P/'environment.json').write_text(json.dumps(env_report.run(),indent=2)+'\n')
if decoded_path and not fail:
    decoded_path.unlink();decoded_path.parent.rmdir();(P/'verification-exchange-path.txt').unlink()
assert not fail,fail[:20]
