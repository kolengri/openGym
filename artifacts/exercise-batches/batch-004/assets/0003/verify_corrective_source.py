"""Read-only original binding/Basis checks and independent normal references."""
import gzip,hashlib,json,sys
from pathlib import Path
import bpy,numpy as np
P=Path(__file__).resolve().parent
sys.path.insert(0,str(P.parents[2]/'batch-003'))
import authoring as a
bpy.ops.wm.open_mainfile(filepath=str(P/'source.blend'))
body=bpy.data.objects['SK_BlenderStudioHuman'];rig=bpy.data.objects['RIG_BlenderStudioHuman'];keys=body.data.shape_keys
names=['JointNeutral','JointRightCross','JointLeftCross']
assert [key.name for key in keys.key_blocks]==['Basis']+names
original=np.array([v.co[:]for v in body.data.vertices]);basis=np.array([v.co[:]for v in keys.key_blocks['Basis'].data])
assert np.array_equal(original,basis)
binding=a.binding_hash(body,rig)
assert binding=='227ede3fc31d1a2b47ff40f20a4a7288fe7bb36179add23bae953993826c8b7b'
assert len(rig.data.bones)==51 and [action.name for action in bpy.data.actions]==['Exercise_0003']
assert rig.animation_data.action==keys.animation_data.action
assert {slot.target_id_type for slot in rig.animation_data.action.slots}=={'OBJECT','KEY'}
assert all(m.show_viewport==(m.type=='ARMATURE')and m.show_render==(m.type=='ARMATURE')for m in body.modifiers)
assert next(m for m in body.modifiers if m.type=='ARMATURE').use_deform_preserve_volume
source_sha=hashlib.sha256((P/'source.blend').read_bytes()).hexdigest()
normal_ref={'source_sha256':source_sha,'basis':np.array(keys.key_blocks['Basis'].normals_vertex_get()).reshape((-1,3)).tolist(),'targets':{name:np.array(keys.key_blocks[name].normals_vertex_get()).reshape((-1,3)).tolist()for name in names},'coordinate_frame':'Original Blender rest normals; Z up'}
with gzip.open(P/'joint-normal-reference.json.gz','wt',compresslevel=9)as stream:json.dump(normal_ref,stream,separators=(',',':'))
pelvic=np.flatnonzero((abs(original[:,0])<.16)&(original[:,1]>.055)&(original[:,2]>.82)&(original[:,2]<1.02))
protected=max(float(np.linalg.norm(np.array([v.co[:]for v in keys.key_blocks[name].data])[pelvic]-basis[pelvic],axis=1).max())for name in names)
assert protected==0
report={'pass':True,'source_sha256':source_sha,'binding_rest_uv_sha256':binding,'basis_identical_to_original_mesh':True,'weights_rest_uv_unchanged':True,'bones':51,'actions':['Exercise_0003'],'action_slots':['OBJECT','KEY'],'morphs':names,'maximum_frozen_pelvic_support_rest_delta_m':protected,'global_corrective_smooth_disabled':True,'all_non_armature_modifiers_disabled':True,'normal_reference':'joint-normal-reference.json.gz','source_saved':False}
corrective=json.loads((P/'joint-corrective-report.json').read_text())
for entry in corrective['keys']:
    delta=np.array([v.co[:]for v in keys.key_blocks[entry['name']].data])-basis
    entry.setdefault('native_joint_changed_original_vertex_ids',entry['changed_original_vertex_ids'])
    entry['changed_original_vertex_ids']=np.flatnonzero(np.linalg.norm(delta,axis=1)>1e-8).tolist()
    entry['total_maximum_rest_delta_m']=float(np.linalg.norm(delta,axis=1).max())
    entry['final_changed_vertex_count']=len(entry['changed_original_vertex_ids'])
(P/'joint-corrective-report.json').write_text(json.dumps(corrective,indent=2)+'\n')
(P/'source-verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
