"""Staged same-side foot grasp repair; user-rejected motion is history only."""
import sys,json,hashlib,math
from pathlib import Path
sys.dont_write_bytecode=True
import bpy,numpy as np
from mathutils import Matrix,Quaternion
from mathutils.bvhtree import BVHTree
P=Path(__file__).resolve().parent
OLD=P.parents[2]/'batch-005/assets/1512'
sys.path.insert(0,str(P.parents[2]/'batch-003'))
import authoring as a
PITCH=84
EXPECTED='227ede3fc31d1a2b47ff40f20a4a7288fe7bb36179add23bae953993826c8b7b'
ACQ=105/115
GRIP_REL=None
PALM_SOURCE=None
PALM_NORMAL_SOURCE=None
FOOT_ANCHOR_SOURCE=None
FOOT_NORMAL_SOURCE=None
FOOT_ANCHOR_LOCAL=None
FOOT_NORMAL_LOCAL=None
REUSED_KEYS={}
FINGER_CLOSED={digit:[-3,75,45] for digit in ['Index','Middle','Ring','Little']}
FINGER_CLOSED['Thumb']=[20,25,15]
THUMB_OPPOSITION=40
BASE_REL=None
CLOSURE_ARC_FOOT_LOCAL=(-.002462023636326194,.0002567582705523819,.002086180727928877)

def ease_between(t,start,end):return a.ease((t-start)/(end-start))
def leg_amount(t):
    if t<1.05:return ACQ*ease_between(t,.15,1.05)
    if t<1.3:return ACQ
    if t<2:return ACQ+(1-ACQ)*ease_between(t,1.3,2)
    if t<=3:return 1
    if t<3.7:return 1-(1-ACQ)*ease_between(t,3,3.7)
    if t<3.95:return ACQ
    return ACQ*(1-ease_between(t,3.95,4.85))

def load_geometry_components():
    """Read body components, discard rejected motion and rebuild the rig action."""
    global REUSED_KEYS
    bpy.ops.wm.open_mainfile(filepath=str(OLD/'source.blend'))
    oldbody=bpy.data.objects['SK_BlenderStudioHuman']
    oldweights=[{oldbody.vertex_groups[g.group].name:float(g.weight)for g in v.groups}for v in oldbody.data.vertices]
    REUSED_KEYS={k.name:np.array([v.co[:]for v in k.data])for k in oldbody.data.shape_keys.key_blocks if k.name!='Basis'}
    source_hash=hashlib.sha256((OLD/'source.blend').read_bytes()).hexdigest()
    assert a.initialize()==EXPECTED
    changed=json.loads((OLD/'local-binding-report.json').read_text())['vertices']
    for row in changed:
        i=row['id'];existing=[a.body.vertex_groups[g.group].name for g in a.body.data.vertices[i].groups]
        for name in existing:a.body.vertex_groups[name].remove([i])
        for name,w in oldweights[i].items():a.body.vertex_groups[name].add([i],w,'REPLACE')
    actual=[{a.body.vertex_groups[g.group].name:float(g.weight)for g in v.groups}for v in a.body.data.vertices]
    assert actual==oldweights
    sums=np.array([sum(row.values())for row in actual]);counts=np.array([sum(w>1e-8 for w in row.values())for row in actual])
    assert np.max(abs(sums-1))<1e-6 and counts.max()<=4
    a.body.shape_key_add(name='Basis',from_mix=False)
    for name,points in REUSED_KEYS.items():
        key=a.body.shape_key_add(name=name,from_mix=False);key.data.foreach_set('co',points.astype(np.float32).ravel());key.value=0
    for mod in a.body.modifiers:
        mod.show_viewport=mod.show_render=mod.type=='ARMATURE'
        if mod.type=='ARMATURE':mod.use_deform_preserve_volume=True
    (P/'reused-geometry-components.json').write_text(json.dumps({'history_source_sha256':source_hash,'history_motion_status':'User-rejected grasp; discarded completely. No visual approval inherited.','components':'Existing239-ID binding and three compact body POSITION keys reused byte-for-byte as technical inputs; no new fairing.','binding_sha256':a.binding_hash(a.body,a.rig),'source_basis_binding_sha256':EXPECTED,'maximum_actual_weight_sum_error':float(np.max(abs(sums-1))),'maximum_actual_influences':int(counts.max()),'key_buffer_sha256':{name:hashlib.sha256(points.astype(np.float32).tobytes()).hexdigest()for name,points in REUSED_KEYS.items()}},indent=2)+'\n')

