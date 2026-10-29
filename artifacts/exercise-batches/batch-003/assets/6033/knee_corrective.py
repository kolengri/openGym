"""Small source-index knee-cap rounding; unchanged Basis, weights and joints."""
import math
import numpy as np
import bpy
from mathutils import Quaternion,Vector
NAME='KneeCapRound'
MAX_OFFSET_M=.030

def normalized_blend_rotation(body,rig,vertex,rest):
    terms=[]
    for group in vertex.groups:
        name=body.vertex_groups[group.group].name
        if name in rest and group.weight>1e-8:
            q=(rig.pose.bones[name].matrix@rest[name].inverted()).to_quaternion()
            terms.append((group.weight,q))
    reference=max(terms,key=lambda term:term[0])[1]
    values=np.zeros(4)
    for weight,q in terms:
        sign=-1 if q.dot(reference)<0 else 1
        values+=np.array(q)*weight*sign
    q=Quaternion(values);q.normalize()
    return q

def flexion_degrees(rig,side):
    h=rig.pose.bones[side+'UpLeg'].head;k=rig.pose.bones[side+'Leg'].head;a=rig.pose.bones[side+'Foot'].head
    return 180-math.degrees((h-k).angle(a-k))

def activation(rig,peak_flexion):
    flexion=sum(flexion_degrees(rig,side) for side in ['Left','Right'])/2
    t=max(0,min(1,(flexion-40)/(peak_flexion-40)))
    return t*t*(3-2*t)

def install(body,rig,scene):
    import knee_native_target as native
    assert body.data.shape_keys is None,'Do not overwrite existing shape keys'
    saved_frame=scene.frame_current
    scene.frame_set(76);bpy.context.view_layer.update()
    rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
    original=np.array([v.co[:] for v in body.data.vertices])
    base,target,mask,report=native.capture(body,rig)
    world_delta=target-base;delta=np.zeros_like(original)
    changed=np.flatnonzero(np.linalg.norm(world_delta,axis=1)>1e-8)
    for index in changed:
        q=normalized_blend_rotation(body,rig,body.data.vertices[int(index)],rest)
        delta[index]=q.inverted()@Vector(world_delta[index])
    maximum=float(np.linalg.norm(delta,axis=1).max())
    assert maximum<=native.MAX_LOCAL_DISPLACEMENT_M+1e-7
    body.shape_key_add(name='Basis',from_mix=False)
    key=body.shape_key_add(name=NAME,from_mix=False)
    key.data.foreach_set('co',(original+delta).astype(np.float32).ravel());key.value=0
    assert np.array_equal(np.array([v.co[:] for v in body.data.vertices]),original)
    peak=sum(flexion_degrees(rig,side) for side in ['Left','Right'])/2
    key.value=1;bpy.context.view_layer.update()
    actual=native.coordinates(body)
    report.update({'name':NAME,'actual_maximum_rest_delta_m':maximum,
        'inverse_dq_target_maximum_error_m':float(np.linalg.norm(actual-target,axis=1).max()),
        'peak_flexion_degrees':peak,'activation':'Smooth0..1from40degrees of authored knee flexion to peak; zero at entry/return. Illustration parameter, not a clinical limit.',
        'base_and_weights_unchanged':True,'helpers_added':0,'original_bones':51,
        'normal_export':'Standard matching glTF NORMAL morph deltas are required.'})
    assert report['inverse_dq_target_maximum_error_m']<.00001
    key.value=0;scene.frame_set(saved_frame);bpy.context.view_layer.update()
    return key,report

def animate(body,rig,scene,key,report,action):
    keys=body.data.shape_keys;keys.animation_data_create()
    slot=action.slots.new(id_type='KEY',name='Knee corrective')
    keys.animation_data.action=action;keys.animation_data.action_slot=slot
    rows=[]
    for frame in range(151):
        scene.frame_set(frame+1);bpy.context.view_layer.update()
        key.value=activation(rig,report['peak_flexion_degrees'])
        key.keyframe_insert('value',frame=frame+1)
        if frame in [0,30,75,120,150]:rows.append({'frame':frame,'weight':float(key.value)})
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for curve in bag.fcurves:
                    for point in curve.keyframe_points:point.interpolation='LINEAR'
    report['sample_weights']=rows
    assert rows[0]['weight']==rows[-1]['weight']==0
    assert len(bpy.data.actions)==1 and action.name=='Exercise_6033'
    scene.frame_set(1);bpy.context.view_layer.update()
