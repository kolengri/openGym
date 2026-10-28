"""Original seated ab-tuck on unchanged51bone binding, optional runtime DQ skin."""
import sys, math, json, hashlib
from pathlib import Path
import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector
P=Path(__file__).resolve().parent
sys.path.insert(0,str(P.parents[1]));sys.path.insert(0,str(P))
import authoring as a
EXPECTED='227ede3fc31d1a2b47ff40f20a4a7288fe7bb36179add23bae953993826c8b7b'
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
assert a.initialize()==EXPECTED
body,rig,scene=a.body,a.rig,a.scene
bone_count=len(rig.data.bones)
assert bone_count==51
arm=next(mod for mod in body.modifiers if mod.type=='ARMATURE')
arm.use_deform_preserve_volume=True
V=a.V
for mod in body.modifiers:
 if mod.type!='ARMATURE': mod.show_viewport=False;mod.show_render=False
# The live runtime requires DQ; standard GLB retains original rigid skin matrices/weights.
scene.render.fps=30;scene.frame_start=1;scene.frame_end=151
scene.render.engine='BLENDER_WORKBENCH'
scene.render.resolution_x=700;scene.render.resolution_y=600;scene.render.resolution_percentage=100
scene.render.film_transparent=True;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
s=scene.display.shading;s.light='STUDIO';s.color_type='MATERIAL';s.show_shadows=False;s.show_cavity=False;s.show_specular_highlight=False
s.background_type='WORLD';scene.world.color=(.97,.97,.97)
scene.view_settings.view_transform='Standard';scene.view_settings.look='None'
camdata=bpy.data.cameras.new('Camera_6033');cam=bpy.data.objects.new('Camera_6033',camdata);scene.collection.objects.link(cam);scene.camera=cam;camdata.type='ORTHO'
camera_file=P/'cameras.json'
assert camera_file.exists(),'Primary-owned camera presets are required'
camera_bytes=camera_file.read_bytes()
cameras=[{'id':row['label'],**{k:row[k] for k in ['position','target','scale']}} for row in json.loads(camera_bytes)]

def pose(f,root_z=.125):
 u=f/150;t=.5-.5*math.cos(2*math.pi*u)
 # Posterior pelvic tilt remains stable; chest moves toward the rising knees.
 root=V((0,.04,root_z))
 pelvis=-48+4*t;spine=-39+19*t;chest=-36+22*t;neck=-34+20*t
 desired=a.torso(root,[pelvis,spine,chest,neck,neck])
 targets={}
 for side,sign in [('Left',1),('Right',-1)]:
  shoulder=side+'Shoulder';sh=desired['Spine1']@a.rest['Spine1'].inverted()@a.heads[shoulder]
  desired[shoulder]=Matrix.Translation(sh)@(a.rx(chest)@a.rest[shoulder].to_quaternion()).to_matrix().to_4x4()
  armhead=desired[shoulder]@a.rest[shoulder].inverted()@a.heads[side+'Arm']
  hd=V((0,1,0));hn=V((0,0,-1));hq=a.palm_rotation(side,hd,hn)
  wrist=V((sign*.23,.22,a.palm_height(side,hq)-.005))
  elbow,wrist=a.two_joint(armhead,wrist,a.length[side+'Arm'],a.length[side+'ForeArm'],armhead+V((sign*.18,.5,-.1)))
  for bone,h,e in [(side+'Arm',armhead,elbow),(side+'ForeArm',elbow,wrist)]:
   desired[bone]=Matrix.Translation(h)@a.orient(bone,e-h).to_matrix().to_4x4()
  desired[side+'Hand']=Matrix.Translation(wrist)@a.orient(side+'Hand',hd,hn).to_matrix().to_4x4()
  hip=desired['Hips']@a.rest['Hips'].inverted()@a.heads[side+'UpLeg']
  ankle=V((sign*.15,-.805+.46*t,.19+.045*t))
  knee,ankle=a.two_joint(hip,ankle,a.length[side+'UpLeg'],a.length[side+'Leg'],V((sign*.15,-.34,.85)))
  for bone,h,e in [(side+'UpLeg',hip,knee),(side+'Leg',knee,ankle)]:
   desired[bone]=Matrix.Translation(h)@a.orient(bone,e-h).to_matrix().to_4x4()
  footq=a.foot_rotation(side,-45+20*t)
  desired[side+'Foot']=Matrix.Translation(ankle)@(footq@a.rest[side+'Foot'].to_quaternion()).to_matrix().to_4x4()
  toe=desired[side+'Foot']@a.rest[side+'Foot'].inverted()@a.heads[side+'ToeBase']
  desired[side+'ToeBase']=Matrix.Translation(toe)@(footq@a.rest[side+'ToeBase'].to_quaternion()).to_matrix().to_4x4()
 for bone,(h,e,parent,digit,index) in a.finger_specs.items():
  # Relaxed open support hands: native digit spread retained, no clenched fists.
  long=(e-h).normalized();normal=V((-1 if bone.startswith('Left') else 1,0,0))
  axis=a.rest[bone].to_3x3().inverted()@long.cross(normal).normalized()
  angle=-2 if index==0 and digit!='Thumb' else 0
  desired[bone]=desired[parent]@a.rest[parent].inverted()@a.rest[bone]@Quaternion(axis,math.radians(angle)).to_matrix().to_4x4()
 for pb in rig.pose.bones:
  parent=pb.parent.name if pb.parent else None
  pb.matrix_basis=a.rest[pb.name].inverted()@(a.rest[parent]@desired[parent].inverted() if parent else Matrix.Identity(4))@desired[pb.name]
 bpy.context.view_layer.update()
 return desired

