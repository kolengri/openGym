"""Author five exercise-specific poses on the accepted continuous human surface."""
import bpy, math, json, sys
from pathlib import Path
from mathutils import Vector, Matrix, Quaternion

P = Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P.parent/'human-animation-base/professional-motion.blend'))
body = bpy.data.objects['SK_BlenderStudioHuman']
rig = bpy.data.objects['RIG_BlenderStudioHuman']
scene = bpy.context.scene
for ob in list(bpy.data.objects):
    if ob not in [body, rig, scene.camera]:
        bpy.data.objects.remove(ob, do_unlink=True)
rig.animation_data_clear()
for action in list(bpy.data.actions):bpy.data.actions.remove(action)
for pb in rig.pose.bones:
    pb.matrix_basis = Matrix.Identity(4)
    pb.rotation_mode = 'QUATERNION'
# Articulated fingers replace the previous rigid open-hand pose.
members=[set() for _ in body.data.vertices]
region_vertices={}
for face,attribute in zip(body.data.polygons,body.data.attributes['.sculpt_face_set'].data):
    region_vertices.setdefault(attribute.value,set()).update(face.vertices)
    for index in face.vertices:members[index].add(attribute.value)
finger_specs={};region_bones={}
for side,base,digits in [('Left',64,['Little','Ring','Middle','Index','Thumb']),('Right',84,['Thumb','Index','Middle','Ring','Little'])]:
    for digit_index,digit in enumerate(digits):
        parts=[base+digit_index*4+i for i in range(4)]
        points=[]
        for region in parts:
            vertices=[body.data.vertices[i].co for i in region_vertices[region]]
            top=max(v.z for v in vertices);ring=[v for v in vertices if v.z>top-.009]
            points.append(sum(ring,Vector())/len(ring))
        for i in range(3):
            name=f'{side}{digit}{i+1}'
            finger_specs[name]=(points[i],points[i+1],side+'Hand' if i==0 else f'{side}{digit}{i}',digit,i)
            region_bones[parts[i]]=name
        region_bones[parts[3]]=f'{side}{digit}3'
bpy.context.view_layer.objects.active=rig;rig.select_set(True);body.select_set(False)
bpy.ops.object.mode_set(mode='EDIT')
for name,(a,b,parent,digit,i) in finger_specs.items():
    bone=rig.data.edit_bones.new(name);bone.head=a;bone.tail=b;bone.parent=rig.data.edit_bones[parent]
bpy.ops.object.mode_set(mode='OBJECT')
for name in finger_specs:body.vertex_groups.new(name=name)
for vertex,regions in zip(body.data.vertices,members):
    groups={region_bones[r] for r in regions if r in region_bones}
    if not groups:continue
    if regions.intersection({9,10}):groups.add('LeftHand' if vertex.co.x>0 else 'RightHand')
    for old in [g.group for g in vertex.groups]:body.vertex_groups[old].remove([vertex.index])
    for group in groups:body.vertex_groups[group].add([vertex.index],1/len(groups),'REPLACE')
for pb in rig.pose.bones:pb.rotation_mode='QUATERNION'
rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
heads = {b.name: b.head_local.copy() for b in rig.data.bones}
tails = {b.name: b.tail_local.copy() for b in rig.data.bones}
length = {b.name: b.length for b in rig.data.bones}
coords = [v.co.copy() for v in body.data.vertices]
def V(x): return Vector(x)
def rx(degrees): return Quaternion(V((1,0,0)), math.radians(degrees))
def rz(degrees): return Quaternion(V((0,0,1)), math.radians(degrees))
def ease(t): return max(0,min(1,t))**2 * (3-2*max(0,min(1,t)))
def cycle(u): return .5-.5*math.cos(2*math.pi*u)
def frame(direction, normal):
    y=V(direction).normalized(); z=V(normal)-y*V(normal).dot(y)
    if z.length<1e-7: z=V((1,0,0))-y*y.x
    z.normalize(); x=y.cross(z).normalized()
    return Matrix((x,y,z)).transposed()
def orient(name, direction, normal=None):
    original=tails[name]-heads[name]
    if normal is None:
        return original.normalized().rotation_difference(V(direction).normalized()) @ rest[name].to_quaternion()
    original_normal=V((-1 if name.startswith('Left') else 1,0,0))
    q=(frame(direction,normal) @ frame(original,original_normal).transposed()).to_quaternion()
    return q @ rest[name].to_quaternion()