def lower_body(t):
    u=leg_amount(t)
    d=a.torso(a.V((-.018*u,.06,.4615-.004*u)),[PITCH]*5)
    for side,sign in [('Left',1),('Right',-1)]:
        hip=d['Hips']@a.rest['Hips'].inverted()@a.heads[side+'UpLeg']
        alpha=math.radians(115*u)if side=='Left'else 0
        knee=hip+a.V((sign*.008,math.sin(alpha),-math.cos(alpha))).normalized()*a.length[side+'UpLeg']
        if side=='Right':
            dx=-.1085385-hip.x;knee=hip+a.V((dx,0,-math.sqrt(a.length[side+'UpLeg']**2-dx**2)))
        # Acquire with140degree knee flexion, then gently pull to130degrees.
        beta=math.radians(2.65+(155-2.65)*min(1,u/ACQ))if side=='Left'else math.radians(2.65)
        ankle=knee+a.V((0,math.cos(beta),math.sin(beta)))*a.length[side+'Leg']
        d[side+'UpLeg']=Matrix.Translation(hip)@a.orient(side+'UpLeg',knee-hip).to_matrix().to_4x4()
        if side=='Left':
            # Transport the planted ankle frame through the sagittal hinge.
            # A shortest-arc shin frame flips near the antipodal direction;
            # an unrelated world foot curve then crushes the blended ankle.
            initial=math.radians(2.65)
            hinge=a.rx(math.degrees(beta-initial))
            legq=hinge@a.orient(side+'Leg',(0,math.cos(initial),math.sin(initial)))
            fq=hinge@a.foot_rotation(side,150)
        else:
            legq=a.orient(side+'Leg',ankle-knee)
            fq=a.foot_rotation(side,150)
        d[side+'Leg']=Matrix.Translation(knee)@legq.to_matrix().to_4x4()
        d[side+'Foot']=Matrix.Translation(ankle)@(fq@a.rest[side+'Foot'].to_quaternion()).to_matrix().to_4x4()
        toe=d[side+'Foot']@a.rest[side+'Foot'].inverted()@a.heads[side+'ToeBase']
        d[side+'ToeBase']=Matrix.Translation(toe)@(fq@a.rest[side+'ToeBase'].to_quaternion()).to_matrix().to_4x4()
    for side in ['Left','Right']:
        sh=side+'Shoulder';head=d['Spine1']@a.rest['Spine1'].inverted()@a.heads[sh]
        d[sh]=Matrix.Translation(head)@(a.rx(PITCH)@a.rest[sh].to_quaternion()).to_matrix().to_4x4()
    return d

def shoulder(d,side):return d[side+'Shoulder']@a.rest[side+'Shoulder'].inverted()@a.heads[side+'Arm']
def grip_rotation(direction,normal):
    source_long=a.tails['LeftHand']-a.heads['LeftHand']
    return (a.frame(direction,normal)@a.frame(source_long,PALM_NORMAL_SOURCE).transposed()).to_quaternion()
def arm_chain(d,side,wrist):
    sh=shoulder(d,side);sign=1 if side=='Left'else-1
    elbow,wrist=a.two_joint(sh,wrist,a.length[side+'Arm'],a.length[side+'ForeArm'],sh+a.V((sign*.38,.02,-.08)))
    q=a.orient(side+'Arm',elbow-sh)
    d[side+'Arm']=Matrix.Translation(sh)@q.to_matrix().to_4x4()
    q=q@a.rest[side+'Arm'].to_quaternion().inverted()@a.rest[side+'ForeArm'].to_quaternion()
    q=(q@a.V((0,1,0))).rotation_difference((wrist-elbow).normalized())@q
    d[side+'ForeArm']=Matrix.Translation(elbow)@q.to_matrix().to_4x4()
    return elbow,wrist

