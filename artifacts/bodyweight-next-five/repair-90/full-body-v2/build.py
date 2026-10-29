"""Freeze only this versioned 90/90 source and export after source QA."""
import bpy,json,sys,hashlib
from pathlib import Path
import numpy as np
P=Path(__file__).resolve().parent;sys.path.insert(0,str(P));import candidate as c;import correctives as k
EXPECTED='227ede3fc31d1a2b47ff40f20a4a7288fe7bb36179add23bae953993826c8b7b'

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def build():
 c.setup();a=c.a;body=a.body;rig=a.rig;scene=a.scene;keys_report=k.prepare(c)
 (P/'corrective-edits.json').write_text(json.dumps(keys_report,indent=2)+'\n')
 rig.animation_data_create();keys=body.data.shape_keys;keys.animation_data_create()
 for identifier in ['10565','6560']:
  action=bpy.data.actions.new('Exercise_'+identifier);action.use_fake_user=True;rig.animation_data.action=action
  previous={}
  for index in range(151):
   scene.frame_set(index+1);c.pose(identifier,index/30)
   for pb in rig.pose.bones:
    if pb.name in previous and previous[pb.name].dot(pb.rotation_quaternion)<0:pb.rotation_quaternion.negate()
    previous[pb.name]=pb.rotation_quaternion.copy();pb.keyframe_insert('location',frame=index+1);pb.keyframe_insert('rotation_quaternion',frame=index+1)
  slot=action.slots.new(id_type='KEY',name='90 degree seated corrective');keys.animation_data.action=action;keys.animation_data.action_slot=slot
  for index in range(151):
   scene.frame_set(index+1);k.set_values(body,identifier,index/30)
   for name in sum(k.NAMES.values(),[]):keys.key_blocks[name].keyframe_insert('value',frame=index+1)
  for layer in action.layers:
   for strip in layer.strips:
    for bag in strip.channelbags:
     for curve in bag.fcurves:
      for key in curve.keyframe_points:key.interpolation='LINEAR'
 assert a.binding_hash(body,rig)==EXPECTED
 assert len(rig.data.bones)==51 and len(body.data.vertices)==10582
 attr=body.data.attributes.get('_SOURCE_INDEX') or body.data.attributes.new(name='_SOURCE_INDEX',type='FLOAT',domain='POINT');attr.data.foreach_set('value',np.arange(10582,dtype=np.float32))
 action=bpy.data.actions['Exercise_10565'];rig.animation_data.action=action;rig.animation_data.action_slot=next(s for s in action.slots if s.target_id_type=='OBJECT');keys.animation_data.action=action;keys.animation_data.action_slot=next(s for s in action.slots if s.target_id_type=='KEY')
 scene.frame_start=1;scene.frame_end=151;scene.frame_set(1);bpy.context.preferences.filepaths.save_version=0
 bpy.ops.wm.save_as_mainfile(filepath=str(P/'source.blend'))
 clips=json.loads((c.BASE/'ninety-clips.json').read_text())
 for item in clips:
  item['skinning']='dualQuaternion';item['asset']='ninety-repaired';item['required_renderer']='Three.js approved DQ adapter with standard POSITION/NORMAL morph targets'
  item['review_status']='native_DQ_morph_shape_reviewed_actual_runtime_review_pending'
  item['correctives']={'names':k.NAMES[item['id']],'all_names':sum(k.NAMES.values(),[]),'source_weights_unchanged':True,'position_and_normal_morphs':True,'native_smoothing_enabled':False}
  item['arms']=('Hands rest separately on the front knee and shin, with a relaxed outward elbow plane. Authored placement: the source does not specify press-hand placement.' if item['id']=='10565' else 'Both open palms and extended fingers rest on the floor alongside the front leg; hands slide a short distance as the body hinges, with outward unlocked elbows.')
  item['explicit_staging']={'pelvis_legs':'Front anatomical left thigh follows torso forward; rear right thigh lies to the side, approximately90degrees between thigh directions. Both knee bend planes follow the actual source anterior-knee frame. The previous135degree thigh spread is removed.','spine':'Flat-back forward hinge along the front thigh; no independent lumbar collapse. Press starts with a20degree forward orientation to keep authored separate leg-hand contacts reachable on the original arm proportions.','hands':item['arms'],'floor':'WorldZ=0m. Curved support witnesses and all-skin penetration are separate from visual silhouette acceptance.','timing':'5seconds:2seconds entry,1second demonstration hold,2seconds return. Workout hold remains20–30seconds; mirrored side is instructed separately.'}
  item['provenance']={'body_source':str(a.SOURCE),'body_source_sha256':a.SOURCE_SHA,'restricted_media_used':False,'binding_rest_uv_sha256':EXPECTED}
 (P/'ninety-clips.json').write_text(json.dumps(clips,indent=2)+'\n')
 (P/'ninety-camera-presets.json').write_bytes((c.BASE/'ninety-camera-presets.json').read_bytes())
 print('SOURCE_FROZEN',sha(P/'source.blend'))

def export():
 verification=json.loads((P/'source-verification.json').read_text());assert verification['ok'] and verification['source_sha256']==sha(P/'source.blend'),verification.get('failures')
 bpy.ops.wm.open_mainfile(filepath=str(P/'source.blend'));body=bpy.data.objects['SK_BlenderStudioHuman'];rig=bpy.data.objects['RIG_BlenderStudioHuman']
 # Blender5.2 ACTIONS discovers inactive KEY actions through NLA, unlike its
 # single-armature OBJECT action discovery. Temporary muted tracks expose both
 # existing key slots without changing or resaving the frozen authoring source.
 keys=body.data.shape_keys
 for action in bpy.data.actions:
  track=keys.animation_data.nla_tracks.new();track.name=action.name;track.mute=True
  strip=track.strips.new(action.name,1,action);strip.action_slot=next(s for s in action.slots if s.target_id_type=='KEY')
 bpy.ops.object.select_all(action='DESELECT');body.select_set(True);rig.select_set(True);bpy.context.view_layer.objects.active=rig
 bpy.ops.export_scene.gltf(filepath=str(P/'motion.glb'),export_format='GLB',use_selection=True,
  export_yup=True,export_apply=False,export_texcoords=True,export_normals=True,export_materials='EXPORT',export_vertex_color='NONE',export_attributes=True,
  export_morph=True,export_morph_normal=True,export_morph_animation=True,export_animations=True,export_animation_mode='ACTIONS',export_merge_animation='ACTION',export_force_sampling=True,export_frame_range=False,export_frame_step=1,export_anim_slide_to_zero=True,
  export_skins=True,export_influence_nb=4,export_def_bones=True,export_leaf_bone=False,export_rest_position_armature=True,export_extras=True,export_cameras=False,export_lights=False)
 print('EXPORTED',sha(P/'motion.glb'))

if __name__=='__main__':
 if '--export' in sys.argv:export()
 else:build()
