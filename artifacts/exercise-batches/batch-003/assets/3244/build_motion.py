"""Original abdominal stretch authored from catalogue text on the unchanged CC0 rig."""
import argparse, hashlib, json, math, struct, sys
from pathlib import Path
import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector
P=Path(__file__).resolve().parent
sys.path.insert(0,str(P.parents[1]))
import authoring as a
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
parser=argparse.ArgumentParser();parser.add_argument('--early',action='store_true');options=parser.parse_args(args)
a.initialize();body,rig,scene=a.body,a.rig,a.scene
REST=np.array([v.co[:] for v in body.data.vertices]); GROUP={g.index:g.name for g in body.vertex_groups}
WEIGHTS={name:np.array([sum(g.weight for g in v.groups if GROUP[g.group]==name) for v in body.data.vertices]) for name in GROUP.values()}
NATIVE_MODS={m.name:(m.show_viewport,m.show_render,getattr(m,'use_deform_preserve_volume',None)) for m in body.modifiers}
for m in body.modifiers:
 m.show_viewport=m.type=='ARMATURE';m.show_render=m.type=='ARMATURE'
 if m.type=='ARMATURE':m.use_deform_preserve_volume=False

def amount(t):
 return a.ease(t/2) if t<2 else 1 if t<=3 else a.ease((5-t)/2)

def pose(t):
 s=amount(t)
 # Pelvis remains prone; extension is spread progressively across the trunk.
 pitches=[90,79-11*s,71-26*s,65-38*s,65-48*s]
 root=a.V((0,.04,.159))
 desired=a.torso(root,pitches)
 for side,sign in [('Left',1),('Right',-1)]:
  sh=side+'Shoulder';h=desired['Spine1']@a.rest['Spine1'].inverted()@a.heads[sh]
  desired[sh]=Matrix.Translation(h)@(a.rx(pitches[2])@a.rest[sh].to_quaternion()).to_matrix().to_4x4()
  armhead=desired[sh]@a.rest[sh].inverted()@a.heads[side+'Arm']
  hdir=a.V((0,-1,0));hnormal=a.V((0,0,-1));hq=a.palm_rotation(side,hdir,hnormal)
  wrist=a.V((sign*.242,-.405,a.palm_height(side,hq)-.011))
  elbow,wrist=a.two_joint(armhead,wrist,a.length[side+'Arm'],a.length[side+'ForeArm'],a.V((sign*.29,.06,.19)))
  for bone,h,tail in [(side+'Arm',armhead,elbow),(side+'ForeArm',elbow,wrist)]:
   desired[bone]=Matrix.Translation(h)@a.orient(bone,tail-h).to_matrix().to_4x4()
  desired[side+'Hand']=Matrix.Translation(wrist)@a.orient(side+'Hand',hdir,hnormal).to_matrix().to_4x4()
  hip=desired['Hips']@a.rest['Hips'].inverted()@a.heads[side+'UpLeg']
  ankle=a.V((sign*.16,.887,.021))
  knee,ankle=a.two_joint(hip,ankle,a.length[side+'UpLeg'],a.length[side+'Leg'],a.V((sign*.15,.45,-.3)))
  for bone,h,tail in [(side+'UpLeg',hip,knee),(side+'Leg',knee,ankle)]:
   desired[bone]=Matrix.Translation(h)@a.orient(bone,tail-h).to_matrix().to_4x4()
  q=a.foot_rotation(side,158)
  desired[side+'Foot']=Matrix.Translation(ankle)@(q@a.rest[side+'Foot'].to_quaternion()).to_matrix().to_4x4()
  toe=desired[side+'Foot']@a.rest[side+'Foot'].inverted()@a.heads[side+'ToeBase']
  desired[side+'ToeBase']=Matrix.Translation(toe)@(q@a.rest[side+'ToeBase'].to_quaternion()).to_matrix().to_4x4()
 for side,sign in [('Left',1),('Right',-1)]:
  transform=desired[side+'Hand']@a.rest[side+'Hand'].inverted()
  for digit in ['Thumb','Index','Middle','Ring','Little']:
   names=[side+digit+str(i) for i in [1,2,3]]
   start=transform@a.heads[names[0]];end=transform@a.tails[names[-1]]
   direction=end-start;direction.z=0;direction.normalize()
   total=sum(a.length[n] for n in names)
   drop=(.014-start.z)/total
   target=(direction*math.sqrt(max(.1,1-drop*drop))+a.V((0,0,drop))).normalized()
   for bone in names:
    parent=rig.data.bones[bone].parent.name
    original=desired[parent]@a.rest[parent].inverted()@a.rest[bone]
    h=original.translation;rot=original.to_quaternion()
    current=rot@a.V((0,1,0))
    q=current.rotation_difference(target)@rot
    desired[bone]=Matrix.Translation(h)@q.to_matrix().to_4x4()
 for pb in rig.pose.bones:
  parent=pb.parent.name if pb.parent else None
  pb.matrix_basis=a.rest[pb.name].inverted()@(a.rest[parent]@desired[parent].inverted() if parent else Matrix.Identity(4))@desired[pb.name]
 bpy.context.view_layer.update()
 return desired

