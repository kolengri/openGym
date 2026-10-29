"""Capture invariant frozen foundation and native DQ skin without side effects."""
import sys
sys.dont_write_bytecode=True
import bpy,numpy as np,json,hashlib
from pathlib import Path
F=Path(__file__).resolve().parent
assert hashlib.sha256((F/'foundation.blend').read_bytes()).hexdigest()=='35502f29ae6ce6f6f8337cd722c79b899871e1364495adae544e6be1e38fac1a'
bpy.ops.wm.open_mainfile(filepath=str(F/'foundation.blend'))
b=bpy.data.objects['SK_BlenderStudioHuman'];r=bpy.data.objects['RIG_BlenderStudioHuman'];s=bpy.context.scene
assert not b.data.shape_keys
for m in b.modifiers:
    m.show_viewport=m.show_render=m.type=='ARMATURE'
    if m.type=='ARMATURE':m.use_deform_preserve_volume=True
rest=np.array([v.co[:]for v in b.data.vertices]);normals=np.array([v.normal[:]for v in b.data.vertices]);names=[pb.name for pb in r.pose.bones]
W=np.zeros((len(rest),len(names)))
for v in b.data.vertices:
    for g in v.groups:W[v.index,names.index(b.vertex_groups[g.group].name)]=g.weight
b.data.calc_loop_triangles();tri=np.array([t.vertices[:]for t in b.data.loop_triangles])
def points():
    bpy.context.view_layer.update();e=b.evaluated_get(bpy.context.evaluated_depsgraph_get());me=e.to_mesh();p=np.array([v.co[:]for v in me.vertices]);e.to_mesh_clear();return p
poses=[];mats=[]
for f in [0,19,37.5,56,75,94,112.5,131,150]:
    act=bpy.data.actions['Exercise_5172'];r.animation_data.action=act;r.animation_data.action_slot=next(x for x in act.slots if x.target_id_type=='OBJECT');s.frame_set(int(f)+1,subframe=f%1);p=points();poses.append(p);mats.append([np.array(pb.matrix@r.data.bones[pb.name].matrix_local.inverted())for pb in r.pose.bones])
np.savez_compressed(F/'capture.npz',rest=rest,normals=normals,weights=W,triangles=tri,frames=[0,19,37.5,56,75,94,112.5,131,150],positions=poses,matrices=mats,bone_rest=[np.array(r.data.bones[n].matrix_local)for n in names],bone_heads=[r.data.bones[n].head_local[:]for n in names],bone_tails=[r.data.bones[n].tail_local[:]for n in names])
top=np.argsort(poses[2][:,2])[-150:]
rows=[]
for i in range(len(rest)):
    if 1.26<rest[i,2]<1.6 and abs(rest[i,0])<.3:
        delta=float(np.linalg.norm(poses[2][i]-rest[i]));rows.append({'id':i,'rest':rest[i].tolist(),'peak':poses[2][i].tolist(),'weights':{n:float(w)for n,w in zip(names,W[i])if w},'native_displacement':delta})
(F/'capture.json').write_text(json.dumps({'source_sha256':hashlib.sha256((F/'foundation.blend').read_bytes()).hexdigest(),'bones':names,'collar':rows},indent=2)+'\n')
print('CAPTURE_READY',len(rest),len(tri),len(names))
