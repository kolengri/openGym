"""Original CC0 four-point abdominal brace; no external exercise media."""
import argparse
import hashlib
import json
import math
import struct
import sys
sys.dont_write_bytecode = True
from pathlib import Path
import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector

P = Path(__file__).resolve().parent
sys.path.insert(0,str(P))
sys.path.insert(0, str(P.parents[1]))
import authoring as a

EXPECTED = '227ede3fc31d1a2b47ff40f20a4a7288fe7bb36179add23bae953993826c8b7b'
MODIFIERS = []
PALM_NORMALS = {}
STATIC_ROTATIONS = None
STATIC_POSED_NORMALS = None


def initialize():
    assert a.initialize() == EXPECTED
    global MODIFIERS
    MODIFIERS = [(m, m.show_viewport, m.show_render) for m in a.body.modifiers]
    for side,sign in [('Left',1),('Right',-1)]:
        group = a.body.vertex_groups[side+'Hand'].index
        strong = {v.index for v in a.body.data.vertices if any(g.group==group and g.weight>.5 for g in v.groups)}
        faces = [p for p in a.body.data.polygons if all(i in strong for i in p.vertices) and p.normal.x*sign < -.5]
        pts = np.array([a.body.data.vertices[i].co for i in sorted({i for p in faces for i in p.vertices})])
        normal = np.linalg.svd(pts-pts.mean(0))[2][-1]
        if normal[0]*sign>0: normal=-normal
        PALM_NORMALS[side] = a.V(normal)
    scene = a.scene
    scene.frame_start = 1
    scene.frame_end = 151
    scene.render.fps = 30
    scene.render.fps_base = 1
    scene.render.engine = 'BLENDER_WORKBENCH'
    scene.render.resolution_x = 1000
    scene.render.resolution_y = 850
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = True
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'
    shade = scene.display.shading
    shade.light = 'STUDIO'
    shade.color_type = 'MATERIAL'
    shade.show_shadows = False
    shade.show_cavity = False
    shade.show_specular_highlight = False
    shade.background_type = 'WORLD'
    scene.world.color = (.94, .95, .96)
    scene.view_settings.view_transform = 'Standard'
    scene.view_settings.look = 'None'
    return a.body, a.rig, a.scene