def two_joint(a,b,l1,l2,pole):
    delta=b-a; d=delta.length
    if d>l1+l2-.0005:
        b=a+delta.normalized()*(l1+l2-.0005);delta=b-a;d=delta.length
    if d<abs(l1-l2)+.001:
        b=a+delta.normalized()*(abs(l1-l2)+.001);delta=b-a;d=delta.length
    axis=delta.normalized();along=(l1*l1-l2*l2+d*d)/(2*d)
    bend=V(pole)-a; bend-=axis*bend.dot(axis)
    if bend.length<1e-6: bend=V((0,-1,0))-axis*(-axis.y)
    bend.normalize()
    return a+axis*along+bend*math.sqrt(max(0,l1*l1-along*along)),b

def foot_rotation(side,pitch=0):
    sign=1 if side=='Left' else -1
    return rx(pitch) @ rz(-sign*20.8)
def sole_height(side,q):
    sign=1 if side=='Left' else -1;ankle=heads[side+'Foot']
    vs=[v for v in coords if v.z<.095 and sign*v.x>.12]
    return -min((q@(v-ankle)).z for v in vs)+.003
def palm_rotation(side,direction,normal):
    name=side+'Hand'
    return orient(name,direction,normal) @ rest[name].to_quaternion().inverted()
def palm_height(side,q):
    sign=1 if side=='Left' else -1; wrist=heads[side+'Hand']
    vs=[v for v in coords if sign*v.x>.375 and v.z<.955]
    return -min((q@(v-wrist)).z for v in vs)+.003

clips = [
 {'id':'5965','name':'1 2 stick drill','duration':4.0,'camera':'front','primary':['quadriceps','calves'],'secondary':['core','glutes'],'stretch':[],
  'arms':'Elbows flexed near90degrees; compact reciprocal arm swing, hands in front of the ribs with palms inward.',
  'interpretation':'The text leaves the footfall pattern unspecified. Authored two lateral shuffle steps left, controlled stop and two steps back; no physical stick or cones.'},
 {'id':'5915','name':'3 leg chaturanga pose','duration':4.0,'camera':'side','primary':['triceps','chest'],'secondary':['shoulders','core','glutes'],'stretch':[],
  'arms':'Palms flat with fingers forward; wrists below elbows at the bottom, elbows track backward close to torso.',
  'interpretation':'One controlled lower/press with the left leg lifted. The next repetition may switch sides.'},
 {'id':'5887','name':'3 leg dog pose','duration':4.0,'camera':'side','primary':['shoulders','glutes'],'secondary':['core','triceps'],'stretch':['hamstrings','calves'],
  'arms':'Hands shoulder-width, palms down and fingers forward, elbows nearly extended; head remains between upper arms.',
  'interpretation':'Lift/lower the left leg with square hips. A shortened hold is shown; source five-breath hold is not performed in real time. Hamstrings/calves use the stretch color, not primary load.'},
 {'id':'0001','name':'3/4 sit-up','duration':4.0,'camera':'side','primary':['abs'],'secondary':['hip flexors','lower back'],'stretch':[],
  'arms':'Hands rest behind the head with elbows open; hands move with the head without pulling the neck.',
  'interpretation':'Controlled trunk curl to approximately45degrees with bent knees and planted feet.'},
 {'id':'9066','name':'4 way single leg hop','duration':6.4,'camera':'front_side','primary':['calves'],'secondary':['quadriceps','glutes'],'stretch':[],
  'arms':'Elbows comfortably bent, hands ahead of torso; small counterbalancing movement. Source does not specify arms, so this is an authored staging choice.',
  'interpretation':'Eight short hops: forward/center, left/center, back/center, right/center on the left leg. Each includes a grounded knee bend, toe push-off, flight and cushioned landing. Front and rear-oblique views show both motion axes and the loaded calf/glute.'}
]
target_errors={item['id']:{'hands':0.,'feet':0.} for item in clips}

