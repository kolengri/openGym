"""Export one authored geometry/rig with two compatible canonical clip identities."""
from pathlib import Path
import bpy,json,shutil,struct,copy
P=Path(__file__).resolve().parent;Q=P.parent/'4714'
bpy.ops.wm.open_mainfile(filepath=str(P/'source.blend'));body=bpy.data.objects['SK_BlenderStudioHuman'];rig=bpy.data.objects['RIG_BlenderStudioHuman'];scene=bpy.context.scene
first=bpy.data.actions.get('Exercise_3948');assert first is not None
if bpy.data.actions.get('Exercise_4714') is None:
 second=first.copy();second.name='Exercise_4714';second.use_fake_user=True
assert set(x.name for x in bpy.data.actions)=={'Exercise_3948','Exercise_4714'}
rig.animation_data.action=first;scene['shared_squat_family']='One geometry and identical motion; canonical identities3948 and4714 differ only in text and muscle roles.'
scene.frame_set(1);bpy.ops.wm.save_as_mainfile(filepath=str(P/'source.blend'));shutil.copyfile(P/'source.blend',Q/'source.blend')
bpy.ops.object.select_all(action='DESELECT');body.select_set(True);rig.select_set(True);bpy.context.view_layer.objects.active=rig
result=bpy.ops.export_scene.gltf(filepath=str(P/'motion.glb'),export_format='GLB',use_selection=True,export_animations=True,export_animation_mode='ACTIONS',export_force_sampling=True,export_frame_range=True,export_frame_step=1,export_skins=True,export_all_influences=False,export_apply=False,export_morph=True,export_morph_normal=True,export_merge_animation='ACTION',export_attributes=True,export_materials='EXPORT',export_vertex_color='NONE',export_anim_slide_to_zero=True,export_rest_position_armature=True,export_influence_nb=4,export_cameras=False,export_lights=False,export_yup=True)
assert result=={'FINISHED'}
# Blender resamples copied actions independently, introducing tiny quaternion
# rounding differences. Both canonical labels intentionally reference identical
# glTF samplers; preserve one geometry and one canonical sample set.
path=P/'motion.glb';blob=path.read_bytes();jsonlen=struct.unpack_from('<I',blob,12)[0];doc=json.loads(blob[20:20+jsonlen]);animations=doc['animations'];canonical=next(x for x in animations if x['name']=='Exercise_3948');doc['animations']=[copy.deepcopy(canonical),copy.deepcopy(canonical)];doc['animations'][1]['name']='Exercise_4714'
j=json.dumps(doc,separators=(',',':')).encode();j+=b' '*((-len(j))%4);tail=blob[20+jsonlen:];path.write_bytes(struct.pack('<4sII',b'glTF',2,20+len(j)+len(tail))+struct.pack('<I4s',len(j),b'JSON')+j+tail)
shutil.copyfile(path,Q/'motion.glb')
samples=json.loads((P/'pose-samples.json').read_text())
for sample in samples:sample['id']='4714'
(Q/'pose-samples.json').write_text(json.dumps(samples,indent=2)+'\n');(Q/'cameras.json').write_text((P/'cameras.json').read_text())
print('EXPORTED_SHARED_TWO_ACTIONS',(P/'motion.glb').stat().st_size)
