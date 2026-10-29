"""Exact accepted6539 native action identity; no new pose or binding fit."""
from pathlib import Path
import sys
sys.dont_write_bytecode=True
import bpy,numpy as np,json,hashlib
F=Path(__file__).resolve().parent;A=F.parent/'assets/1315';O=F.parents[1]/'batch-008/assets/6539'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(O/'source.blend')=='b8499ef44ef06bb5f9ae85edf787b86021cbe555cdce9e1220a01bc5f566a332'
bpy.ops.wm.open_mainfile(filepath=str(O/'source.blend'));b=bpy.data.objects['SK_BlenderStudioHuman'];r=bpy.data.objects['RIG_BlenderStudioHuman'];s=bpy.context.scene
key=b.data.shape_keys.key_blocks['RestingHipVolume']
def sample():
 bpy.context.view_layer.update();ev=b.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh();x=np.array([v.co[:]for v in me.vertices],np.float32);ev.to_mesh_clear();return x,np.array([pb.matrix for pb in r.pose.bones],np.float32),float(key.value)
old=[]
for f in range(151):s.frame_set(f+1);old.append(sample())
bpy.data.actions['Exercise_6539'].name='Exercise_1315'
assert r.animation_data.action.name==b.data.shape_keys.animation_data.action.name=='Exercise_1315'
maximum=[0.,0.,0.]
for f,ref in enumerate(old):
 s.frame_set(f+1);now=sample()
 for i in range(3):maximum[i]=max(maximum[i],float(np.max(np.abs(now[i]-ref[i]))))
assert maximum==[0,0,0]
old.clear();s.frame_set(1);bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(A/'source.blend'))
report={'ok':True,'frames':151,'source_sha256':sha(A/'source.blend'),'reused_source_sha256':sha(O/'source.blend'),'maximum_native_skin_identity_error_m':maximum[0],'maximum_native_matrix_identity_error':maximum[1],'maximum_native_morph_identity_error':maximum[2],'no_refit':True,'identity_change':'Only Exercise_6539 action identity becomes Exercise_1315. Original weights, Basis, topology, UV, rest skeleton, hip target and 151 keyed poses are exact.'}
(F/'rest-native-identity.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
