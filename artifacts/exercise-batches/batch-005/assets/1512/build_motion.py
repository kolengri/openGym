"""Source-text-only all-fours quadriceps stretch, original CC0 rig.

All angles and trajectories are authored choices, not source measurements.
"""
import json, math, sys
from pathlib import Path
sys.dont_write_bytecode = True
import bpy
import numpy as np
from mathutils import Matrix, Quaternion

P = Path(__file__).resolve().parent
sys.path.insert(0, str(P.parents[2] / 'batch-003'))
import authoring as a
EXPECTED = '227ede3fc31d1a2b47ff40f20a4a7288fe7bb36179add23bae953993826c8b7b'
PITCH=84

def smooth(x): return a.ease(x)

def repair_pelvic_binding():
    """Remove diagnosed high-waist thigh influence, retaining the hip crease."""
    rows=[]
    hip_group=a.body.vertex_groups['Hips']
    for v in a.body.data.vertices:
        blend=smooth((v.co.z-.90)/.14)
        if blend<=0:continue
        before={a.body.vertex_groups[g.group].name:g.weight for g in v.groups}
        after=dict(before);transfer=0
        for side in ['Left','Right']:
            name=side+'UpLeg';old=after.get(name,0);move=old*blend
            if move>0:
                transfer+=move;after[name]=old-move
        if transfer<=1e-8:continue
        after['Hips']=after.get('Hips',0)+transfer
        # Adding Hips can produce a fifth tiny influence on upper-waist rows.
        if len([w for w in after.values() if w>1e-8])>4:
            smallest=min(after,key=after.get);after['Hips']+=after.pop(smallest)
        for name in before:a.body.vertex_groups[name].remove([v.index])
        for name,w in after.items():
            if w>1e-8:a.body.vertex_groups[name].add([v.index],w,'REPLACE')
        rows.append({'id':v.index,'source':list(v.co),'before':before,'after':after})
    (P/'local-binding-report.json').write_text(json.dumps({'method':'Only original thigh influences above source Z0.90m are transferred to Hips using smoothstep, full transfer at1.04m; high-waist thigh contamination reaches1.14m in original source. Original Basis/rest/UV/topology retained.','source_binding_sha256':EXPECTED,'vertices':rows,'changed_vertices':len(rows),'maximum_influences':max(len(v.groups)for v in a.body.data.vertices),'binding_sha256':a.binding_hash(a.body,a.rig)},indent=2)+'\n')

def amount(t):
    return smooth(t / 2) if t < 2 else (1 if t <= 3 else smooth((5-t) / 2))

def chain(d, side, wrist, pole):
    sh = side + 'Shoulder'
    h = d['Spine1'] @ a.rest['Spine1'].inverted() @ a.heads[sh]
    d[sh] = Matrix.Translation(h) @ (a.rx(PITCH) @ a.rest[sh].to_quaternion()).to_matrix().to_4x4()
    arm = d[sh] @ a.rest[sh].inverted() @ a.heads[side+'Arm']
    elbow, wrist = a.two_joint(arm, wrist, a.length[side+'Arm'], a.length[side+'ForeArm'], pole)
    d[side+'Arm'] = Matrix.Translation(arm) @ a.orient(side+'Arm', elbow-arm).to_matrix().to_4x4()
    q = d[side+'Arm'].to_quaternion() @ a.rest[side+'Arm'].to_quaternion().inverted() @ a.rest[side+'ForeArm'].to_quaternion()
    q = (q @ a.V((0,1,0))).rotation_difference((wrist-elbow).normalized()) @ q
    d[side+'ForeArm'] = Matrix.Translation(elbow) @ q.to_matrix().to_4x4()
    return wrist

