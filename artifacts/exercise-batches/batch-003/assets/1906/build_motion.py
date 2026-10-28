"""Original unilateral supine knee-fall-out illustration on the accepted CC0 rig.
Run: blender -b -t 2 --python build_motion.py -- [--final]
"""
import sys, json, math, hashlib
from pathlib import Path
import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector
P=Path(__file__).resolve().parent
sys.path.insert(0,str(P.parents[1]))
import authoring as a
EXPECTED='227ede3fc31d1a2b47ff40f20a4a7288fe7bb36179add23bae953993826c8b7b'
assert a.initialize()==EXPECTED
body,rig,scene=a.body,a.rig,a.scene
V=a.V
for m in body.modifiers:
    print('MODIFIER',m.name,m.type,getattr(m,'use_deform_preserve_volume',None),getattr(m,'levels',None))
# Retain source modifier configuration in the editable source. Runtime is exported
# as the original linear cage; both representations are inspected independently.
foot_ids={s:[v.index for v in body.data.vertices if sum(g.weight for g in v.groups if body.vertex_groups[g.group].name in [s+'Foot',s+'ToeBase'])>.5] for s in ['Left','Right']}

def heel_height(side,q):
    return .002-min((q@(a.coords[i]-a.heads[side+'Foot'])).z for i in foot_ids[side])

def shape(t):
    t=min(t,5-t)
    return a.ease(t/.95),a.ease((t-.65)/1.35)

def pose(t,root_z=.100,pitches=(-105,-65,-90,-105,-100),wrist_z=.031):
    flex,opening=shape(t)
    root=V((0,.04,root_z))
    d=a.torso(root,pitches)
    for side,sign in [('Left',1),('Right',-1)]:
        sh=side+'Shoulder';arm=side+'Arm';fore=side+'ForeArm';hand=side+'Hand'
        h=d['Spine1']@a.rest['Spine1'].inverted()@a.heads[sh]
        d[sh]=Matrix.Translation(h)@(a.rx(pitches[2])@a.rest[sh].to_quaternion()).to_matrix().to_4x4()
        shoulder=d[sh]@a.rest[sh].inverted()@a.heads[arm]
        wrist=V((sign*.37,-.015,wrist_z))
        elbow,wrist=a.two_joint(shoulder,wrist,a.length[arm],a.length[fore],V((sign*.43,.20,.115)))
        arm_normal=V((-sign,0,0))
        d[arm]=Matrix.Translation(shoulder)@a.orient(arm,elbow-shoulder,arm_normal).to_matrix().to_4x4()
        d[fore]=Matrix.Translation(elbow)@a.orient(fore,wrist-elbow,arm_normal).to_matrix().to_4x4()
        d[hand]=Matrix.Translation(wrist)@a.orient(hand,V((sign*.12,-1,.02)),V((0,0,1))).to_matrix().to_4x4()
        hip=d['Hips']@a.rest['Hips'].inverted()@a.heads[side+'UpLeg']
        if side=='Left':
            q=Quaternion(V((0,1,0)),math.radians(36*opening))@a.rz(20*opening)@a.rx(-90*(1-flex))
            ankle=V((.181+.055*opening,-.805+.365*flex,heel_height(side,q)))
            pole=V((.15+.57*opening,-.18,.82-.29*opening))
        else:
            q=Quaternion(V((0,1,0)),math.radians(-8))@a.rx(-90)
            ankle=V((-.181,-.805,heel_height(side,q)))
            pole=V((-.16,-.40,.65))
        knee,ankle=a.two_joint(hip,ankle,a.length[side+'UpLeg'],a.length[side+'Leg'],pole)
        norm=(ankle-knee).cross(knee-hip).normalized()
        if side=='Right': norm=-norm
        for name,start,end in [(side+'UpLeg',hip,knee),(side+'Leg',knee,ankle)]:
            d[name]=Matrix.Translation(start)@a.orient(name,end-start,norm).to_matrix().to_4x4()
        d[side+'Foot']=Matrix.Translation(ankle)@(q@a.rest[side+'Foot'].to_quaternion()).to_matrix().to_4x4()
        toe=d[side+'Foot']@a.rest[side+'Foot'].inverted()@a.heads[side+'ToeBase']
        d[side+'ToeBase']=Matrix.Translation(toe)@(q@a.rest[side+'ToeBase'].to_quaternion()).to_matrix().to_4x4()
    for name,(h,tail,parent,digit,index) in a.finger_specs.items():
        direction=(tail-h).normalized();normal=V((-1 if name.startswith('Left') else 1,0,0))
        axis=a.rest[name].to_3x3().inverted()@direction.cross(normal).normalized()
        angle=([5,8,4] if digit!='Thumb' else [7,4,3])[index]
        d[name]=d[parent]@a.rest[parent].inverted()@a.rest[name]@Quaternion(axis,math.radians(angle)).to_matrix().to_4x4()
    for pb in rig.pose.bones:
        parent=pb.parent.name if pb.parent else None
        pb.matrix_basis=a.rest[pb.name].inverted()@(a.rest[parent]@d[parent].inverted() if parent else Matrix.Identity(4))@d[pb.name]
    return d

scene.render.fps=30;scene.frame_start=1;scene.frame_end=151
rig.animation_data_create()
act=bpy.data.actions.new('Exercise_1906');act.use_fake_user=True;rig.animation_data.action=act
for f in range(151):
    scene.frame_set(f+1);pose(f/30)
    for pb in rig.pose.bones:
        pb.keyframe_insert('location',frame=f+1);pb.keyframe_insert('rotation_quaternion',frame=f+1)