def positions():
 ev=body.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh();p=np.array([body.matrix_world@v.co for v in me.vertices]);ev.to_mesh_clear();return p

scene.render.engine='BLENDER_WORKBENCH';scene.render.resolution_x=1100;scene.render.resolution_y=650;scene.render.resolution_percentage=100
scene.render.film_transparent=False;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
shade=scene.display.shading;shade.light='STUDIO';shade.color_type='MATERIAL';shade.show_shadows=False;shade.show_cavity=False;shade.show_specular_highlight=False;shade.background_type='WORLD'
scene.world.color=(.92,.94,.96);scene.view_settings.view_transform='Standard';scene.view_settings.look='None'
camdata=bpy.data.cameras.new('ReviewCamera');cam=bpy.data.objects.new('ReviewCamera',camdata);scene.collection.objects.link(cam);scene.camera=cam
CAMERAS=[{'label':'side','position':[5,.08,.56],'target':[0,.08,.40],'scale':2.06},{'label':'oblique','position':[3.8,-3.2,2.25],'target':[0,.08,.32],'scale':2.03}]
def camera(c):
 cam.location=c['position'];target=a.V(c['target']);cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();camdata.type='ORTHO';camdata.ortho_scale=c['scale']
# The floor is a neutral visual witness for curated proofs only; it is not exported.
bpy.ops.mesh.primitive_plane_add(size=2.4,location=(0,.10,-.004));floor=bpy.context.object;floor.name='QA_Floor';mat=bpy.data.materials.new('QA_Floor_Neutral');mat.diffuse_color=(.84,.86,.88,1);floor.data.materials.append(mat)

def render(name,t,c=0,wire=False):
 scene.frame_set(round(t*30)+1);pose(t);camera(CAMERAS[c]);body.show_wire=wire
 scene.render.filepath=str(P/name);bpy.ops.render.render(write_still=True);body.show_wire=False

if options.early:
 samples={}
 for label,t in [('start',0),('peak',2.5),('return',5)]:
  pose(t);p=positions();samples[label]={}
  masks={'pelvis':(REST[:,2]>.82)&(REST[:,2]<1.07)&(REST[:,1]<.035)&(abs(REST[:,0])<.21),'thigh_L':WEIGHTS['LeftUpLeg']>.7,'shin_L':WEIGHTS['LeftLeg']>.7,'foot_L':(WEIGHTS['LeftFoot']+WEIGHTS['LeftToeBase'])>.7,'palm_L':WEIGHTS['LeftHand']>.7,**{digit:WEIGHTS['Left'+digit+'3']>.5 for digit in ['Thumb','Index','Middle','Ring','Little']}}
  for n,m in masks.items():samples[label][n]={'min_z':float(p[m,2].min()),'median_z':float(np.median(p[m,2]))}
  samples[label]['global_min_z']=float(p[:,2].min()); samples[label]['lowest']=[{'i':int(i),'xyz':p[i].tolist(),'rest':REST[i].tolist(),'groups':[(GROUP[g.group],g.weight) for g in body.data.vertices[i].groups]} for i in np.argsort(p[:,2])[:3]]
  render('early-'+label+'-side.png',t)
 render('early-peak-oblique.png',2.5,1)
 (P/'early-contacts.json').write_text(json.dumps(samples,indent=2)+'\n')
 print(json.dumps(samples));sys.exit(0)

