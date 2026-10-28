"""Source-index sit-up surface QA; illustrative authoring checks, not issue closure."""
import bpy,json,math,sys,hashlib
from pathlib import Path
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
P=Path(__file__).resolve().parent
REPAIR=P/'situp-repair'
FRAMES=[0,15,30,50,60,70,90,105,120]

def rest_hash(body):
    co=np.empty(len(body.data.vertices)*3,np.float32);body.data.vertices.foreach_get('co',co)
    return hashlib.sha256(co.tobytes()).hexdigest()

def author_landmarks(body):
    """Freeze authored source-surface patches, independently of atlas masks."""
    rest=np.array([v.co[:] for v in body.data.vertices]);n=len(rest)
    patches={}
    def add(key,ids,kind,rationale):
        ids=sorted(set(map(int,ids)))
        if not ids:raise ValueError('Empty authored patch '+key)
        id_set=set(ids)
        faces=[p.index for p in body.data.polygons if all(i in id_set for i in p.vertices)]
        patches[key]={'vertex_ids':ids,'polygon_ids':faces,'kind':kind,'rationale':rationale,'phase_frames':[0,120]}
    add('pelvic_support_L',[8650,8586,8652,8590],'supported','Posterior left pelvic skin quad, selected from the actual low support-facing surface in the accepted side/oblique pose. Not an atlas glute mask or a clinically identified ischial landmark.')
    add('pelvic_support_R',[3392,3329,3394,3333],'supported','Mirrored posterior right pelvic skin quad; same floor and authored soft-tissue support interpretation as left.')
    for side,sign,suffix in [('Left',1,'L'),('Right',-1,'R')]:
        foot=(rest[:,0]*sign>.15)&(rest[:,2]<.05)
        add('heel_'+suffix,np.flatnonzero(foot&(rest[:,1]>.105)&(rest[:,2]<.025)),'supported','Original plantar heel vertices; rest-space posterior heel and low sole surface, not the entire Foot group.')
        add('sole_'+suffix,np.flatnonzero(foot&(rest[:,1]<.025)&(rest[:,1]>-.075)&(rest[:,2]<.012)),'supported','Original plantar forefoot/sole patch; separated from heel to verify a shared planted foot plane.')
        face_set=9 if side=='Left' else 10
        palm=set()
        for face,value in zip(body.data.polygons,body.data.attributes['.sculpt_face_set'].data):
            if value.value==face_set:palm.update(face.vertices)
        add('palm_'+suffix,palm,'clear','Source palm face-set surface, including its boundary; evaluated against head/ear triangles, not wrist-to-head joint distance.')
        tips=[];hand=[]
        group_names={g.index:g.name for g in body.vertex_groups}
        for vertex in body.data.vertices:
            names=[group_names[g.group] for g in vertex.groups if g.weight>.5]
            if any(name.startswith(side) and ('Hand' in name or any(d in name for d in ['Thumb','Index','Middle','Ring','Little'])) for name in names):hand.append(vertex.index)
        for digit in ['Index','Middle','Ring','Little']:
            ids=[v.index for v in body.data.vertices if any(group_names[g.group]==side+digit+'3' and g.weight>.5 for g in v.groups)]
            low=min(rest[ids,2]);tips.extend(i for i in ids if rest[i,2]<low+.007)
        add('fingertips_'+suffix,tips,'light_touch','Distal source skin vertices on four fingers, near the posterior scalp; thumb is included in whole-hand clearance, not required to touch.')
        add('hand_'+suffix,hand,'clear','All strongly hand/finger-bound source vertices for scalp and ear penetration detection.')
    add('lumbar_clearance',np.flatnonzero((abs(rest[:,0])<.07)&(rest[:,1]>.08)&(rest[:,2]>1.04)&(rest[:,2]<1.22)),'clear','Posterior lumbar skin strip: verifies lowering pelvis did not push the lower back through the floor.')
    head_ids=np.flatnonzero(rest[:,2]>1.59).tolist();head_set=set(head_ids)
    head_faces=[list(p.vertices) for p in body.data.polygons if all(i in head_set for i in p.vertices)]
    head_triangles=[]
    for face in head_faces:
        head_triangles.extend([[face[0],face[i],face[i+1]] for i in range(1,len(face)-1)])
    add('head_surface',head_ids,'clear','Original head and ears above the jaw/upper-neck boundary; triangles support signed closest-surface hand clearance checks.')
    patches['head_surface']['triangles']=head_triangles
    return {'schema_version':'1.0.0','exercise_id':'0001','body':body.name,'base_vertex_count':n,'rest_coordinates_sha256':rest_hash(body),'index_space':'Original body.data.vertices indices, corresponding to exported _SOURCE_INDEX; not evaluated/subdivision indices.','coordinate_frame':'Blender world metres; exported Three.js conversion [x,z,-y].','floor_plane':{'point':[0,0,0],'normal':[0,0,1]},'sample_frames':FRAMES,'phases':{'start':[0],'raising':[15,30],'top_hold':[50,60,70],'lowering':[90,105],'end_contact':[120]},'patches':patches,'tolerances':{'support_near_distance_m':.012,'support_minimum_near_fraction':.20,'support_maximum_closest_gap_m':.012,'maximum_skin_floor_penetration_m':.004,'minimum_lumbar_clearance_m':.002,'maximum_hand_scalp_penetration_m':.003,'maximum_fingertip_light_touch_gap_m':.012,'minimum_opposing_hand_lateral_separation_m':.003,'top_torso_inclination_degrees':[42,48]},'tolerance_basis':'Authored illustration QA at 1.8m character scale and 768px review framing; millimetre clearance/contact bands account for curved soft skin and cage/native interpolation. Not medical landmarks, physiological limits, or biomechanics approval. Values are declared before reading this candidate report.','issue_closure':'Primary review required; contract issues remain open.'}

