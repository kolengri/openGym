"""Freeze original-v5 near-arm body skin before a geodesic exclusion."""
import sys
sys.dont_write_bytecode=True
import bpy,numpy as np,json
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
F=Path(__file__).resolve().parent;sys.path.insert(0,str(F.parent));from self_clearance import SelfClearance
bpy.ops.wm.open_mainfile(filepath=str(F/'foundation.blend'));b=bpy.data.objects['SK_BlenderStudioHuman'];r=bpy.data.objects['RIG_BlenderStudioHuman'];s=bpy.context.scene
for m in b.modifiers:
    m.show_viewport=m.show_render=m.type=='ARMATURE'
    if m.type=='ARMATURE':m.use_deform_preserve_volume=True
c=SelfClearance(b,r);body_ids=np.array(sorted(set(i for face in c.torso for i in face)),int);distance=np.full(10582,np.inf)
for f in [37.5,112.5]:
    action=bpy.data.actions['Exercise_5172'];r.animation_data.action=action;r.animation_data.action_slot=next(x for x in action.slots if x.target_id_type=='OBJECT');s.frame_set(int(f)+1,subframe=.5);bpy.context.view_layer.update();e=b.evaluated_get(bpy.context.evaluated_depsgraph_get());me=e.to_mesh();p=np.array([v.co[:]for v in me.vertices]);e.to_mesh_clear();v=[Vector(x)for x in p]
    for side in ['Left','Right']:
        tree=BVHTree.FromPolygons(v,c.distal[side],all_triangles=True)
        for i in body_ids:distance[i]=min(distance[i],tree.find_nearest(v[i])[3])
rest=np.array([v.co[:]for v in b.data.vertices]);anatomy=np.flatnonzero((abs(rest[:,0])>.11)&(rest[:,2]>1.14)&(rest[:,2]<=1.36)&np.isin(np.arange(10582),body_ids))
near=body_ids[distance[body_ids]<.035];seeds=np.union1d(near,anatomy)
np.savez_compressed(F/'native-contact-domain.npz',near_arm_body_ids=near,lower_axilla_body_ids=anatomy,seed_source_ids=seeds,minimum_native_distal_arm_distance_m=distance)
(F/'native-contact-domain.json').write_text(json.dumps({'native_near_arm_cutoff_m':.035,'native_near_arm_source_ids':near.tolist(),'broad_lower_axilla_source_rule':'Dominant torso-face vertices withabsX>110mm and sourceZ1140..1360mm.','lower_axilla_source_ids':anatomy.tolist(),'union_seed_source_ids':seeds.tolist(),'source_vertices':10582,'source_reference':'Unmodifiedfrozenv5 both exact crossover peaks; source-index geodesic collar follows this capture.','geometry_changed':False},indent=2)+'\n')
print('CONTACT_DOMAIN',len(near),len(anatomy),len(seeds))