# Exactly one original 5-second action, with keys baked from the pose solver.
rig.animation_data_create();action=bpy.data.actions.new('Exercise_3244');action.use_fake_user=True;rig.animation_data.action=action
previous={}
for runtime_frame in range(151):
 scene.frame_set(runtime_frame+1);pose(runtime_frame/30)
 for pb in rig.pose.bones:
  if pb.name in previous and pb.rotation_quaternion.dot(previous[pb.name])<0:pb.rotation_quaternion.negate()
  previous[pb.name]=pb.rotation_quaternion.copy()
  pb.keyframe_insert('location',frame=runtime_frame+1);pb.keyframe_insert('rotation_quaternion',frame=runtime_frame+1)
for layer in action.layers:
 for strip in layer.strips:
  for bag in strip.channelbags:
   for curve in bag.fcurves:
    for key in curve.keyframe_points:key.interpolation='LINEAR'
scene.frame_start=1;scene.frame_end=151
assert a.binding_hash(body,rig)=='227ede3fc31d1a2b47ff40f20a4a7288fe7bb36179add23bae953993826c8b7b'
attribute=body.data.attributes.get('_SOURCE_INDEX') or body.data.attributes.new(name='_SOURCE_INDEX',type='FLOAT',domain='POINT')
attribute.data.foreach_set('value',np.arange(len(body.data.vertices),dtype=np.float32))
(P/'cameras.json').write_text(json.dumps(CAMERAS,indent=2)+'\n')
source_record=P.parents[4]/'catalogue/exercises/3244.json'
clip={'id':'3244','name':'abdominal stretch','action':'Exercise_3244','duration':5,'duration_seconds':5,'frames':150,'fps':30,
 'primary':['abs'],'secondary':['hip flexors','chest'],'stretch':['abs','hip flexors','chest'],'display_mode':'stretch','highlight_sides':{},
 'phases':[{'start':0,'end':2,'label':'Enter'},{'start':2,'end':3,'label':'Hold'},{'start':3,'end':5,'label':'Return'}],
 'source_hold_recommendation_seconds':[20,30],
 'interpretation':'Original low prone press-up with planted ventral pelvis and relaxed legs, flat open palms, extended finger pads and natural bent elbows. A low preparatory chest clearance avoids forcing the original neutral cage through the floor. The hips never rise; this is not an upward-dog transition. Trunk extension is distributed across spine segments and the head remains relaxed near forward gaze at the hold. The 5-second demonstration compresses a source 20–30-second hold.',
 'source_roles':{'primary':['abs'],'additional':['hip flexors','chest'],'illustrative_palette':'cyan stretch, neutral inactive skin; not measured recruitment'},
 'source_record':'catalogue/exercises/3244.json','source_record_sha256':hashlib.sha256(source_record.read_bytes()).hexdigest(),
 'provenance':'Repository instruction text and unchanged Blender Studio CC0 mannequin. No restricted exercise images/video used.',
 'staging':{'laterality':'Bilateral symmetrical press-up; no alternating side.','support':'Ventral pelvis, anterior thigh/knee/shin, foot dorsum, palm heel and all distal finger pads on shared z=0 illustration floor.','hands':'Open palm down, fingers forward, mild natural spread; thumb abducted to the floor.','elbow_poles':'Backward with small lateral offset; no elbow lock.','neck':'Head pitch 65 degrees downward at low entry, 17 degrees at hold; no extreme backward neck tilt.','timing':'2 seconds enter, 1 second hold, 2 seconds return. Workout hold remains separate.'},
 'joint_targets':{'basis':'Blender-world rotations about +X applied to original rest segments; 0 upright, 90 prone. These are authored segment orientations, not validated anatomical joint limits.','segment_pitch_start_degrees':[90,79,71,65,65],'segment_pitch_hold_degrees':[90,68,45,27,17],'segment_order':['Hips','Spine','Spine1','Neck','Head'],'clinical_safe_limits':None},
 'binding_rest_uv_sha256':a.binding_hash(body,rig),'source_vertex_count':10582,'bone_count':51,
 'native_surface':'Original native JointSurfaceCorrective and Multires retained; independent QA compares against exported original cage with linear skinning.',
 'not_production_approved':True}