def aligned_grip(d):
    """Solve a forearm+palm chain: source palm skin reaches the foot anchor."""
    sh=shoulder(d,'Left');foot=d['LeftFoot']
    target=foot@FOOT_ANCHOR_LOCAL
    normal=-(foot.to_3x3()@FOOT_NORMAL_LOCAL).normalized()
    handlong=(a.tails['LeftHand']-a.heads['LeftHand']).normalized()
    source_offset=PALM_SOURCE-a.heads['LeftHand'];along=source_offset.dot(handlong)
    direction=(target-sh).normalized();error=1
    for _ in range(12):
        hq=grip_rotation(direction,normal)
        offset=hq@source_offset;perpendicular=offset-direction*along
        elbow,virtual=a.two_joint(sh,target-perpendicular,a.length['LeftArm'],a.length['LeftForeArm']+along,sh+a.V((.38,.02,-.08)))
        direction=(virtual-elbow).normalized()
    hq=grip_rotation(direction,normal);wrist=elbow+direction*a.length['LeftForeArm']
    error=(wrist+hq@source_offset-target).length
    assert error<.0002,('Palm virtual-chain target unreachable; actual surface target error m',error,'target',list(target),'shoulder',list(sh),'arm lengths m',[a.length['LeftArm'],a.length['LeftForeArm']])
    return Matrix.Translation(wrist)@(hq@a.rest['LeftHand'].to_quaternion()).to_matrix().to_4x4(),target

def floor_hand(side,d):
    q=a.palm_rotation(side,(0,-1,0),(0,0,-1));g=a.body.vertex_groups[side+'Hand'].index
    pts=[v.co for v in a.body.data.vertices if any(w.group==g and w.weight>.5 for w in v.groups)]
    z=.003-min((q@(v-a.heads[side+'Hand'])).z for v in pts)
    arm=shoulder(d,side);return a.V((arm.x if side=='Left'else-.18,arm.y,z)),q

def free_hand(d,t):
    tau=t if t<=2.5 else 5-t
    start,startq=floor_hand('Left',d)
    acq=lower_body(1.3);locked=acq['LeftFoot']@GRIP_REL
    out=acq['LeftFoot'].to_3x3()@FOOT_NORMAL_LOCAL;out.normalize()
    pre=locked.translation+out*.040
    lift=a.V((.27,-.36,.25));way=a.V((.34,-.04,.50))
    if tau<.30:wrist=start.lerp(lift,ease_between(tau,0,.30))
    elif tau<.85:wrist=lift.lerp(way,ease_between(tau,.30,.85))
    elif tau<1.05:wrist=way.lerp(pre,ease_between(tau,.85,1.05))
    else:
        # The new thumb wrap needs a small outward arc while it closes.
        # This clears the measured 1.04mm intermediate intrusion, then
        # reaches the unchanged stable collar frame with zero end speed.
        closing=max(0,min(1,(tau-1.10)/.20))
        clearance_arc=.0035*math.sin(math.pi*closing)**2
        arc_normal=acq['LeftFoot'].to_3x3()@a.V(CLOSURE_ARC_FOOT_LOCAL)
        wrist=locked.translation+out*(.040*(1-ease_between(tau,1.05,1.30))**.7+clearance_arc)+arc_normal*math.sin(math.pi*closing)**2
    elbow,wrist=arm_chain(d,'Left',wrist)
    fore=(wrist-elbow).normalized();neutral=grip_rotation(fore,(-1,0,0))
    if tau<.55:hq=startq.slerp(neutral,ease_between(tau,.05,.55))
    else:hq=neutral
    if tau>.85:
        endq=locked.to_quaternion()@a.rest['LeftHand'].to_quaternion().inverted()
        hq=hq.slerp(endq,ease_between(tau,.85,1.05))
    hand=Matrix.Translation(wrist)@(hq@a.rest['LeftHand'].to_quaternion()).to_matrix().to_4x4()
    close=ease_between(tau,1.10,1.30)
    return hand,close