def render(frame,view,filename,wire=False):
 scene.frame_set(frame+1)
 cam.location=view['position'];cam.rotation_euler=(V(view['target'])-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=view['scale']
 s.type='WIREFRAME' if wire else 'SOLID'
 scene.render.filepath=str(P/filename)
 if filename=='early-start-side.png':bpy.ops.render.render(write_still=False)
 bpy.ops.render.render(write_still=True)

pelvic_ids=[v.index for v in body.data.vertices if .85<v.co.z<1.03 and v.co.y>.05]
action=bpy.data.actions.new('Exercise_6033');action.use_fake_user=True
rig.animation_data_create();rig.animation_data.action=action
for f in range(151):
 scene.frame_set(f+1)
 # Couple actual posterior pelvic skin to the floor; wrists and airborne ankles
 # retain their independent targets while the arm/leg chains are solved again.
 z=.125
 for iteration in range(4):
  pose(f,z)
  evaluated=body.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=evaluated.to_mesh()
  gap=min(mesh.vertices[i].co.z for i in pelvic_ids)+.0015
  evaluated.to_mesh_clear()
  z-=gap
 pose(f,z)
 for pb in rig.pose.bones:
  pb.keyframe_insert('location',frame=f+1);pb.keyframe_insert('rotation_quaternion',frame=f+1)
for layer in action.layers:
 for strip in layer.strips:
  for bag in strip.channelbags:
   for fc in bag.fcurves:
    for kp in fc.keyframe_points:kp.interpolation='LINEAR'
import knee_corrective as kc
knee_key,knee_report=kc.install(body,rig,scene)
kc.animate(body,rig,scene,knee_key,knee_report,action)
assert a.binding_hash(body,rig)==EXPECTED
(P/'knee-corrective-report.json').write_text(json.dumps(knee_report,indent=2)+'\n')
scene.frame_set(1)
attribute=body.data.attributes.get('_SOURCE_INDEX') or body.data.attributes.new(name='_SOURCE_INDEX',type='FLOAT',domain='POINT')
attribute.data.foreach_set('value',np.arange(len(body.data.vertices),dtype=np.float32))
bpy.context.preferences.filepaths.save_version=0
cam.location=cameras[0]['position'];cam.rotation_euler=(V(cameras[0]['target'])-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=cameras[0]['scale']
bpy.ops.wm.save_as_mainfile(filepath=str(P/'source.blend'))
# Review a fresh-read keyed action so background Workbench does not reuse an authoring draw cache.
bpy.ops.wm.open_mainfile(filepath=str(P/'source.blend'))
body=bpy.data.objects['SK_BlenderStudioHuman'];rig=bpy.data.objects['RIG_BlenderStudioHuman'];scene=bpy.context.scene;cam=scene.camera;s=scene.display.shading
for f,label in [(0,'start'),(75,'peak'),(150,'return')]: render(f,cameras[1],f'early-{label}-side.png')
render(75,cameras[0],'early-peak-oblique.png')
render(75,{'position':[3,4,1.8],'target':[0,.05,.36],'scale':1.6},'early-peak-rear.png')
for mod in body.modifiers:mod.show_viewport=mod.show_render=mod.type in ['ARMATURE','MULTIRES']
render(75,cameras[1],'early-native-peak-side.png')
render(75,cameras[0],'early-native-peak-oblique.png')
for mod in body.modifiers:mod.show_viewport=mod.show_render=mod.type=='ARMATURE'
assert a.binding_hash(body,rig)==EXPECTED
print('EARLY_DQ_PROOF_READY')

if '--final' in args:
 import verify_asset
 report=verify_asset.run()
 assert report['ok'],report['failures']
 body=bpy.data.objects['SK_BlenderStudioHuman'];rig=bpy.data.objects['RIG_BlenderStudioHuman'];scene=bpy.context.scene
 assert a.binding_hash(body,rig)==EXPECTED
 bpy.ops.object.select_all(action='DESELECT');body.select_set(True);rig.select_set(True);bpy.context.view_layer.objects.active=rig
 bpy.ops.export_scene.gltf(filepath=str(P/'motion.glb'),export_format='GLB',use_selection=True,
  export_yup=True,export_apply=False,export_texcoords=True,export_normals=True,export_materials='EXPORT',export_vertex_color='NONE',export_attributes=True,
  export_morph=True,export_morph_normal=True,export_animations=True,export_animation_mode='ACTIONS',export_merge_animation='ACTION',export_force_sampling=True,export_frame_range=False,export_frame_step=1,export_anim_slide_to_zero=True,
  export_skins=True,export_influence_nb=4,export_def_bones=True,export_leaf_bone=False,export_rest_position_armature=True,export_extras=True,export_cameras=False,export_lights=False)
 clip={'id':'6033','name':'ab tuck','action':'Exercise_6033','duration':5.0,'duration_seconds':5.0,'frames':150,'duration_frames':150,'fps':30,'skinning':'dualQuaternion','bones':bone_count,'corrective':{'name':kc.NAME,'scope':'Whole local knee circumference only','maximum_displacement_m':knee_report['actual_maximum_rest_delta_m'],'zero_at_entry_return':True,'position_and_normal_morph':True},'source_hold_recommendation_seconds':None,'display_mode':'heat','camera':'oblique','primary':['abs'],'secondary':['lower abs','hip flexors'],'stretch':[],
  'source_roles':{'primary':['abs'],'secondary':['lower abs','hip flexors']},'muscle_display_roles':{'primary':'main','secondary':'additional'},'highlight_sides':{},'side_note':'Bilateral abs and hip-flexor exercise; both anatomical sides use the catalogue training roles.',
  'phases':[{'start':0,'end':2.5,'label':'Draw knees and chest together'},{'start':2.5,'end':5,'label':'Extend under control'}],
  'source_instructions':['Sit on the floor and lean back slightly.','Extend your legs in front of you.','Pull your knees to your chest as you bring your torso forward.','Extend again under control.','Keep your core braced.'],
  'interpretation':'Original supported seated tuck: lean back with open palms placed behind and lateral to pelvis, fingers away from body; both feet hover throughout. Pelvic skin remains on the floor while chest and knees approach, then extend under control. Hand placement and hovering feet are explicit reversible staging choices because the source omits those details.',
  'explicit_staging':{'hands':'Open palms behind/lateral to hips; fingers directed posteriorly, subtle2degree proximal extension preserves open support shape. Fixed wrists atx±0.23m,y0.22m retain posterior/lateral support while remaining reachable under the original DQ pelvic volume. No hand/body contact.','pelvis':'Actual bilateral posterior pelvic skin contacts floor. Root height is solved per frame against evaluated posterior skin with independent hand/ankle targets and re-solved limb chains.','legs':'Bilateral near-full extension to a controlled tuck, feet hovering; no floor foot support.','neck':'Tracks chest with neutral small offset; no isolated head rocking.','timing':'One5second controlled tuck/extend cycle at30fps, no workout hold duration asserted.','floor':'World Z=0 metres; illustration contact tolerance12mm/4mm penetration.'},
  'muscle_notice':'Illustrative catalogue training emphasis, not measured EMG or instantaneous recruitment. Lower abs uses inferior rectus-abdominis blocks; hip flexors includes a limited deep iliopsoas projection.',
  'provenance':{'text':'catalogue/exercises/6033.json','body':'Original Blender Studio CC0 mannequin in artifacts/bodyweight-five/bodyweight-five.blend','restricted_media_used':False},'review_status':'dq_source_checked_runtime_gpu_appearance_review_pending','source_record_sha256':hashlib.sha256((P.parents[4]/'catalogue/exercises/6033.json').read_bytes()).hexdigest(),'source_gaps':{'arms_hands':'Source unspecified; authored open posterior support palms.','foot_support':'Source unspecified; authored hovering feet.','joint_angles':'Authored illustration only, no validated clinical angles.'}}
 (P/'clip.json').write_text(json.dumps(clip,indent=2)+'\n')
 assert camera_file.read_bytes()==camera_bytes,'Primary-owned cameras changed during build'
 files={name:{'bytes':(P/name).stat().st_size,'sha256':hashlib.sha256((P/name).read_bytes()).hexdigest()} for name in ['source.blend','motion.glb']}
 (P/'build-report.json').write_text(json.dumps({'id':'6033','blender':bpy.app.version_string,'binding_rest_uv_sha256':EXPECTED,'skinning':'dualQuaternion','original_vertices':10582,'triangles':21160,'bones':bone_count,'actions':['Exercise_6033'],'materials':1,'textures':0,'shape_keys_added':1,'corrective':knee_report,'files':files,'native_modifiers':'Armature PreserveVolume enabled. One local knee key is active through flexion. Global CorrectiveSmooth remains disabled; optional native preview enables Multires only, so knee smoothing is never doubled.','geometry_contact_qa_ok':True,'shape_acceptance':'native_dq_reviewed_runtime_adapter_verification_pending','ready_for_integration':False},indent=2)+'\n')
 print('FINAL_EXPORT_READY',json.dumps(files))