for layer in act.layers:
    for strip in layer.strips:
        for bag in strip.channelbags:
            for fc in bag.fcurves:
                for k in fc.keyframe_points:k.interpolation='LINEAR'
# Identity survives UV seam splits in glTF.
attr=body.data.attributes.get('_SOURCE_INDEX') or body.data.attributes.new('_SOURCE_INDEX','FLOAT','POINT')
attr.data.foreach_set('value',np.arange(len(body.data.vertices),dtype=np.float32))
sys.path.insert(0,str(P))
import skin_corrective
skin_corrective.apply(body,rig,scene,P/'skin-corrective-report.json')
assert a.binding_hash(body,rig)==EXPECTED
scene.render.engine='BLENDER_WORKBENCH'
scene.render.resolution_x=1000;scene.render.resolution_y=800;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA';scene.render.film_transparent=True
shade=scene.display.shading;shade.light='STUDIO';shade.color_type='MATERIAL';shade.show_shadows=False;shade.show_cavity=False;shade.show_specular_highlight=False
scene.view_settings.view_transform='Standard';scene.view_settings.look='None'
camdata=bpy.data.cameras.new('ReviewCamera');cam=bpy.data.objects.new('ReviewCamera',camdata);scene.collection.objects.link(cam);scene.camera=cam;camdata.type='ORTHO'
cameras={'overhead_oblique':{'position':[2.6,-2.5,4.8],'target':[.05,.01,.10],'scale':2.15},'selected_hip_side':{'position':[3.8,.85,1.75],'target':[.04,-.02,.12],'scale':2.10}}
def camera(name):
    c=cameras[name];cam.location=c['position'];cam.rotation_euler=(V(c['target'])-cam.location).to_track_quat('-Z','Y').to_euler();camdata.ortho_scale=c['scale']

def render(name,f,view='overhead_oblique',linear=False,wire=False):
    scene.frame_set(f+1);camera(view)
    states=[(m,m.show_viewport,m.show_render) for m in body.modifiers]
    if linear:
        for m in body.modifiers:
            if m.type!='ARMATURE':m.show_viewport=False;m.show_render=False
        for m in body.modifiers:
            if m.type=='ARMATURE':m.use_deform_preserve_volume=False
    wire_ob=None
    if wire:
        wire_ob=body.copy();wire_ob.data=body.data.copy();wire_ob.name='ReviewWire';scene.collection.objects.link(wire_ob)
        dark=bpy.data.materials.new('ReviewWireDark');dark.diffuse_color=(.04,.04,.04,1);wire_ob.data.materials.clear();wire_ob.data.materials.append(dark)
        wm=wire_ob.modifiers.new('ReviewWire','WIREFRAME');wm.thickness=.0007;wm.offset=1
    body.show_wire=False
    scene.render.filepath=str(P/name);bpy.ops.render.render(write_still=True)
    if wire_ob:
        mesh=wire_ob.data;bpy.data.objects.remove(wire_ob,do_unlink=True);bpy.data.meshes.remove(mesh)
    for m,viewport,rendering in states:m.show_viewport=viewport;m.show_render=rendering
for label,f in [('start',0),('peak',75),('return',150)]:
    render(f'early-{label}-oblique.png',f)
render('early-peak-hip-side.png',75,'selected_hip_side')
scene.frame_set(1);camera('overhead_oblique')
bpy.ops.wm.save_as_mainfile(filepath=str(P/'source.blend'))
(P/'cameras.json').write_text(json.dumps([dict(label=k,**v) for k,v in cameras.items()],indent=2)+'\n')
samples=[]
for f in [0,15,30,45,60,75,90,105,120,135,150]:
    scene.frame_set(f+1);bpy.context.view_layer.update()
    samples.append({'id':'1906','frame':f,'time_seconds':f/30,'joints':{pb.name:list(rig.matrix_world@pb.head) for pb in rig.pose.bones}})
(P/'pose-samples.json').write_text(json.dumps(samples,indent=2)+'\n')
print('EARLY_PROOF_READY',str(P))
if '--final' not in sys.argv:sys.exit(0)
for label,f in [('start',0),('peak',75),('return',150)]:
    render(f'linear-{label}-oblique.png',f,linear=True)
render('native-peak-wire.png',75,'selected_hip_side',wire=True)
render('linear-peak-wire.png',75,'selected_hip_side',linear=True,wire=True)
# Export only accepted original cage + rig. Original native modifier settings
# remain in source.blend; non-armature modifiers are excluded from GLB.
for m in body.modifiers:
    if m.type!='ARMATURE':m.show_viewport=False;m.show_render=False
    else:m.use_deform_preserve_volume=False
scene.frame_set(1)
bpy.ops.object.select_all(action='DESELECT');body.select_set(True);rig.select_set(True);bpy.context.view_layer.objects.active=rig
result=bpy.ops.export_scene.gltf(filepath=str(P/'motion.glb'),export_format='GLB',use_selection=True,export_animations=True,export_animation_mode='ACTIONS',export_force_sampling=True,export_frame_range=True,export_frame_step=1,export_skins=True,export_all_influences=False,export_apply=False,export_attributes=True,export_materials='EXPORT',export_vertex_color='NONE',export_anim_slide_to_zero=True,export_rest_position_armature=True,export_influence_nb=4,export_cameras=False,export_lights=False,export_yup=True,export_morph=True)
assert result=={'FINISHED'}
import patch_morph_normals
patch_morph_normals.patch(P/'motion.glb',P/'normal-patch-report.json')
print('EXPORTED',str(P/'motion.glb'))