(P/'clip.json').write_text(json.dumps(clip,indent=2)+'\n')
# Native source retains the inherited corrective/subdivision configuration.
for m in body.modifiers:
 m.show_viewport,m.show_render,preserve=NATIVE_MODS[m.name]
 if preserve is not None:m.use_deform_preserve_volume=preserve
scene.frame_set(1);camera(CAMERAS[0]);bpy.ops.wm.save_as_mainfile(filepath=str(P/'source.blend'))
for label,t,c in [('start',0,0),('peak',2.5,0),('return',5,0),('peak',2.5,1)]:render('native-'+label+'-'+CAMERAS[c]['label']+'-solid.png',t,c)
# Wire proof is a temporary QA object over actual native evaluated geometry.
scene.frame_set(76);pose(2.5)
ev=body.evaluated_get(bpy.context.evaluated_depsgraph_get());wiremesh=bpy.data.meshes.new_from_object(ev);wire=bpy.data.objects.new('QA_Wire',wiremesh);scene.collection.objects.link(wire)
wiremod=wire.modifiers.new('QA_Wire','WIREFRAME');wiremod.thickness=.0007;wiremod.use_replace=True
wire.data.materials.clear();wiremat=bpy.data.materials.new('QA_Wire_Dark');wiremat.diffuse_color=(.055,.065,.075,1);wire.data.materials.append(wiremat)
render('native-peak-oblique-wire.png',2.5,1);bpy.data.objects.remove(wire,do_unlink=True)
# Export unchanged original cage with linear blend skinning; no native smooth fix is baked.
for m in body.modifiers:
 m.show_viewport=m.type=='ARMATURE';m.show_render=m.type=='ARMATURE'
 if m.type=='ARMATURE':m.use_deform_preserve_volume=False
bpy.ops.object.select_all(action='DESELECT');body.select_set(True);rig.select_set(True);bpy.context.view_layer.objects.active=rig
bpy.ops.export_scene.gltf(filepath=str(P/'motion.glb'),export_format='GLB',use_selection=True,
 export_yup=True,export_apply=False,export_texcoords=True,export_normals=True,export_materials='EXPORT',export_vertex_color='NONE',export_attributes=True,
 export_animations=True,export_animation_mode='ACTIONS',export_force_sampling=True,export_frame_range=False,export_frame_step=1,export_anim_slide_to_zero=True,
 export_skins=True,export_influence_nb=4,export_def_bones=True,export_leaf_bone=False,export_rest_position_armature=True,export_extras=True,export_cameras=False,export_lights=False)
blob=(P/'motion.glb').read_bytes();chunk,kind=struct.unpack_from('<II',blob,12);doc=json.loads(blob[20:20+chunk]);prims=[p for me in doc['meshes'] for p in me['primitives']]
assert len(doc['meshes'])==len(doc['skins'])==1 and len(doc['skins'][0]['joints'])==51
assert len(doc['animations'])==1 and doc['animations'][0]['name']=='Exercise_3244'
assert sum(doc['accessors'][p['indices']]['count']//3 for p in prims)==21160
assert not doc.get('images') and not doc.get('textures') and len(doc['materials'])==1
assert all('_SOURCE_INDEX' in p['attributes'] for p in prims)
export={'id':'3244','source_sha256':hashlib.sha256((P/'source.blend').read_bytes()).hexdigest(),'motion_sha256':hashlib.sha256(blob).hexdigest(),'motion_bytes':len(blob),'source_bytes':(P/'source.blend').stat().st_size,
 'binding_rest_uv_sha256':a.binding_hash(body,rig),'original_vertices':10582,'triangles':21160,'bones':51,'animations':[x['name'] for x in doc['animations']],'source_index':'_SOURCE_INDEX','materials':1,'textures':0,'native_modifiers':NATIVE_MODS,'runtime':'Linear skinning of original cage. No native corrective/subdivision baked.'}
(P/'export-report.json').write_text(json.dumps(export,indent=2)+'\n');print(json.dumps(export))