def make_pose(t):
    # Isometric stillness is deliberate: source bracing and normal breathing
    # do not establish a visible joint trajectory or an activation curve.
    pitch = 79
    hand_rotations = {}
    desired = a.torso(a.V((0, .06, .4795)), [pitch, pitch, pitch, pitch, pitch])
    for side, sign in [('Left', 1), ('Right', -1)]:
        shoulder = side+'Shoulder'
        sh = desired['Spine1'] @ a.rest['Spine1'].inverted() @ a.heads[shoulder]
        desired[shoulder] = Matrix.Translation(sh) @ (a.rx(pitch) @ a.rest[shoulder].to_quaternion()).to_matrix().to_4x4()
        armhead = desired[shoulder] @ a.rest[shoulder].inverted() @ a.heads[side+'Arm']
        normal = PALM_NORMALS[side]
        long = a.tails[side+'Hand']-a.heads[side+'Hand']
        tangent = long-normal*long.dot(normal)
        hq = (a.frame((0,-1,0),(0,0,-1)) @ a.frame(tangent,normal).transposed()).to_quaternion()
        hand_rotations[side] = hq
        group = a.body.vertex_groups[side+'Hand'].index
        palm = [v.co for v in a.body.data.vertices if any(g.group==group and g.weight>.5 for g in v.groups)]
        height = .002-min((hq @ (v-a.heads[side+'Hand'])).z for v in palm)
        wrist = a.V((armhead.x, armhead.y, height))
        elbow, wrist = a.two_joint(armhead, wrist, a.length[side+'Arm'], a.length[side+'ForeArm'], armhead+a.V((sign*.13,.35,-.25)))
        desired[side+'Arm'] = Matrix.Translation(armhead) @ a.orient(side+'Arm',elbow-armhead).to_matrix().to_4x4()
        desired[side+'ForeArm'] = Matrix.Translation(elbow) @ a.orient(side+'ForeArm',wrist-elbow).to_matrix().to_4x4()
        desired[side+'Hand'] = Matrix.Translation(wrist) @ (hq @ a.rest[side+'Hand'].to_quaternion()).to_matrix().to_4x4()
        hip = desired['Hips'] @ a.rest['Hips'].inverted() @ a.heads[side+'UpLeg']
        knee = hip+a.V((sign*.008,0,-1)).normalized()*a.length[side+'UpLeg']
        ankle = knee+a.V((0,1,0))*a.length[side+'Leg']
        desired[side+'UpLeg'] = Matrix.Translation(hip) @ a.orient(side+'UpLeg',knee-hip).to_matrix().to_4x4()
        desired[side+'Leg'] = Matrix.Translation(knee) @ a.orient(side+'Leg',ankle-knee).to_matrix().to_4x4()
        fq = a.foot_rotation(side,150)
        desired[side+'Foot'] = Matrix.Translation(ankle) @ (fq@a.rest[side+'Foot'].to_quaternion()).to_matrix().to_4x4()
        toe = desired[side+'Foot'] @ a.rest[side+'Foot'].inverted() @ a.heads[side+'ToeBase']
        desired[side+'ToeBase'] = Matrix.Translation(toe) @ (fq@a.rest[side+'ToeBase'].to_quaternion()).to_matrix().to_4x4()
    for bone,(start,end,parent,digit,index) in a.finger_specs.items():
        side='Left' if bone.startswith('Left') else 'Right'
        transform=desired[parent] @ a.rest[parent].inverted()
        head=transform @ start
        long=(end-start).normalized()
        if digit=='Thumb':
            normal=a.V((-1 if side=='Left' else 1,0,0))
            axis=a.rest[bone].to_3x3().inverted() @ long.cross(normal).normalized()
            angle=[0,-18,-17][index]
            desired[bone]=transform @ a.rest[bone] @ Quaternion(axis,math.radians(angle)).to_matrix().to_4x4()
        else:
            q=hand_rotations[side]
            natural=q @ long
            tangent=a.V((natural.x,natural.y,0)).normalized()
            ztarget={'Little':.013,'Ring':.016,'Middle':.016,'Index':.015}[digit]
            delta=max(-.95,min(.95,(ztarget-head.z)/a.length[bone])) if index==0 else 0
            direction=tangent*math.sqrt(1-delta*delta)+a.V((0,0,delta))
            fq=natural.rotation_difference(direction) @ q
            desired[bone]=Matrix.Translation(head) @ (fq @ a.rest[bone].to_quaternion()).to_matrix().to_4x4()
    for pb in a.rig.pose.bones:
        parent = pb.parent.name if pb.parent else None
        pb.matrix_basis = a.rest[pb.name].inverted() @ (a.rest[parent] @ desired[parent].inverted() if parent else Matrix.Identity(4)) @ desired[pb.name]
    bpy.context.view_layer.update()
    return desired


CAMERAS = {
    'side': {'position':[3.5,-.03,.68], 'target':[0,-.04,.34], 'scale':1.82},
    'oblique': {'position':[2.7,-2.4,1.55], 'target':[0,-.06,.30], 'scale':1.87},
    'rear': {'position':[2.1,2.7,1.5], 'target':[0,-.02,.31], 'scale':1.83},
    'hands': {'position':[1.8,-2.4,.92], 'target':[0,-.40,.24], 'scale':.88},
}