def pose(t):
    u = amount(t)
    d = a.torso(a.V((-.018*u,.06,.4615-.004*u)), [PITCH]*5)
    hand_q = {}
    for side, sign in [('Left',1),('Right',-1)]:
        hip = d['Hips'] @ a.rest['Hips'].inverted() @ a.heads[side+'UpLeg']
        alpha = math.radians(110*u) if side == 'Left' else 0
        knee = hip + a.V((sign*.008, math.sin(alpha), -math.cos(alpha))).normalized()*a.length[side+'UpLeg']
        if side=='Right':
            dx=-.1085385-hip.x
            knee=hip+a.V((dx,0,-math.sqrt(a.length[side+'UpLeg']**2-dx**2)))
        beta = math.radians(2.65+(150-2.65)*u) if side == 'Left' else math.radians(2.65)
        ankle = knee + a.V((0, math.cos(beta), math.sin(beta)))*a.length[side+'Leg']
        d[side+'UpLeg'] = Matrix.Translation(hip) @ a.orient(side+'UpLeg', knee-hip).to_matrix().to_4x4()
        d[side+'Leg'] = Matrix.Translation(knee) @ a.orient(side+'Leg', ankle-knee).to_matrix().to_4x4()
        fq = a.foot_rotation(side,150-120*u if side=='Left' else 150)
        d[side+'Foot'] = Matrix.Translation(ankle) @ (fq @ a.rest[side+'Foot'].to_quaternion()).to_matrix().to_4x4()
        toe = d[side+'Foot'] @ a.rest[side+'Foot'].inverted() @ a.heads[side+'ToeBase']
        d[side+'ToeBase'] = Matrix.Translation(toe) @ (fq @ a.rest[side+'ToeBase'].to_quaternion()).to_matrix().to_4x4()
        sh = d['Spine1'] @ a.rest['Spine1'].inverted() @ a.heads[side+'Shoulder']
        ah = sh + a.rx(PITCH) @ (a.heads[side+'Arm']-a.heads[side+'Shoulder'])
        hq = a.palm_rotation(side,(0,-1,0),(0,0,-1))
        group = a.body.vertex_groups[side+'Hand'].index
        verts = [v.co for v in a.body.data.vertices if any(g.group==group and g.weight>.5 for g in v.groups)]
        height=.003-min((hq @ (v-a.heads[side+'Hand'])).z for v in verts)
        start=a.V((ah.x if side=='Left'else-.18, ah.y, height))
        if side == 'Left':
            target=ankle+a.V((.082,-.166,.019))
            # The hand clears the lateral thigh before approaching the ankle.
            wrist=start.lerp(target,u)+a.V((.18,0,.10))*math.sin(math.pi*u)
            endq=a.palm_rotation(side,(0,.995,-.10),(-1,0,0))
            hq=hq.slerp(endq,u)
        else: wrist=start
        wrist=chain(d,side,wrist,a.V((sign*.48, -.12, .42)))
        hand_q[side]=hq
        d[side+'Hand']=Matrix.Translation(wrist) @ (hq @ a.rest[side+'Hand'].to_quaternion()).to_matrix().to_4x4()
    for name,(h,tail,parent,digit,index) in a.finger_specs.items():
        side='Left' if name.startswith('Left') else 'Right'
        normal=a.V((-1 if side=='Left' else 1,0,0))
        axis=a.rest[name].to_3x3().inverted() @ (tail-h).normalized().cross(normal).normalized()
        angles=[0,0,0] if digit!='Thumb' else [0,-18,-17]
        if side=='Left':
            angles=([34*u,45*u,28*u] if digit!='Thumb' else [-12*u,-18,-17+5*u])
        d[name]=d[parent] @ a.rest[parent].inverted() @ a.rest[name] @ Quaternion(axis,math.radians(angles[index])).to_matrix().to_4x4()
    for pb in a.rig.pose.bones:
        parent=pb.parent.name if pb.parent else None
        pb.matrix_basis=a.rest[pb.name].inverted() @ (a.rest[parent] @ d[parent].inverted() if parent else Matrix.Identity(4)) @ d[pb.name]
    bpy.context.view_layer.update()
    return d

CAMERAS={
 'side': {'label':'Whole body side','position':[3.6,-.05,.78],'target':[0,.02,.38],'scale':1.90},
 'oblique': {'label':'Quad and ankle oblique','position':[2.8,-2.3,1.55],'target':[0,.06,.38],'scale':1.90},
 'rear': {'label':'Rear support review','position':[2.0,3.0,1.55],'target':[0,.05,.38],'scale':1.90},
}

