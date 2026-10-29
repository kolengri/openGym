"""Three source-facing, complete five-second standing movement cycles.

All metric amplitudes/timings below are authored demonstration choices.
"""
import math
from mathutils import Vector, Matrix, Quaternion

IDS = ('3220', '3672', '6097')
SIDES = [('Left', 1), ('Right', -1)]

def smooth(x):
    x = max(0., min(1., x))
    return x*x*x*(x*(x*6-15)+10)

def ramp(u, a, b):
    return smooth((u-a)/(b-a))

def state(frame, exercise):
    f = frame % 150
    if exercise == '3220':
        u = (f % 75)/75
        airborne = 1/3 < u < .64
        t = max(0., min(1., (u-1/3)/(.64-1/3)))
        load = ramp(u, 0, .20)*(1-ramp(u, .20, 1/3))
        absorb = ramp(u, .64, .79)*(1-ramp(u, .79, 1))
        spread = math.sin(math.pi*min(1., t/.82))**2 if airborne else 0.
        return dict(frame=frame, time=frame/30, repetition=int(f//75), u=u,
                    flight=airborne, grounded=[] if airborne else ['Left', 'Right'],
                    flight_height=.18*4*t*(1-t), spread=spread, load=load,
                    absorb=absorb, phase=('Squat to load' if u<.20 else
                    'Extend to take off' if u<=1/3 else 'Spread then close during flight' if u<.64
                    else 'Absorb shoulder-width landing' if u<.79 else 'Return to standing'))
    if exercise == '3672':
        step=int(f//75); u=(f%75)/75; moving='Right' if step%2==0 else 'Left'
        travel=ramp(u,.10,.30)*(1-ramp(u,.67,.90))
        swing=(.10<u<.30) or (.67<u<.90)
        sf=(u-.10)/.20 if u<.50 else (u-.67)/.23
        lift=.075*math.sin(math.pi*max(0.,min(1.,sf)))**2 if swing else 0.
        load=ramp(u,.30,.45)*(1-ramp(u,.55,.67))
        transfer=ramp(u,0,.10)*(1-ramp(u,.90,1))
        return dict(frame=frame,time=frame/30,repetition=step,u=u,moving_side=moving,
                    flight=False,grounded=[s for s,_ in SIDES if not(s==moving and swing)],
                    travel=travel,foot_lift=lift,load=load,transfer=transfer,
                    rear_heel_lift_degrees=30*travel,
                    phase=('Transfer weight' if u<.10 else 'Place forward foot' if u<.30
                    else 'Lower into supported forward lunge' if u<.55 else 'Push back to rise' if u<.67
                    else 'Step foot home' if u<.90 else 'Recenter'))
    step=int(f//37.5);u=(f%37.5)/37.5;p=math.sin(math.pi*u)**2
    moving='Right' if step%2==0 else 'Left'
    return dict(frame=frame,time=frame/30,repetition=step,u=u,moving_side=moving,
                flight=False,grounded=[s for s,_ in SIDES if s!=moving] if 1e-8<u<1-1e-8 else ['Left','Right'],
                kick=p,press=p,phase='Kick backward and press overhead' if u<.5 else 'Return foot and hands to shoulder height')

def transported(a,name,parent,q,direction):
    base=q@a.rest[parent].to_quaternion().inverted()@a.rest[name].to_quaternion()
    return (base@Vector((0,1,0))).rotation_difference(direction.normalized())@base

def pose(a,frame,exercise,offsets=None):
    offsets=offsets or {};st=state(frame,exercise);root=Vector((0,.025,.945));pitch=0.
    if exercise=='3220':
        root.z-=.145*st['load']+.125*st['absorb']+.055*st['spread'];root.z+=st['flight_height']
        root.y+=.12*st['load']+.10*st['absorb'];pitch=25*st['load']+20*st['absorb']
    elif exercise=='3672':
        sign=1 if st['moving_side']=='Left' else -1
        root.x=-sign*.035*st['transfer'];root.y-=.18*st['travel']+.04*st['load'];root.z-=.07*st['travel']+.025*st['load'];pitch=5*st['load']
    else:
        sign=1 if st['moving_side']=='Left' else -1
        root.x=-sign*.035*st['kick'];root.z-=.006*st['kick']
    d=a.torso(root,[pitch,pitch,pitch,pitch,pitch]);reach={}
    for side,sign in SIDES:
        hip=d['Hips']@a.rest['Hips'].inverted()@a.heads[side+'UpLeg']
        yaw=a.rz(-sign*7);fq=yaw@a.rest[side+'Foot'].to_quaternion()
        base=Vector((sign*.155,0,a.sole_height(side,yaw)-.002))
        ankle=base.copy();active=st.get('moving_side')==side
        if exercise=='3220':
            ankle.x+=sign*.17*st['spread'];ankle.z+=st['flight_height']
        elif exercise=='3672':
            if active:ankle.y-=.43*st['travel'];ankle.z+=st['foot_lift']
            else:
                pitchq=a.rx(st['rear_heel_lift_degrees']);rot=pitchq@yaw
                # Toe joint is the stable forefoot pivot during rear-heel release.
                delta=a.heads[side+'ToeBase']-a.heads[side+'Foot']
                ankle+=yaw@delta-rot@delta
                ankle.z=a.sole_height(side,rot)-.002;fq=rot@a.rest[side+'Foot'].to_quaternion()
        elif active:
            ankle.y+=.30*st['kick'];ankle.z+=.045*st['kick']
        ankle.z+=offsets.get(side,0.)
        knee,actual=a.two_joint(hip,ankle,a.length[side+'UpLeg'],a.length[side+'Leg'],hip+Vector((sign*.055,-1,0)))
        reach[side+'_ankle']=float((actual-ankle).length);ankle=actual
        uq=a.orient(side+'UpLeg',knee-hip);lq=transported(a,side+'Leg',side+'UpLeg',uq,ankle-knee)
        if exercise=='6097' and active:
            # Shin-relative foot transport avoids a backward-kick ankle hook.
            bk,ba=a.two_joint(hip,base,a.length[side+'UpLeg'],a.length[side+'Leg'],hip+Vector((sign*.055,-1,0)))
            bu=a.orient(side+'UpLeg',bk-hip);bl=transported(a,side+'Leg',side+'UpLeg',bu,ba-bk)
            fq=fq.slerp(lq@bl.inverted()@fq,.75)
        for name,head,q in [(side+'UpLeg',hip,uq),(side+'Leg',knee,lq),(side+'Foot',ankle,fq)]:
            d[name]=Matrix.Translation(head)@q.to_matrix().to_4x4()
        toe=d[side+'Foot']@a.rest[side+'Foot'].inverted()@a.heads[side+'ToeBase']
        tq=fq@a.rest[side+'Foot'].to_quaternion().inverted()@a.rest[side+'ToeBase'].to_quaternion()
        d[side+'ToeBase']=Matrix.Translation(toe)@tq.to_matrix().to_4x4()
        chestq=d['Spine1'].to_quaternion()@a.rest['Spine1'].to_quaternion().inverted()
        elevation=st['spread'] if exercise=='3220' else st['press'] if exercise=='6097' else 0.
        name=side+'Shoulder';sh=d['Spine1']@a.rest['Spine1'].inverted()@a.heads[name]
        scap=Quaternion(Vector((0,1,0)),math.radians(-sign*8*elevation))
        d[name]=Matrix.Translation(sh)@(chestq@scap@a.rest[name].to_quaternion()).to_matrix().to_4x4()
        shoulder=d[name]@a.rest[name].inverted()@a.heads[side+'Arm']
        if exercise=='6097':
            p=st['press'];target=shoulder+Vector((sign*(.25-.055*p),-.10,.025+.445*p));pole=shoulder+Vector((sign*.45,-.04,-.40))
        else:
            angle=math.radians(25+75*elevation)
            length=math.sqrt(a.length[side+'Arm']**2+a.length[side+'ForeArm']**2+2*a.length[side+'Arm']*a.length[side+'ForeArm']*math.cos(math.radians(18)))
            swing=(-.055*st['load'] if side==st.get('moving_side') else .055*st.get('load',0)) if exercise=='3672' else .035*st['load']
            target=shoulder+Vector((sign*length*math.sin(angle),-.07+swing,-length*math.cos(angle)))
            target=shoulder+(target-shoulder).normalized()*length;pole=shoulder+Vector((sign*.20,.10,-.40))
        elbow,wrist=a.two_joint(shoulder,target,a.length[side+'Arm'],a.length[side+'ForeArm'],pole)
        reach[side+'_wrist']=float((target-wrist).length)
        aq=transported(a,side+'Arm',side+'Shoulder',d[side+'Shoulder'].to_quaternion(),elbow-shoulder)
        bq=transported(a,side+'ForeArm',side+'Arm',aq,wrist-elbow)
        if exercise!='6097':
            # Reuse accepted6014 source-rest relaxed endpoint and parent-relative fold.
            baseaq=d[side+'Shoulder'].to_quaternion()@a.rest[side+'Shoulder'].to_quaternion().inverted()@a.rest[side+'Arm'].to_quaternion()
            rel=a.rest[side+'Arm'].to_quaternion().inverted()@a.rest[side+'ForeArm'].to_quaternion()
            targetrel=aq.inverted()@bq;fraction=elevation if exercise=='3220' else .25*st['load']
            aq=baseaq.slerp(aq,fraction);bq=aq@rel.slerp(targetrel,fraction)
            elbow=shoulder+aq@Vector((0,a.length[side+'Arm'],0));wrist=elbow+bq@Vector((0,a.length[side+'ForeArm'],0))
        hq=bq@a.rest[side+'ForeArm'].to_quaternion().inverted()@a.rest[side+'Hand'].to_quaternion()
        for name,head,q in [(side+'Arm',shoulder,aq),(side+'ForeArm',elbow,bq),(side+'Hand',wrist,hq)]:
            d[name]=Matrix.Translation(head)@q.to_matrix().to_4x4()
    for name,(head,tail,parent,digit,index) in a.finger_specs.items():
        sign=1 if name.startswith('Left') else -1;side='Left' if sign==1 else 'Right'
        palmar=a.rest[side+'Hand'].to_3x3()@Vector((-sign,0,0));axis=a.rest[name].to_3x3().inverted()@(tail-head).normalized().cross(palmar).normalized()
        angle=([4,8,5] if digit=='Thumb' else [8,12,5])[index]
        d[name]=d[parent]@a.rest[parent].inverted()@a.rest[name]@Quaternion(axis,math.radians(angle)).to_matrix().to_4x4()
    for name,mat in d.items():d[name]=Matrix.Translation(mat.translation)@mat.to_quaternion().normalized().to_matrix().to_4x4()
    for pb in a.rig.pose.bones:
        parent=pb.parent.name if pb.parent else None
        pb.matrix_basis=a.rest[pb.name].inverted()@(a.rest[parent]@d[parent].inverted() if parent else Matrix.Identity(4))@d[pb.name]
    return d,{**st,'reach_errors_m':reach}
