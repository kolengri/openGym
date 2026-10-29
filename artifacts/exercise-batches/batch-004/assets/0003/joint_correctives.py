"""Three compact exact-DQ local joint keys with a bounded flank floor guard."""
import math,json
import bpy,numpy as np
from mathutils import Quaternion,Vector
import local_joint_target as local

STATES=[('JointNeutral',0),('JointRightCross',37.5),('JointLeftCross',112.5)]


def rotation(body,rig,index,rest):
    terms=[(group.weight,(rig.pose.bones[body.vertex_groups[group.group].name].matrix@rest[body.vertex_groups[group.group].name].inverted()).to_quaternion())for group in body.data.vertices[index].groups if group.weight>1e-8]
    reference=max(terms,key=lambda value:value[0])[1];value=np.zeros(4)
    for weight,q in terms:value+=np.array(q)*weight*(-1 if q.dot(reference)<0 else 1)
    q=Quaternion(value);q.normalize();return q


def weights(frame):
    swing=max(-1,min(1,math.sin(2*math.pi*frame/150)/math.sin(2*math.pi*37/150)))
    if abs(swing)<1e-12:swing=0
    return [1-abs(swing),max(0,swing),max(0,-swing)]


def set_frame(scene,frame):
    scene.frame_set(int(frame)+1,subframe=frame%1);bpy.context.view_layer.update()


def install(body,rig,scene,action):
    assert body.data.shape_keys is None
    original=np.array([v.co[:]for v in body.data.vertices]);rest={bone.name:bone.matrix_local.copy()for bone in rig.data.bones}
    flank=local.flank_mask(body);flank_ids=np.flatnonzero(flank>1e-5)
    deltas=[];up_directions=[];reports=[];targets=[]
    for name,frame in STATES:
        set_frame(scene,frame);base,target,report=local.capture(body,rig)
        delta=np.zeros_like(original);up={}
        for index in np.flatnonzero(np.linalg.norm(target-base,axis=1)>1e-8):
            delta[index]=rotation(body,rig,int(index),rest).inverted()@Vector(target[index]-base[index])
        for index in flank_ids:up[int(index)]=rotation(body,rig,int(index),rest).inverted()@Vector((0,0,1))
        deltas.append(delta);up_directions.append(up);reports.append({'name':name,'frame':frame,**report});targets.append(target)

    # DQ positions are affine in rest-space morph deltas for fixed bones. A
    # smooth constant-amplitude pocket per key avoids per-vertex fit creases.
    # Select its smallest sufficient amplitude over the full authored cycle;
    # no per-frame shape keys, mesh projection or weight fits are introduced.
    amplitudes=np.zeros(3);baseline_floor=1.;worst_requirement=None
    for frame in range(151):
        set_frame(scene,frame);points=local.coordinates(body);w=weights(frame);state=int(np.argmax(w))
        for index in flank_ids:
            index=int(index);q=rotation(body,rig,index,rest)
            current=Vector(points[index])
            for key in range(3):current+=w[key]*(q@Vector(deltas[key][index]))
            baseline_floor=min(baseline_floor,current.z)
            required=.001-current.z
            if required<=1e-7:continue
            sensitivity=w[state]*(q@up_directions[state][index]).z*flank[index]
            assert sensitivity>1e-5,('Unreachable local flank guard',frame,index)
            amplitude=required/sensitivity
            if amplitude>amplitudes[state]:
                amplitudes[state]=amplitude;worst_requirement={'frame':frame,'original_id':index,'source_coordinate':original[index].tolist(),'uncorrected_z':current.z}
    assert float(amplitudes.max())<.035,('Local flank requirement exceeds35mm',amplitudes.tolist(),worst_requirement)
    for state in range(3):
        for index in flank_ids:deltas[state][index]+=up_directions[state][int(index)]*(amplitudes[state]*flank[index])

    body.shape_key_add(name='Basis',from_mix=False)
    for state,(name,frame)in enumerate(STATES):
        key=body.shape_key_add(name=name,from_mix=False);key.data.foreach_set('co',(original+deltas[state]).astype(np.float32).ravel());key.value=0
        reports[state]['flank_guard_amplitude_m']=float(amplitudes[state])
        reports[state]['total_maximum_rest_delta_m']=float(np.linalg.norm(deltas[state],axis=1).max())
        reports[state]['native_joint_changed_original_vertex_ids']=reports[state]['changed_original_vertex_ids']
        reports[state]['changed_original_vertex_ids']=np.flatnonzero(np.linalg.norm(deltas[state],axis=1)>1e-8).tolist()
    assert np.array_equal(original,np.array([v.co[:]for v in body.data.vertices]))
    keys=body.data.shape_keys;keys.animation_data_create();slot=action.slots.new(id_type='KEY',name='Local joint and flank keys');keys.animation_data.action=action;keys.animation_data.action_slot=slot
    for frame in range(151):
        set_frame(scene,frame)
        for (name,_),weight in zip(STATES,weights(frame)):
            key=keys.key_blocks[name];key.value=weight;key.keyframe_insert('value',frame=frame+1)
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for curve in bag.fcurves:
                    for point in curve.keyframe_points:point.interpolation='LINEAR'
    assert len(bpy.data.actions)==1
    set_frame(scene,0)
    return {'method':'Three state keys: exact native original-cage local joint smoothing mapped by inverse unit DQ rotation, plus one smoothly feathered posterior flank pocket per key. No global smoothing, helper, weight or Basis edit.','keys':reports,'flank_guard':{'amplitudes_m':amplitudes.tolist(),'worst_requirement':worst_requirement,'uncorrected_minimum_flank_z_m':baseline_floor,'source_bounds':'Posterior sourceY>15mm, |sourceX|40..260mm, sourceZ1.02..1.36m; full smooth feather, central40mm lumbar strip and frozen pelvic support sourceZ<1.02 excluded.','full_cycle_constraints_sampled':151,'target_floor_z':.001},'weights':'Three nonnegative partition weights [1-|s|,max(0,s),max(0,-s)]; s is sine normalized to its sampled30fps maximum and clamped. Neutral1atentry/return; pure cross targets at37.5/112.5.','action':'Exercise_0003','normal_export':'Matching NORMAL target for each POSITION target is mandatory.'}
