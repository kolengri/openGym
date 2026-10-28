"""Measure named sit-up contacts; do not infer visual correctness from global min Z."""
import bpy,json,math,sys
from pathlib import Path
import numpy as np
P=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P/'bodyweight-five.blend'))
body=bpy.data.objects['SK_BlenderStudioHuman'];rig=bpy.data.objects['RIG_BlenderStudioHuman']
sys.path.insert(0,str(P.parent/'mannequin-muscle-atlas'));import muscle_atlas as atlas
weights=atlas.prepare(body)
rig.animation_data.action=bpy.data.actions['Exercise_0001']
results=[]
for frame in [0,30,60]:
    bpy.context.scene.frame_set(frame+1);bpy.context.view_layer.update()
    evaluated=body.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=evaluated.to_mesh()
    co=np.empty(len(mesh.vertices)*3,np.float32);mesh.vertices.foreach_get('co',co);co=co.reshape(-1,3)
    contacts={};angles={}
    for side,suffix in [('Left','L'),('Right','R')]:
        name=atlas.WEIGHT_PREFIX+'gluteus_maximus.'+suffix
        values=np.empty(len(mesh.vertices),np.float32);mesh.attributes[name].data.foreach_get('value',values)
        contact=co[values>.4,2]
        contacts[side+'GluteSurface']={'minimum_z_m':float(contact.min()),'fraction_within_1cm_of_floor':float(np.mean(abs(contact)<.01)),'scope':'Illustrative glute region proxy; not a verified ischial contact landmark.'}
        group_ids={body.vertex_groups[side+name].index for name in ['Foot','ToeBase']}
        ids=[v.index for v in mesh.vertices if sum(g.weight for g in v.groups if g.group in group_ids)>.8]
        contacts[side+'FootSurface']={'minimum_z_m':float(co[ids,2].min()),'fraction_within_1cm_of_floor':float(np.mean(abs(co[ids,2])<.01))}
        a=rig.pose.bones[side+'Arm'].head;e=rig.pose.bones[side+'ForeArm'].head;w=rig.pose.bones[side+'Hand'].head
        angles[side+'ElbowInternalDegrees']=math.degrees((a-e).angle(w-e))
    results.append({'frame':frame,'contacts':contacts,'joint_measurements':angles})
    evaluated.to_mesh_clear()
report={'status':'open_visual_defect','exercise_id':'0001','user_report':['Pelvis and feet do not read as sharing a floor plane.','Hand/head placement and arm bend look unnatural.'],
        'interpretation':'Contact proxy minima and joint angles are measurements, not acceptance. Contact area, named support landmarks, palm/head clearance, wrist orientation and camera floor readability remain unvalidated.',
        'samples':results,'not_biomechanically_approved':True}
(P/'situp-contact-investigation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
