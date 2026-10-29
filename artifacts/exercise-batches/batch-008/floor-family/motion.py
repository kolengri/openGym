"""Floor exercises on the invariant Blender Studio rest skeleton."""
import math
from mathutils import Matrix, Vector
import palm_frame

PALMS = None

def configure(a):
    global PALMS
    PALMS = palm_frame.prepare(a)

def smooth(t):
    t = max(0., min(1., t))
    return t*t*t*(10+t*(-15+6*t))

def schedule(frame, exercise):
    f = frame % 150
    if exercise == '3204':
        p = smooth(f/60) if f < 60 else 1. if f < 85 else 1-smooth((f-85)/60) if f < 145 else 0.
        return {'envelope': p, 'sweep': 0., 'phase': 'Curl upright' if f < 60 else 'Tall pause' if f < 85 else 'Lower with control' if f < 145 else 'Supine'}
    p = smooth(f/24) if f < 24 else 1. if f < 120 else 1-smooth((f-120)/30)
    sweep = smooth((f-24)/48) if f < 72 else 1-smooth((f-72)/48) if f < 120 else 0.
    return {'envelope': p, 'sweep': sweep, 'phase': 'Bilateral lift' if f < 24 else 'Wide sweep toward hips' if f < 72 else 'Wide sweep overhead' if f < 120 else 'Controlled lower'}

def transported(a, name, parent, q, direction):
    base = q @ a.rest[parent].to_quaternion().inverted() @ a.rest[name].to_quaternion()
    return (base @ Vector((0,1,0))).rotation_difference(direction.normalized()) @ base

def pose(a, frame, exercise, root_z, offsets=None):
    state = schedule(frame, exercise)
    p, sw = state['envelope'], state['sweep']
    offsets = offsets or {}
    sit = exercise == '3204'
    if sit:
        # Pelvis stays supported while the lumbar and thoracic segments peel.
        pitch = [-90+16*p, -89+75*p, -89+88*p, -90+89*p, -90+89*p]
        root = Vector((0,.05,root_z))
    else:
        pitch = [90, 88-5*p, 84-10*p, 84-10*p, 84-10*p]
        root = Vector((0,.04,root_z))
    d = a.torso(root, pitch)
    cq = d['Spine1'].to_quaternion() @ a.rest['Spine1'].to_quaternion().inverted()
    reach = {}
    for side, sign in [('Left',1), ('Right',-1)]:
        hip = d['Hips'] @ a.rest['Hips'].inverted() @ a.heads[side+'UpLeg']
        if sit:
            fq = a.foot_rotation(side)
            ankle = Vector((sign*.16,-.51,a.sole_height(side,fq)+offsets.get(side+'_foot',0)))
            knee, actual = a.two_joint(hip,ankle,a.length[side+'UpLeg'],a.length[side+'Leg'],hip+Vector((0,-.2,.7)))
            reach[side+'_ankle'] = (actual-ankle).length
            ankle = actual
            uq = a.orient(side+'UpLeg',knee-hip)
            lq = transported(a,side+'Leg',side+'UpLeg',uq,ankle-knee)
        else:
            angle = math.radians(-8.4+2.8*p)
            direction = Vector((sign*.035,math.cos(angle),math.sin(angle))).normalized()
            knee = hip + direction*a.length[side+'UpLeg']
            ankle = knee + direction*a.length[side+'Leg']
            uq = a.orient(side+'UpLeg',direction)
            lq = transported(a,side+'Leg',side+'UpLeg',uq,direction)
            fq = a.rx(150+2.2*p) @ a.rz(-sign*20.8)
        for name,head,q in [(side+'UpLeg',hip,uq),(side+'Leg',knee,lq),(side+'Foot',ankle,fq@a.rest[side+'Foot'].to_quaternion())]:
            d[name] = Matrix.Translation(head) @ q.to_matrix().to_4x4()
        toe = d[side+'Foot'] @ a.rest[side+'Foot'].inverted() @ a.heads[side+'ToeBase']
        d[side+'ToeBase'] = Matrix.Translation(toe) @ (fq@a.rest[side+'ToeBase'].to_quaternion()).to_matrix().to_4x4()
        sh = d['Spine1'] @ a.rest['Spine1'].inverted() @ a.heads[side+'Shoulder']
        d[side+'Shoulder'] = Matrix.Translation(sh) @ (cq@a.rest[side+'Shoulder'].to_quaternion()).to_matrix().to_4x4()
        shoulder = d[side+'Shoulder'] @ a.rest[side+'Shoulder'].inverted() @ a.heads[side+'Arm']
        if sit:
            direction = (cq @ Vector((sign*.09,0,1))).normalized()
            normal = cq @ Vector((-sign,0,0))
            pole = shoulder + cq@Vector((sign*.6,-.08,.2))
        else:
            theta = math.radians(155*sw)
            direction = Vector((sign*(.10+math.sin(theta)), -math.cos(theta), .015+.12*p)).normalized()
            normal = Vector((0,0,-1))
            pole = shoulder + Vector((sign*.7,0,.1))
        length = math.sqrt(a.length[side+'Arm']**2+a.length[side+'ForeArm']**2+2*a.length[side+'Arm']*a.length[side+'ForeArm']*math.cos(math.radians(7)))
        wrist = shoulder + direction*length
        if not sit:
            wrist.z = .045+.13*p+offsets.get(side+'_hand',0)*(1-p)
            delta = wrist.z-shoulder.z
            horizontal = Vector((direction.x,direction.y,0)).normalized()
            wrist = shoulder + horizontal*math.sqrt(max(.001,length*length-delta*delta))
            wrist.z = .045+.13*p+offsets.get(side+'_hand',0)*(1-p)
            direction = (wrist-shoulder).normalized()
        elbow, actual = a.two_joint(shoulder,wrist,a.length[side+'Arm'],a.length[side+'ForeArm'],pole)
        reach[side+'_wrist'] = (actual-wrist).length
        wrist = actual
        aq = cq @ a.orient(side+'Arm',cq.inverted()@(elbow-shoulder))
        bq = transported(a,side+'ForeArm',side+'Arm',aq,wrist-elbow)
        hq = palm_frame.hand(a,side,direction,normal,PALMS)
        for name,head,q in [(side+'Arm',shoulder,aq),(side+'ForeArm',elbow,bq),(side+'Hand',wrist,hq)]:
            d[name] = Matrix.Translation(head) @ q.to_matrix().to_4x4()
    for name,(_,_,parent,_,_) in a.finger_specs.items():
        d[name] = d[parent] @ a.rest[parent].inverted() @ a.rest[name]
    for bone in a.rig.pose.bones:
        parent = bone.parent.name if bone.parent else None
        bone.matrix_basis = a.rest[bone.name].inverted() @ (a.rest[parent]@d[parent].inverted() if parent else Matrix.Identity(4)) @ d[bone.name]
    return d,{**state,'reach_errors_m':reach}
