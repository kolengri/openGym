"""Build original air-bike cycle; first pass is a neutral cage review draft."""
import json, sys, math, hashlib
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector

P=Path(__file__).resolve().parent
sys.path.insert(0,str(P.parents[2]/'batch-003'));sys.path.insert(0,str(P))
import authoring as a
import air_bike_pose
EXPECTED='227ede3fc31d1a2b47ff40f20a4a7288fe7bb36179add23bae953993826c8b7b'
assert a.initialize()==EXPECTED
body,rig,scene=a.body,a.rig,a.scene
for modifier in body.modifiers:
    modifier.show_viewport=modifier.show_render=modifier.type=='ARMATURE'
    if modifier.type=='ARMATURE':modifier.use_deform_preserve_volume=True
scene.frame_start=1;scene.frame_end=151;scene.render.fps=30
scene.render.engine='BLENDER_WORKBENCH'
scene.render.resolution_x=800;scene.render.resolution_y=650;scene.render.resolution_percentage=100
scene.render.film_transparent=True;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
shading=scene.display.shading
shading.light='STUDIO';shading.color_type='MATERIAL';shading.show_shadows=False;shading.show_cavity=False;shading.show_specular_highlight=False
scene.view_settings.view_transform='Standard';scene.view_settings.look='None'
camera_data=bpy.data.cameras.new('Camera_0003');camera=bpy.data.objects.new('Camera_0003',camera_data);scene.collection.objects.link(camera);scene.camera=camera;camera_data.type='ORTHO'
cameras=[{'label':'oblique','position':[2.8,-3.5,4.6],'target':[0,-.03,.28],'scale':2.35},
         {'label':'side','position':[5,-.15,1.1],'target':[0,-.03,.28],'scale':2.35}]
if (P/'cameras.json').exists():cameras=json.loads((P/'cameras.json').read_text())
else:(P/'cameras.json').write_text(json.dumps(cameras,indent=2)+'\n')
source_rest=np.array([v.co[:] for v in body.data.vertices])
pelvic_support=np.flatnonzero((abs(source_rest[:,0])<.16)&(source_rest[:,1]>.055)&(source_rest[:,2]>.82)&(source_rest[:,2]<1.02))
assert len(pelvic_support)>50

def pose(frame):
    air_bike_pose.pose(a,frame,.12);bpy.context.view_layer.update()
    evaluated=body.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=evaluated.to_mesh()
    minimum=min(mesh.vertices[int(i)].co.z for i in pelvic_support)
    evaluated.to_mesh_clear()
    air_bike_pose.pose(a,frame,.12-minimum+.001)
    bpy.context.view_layer.update()

rig.animation_data_create();action=bpy.data.actions.new('Exercise_0003');action.use_fake_user=True;rig.animation_data.action=action
previous={}
for frame in range(151):
    scene.frame_set(frame+1);pose(frame)
    for bone in rig.pose.bones:
        if bone.name in previous and bone.rotation_quaternion.dot(previous[bone.name])<0:bone.rotation_quaternion.negate()
        previous[bone.name]=bone.rotation_quaternion.copy()
        bone.keyframe_insert('location',frame=frame+1);bone.keyframe_insert('rotation_quaternion',frame=frame+1)
for layer in action.layers:
    for strip in layer.strips:
        for bag in strip.channelbags:
            for curve in bag.fcurves:
                for key in curve.keyframe_points:key.interpolation='LINEAR'
import joint_correctives
corrective_report=joint_correctives.install(body,rig,scene,action)
(P/'joint-corrective-report.json').write_text(json.dumps(corrective_report,indent=2)+'\n')
attribute=body.data.attributes.get('_SOURCE_INDEX') or body.data.attributes.new(name='_SOURCE_INDEX',type='FLOAT',domain='POINT')
attribute.data.foreach_set('value',np.arange(10582,dtype=np.float32))
assert a.binding_hash(body,rig)==EXPECTED
bpy.context.preferences.filepaths.save_version=0

def set_view(preset):
    camera.location=preset['position'];camera.rotation_euler=(Vector(preset['target'])-camera.location).to_track_quat('-Z','Y').to_euler();camera_data.ortho_scale=preset['scale']