def camera(key):
    if a.scene.camera is None:
        data = bpy.data.cameras.new('ExerciseReviewCamera')
        ob = bpy.data.objects.new('ExerciseReviewCamera', data)
        a.scene.collection.objects.link(ob)
        a.scene.camera = ob
    c = CAMERAS[key]
    a.scene.camera.location = c['position']
    a.scene.camera.rotation_euler = (a.V(c['target'])-a.scene.camera.location).to_track_quat('-Z','Y').to_euler()
    a.scene.camera.data.type = 'ORTHO'
    a.scene.camera.data.ortho_scale = c['scale']


def set_path(path):
    for mod, viewport, render in MODIFIERS:
        mod.show_viewport = viewport if path == 'native' else mod.type == 'ARMATURE'
        mod.show_render = render if path == 'native' else mod.type == 'ARMATURE'
    bpy.context.view_layer.update()


def render(name, t, view, path='native', wire=False):
    a.scene.frame_set(round(t*30)+1)
    make_pose(t)
    set_path(path)
    camera(view)
    a.body.show_wire = wire
    a.body.show_all_edges = wire
    a.scene.render.filepath = str(P/(name+'.png'))
    bpy.ops.render.render(write_still=True)
    a.body.show_wire = False


def add_datum(scene):
    """Thin Z=0 reference lines for contact review; no filled floor surface."""
    old=bpy.data.objects.get('QA_Z0_Datum')
    if old is not None:bpy.data.objects.remove(old,do_unlink=True)
    data=bpy.data.curves.new('QA_Z0_Datum','CURVE')
    data.dimensions='3D';data.bevel_depth=.00065;data.bevel_resolution=0;data.resolution_u=1
    lines=[ [(-.34,-.74,0),(.34,-.74,0),(.34,.76,0),(-.34,.76,0),(-.34,-.74,0)],
            [(-.34,-.50,0),(.34,-.50,0)], [(-.34,.10,0),(.34,.10,0)],
            [(-.18,-.74,0),(-.18,.76,0)], [(.18,-.74,0),(.18,.76,0)] ]
    for points in lines:
        spline=data.splines.new('POLY');spline.points.add(len(points)-1)
        for point,co in zip(spline.points,points):point.co=(*co,1)
    ob=bpy.data.objects.new('QA_Z0_Datum',data);scene.collection.objects.link(ob)
    mat=bpy.data.materials.new('QA_Z0_Datum_Material');mat.diffuse_color=(.15,.43,.58,1)
    data.materials.append(mat);ob.hide_select=True
    ob['datum']='All line centerpoints are world Z=0 meters; no filled floor or masking geometry.'
    return ob