def make_pose(item,u):
    name=item['id']; root=V((0,.04,.91)); pelvis=0; spine=0; chest=0;neck=0
    wrists={};hands={};feet={};poles={};leg_poles={}
    if name=='5965':
        # Authored shuffle contacts: lead foot steps, trailing foot follows; no crossing.
        knots=[(0,0,0,0),(0.25,-.17,-.34,0),(0.5,-.34,-.34,-.34),(.75,-.17,-.34,0),(1,0,0,0)]
        seg=min(3,int(u*4));a,b=knots[seg:seg+2];t=(u-a[0])/(b[0]-a[0]);s=ease(t)
        root.x=a[1]+(b[1]-a[1])*s;root.z=.89+.018*math.sin(math.pi*t)**2
        for side,sign,col in [('Left',1,3),('Right',-1,2)]:
            q=foot_rotation(side);shift=a[col]+(b[col]-a[col])*s
            step=abs(b[col]-a[col])>.01
            feet[side]=(V((sign*.19+shift,.02,sole_height(side,q)+(.055*math.sin(math.pi*t)**2 if step else 0))),q)
            swing=math.sin(2*math.pi*u*2)*sign
            wrists[side]=root+V((sign*.20,-.27+.075*swing,.23+.025*swing))
            hands[side]=(V((0,-1,.10)),V((-sign,0,0)))
        pelvis=spine=chest=6
    elif name=='5915':
        load=cycle(u);root=V((0,-.27-.03*load,.395-.105*load));pelvis=spine=chest=neck=82+3*load
        for side,sign in [('Left',1),('Right',-1)]:
            q=foot_rotation(side,64 if side=='Right' else 140)
            ankle_z=sole_height(side,q) if side=='Right' else root.z+.15
            hip_y=root.y+.03;hip_z=root.z
            reach=length[side+'UpLeg']+length[side+'Leg']-.006
            ankle_y=.55 if side=='Right' else hip_y+math.sqrt(max(.1,reach*reach-(ankle_z-hip_z)**2))
            feet[side]=(V((sign*.13,ankle_y,ankle_z)),q)
            hdir=V((0,-1,0));hnormal=V((0,0,-1));hq=palm_rotation(side,hdir,hnormal)
            wrists[side]=V((sign*.215,-.455,palm_height(side,hq)))
            hands[side]=(hdir,hnormal);poles[side]=V((sign*.235,-.10,.65))
            leg_poles[side]=V((sign*.13,.45,-.3))
    elif name=='5887':
        lift=cycle(u);root=V((0,.28,.775));pelvis=spine=chest=neck=130
        for side,sign in [('Left',1),('Right',-1)]:
            q=foot_rotation(side,0 if side=='Right' else -20*lift)
            ankle=V((sign*.15,.745,sole_height(side,q)))
            if side=='Left':
                h=V((sign*.105,.28,.775))+rx(130)@V((0,0,-.03))
                down=(ankle-h).normalized();up=V((0,.89,.46)).normalized();direction=down.lerp(up,ease(lift)).normalized()
                ankle=h+direction*(length[side+'UpLeg']+length[side+'Leg']-.002)
                q=foot_rotation(side,150*ease(lift))
            feet[side]=(ankle,q)
            hdir=V((0,-1,0));hnormal=V((0,0,-1));hq=palm_rotation(side,hdir,hnormal)
            wrists[side]=V((sign*.205,-.35,palm_height(side,hq)));hands[side]=(hdir,hnormal)
            poles[side]=V((sign*.27,-.20,.20));leg_poles[side]=V((sign*.16,.05,.10))
    elif name=='0001':
        curl=cycle(u);root=V((0,.05,.17));pelvis=-90+12*curl;spine=-90+35*curl;chest=-90+47*curl;neck=-88+47*curl
        for side,sign in [('Left',1),('Right',-1)]:
            q=foot_rotation(side);feet[side]=(V((sign*.16,-.53,sole_height(side,q))),q)
            leg_poles[side]=V((sign*.15,-.20,.70))
    else:
        path=[(0,0),(0,-.20),(0,0),(.20,0),(0,0),(0,.20),(0,0),(-.20,0),(0,0)]
        seg=min(7,int(u*8));t=u*8-seg;a=V((*path[seg],0));b=V((*path[seg+1],0))
        flight=max(0,min(1,(t-.16)/.52));travel=a.lerp(b,ease(flight))
        air=4*flight*(1-flight)
        if t<.16:
            rise=ease(t/.16);height=.80+.11*rise;pitch=24*rise
        elif t<.68:
            height=.91+.16*air;pitch=24-9*ease(flight)
        elif t<.86:
            absorb=ease((t-.68)/.18);height=.91-.12*absorb;pitch=15*(1-absorb)
        else:
            height=.79+.01*ease((t-.86)/.14);pitch=0
        root=V((travel.x+.10,travel.y+.04,height))
        for side,sign in [('Left',1),('Right',-1)]:
            q=foot_rotation(side,pitch)
            feet[side]=(V((travel.x+sign*.13,travel.y+.02,sole_height(side,q)+.20*air)),q)
            if side=='Right':feet[side]=(root+V((-.13,.27+.04*air,-.43)),foot_rotation(side,30-12*air))
            wrists[side]=root+V((sign*.23,-.25+sign*.04*air,.18+.055*air))
            hands[side]=(V((0,-1,.1)),V((-sign,0,0)))
            leg_poles[side]=root+V((sign*.15,-.35,-.20))
        pelvis=spine=chest=5+5*max(0,(.91-height)/.12)
    desired={}
    for bone,angle in [('Hips',pelvis),('Spine',spine),('Spine1',chest),('Neck',neck if name!='5965' else 6),('Head',neck if name in ['0001','5887','5915'] else 0)]:
        parent=rig.data.bones[bone].parent
        h=root if parent is None else desired[parent.name]@rest[parent.name].inverted()@heads[bone]
        desired[bone]=Matrix.Translation(h)@(rx(angle)@rest[bone].to_quaternion()).to_matrix().to_4x4()
    for side,sign in [('Left',1),('Right',-1)]:
        shoulder=side+'Shoulder';parent='Spine1'
        sh=desired[parent]@rest[parent].inverted()@heads[shoulder]
        desired[shoulder]=Matrix.Translation(sh)@(rx(chest)@rest[shoulder].to_quaternion()).to_matrix().to_4x4()
        armhead=desired[shoulder]@rest[shoulder].inverted()@heads[side+'Arm']
        if name=='0001':
            head_center=desired['Head']@rest['Head'].inverted()@V((0,.01,1.68))
            back=rx(neck)@V((0,1,0));up=rx(neck)@V((0,0,1))
            wrists[side]=head_center+V((sign*.12,0,0))+back*.068-up*.025
            hands[side]=(V((-sign,.05,0)), -back)
            poles[side]=armhead+V((sign*.65,0,0))+back*.05+up*.1
        elbow,wrist=two_joint(armhead,wrists[side],length[side+'Arm'],length[side+'ForeArm'],poles.get(side,armhead+V((sign*.30,.15,-.2))))
        target_errors[name]['hands']=max(target_errors[name]['hands'],(wrist-wrists[side]).length)
        desired[side+'Arm']=Matrix.Translation(armhead)@orient(side+'Arm',elbow-armhead).to_matrix().to_4x4()
        desired[side+'ForeArm']=Matrix.Translation(elbow)@orient(side+'ForeArm',wrist-elbow).to_matrix().to_4x4()
        desired[side+'Hand']=Matrix.Translation(wrist)@orient(side+'Hand',*hands[side]).to_matrix().to_4x4()
        hip=desired['Hips']@rest['Hips'].inverted()@heads[side+'UpLeg']
        ankle,footq=feet[side]
        knee,ankle=two_joint(hip,ankle,length[side+'UpLeg'],length[side+'Leg'],leg_poles.get(side,hip+V((0,-1,-.1))))
        target_errors[name]['feet']=max(target_errors[name]['feet'],(ankle-feet[side][0]).length)
        for bone,h,t in [(side+'UpLeg',hip,knee),(side+'Leg',knee,ankle)]:
            desired[bone]=Matrix.Translation(h)@orient(bone,t-h).to_matrix().to_4x4()
        desired[side+'Foot']=Matrix.Translation(ankle)@(footq@rest[side+'Foot'].to_quaternion()).to_matrix().to_4x4()
        toe=desired[side+'Foot']@rest[side+'Foot'].inverted()@heads[side+'ToeBase']
        desired[side+'ToeBase']=Matrix.Translation(toe)@(footq@rest[side+'ToeBase'].to_quaternion()).to_matrix().to_4x4()
    for bone,(a,b,parent,digit,index) in finger_specs.items():
        parent_matrix=desired[parent]@rest[parent].inverted()
        long=(b-a).normalized();normal=V((-1 if bone.startswith('Left') else 1,0,0))
        axis=rest[bone].to_3x3().inverted()@long.cross(normal).normalized()
        if name in ['5965','9066']:angle=([65,80,45] if digit=='Thumb' else [55,72,40])[index]
        elif name in ['5915','5887']:angle=0
        else:angle=[10,12,5][index]
        desired[bone]=parent_matrix@rest[bone]@Quaternion(axis,math.radians(angle)).to_matrix().to_4x4()
    for pb in rig.pose.bones:
        parent=pb.parent.name if pb.parent else None
        pb.matrix_basis=rest[pb.name].inverted()@(rest[parent]@desired[parent].inverted() if parent else Matrix.Identity(4))@desired[pb.name]
    return desired