set_view(cameras[0]);scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(P/'source.blend'))
bpy.ops.wm.open_mainfile(filepath=str(P/'source.blend'))
body=bpy.data.objects['SK_BlenderStudioHuman'];rig=bpy.data.objects['RIG_BlenderStudioHuman'];scene=bpy.context.scene;camera=scene.camera;camera_data=camera.data
rows=[]
for frame,label in [(0,'start'),(19,'entry'),(37.5,'right-elbow-left-knee'),(112.5,'left-elbow-right-knee')]:
    scene.frame_set(int(frame)+1,subframe=frame%1);bpy.context.view_layer.update()
    joints={bone.name:list(rig.matrix_world@bone.head) for bone in rig.pose.bones}
    rows.append({'id':'0003','frame':frame,'joints':joints})
    for view in cameras:
        if label=='entry' and view['label']=='side':continue
        set_view(view);scene.render.filepath=str(P/f"early-{label}-{view['label']}.png")
        if frame==0 and view['label']=='oblique':bpy.ops.render.render(write_still=False)
        bpy.ops.render.render(write_still=True)
    if frame==37.5:
        set_view({'position':[3.5,3.5,2.4],'target':[0,.05,.3],'scale':1.9})
        scene.render.filepath=str(P/'early-peak-rear.png');bpy.ops.render.render(write_still=True)
    if frame==0:
        set_view({'position':[3.5,3.5,2.4],'target':[0,.05,.3],'scale':2.35})
        scene.render.filepath=str(P/'early-start-rear.png');bpy.ops.render.render(write_still=True)
scene.frame_set(1);set_view(cameras[0])
bpy.ops.object.select_all(action='DESELECT');body.select_set(True);rig.select_set(True);bpy.context.view_layer.objects.active=rig
bpy.ops.export_scene.gltf(filepath=str(P/'motion.glb'),export_format='GLB',use_selection=True,export_yup=True,export_apply=False,export_texcoords=True,export_normals=True,export_materials='EXPORT',export_vertex_color='NONE',export_attributes=True,export_morph=True,export_morph_normal=True,export_animations=True,export_animation_mode='ACTIONS',export_merge_animation='ACTION',export_force_sampling=True,export_frame_range=False,export_frame_step=1,export_anim_slide_to_zero=True,export_skins=True,export_influence_nb=4,export_def_bones=True,export_leaf_bone=False,export_rest_position_armature=True,export_extras=True,export_cameras=False,export_lights=False)
record=json.loads((P.parents[4]/'catalogue/exercises/0003.json').read_text())
clip={'id':'0003','name':'air bike','action':'Exercise_0003','duration':5,'duration_seconds':5,'frames':150,'fps':30,'skinning':'dualQuaternion','primary':record['target'] if isinstance(record['target'],list) else [record['target']],'secondary':record['secondaryMuscles'],'display_mode':'heat','highlight_sides':{},'phases':[{'start':0,'end':1.25,'label':'Right elbow toward left knee; right leg extends'},{'start':1.25,'end':2.5,'label':'Return through raised-knee centre'},{'start':2.5,'end':3.75,'label':'Left elbow toward right knee; left leg extends'},{'start':3.75,'end':5,'label':'Return through raised-knee centre'}],'cross_pair_witnesses':[{'time':1.25,'frame':37.5,'elbow':'RightForeArm','knee':'LeftLeg','extended_leg':'Right'},{'time':3.75,'frame':112.5,'elbow':'LeftForeArm','knee':'RightLeg','extended_leg':'Left'}],'source_hold_recommendation_seconds':None,'source_instructions':record['instructions'],'interpretation':'One alternating supine air-bicycle repetition, not a seated bicycle. Raised legs start with knees90degrees; shoulders remain lightly curled for active repetitions. Separate open palms cradle the occiput with relaxed fingers, no neck pull. Pelvis/lumbar skin supports against floor and both feet stay airborne. All non-Armature modifiers off. Timings and joint angles beyond source90degree setup are authored illustration, not clinical limits.','source_roles':{'primary':['abs'],'secondary':['hip flexors']},'source_gaps':{'timing':'Source gives desired repetitions, no speed; one5second cycle authored.','hand_detail':'Hands behind head is sourced; exact separated palm placement and gentle finger curl authored.'},'review_status':'early_neutral_cage_review_pending'}
(P/'clip.json').write_text(json.dumps(clip,indent=2)+'\n');(P/'pose-samples.json').write_text(json.dumps(rows,indent=2)+'\n')
sha=lambda name:hashlib.sha256((P/name).read_bytes()).hexdigest()
(P/'early-report.json').write_text(json.dumps({'status':'early_neutral_cage_review_pending','source_sha256':sha('source.blend'),'motion_sha256':sha('motion.glb'),'binding_rest_uv_sha256':EXPECTED,'skinning':'dualQuaternion','source_vertices':10582,'bones':51,'source_mechanic':'Supine alternating air bicycle; right elbow to left knee while right leg extends, then opposite.','geometry_qa':'Not run before first visual review.','remaining_issues':'Inspect actual cage wrists/head clearance, shoulders/elbows, posterior pelvis and knee cap silhouettes before accepting this draft.','cross_pair_witnesses':clip['cross_pair_witnesses']},indent=2)+'\n')
print('EARLY_AIR_BIKE_READY',sha('source.blend'),sha('motion.glb'))
if '--final' in sys.argv:
    import verify_asset
    verification=verify_asset.run()
    assert verification['ok'],verification['failures']
import write_metadata
write_metadata.write()