def add_static_corrective():
    """Invert this one static pose's actual LBS blend; do not alter Basis."""
    make_pose(2.5)
    set_path('linear')
    def evaluated():
        ob=a.body.evaluated_get(bpy.context.evaluated_depsgraph_get())
        mesh=ob.to_mesh();co=np.array([v.co for v in mesh.vertices],dtype=np.float64)
        ob.to_mesh_clear();return co
    linear=evaluated()
    for mod in a.body.modifiers:mod.show_viewport=mod.type in ['ARMATURE','CORRECTIVE_SMOOTH']
    bpy.context.view_layer.update()
    target=evaluated()
    normal_ob=a.body.evaluated_get(bpy.context.evaluated_depsgraph_get())
    normal_mesh=normal_ob.to_mesh()
    normal_values=np.empty(len(normal_mesh.vertices)*3,np.float32)
    normal_mesh.vertex_normals.foreach_get('vector',normal_values)
    global STATIC_POSED_NORMALS, STATIC_ROTATIONS
    STATIC_POSED_NORMALS=normal_values.reshape(-1,3).copy()
    normal_ob.to_mesh_clear()
    assert len(target)==len(linear)==10582
    camera('oblique');a.scene.render.filepath=str(P/'native-corrective-target.png');bpy.ops.render.render(write_still=True)
    rest=np.array([v.co for v in a.body.data.vertices],dtype=np.float64)
    names={g.index:g.name for g in a.body.vertex_groups}
    matrices={name:np.array(a.rig.pose.bones[name].matrix @ a.rest[name].inverted(),dtype=np.float64) for name in a.heads}
    blended=[]
    for vertex in a.body.data.vertices:
        total=sum(g.weight for g in vertex.groups)
        assert total>0
        blended.append(sum((matrices[names[g.group]]*g.weight/total for g in vertex.groups),np.zeros((4,4))))
    blended=np.array(blended)
    rotations=blended[:,:3,:3]
    STATIC_ROTATIONS=rotations.copy()
    predicted=np.einsum('nij,nj->ni',rotations,rest)+blended[:,:3,3]
    prediction_error=float(np.linalg.norm(predicted-linear,axis=1).max())
    condition=np.linalg.cond(rotations)
    assert np.isfinite(condition).all() and condition.max()<10, 'Unstable static LBS inversion'
    assert prediction_error<.000002, 'LBS model does not reproduce actual Armature output'
    delta=np.linalg.solve(rotations,(target-linear)[...,None])[...,0]
    lengths=np.linalg.norm(delta,axis=1)
    assert np.isfinite(delta).all()
    assert lengths.max()<.05 and np.percentile(lengths,99)<.02, 'Static corrective exceeds bounded rest-space offsets'
    # Ignore sub-micron floating-point noise away from the native correction.
    delta[lengths<.000001]=0
    basis=a.body.shape_key_add(name='Basis',from_mix=False)
    correction=a.body.shape_key_add(name='StaticPoseCorrective_4348',from_mix=False)
    correction.data.foreach_set('co',(rest+delta).astype(np.float32).reshape(-1))
    correction.value=1;correction.slider_min=0;correction.slider_max=1
    a.body['static_pose_corrective_scope']='Constant correction valid only for the static Exercise_4348 pose.'
    global MODIFIERS
    MODIFIERS=[(mod,False,False) if mod.type=='CORRECTIVE_SMOOTH' else (mod,viewport,render) for mod,viewport,render in MODIFIERS]
    set_path('linear')
    actual=evaluated()
    error=np.linalg.norm(actual-target,axis=1)
    assert error.max()<.000003, 'Baked static corrective does not reproduce native corrected cage'
    assert np.array_equal(np.array([v.co for v in basis.data]),rest)
    assert a.binding_hash(a.body,a.rig)==EXPECTED
    report={
        'morph':'StaticPoseCorrective_4348','weight':1,'animated':False,'morph_target_count':1,
        'basis_binding_rest_uv_sha256':EXPECTED,'basis_unchanged':True,'weights_unchanged':True,
        'method':'Per original vertex, solve the actual blended linear bone matrix for the rest-space delta needed to reproduce the native CorrectiveSmooth cage at the constant isometric pose.',
        'max_condition_number':float(condition.max()),'linear_prediction_error_m':prediction_error,
        'offset_m':{str(q):float(np.percentile(lengths,q)) for q in [0,50,90,95,99,100]},
        'bounds':{'maximum_condition_number':10,'maximum_rest_offset_m':.05,'maximum_p99_rest_offset_m':.02},
        'affected_vertices_over_1micron':int((np.linalg.norm(delta,axis=1)>0).sum()),
        'corrected_cage_target_error_max_m':float(error.max()),
        'native_modifiers':'Static shape key at1 -> Armature -> Multires. Original CorrectiveSmooth disabled to avoid double correction.',
        'export_modifiers':'Static shape key at1 -> Armature only; one morph target with GLB mesh defaultweight1, no morph action.'}
    (P/'static-corrective.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report),flush=True)
    return report


def metadata():
    record=Path('catalogue/exercises/4348.json')
    context=P.parents[1]/'contexts/4348.json'
    return {
        'id':'4348','name':'abdominal 4 points','action':'Exercise_4348',
        'duration':5,'duration_seconds':5,'frames':150,'fps':30,
        'primary':['abs'],'secondary':['core','shoulders','hip flexors'],
        'display_mode':'heat','highlight_sides':{},
        'phases':[{'start':0,'end':2,'label':'Brace'}, {'start':2,'end':3,'label':'Hold'}, {'start':3,'end':5,'label':'Relax'}],
        'source_hold_recommendation_seconds':[15,30],
        'interpretation':'Compressed 5-second bracing demonstration on hands and knees; the source workout hold remains15–30seconds. The skeleton intentionally remains still during brace, hold and relaxation: no knee hover, plank transition, visible abdominal deformation or exaggerated breathing. The viewer may label the phases; no invented physiological activation curve. Normal breathing is an instruction, not simulated mechanics.',
        'authored_staging':{
            'floor':'Level Z=0 plane in original Blender world meters; review stills use thin datum lines with no masking floor surface.',
            'pose':'Wrists under shoulders, knees under hips; straight torso and neutral neck share a79degree world-X pitch (11degree upward slope toward shoulders). This reversible slope matches the unchanged mannequin limb lengths with natural near-straight elbows.',
            'hands':'Open palm support and all ten finger pads on the common floor. Palm orientation fitted to original palmar skin plane; distal finger phalanges are horizontal. Basis coordinates, rest, weights and UVs unchanged. One constant pose-corrective morph reproduces the clean native CorrectiveSmooth cage.',
            'feet':'Both lower legs extend behind with relaxed plantar-flexed feet; knee support is required, foot dorsum is supplementary.',
            'joint_angle_status':'Authored illustration placement; no clinical joint-range limits are claimed.'},
        'source':{'text_path':str(record),'text_sha256':hashlib.sha256(record.read_bytes()).hexdigest(),
                  'context_path':'artifacts/exercise-batches/batch-003/contexts/4348.json',
                  'context_sha256':hashlib.sha256(context.read_bytes()).hexdigest(),
                  'body_path':str(a.SOURCE),'body_sha256':a.SOURCE_SHA,'binding_rest_uv_sha256':EXPECTED,
                  'motion':'Original authored pose/action. All inherited historical actions are removed; no capture trajectory is used.',
                  'restricted_media_used':False},
        'static_pose_corrective':{'name':'StaticPoseCorrective_4348','weight':1,'animated':False,'reason':'Native CorrectiveSmooth cage reproduced in actual GLB LBS to remove rejected angular waist/shoulder folds.'},
        'readiness':'authored_prototype_requires_primary_runtime_and_user_review'
    }


def write_source_and_export():
    a.rig.animation_data_create()
    action=bpy.data.actions.new('Exercise_4348')
    action.use_fake_user=True
    a.rig.animation_data.action=action
    for frame in [1,31,61,76,91,121,151]:
        a.scene.frame_set(frame)
        make_pose((frame-1)/30)
        for pb in a.rig.pose.bones:
            pb.keyframe_insert('location',frame=frame)
            pb.keyframe_insert('rotation_quaternion',frame=frame)
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for curve in bag.fcurves:
                    for key in curve.keyframe_points:key.interpolation='LINEAR'
    assert len(bpy.data.actions)==1
    attr=a.body.data.attributes.get('_SOURCE_INDEX') or a.body.data.attributes.new(name='_SOURCE_INDEX',type='FLOAT',domain='POINT')
    attr.data.foreach_set('value',np.arange(len(a.body.data.vertices),dtype=np.float32))
    assert a.binding_hash(a.body,a.rig)==EXPECTED
    set_path('native');a.scene.frame_set(76);camera('oblique')
    a.scene['exercise_id']='4348'
    a.scene['demonstration_seconds']=5
    a.scene['workout_hold_seconds']='15–30'
    a.scene['isometric_stillness']='Deliberate: no fabricated visible joint or muscle-activation cycle.'
    bpy.context.preferences.filepaths.save_version=0
    bpy.ops.wm.save_as_mainfile(filepath=str(P/'source.blend'))
    (P/'clip.json').write_text(json.dumps(metadata(),indent=2)+'\n')
    (P/'cameras.json').write_text(json.dumps([{'label':name,**CAMERAS[name]} for name in ['oblique','side']],indent=2)+'\n')
    set_path('linear')
    bpy.ops.object.select_all(action='DESELECT')
    a.body.select_set(True);a.rig.select_set(True);bpy.context.view_layer.objects.active=a.rig
    bpy.ops.export_scene.gltf(filepath=str(P/'motion.glb'),export_format='GLB',use_selection=True,
        export_yup=True,export_apply=False,export_texcoords=True,export_normals=True,
        export_materials='EXPORT',export_vertex_color='NONE',export_attributes=True,
        export_animations=True,export_animation_mode='ACTIONS',export_force_sampling=True,
        export_frame_range=False,export_frame_step=1,export_anim_slide_to_zero=True,
        export_skins=True,export_influence_nb=4,export_def_bones=True,export_leaf_bone=False,
        export_rest_position_armature=True,export_extras=True,export_cameras=False,export_lights=False)
    from glb_normals import patch_morph_normals
    normals=patch_morph_normals(P/'motion.glb',STATIC_POSED_NORMALS,STATIC_ROTATIONS)
    (P/'normal-corrective.json').write_text(json.dumps(normals,indent=2)+'\n')
    data=(P/'motion.glb').read_bytes();length,kind=struct.unpack_from('<II',data,12);doc=json.loads(data[20:20+length])
    primitives=[p for mesh in doc['meshes'] for p in mesh['primitives']]
    assert len(doc['meshes'])==len(doc['skins'])==1
    assert len(doc['skins'][0]['joints'])==51
    assert [x['name'] for x in doc['animations']]==['Exercise_4348']
    assert sum(doc['accessors'][x['indices']]['count']//3 for x in primitives)==21160
    assert all('_SOURCE_INDEX' in x['attributes'] for x in primitives)
    assert len(doc.get('materials',[]))==1 and not doc.get('textures') and not doc.get('images')
    assert doc['meshes'][0].get('weights')==[1.0]
    assert all(len(p.get('targets',[]))==1 for p in primitives)
    summary={'source_sha256':hashlib.sha256((P/'source.blend').read_bytes()).hexdigest(),
        'glb_sha256':hashlib.sha256(data).hexdigest(),'glb_bytes':len(data),'source_bytes':(P/'source.blend').stat().st_size,
        'source_vertices':10582,'triangles':21160,'bones':51,'meshes':1,'materials':1,'textures':0,
        'animation':'Exercise_4348','binding_rest_uv_sha256':EXPECTED,
        'native_modifier_path':'StaticPoseCorrective_4348 at1 + Armature + Multires; CorrectiveSmooth disabled',
        'export_modifier_path':'Original Basis + one constant corrective morph at1, only Armature enabled',
        'morphs':1,'morph_default_weights':[1],
        'runtime_review_owner':'Primary agent'}
    (P/'runtime-export.json').write_text(json.dumps(summary,indent=2)+'\n')
    for report_name in ['static-corrective.json','normal-corrective.json']:
        report=json.loads((P/report_name).read_text())
        report.update(source_sha256=summary['source_sha256'],glb_sha256=summary['glb_sha256'])
        (P/report_name).write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(summary),flush=True)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--proof-only',action='store_true')
    options=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    initialize()
    add_datum(a.scene)
    add_static_corrective()
    for label,t,view in [('start',0,'side'),('hold',2.5,'oblique'),('return',5,'rear')]:
        render('early-'+label,t,view)
    render('early-hands',2.5,'hands')
    render('early-linear',2.5,'oblique','linear')
    if options.proof_only:return
    write_source_and_export()

if __name__=='__main__':main()