scene.render.fps=30
scene.render.resolution_x=768;scene.render.resolution_y=768;scene.render.resolution_percentage=100
scene.render.engine='BLENDER_WORKBENCH';scene.render.film_transparent=True
scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
shade=scene.display.shading;shade.light='STUDIO';shade.color_type='SINGLE';shade.single_color=(.60,.66,.71)
shade.show_shadows=False;shade.show_cavity=True;shade.cavity_type='BOTH';shade.curvature_ridge_factor=1.4;shade.curvature_valley_factor=1.1;shade.show_specular_highlight=False
shade.background_type='WORLD';scene.world.color=(.94,.955,.97)
scene.view_settings.view_transform='Standard';scene.view_settings.look='None'
def camera_for(item):
    if item['camera']=='front':target=V((-.17,0,.93));scene.camera.location=(target.x,-6,.93);scale=2.20
    elif item['camera']=='front_side':target=V((0,0,.93));scene.camera.location=(0,-6,.93);scale=2.15
    elif item['id']=='0001':target=V((0,-.05,.45));scene.camera.location=(6,-.05,.45);scale=1.95
    else:target=V((0,.20,.63));scene.camera.location=(6,.20,.63);scale=2.30
    scene.camera.rotation_euler=(target-scene.camera.location).to_track_quat('-Z','Y').to_euler();scene.camera.data.type='ORTHO';scene.camera.data.ortho_scale=scale