def pose(t,enforce_reach=True):
    d=lower_body(t)
    wr,q=floor_hand('Right',d);_,wr=arm_chain(d,'Right',wr)
    d['RightHand']=Matrix.Translation(wr)@(q@a.rest['RightHand'].to_quaternion()).to_matrix().to_4x4()
    if 1.3<=t<=3.7:
        hand=d['LeftFoot']@GRIP_REL;_,wr=arm_chain(d,'Left',hand.translation)
        distance=(hand.translation-shoulder(d,'Left')).length
        if enforce_reach:assert(wr-hand.translation).length<1e-5,('Unreachable held foot-local wrist','time',t,'target_distance_m',distance,'arm_length_m',a.length['LeftArm']+a.length['LeftForeArm'],'reach_deficit_m',distance-a.length['LeftArm']-a.length['LeftForeArm'],'target',list(hand.translation))
        d['LeftHand']=hand;close=1
    else:d['LeftHand'],close=free_hand(d,t)
    for name,(h,tail,parent,digit,index)in a.finger_specs.items():
        side='Left'if name.startswith('Left')else'Right'
        normal=a.V((-1 if side=='Left'else 1,0,0));axis=a.rest[name].to_3x3().inverted()@(tail-h).normalized().cross(normal).normalized()
        angles=[0,0,0]if digit!='Thumb'else[0,-18,-17]
        if side=='Left':angles=[start+(end-start)*close for start,end in zip(angles,FINGER_CLOSED[digit])]
        d[name]=d[parent]@a.rest[parent].inverted()@a.rest[name]@Quaternion(axis,math.radians(angles[index])).to_matrix().to_4x4()
        if name=='LeftThumb1':
            mat=d[name];axis=d['LeftHand'].to_3x3()@a.V((0,1,0));q=Quaternion(axis,math.radians(THUMB_OPPOSITION*close));d[name]=Matrix.Translation(mat.translation)@q.to_matrix().to_4x4()@mat.to_3x3().to_4x4()
    return d,close

def apply(d):
    for pb in a.rig.pose.bones:
        parent=pb.parent.name if pb.parent else None
        pb.matrix_basis=a.rest[pb.name].inverted()@(a.rest[parent]@d[parent].inverted()if parent else Matrix.Identity(4))@d[pb.name]
    bpy.context.view_layer.update()

def coords():
    e=a.body.evaluated_get(bpy.context.evaluated_depsgraph_get());m=e.to_mesh();p=np.array([v.co[:]for v in m.vertices]);e.to_mesh_clear();return p

def readback_weights():
    sums=[];counts=[]
    for v in a.body.data.vertices:
        ws=[float(g.weight)for g in v.groups];sums.append(sum(ws));counts.append(len([w for w in ws if w>1e-8]))
    result={'source_sha256':hashlib.sha256((P/'source.blend').read_bytes()).hexdigest(),'readback':'Actual saved/reopened Blender VertexGroupElement values, not solver arrays.','vertices':len(sums),'maximum_influences':max(counts),'minimum_weight_sum':min(sums),'maximum_weight_sum':max(sums),'maximum_sum_error':max(abs(x-1)for x in sums)}
    assert result['maximum_influences']<=4 and result['maximum_sum_error']<1e-6
    (P/'weight-readback.json').write_text(json.dumps(result,indent=2)+'\n')