def _stats(values):
    return {'minimum_m':float(np.min(values)),'p10_m':float(np.percentile(values,10)),'median_m':float(np.median(values)),'p90_m':float(np.percentile(values,90)),'maximum_m':float(np.max(values))}

def measure(body,rig,scene,landmarks=None):
    landmarks=landmarks or json.loads((REPAIR/'landmarks.json').read_text())
    if rest_hash(body)!=landmarks['rest_coordinates_sha256']:raise ValueError('Landmark source-coordinate identity mismatch')
    original_action=rig.animation_data.action;original_frame=scene.frame_current
    modifier_state=[(m,m.show_viewport,m.show_render) for m in body.modifiers]
    attributes=[]
    for name,patch in landmarks['patches'].items():
        attribute=body.data.attributes.new(name='QA_Situp_'+name,type='FLOAT',domain='POINT');values=np.zeros(len(body.data.vertices),np.float32);values[patch['vertex_ids']]=1;attribute.data.foreach_set('value',values);attributes.append(attribute.name)
    rows=[];tolerance=landmarks['tolerances'];original_modifiers=[{'name':m.name,'type':m.type,'viewport':v,'render':r,'levels':getattr(m,'levels',None),'render_levels':getattr(m,'render_levels',None)} for m,v,r in modifier_state]
    rig.animation_data.action=bpy.data.actions['Exercise_0001']
    try:
        for path in ['native','linear_cage']:
            for modifier,viewport,render in modifier_state:modifier.show_viewport=viewport if path=='native' else modifier.type=='ARMATURE'
            first_centroids={};previous=None
            for frame in landmarks['sample_frames']:
                scene.frame_set(frame+1);bpy.context.view_layer.update()
                evaluated=body.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=evaluated.to_mesh()
                try:
                    positions=np.array([body.matrix_world@v.co for v in mesh.vertices]);masks={}
                    for name in landmarks['patches']:
                        values=np.empty(len(mesh.vertices),np.float32);mesh.attributes['QA_Situp_'+name].data.foreach_get('value',values);masks[name]=values>.35
                    contact={}
                    for name,patch in landmarks['patches'].items():
                        if patch['kind']!='supported' and name!='lumbar_clearance':continue
                        points=positions[masks[name]];z=points[:,2];centroid=points[:,:2].mean(0);first_centroids.setdefault(name,centroid.copy())
                        contact[name]={**_stats(z),'sampled_vertices':len(points),'fraction_within_contact_band':float(np.mean(abs(z)<=tolerance['support_near_distance_m'])),'deepest_penetration_m':float(max(0,-z.min())),'tangential_centroid_displacement_m':float(np.linalg.norm(centroid-first_centroids[name]))}
                    head_faces=[tuple(p.vertices) for p in mesh.polygons if all(masks['head_surface'][i] for i in p.vertices)]
                    bvh=BVHTree.FromPolygons([Vector(p) for p in positions],head_faces,all_triangles=False)
                    hand_separation=float(positions[masks['hand_L'],0].min()-positions[masks['hand_R'],0].max())
                    clearance={}
                    for name in ['palm_L','palm_R','hand_L','hand_R','fingertips_L','fingertips_R']:
                        signed=[]
                        for p in positions[masks[name]]:
                            closest,normal,_,distance=bvh.find_nearest(Vector(p));signed.append(distance if (Vector(p)-closest).dot(normal)>=0 else -distance)
                        values=np.array(signed)
                        clearance[name]={**_stats(values),'sampled_vertices':len(values),'deepest_penetration_m':float(max(0,-values.min())),'floor_minimum_m':float(positions[masks[name],2].min())}
                    angles={}
                    for side in ['Left','Right']:
                        shoulder=rig.pose.bones[side+'Arm'].head;elbow=rig.pose.bones[side+'ForeArm'].head;wrist=rig.pose.bones[side+'Hand'].head
                        angles[side+'_elbow_internal_degrees']=math.degrees((shoulder-elbow).angle(wrist-elbow))
                    torso=rig.pose.bones['Neck'].head-rig.pose.bones['Hips'].head
                    angles['torso_hip_to_neck_inclination_degrees']=math.degrees(math.atan2(torso.z,math.hypot(torso.x,torso.y)))
                    joints={name:np.array(rig.pose.bones[name].head) for name in ['LeftForeArm','RightForeArm','LeftHand','RightHand','LeftLeg','RightLeg']}
                    path_step=max((np.linalg.norm(joints[name]-previous[name]) for name in joints),default=0.) if previous else 0.;previous=joints
                    rows.append({'path':path,'frame':frame,'evaluated_vertices':len(mesh.vertices),'body_minimum_z_m':float(positions[:,2].min()),'contacts':contact,'head_clearances':clearance,'opposing_hands_lateral_separation_m':hand_separation,'joint_angles':angles,'largest_limb_sample_step_m':float(path_step)})
                finally:evaluated.to_mesh_clear()
    finally:
        for name in attributes:
            attribute=body.data.attributes.get(name)
            if attribute:body.data.attributes.remove(attribute)
        for modifier,viewport,render in modifier_state:modifier.show_viewport=viewport;modifier.show_render=render
        rig.animation_data.action=original_action;scene.frame_set(original_frame);bpy.context.view_layer.update()
    failures=[]
    for row in rows:
        label=f"{row['path']} frame {row['frame']}"
        if row['body_minimum_z_m'] < -tolerance['maximum_skin_floor_penetration_m']:failures.append(label+' body-floor penetration')
        if row['opposing_hands_lateral_separation_m']<tolerance['minimum_opposing_hand_lateral_separation_m']:failures.append(label+' opposing hands overlap')
        for name,contact in row['contacts'].items():
            if name=='lumbar_clearance':
                if contact['minimum_m']<tolerance['minimum_lumbar_clearance_m']:failures.append(label+' lumbar-floor clearance')
            elif contact['minimum_m']>tolerance['support_maximum_closest_gap_m'] or contact['deepest_penetration_m']>tolerance['maximum_skin_floor_penetration_m'] or contact['fraction_within_contact_band']<tolerance['support_minimum_near_fraction']:failures.append(label+' '+name+' support')
        for name,clearance in row['head_clearances'].items():
            if clearance['deepest_penetration_m']>tolerance['maximum_hand_scalp_penetration_m']:failures.append(label+' '+name+' scalp penetration')
            if name.startswith('fingertips') and clearance['minimum_m']>tolerance['maximum_fingertip_light_touch_gap_m']:failures.append(label+' '+name+' light-touch gap')
        if row['frame']==60:
            angle=row['joint_angles']['torso_hip_to_neck_inclination_degrees'];lo,hi=tolerance['top_torso_inclination_degrees']
            if not lo<=angle<=hi:failures.append(label+' source torso inclination')
    return {'exercise_id':'0001','status':'measured_candidate_requires_primary_review','checks_pass':not failures,'failures':failures,'native_modifiers':original_modifiers,'landmarks_path':'situp-repair/landmarks.json','source_blend_sha256':hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest(),'authoring_script_sha256':hashlib.sha256((P/'build_motion.py').read_bytes()).hexdigest(),'scope':'Authored original-index surface patches at start/raising/top-hold/lowering/end; native skin and pure linear Armature cage separately. Closest-surface signed palm/fingertip/head distances, not bone-distance substitutes. Sampled paths, not continuous collision certification.','samples':rows,'not_biomechanically_approved':True,'contract_issues_closed':False}

if __name__=='__main__':
    args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
    source=Path(args[args.index('--source')+1]) if '--source' in args else P/'bodyweight-five.blend'
    bpy.ops.wm.open_mainfile(filepath=str(source));body=bpy.data.objects['SK_BlenderStudioHuman'];rig=bpy.data.objects['RIG_BlenderStudioHuman']
    REPAIR.mkdir(exist_ok=True)
    if not (REPAIR/'landmarks.json').exists():
        (REPAIR/'landmarks.json').write_text(json.dumps(author_landmarks(body),indent=2)+'\n')
    report=measure(body,rig,bpy.context.scene)
    (REPAIR/'contact-report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'checks_pass':report['checks_pass'],'failures':report['failures'],'samples':len(report['samples']),'native_modifiers':report['native_modifiers']}))