reports=[]
for item in clips:
    item['highlight_sides']=({'glutes':['L']} if item['id']=='5915' else
        {'glutes':['L'],'hamstrings':['R'],'calves':['R']} if item['id']=='5887' else
        {'calves':['L'],'quadriceps':['L'],'glutes':['L']} if item['id']=='9066' else {})
    n=round(item['duration']*30);item['frames']=n;item['action']='Exercise_'+item['id']
    rig.animation_data_clear();action=bpy.data.actions.new(item['action']);action.use_fake_user=True;rig.animation_data_create();rig.animation_data.action=action
    for i in range(n+1):
        scene.frame_set(i+1);make_pose(item,i/n)
        for pb in rig.pose.bones:
            pb.keyframe_insert('location',frame=i+1);pb.keyframe_insert('rotation_quaternion',frame=i+1)
    camera_for(item);scene.frame_start=1;scene.frame_end=n+1
    for i in [0,n//4,n//2,3*n//4]:
        scene.frame_set(i+1);scene.render.filepath=str(P/f"proof-{item['id']}-{i:03d}.png");bpy.ops.render.render(write_still=True)
    reports.append({'id':item['id'],'action':action.name,'frames':n+1})
rig.animation_data.action=bpy.data.actions[clips[0]['action']];camera_for(clips[0]);scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(P/'bodyweight-five.blend'))
(P/'clips.json').write_text(json.dumps(clips,indent=2)+'\n')
(P/'build-report.json').write_text(json.dumps({'body_vertices':len(body.data.vertices),'bones':len(rig.data.bones),'clips':reports,'max_target_error_m':target_errors,'motion_source':'New exercise-specific authored keyframes on accepted CC0 human. No GymVisual media used. No capture hand pose copied.'},indent=2)+'\n')
print('Built five exercise-specific actions')