def prepare(use_fit=True):
    global GRIP_REL,BASE_REL,PALM_SOURCE,PALM_NORMAL_SOURCE,FOOT_ANCHOR_SOURCE,FOOT_NORMAL_SOURCE,FOOT_ANCHOR_LOCAL,FOOT_NORMAL_LOCAL
    load_geometry_components()
    handlong=(a.tails['LeftHand']-a.heads['LeftHand']).normalized()
    desired=a.heads['LeftHand']+handlong*.075+a.V((-.020,0,0))
    group=a.body.vertex_groups['LeftHand'].index
    candidates=[v for v in a.body.data.vertices if any(g.group==group and g.weight>.8 for g in v.groups)]
    strong={v.index for v in a.body.data.vertices if any(g.group==group and g.weight>.5 for g in v.groups)}
    palm_faces=[p for p in a.body.data.polygons if all(i in strong for i in p.vertices)and p.normal.x<-.5]
    palm_points=np.array([a.body.data.vertices[i].co[:]for i in sorted({i for p in palm_faces for i in p.vertices})])
    fitted=np.linalg.svd(palm_points-palm_points.mean(axis=0))[2][-1]
    if fitted[0]>0:fitted=-fitted
    PALM_NORMAL_SOURCE=a.V(fitted)
    vertex=min(candidates,key=lambda v:(v.co-desired).length);palm_source_id=int(vertex.index);PALM_SOURCE=vertex.co.copy()
    footlong=(a.heads['LeftToeBase']-a.heads['LeftFoot']).normalized()
    footfaces=[]
    for face in a.body.data.polygons:
        center=face.center;along=(center-a.heads['LeftFoot']).dot(footlong)
        if center.x>.1 and .005<along<.050 and face.normal.x>.35 and .055<center.z<.15:footfaces.append(list(face.vertices))
    tree=BVHTree.FromPolygons([v.co.copy()for v in a.body.data.vertices],footfaces)
    query=a.heads['LeftFoot']+a.V((.12,0,-.02))
    nearest,normal,_,_=tree.find_nearest(query)
    FOOT_NORMAL_SOURCE=normal.copy();FOOT_ANCHOR_SOURCE=nearest+normal*.018
    acq=lower_body(1.3)
    for pb in a.rig.pose.bones:
        if pb.name not in acq:continue
        parent=pb.parent.name if pb.parent else None
        pb.matrix_basis=a.rest[pb.name].inverted()@(a.rest[parent]@acq[parent].inverted()if parent else Matrix.Identity(4))@acq[pb.name]
    for name,w in zip(['LocalStart','LocalEntry','LocalHold'],[max(0,1-2*ACQ),1-abs(2*ACQ-1),max(0,2*ACQ-1)]):a.body.data.shape_keys.key_blocks[name].value=w
    bpy.context.view_layer.update();actual=coords()
    actual_tree=BVHTree.FromPolygons([a.V(p)for p in actual],footfaces)
    actual_query=acq['LeftFoot']@a.rest['LeftFoot'].inverted()@query
    point,normal,_,_=actual_tree.find_nearest(actual_query)
    FOOT_ANCHOR_LOCAL=acq['LeftFoot'].inverted()@(point+normal*.018)
    FOOT_NORMAL_LOCAL=(acq['LeftFoot'].to_3x3().inverted()@normal).normalized()
    hand,anchor=aligned_grip(acq);GRIP_REL=acq['LeftFoot'].inverted()@hand;BASE_REL=GRIP_REL.copy()
    if use_fit and (P/'grip-pose-fit.json').exists():
        fit=json.loads((P/'grip-pose-fit.json').read_text())
        if fit.get('accepted',False) or '--candidate-fit' in sys.argv:configure_fit(fit['parameters'])
    shift_transport_grasp(True)
    return palm_source_id

def shift_transport_grasp(write_receipt=False):
    # The causally repaired foot frame puts the prior attachment 0.681mm
    # beyond fixed arm reach. Root authorized one 2mm collar translation;
    # retain all finger parameters and never satisfy it by IK clamping.
    hold=lower_body(2);hand=hold['LeftFoot']@GRIP_REL
    toward=(shoulder(hold,'Left')-hand.translation).normalized()
    displacement=hold['LeftFoot'].to_3x3().inverted()@(toward*.002)
    before=(hand.translation-shoulder(hold,'Left')).length
    GRIP_REL.translation+=displacement
    after=((hold['LeftFoot']@GRIP_REL).translation-shoulder(hold,'Left')).length
    if write_receipt:(P/'foot-return-repair'/'attachment-shift.json').write_text(json.dumps({'method':'One authorized 2mm foot-local collar translation toward the hold shoulder, retained during the later authorized bounded digit re-fit.','foot_local_displacement_m':list(displacement),'displacement_length_m':displacement.length,'before_wrist_target_distance_m':before,'after_wrist_target_distance_m':after,'unchanged_arm_length_m':a.length['LeftArm']+a.length['LeftForeArm'],'after_reach_margin_m':a.length['LeftArm']+a.length['LeftForeArm']-after},indent=2)+'\n')