def render(label, f, kind, wire=False):
    a.scene.frame_set(f+1)
    c=CAMERAS[kind];cam=a.scene.camera
    cam.location=c['position'];cam.rotation_euler=(a.V(c['target'])-cam.location).to_track_quat('-Z','Y').to_euler()
    cam.data.ortho_scale=c['scale']
    ob=None
    if wire:
        ob=a.body.copy();ob.data=a.body.data.copy();a.scene.collection.objects.link(ob)
        mat=bpy.data.materials.new('QA_Wire');mat.diffuse_color=(.02,.02,.02,1);ob.data.materials.clear();ob.data.materials.append(mat)
        mod=ob.modifiers.new('QA_Wire','WIREFRAME');mod.thickness=.00055;mod.offset=1
    a.scene.render.filepath=str(P/f'{label}-{kind}.png');bpy.ops.render.render(write_still=True)
    if ob:
        mesh=ob.data;bpy.data.objects.remove(ob,do_unlink=True);bpy.data.meshes.remove(mesh)

def main():
    assert a.initialize()==EXPECTED
    repair_pelvic_binding()
    for m in a.body.modifiers:
        m.show_viewport=m.show_render=m.type=='ARMATURE'
        if m.type=='ARMATURE':m.use_deform_preserve_volume=True
    a.scene.frame_start=1;a.scene.frame_end=151
    a.rig.animation_data_create();act=bpy.data.actions.new('Exercise_1512');act.use_fake_user=True;a.rig.animation_data.action=act
    for f in range(151):
        a.scene.frame_set(f+1);pose(f/30)
        for pb in a.rig.pose.bones:
            pb.keyframe_insert('location',frame=f+1);pb.keyframe_insert('rotation_quaternion',frame=f+1)
    for layer in act.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for fc in bag.fcurves:
                    for key in fc.keyframe_points:key.interpolation='LINEAR'
    sys.path.insert(0,str(P))
    import local_correctives
    report=local_correctives.install(a.body,a.rig,a.scene,act,amount)
    (P/'local-corrective-report.json').write_text(json.dumps(report,indent=2)+'\n')
    attr=a.body.data.attributes.get('_SOURCE_INDEX') or a.body.data.attributes.new('_SOURCE_INDEX','FLOAT','POINT')
    attr.data.foreach_set('value',np.arange(len(a.body.data.vertices),dtype=np.float32))
    assert a.binding_hash(a.body,a.rig)==json.loads((P/'local-binding-report.json').read_text())['binding_sha256']
    s=a.scene;s.render.engine='BLENDER_WORKBENCH';s.render.resolution_x=1000;s.render.resolution_y=850;s.render.resolution_percentage=100
    s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGBA';s.render.film_transparent=True
    sh=s.display.shading;sh.light='STUDIO';sh.color_type='MATERIAL';sh.show_shadows=False;sh.show_cavity=False;sh.show_specular_highlight=False
    s.view_settings.view_transform='Standard';s.view_settings.look='None'
    cd=bpy.data.cameras.new('QA_Camera');cam=bpy.data.objects.new('QA_Camera',cd);s.collection.objects.link(cam);s.camera=cam;cd.type='ORTHO'
    for label,f in [('early-start',0),('early-entry',30),('early-hold',75)]:
        for kind in CAMERAS:render(label,f,kind)
    render('neutral-wire',0,'oblique',True);render('hold-wire',75,'oblique',True)
    a.scene.frame_set(1);bpy.ops.wm.save_as_mainfile(filepath=str(P/'source.blend'))
    (P/'cameras.json').write_text(json.dumps([{**CAMERAS[k],'scale':CAMERAS[k]['scale']*s.render.resolution_x/s.render.resolution_y}for k in ['side','oblique']],indent=2)+'\n')
    samples=[]
    for f in [0,15,30,45,60,75,90,105,120,135,150]:
        s.frame_set(f+1);bpy.context.view_layer.update();samples.append({'id':'1512','frame':f,'joints':{pb.name:list(a.rig.matrix_world@pb.head) for pb in a.rig.pose.bones}})
    (P/'pose-samples.json').write_text(json.dumps(samples,indent=2)+'\n')
    print('EARLY_PROOF_READY',P)

if __name__=='__main__':main()