def configure_fit(x):
    global GRIP_REL,THUMB_OPPOSITION,FINGER_CLOSED
    acq=lower_body(1.3);base=acq['LeftFoot']@BASE_REL;normal=acq['LeftFoot'].to_3x3()@FOOT_NORMAL_LOCAL;normal.normalize();long=base.to_3x3()@a.V((0,1,0));long.normalize();cross=long.cross(normal).normalized()
    position=base.translation+.01*(normal*x[0]+long*x[1]+cross*x[2])
    q=base.to_quaternion()@Quaternion(a.V((1,0,0)),math.radians(x[3]*10))@Quaternion(a.V((0,1,0)),math.radians(x[4]*10))@Quaternion(a.V((0,0,1)),math.radians(x[5]*10))
    GRIP_REL=acq['LeftFoot'].inverted()@(Matrix.Translation(position)@q.to_matrix().to_4x4())
    for i,digit in enumerate(['Index','Middle','Ring','Little','Thumb']):FINGER_CLOSED[digit]=[float(v*10)for v in x[6+i*3:9+i*3]]
    THUMB_OPPOSITION=float(x[21]*10)

def main():
    palm_source_id=prepare()
    a.rig.animation_data_clear();a.body.data.shape_keys.animation_data_clear()
    for action in list(bpy.data.actions):bpy.data.actions.remove(action)
    action=bpy.data.actions.new('Exercise_1512');action.use_fake_user=True;a.rig.animation_data_create();a.rig.animation_data.action=action
    keys=a.body.data.shape_keys;keys.animation_data_create();keys.animation_data.action=action;keys.animation_data.action_slot=action.slots.new(id_type='KEY',name='Preserved compact body components')
    a.scene.frame_start=1;a.scene.frame_end=151
    for f in range(151):
        a.scene.frame_set(f+1);d,close=pose(f/30);apply(d)
        for pb in a.rig.pose.bones:
            pb.keyframe_insert('location',frame=f+1);pb.keyframe_insert('rotation_quaternion',frame=f+1)
        u=leg_amount(f/30)
        for name,w in zip(['LocalStart','LocalEntry','LocalHold'],[max(0,1-2*u),1-abs(2*u-1),max(0,2*u-1)]):
            k=keys.key_blocks[name];k.value=w;k.keyframe_insert('value',frame=f+1)
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for curve in bag.fcurves:
                    for key in curve.keyframe_points:key.interpolation='LINEAR'
    attr=a.body.data.attributes.get('_SOURCE_INDEX')or a.body.data.attributes.new('_SOURCE_INDEX','FLOAT','POINT');attr.data.foreach_set('value',np.arange(10582,dtype=np.float32))
    s=a.scene;s.render.engine='BLENDER_WORKBENCH';s.render.resolution_x=1100;s.render.resolution_y=850;s.render.resolution_percentage=100
    s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGBA';s.render.film_transparent=True
    sh=s.display.shading;sh.light='STUDIO';sh.color_type='MATERIAL';sh.show_shadows=False;sh.show_cavity=False;sh.show_specular_highlight=False
    s.view_settings.view_transform='Standard';s.view_settings.look='None'
    camera_data=bpy.data.cameras.new('RepairReviewCamera');camera=bpy.data.objects.new('RepairReviewCamera',camera_data);s.collection.objects.link(camera);s.camera=camera;camera_data.type='ORTHO'
    a.scene.frame_set(1);bpy.ops.wm.save_as_mainfile(filepath=str(P/'source.blend'))
    bpy.ops.wm.open_mainfile(filepath=str(P/'source.blend'));a.body=bpy.data.objects['SK_BlenderStudioHuman'];a.rig=bpy.data.objects['RIG_BlenderStudioHuman'];a.scene=bpy.context.scene;s=a.scene;camera=s.camera
    assert[a.name for a in bpy.data.actions]==['Exercise_1512']
    readback_weights()
    samples=[]
    for f in range(151):
        s.frame_set(f+1);bpy.context.view_layer.update();expected,_=pose(f/30)
        error=max(max(abs(float(x-y))for rowa,rowb in zip(pb.matrix,expected[pb.name])for x,y in zip(rowa,rowb))for pb in a.rig.pose.bones)
        assert error<.00001,('Keyed native pose readback',f,error)
        shoulder_p,elbow,wrist,palm=[a.rig.pose.bones[n].head.copy()for n in ['LeftArm','LeftForeArm','LeftHand','LeftMiddle1']]
        relative=a.rig.pose.bones['LeftFoot'].matrix.inverted()@a.rig.pose.bones['LeftHand'].matrix
        samples.append({'frame':f,'phase':('held' if 1.3<=f/30<=3.7 else 'free'),'wrist_deviation_degrees':math.degrees((wrist-elbow).angle(palm-wrist)),'elbow_flexion_degrees':math.degrees((elbow-shoulder_p).angle(wrist-elbow)),'foot_local_hand_matrix':[list(row)for row in relative],'joints':{pb.name:list(pb.head)for pb in a.rig.pose.bones},'maximum_native_matrix_error':error})
    (P/'early-native-readback.json').write_text(json.dumps({'source_sha256':hashlib.sha256((P/'source.blend').read_bytes()).hexdigest(),'palm_source_id':palm_source_id,'palm_source_coordinate':list(PALM_SOURCE),'foot_anchor_source_coordinate':list(FOOT_ANCHOR_SOURCE),'foot_anchor_source_normal':list(FOOT_NORMAL_SOURCE),'foot_local_grasp_matrix':[list(row)for row in GRIP_REL],'all151_keyed_bone_readback':True,'samples':samples},indent=2)+'\n')
    views={'side':([3.6,-.05,.88],[0,.02,.43],1.90),'oblique':([2.8,-2.3,1.55],[0,.06,.43],1.90)}
    receipts=[]
    for label,f,kind in [('start',0,'side'),('approach',25,'oblique'),('grasp',40,'oblique'),('hold',75,'side'),('release',115,'oblique'),('return',140,'side')]:
        s.frame_set(f+1);bpy.context.view_layer.update();before=coords();matrices={pb.name:pb.matrix.copy()for pb in a.rig.pose.bones}
        position,target,width=views[kind];camera.location=position;camera.rotation_euler=(a.V(target)-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.ortho_scale=width
        s.render.filepath=str(P/f'early-{label}-{kind}.png');bpy.ops.render.render(write_still=True)
        after=coords();surface_error=float(np.linalg.norm(after-before,axis=1).max());bone_error=max(max(abs(float(x-y))for rowa,rowb in zip(pb.matrix,matrices[pb.name])for x,y in zip(rowa,rowb))for pb in a.rig.pose.bones)
        assert surface_error<1e-7 and bone_error<1e-7,('Render overrides action',label)
        receipts.append({'phase':label,'frame':f,'surface_before_after_render_max_m':surface_error,'bone_before_after_render_max_error':bone_error})
    for label,f in [('grasp',40),('release',115)]:
        s.frame_set(f+1);bpy.context.view_layer.update();target=a.rig.pose.bones['LeftFoot'].head+a.V((.05,-.04,-.03));camera.location=target+a.V((2,.8,.5));camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.ortho_scale=.47
        before=coords();s.render.filepath=str(P/f'early-{label}-detail.png');bpy.ops.render.render(write_still=True);assert float(np.linalg.norm(coords()-before,axis=1).max())<1e-7
    (P/'early-render-readback.json').write_text(json.dumps({'source_sha256':hashlib.sha256((P/'source.blend').read_bytes()).hexdigest(),'samples':receipts},indent=2)+'\n')
    print('STAGED_GRASP_EARLY_READY',P)

if __name__=='__main__':main()
