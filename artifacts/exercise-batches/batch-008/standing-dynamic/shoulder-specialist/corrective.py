"""Install a pose-only component into an explicitly provided local copy."""
from pathlib import Path
import bpy,numpy as np
F=Path(__file__).resolve().parent
ARCHIVE='shoulder-ownership-target.npz'
STATES=[('OwnershipRightCross',37.5),('OwnershipLeftCross',112.5)]
def values(frame,exercise):
    if exercise!='5172':return [0.,0.]
    f=frame%150;cycle=int(f//75);p=np.sin(np.pi*(f-cycle*75)/75)**2
    return [p*p if cycle%2==i else 0. for i in range(2)]
def select(body,rig,exercise):
    act=bpy.data.actions['Exercise_'+exercise];rig.animation_data.action=act;rig.animation_data.action_slot=next(s for s in act.slots if s.target_id_type=='OBJECT')
    if body.data.shape_keys:
        body.data.shape_keys.animation_data.action=act;body.data.shape_keys.animation_data.action_slot=next(s for s in act.slots if s.target_id_type=='KEY')
def install(body,rig,scene,archive_path=None):
    assert not body.data.shape_keys
    data=np.load(archive_path or F/ARCHIVE);ids=data['source_ids'];basis=np.array([v.co[:]for v in body.data.vertices],np.float32);assert np.array_equal(basis[ids],data['source_basis'])
    body.shape_key_add(name='Basis',from_mix=False)
    for k,(name,_)in enumerate(STATES):
        target=basis.copy();target[ids]+=data['rest_deltas'][k]
        key=body.shape_key_add(name=name,from_mix=False);key.data.foreach_set('co',target.ravel());key.value=0.
    keys=body.data.shape_keys;keys.animation_data_create()
    for exercise in ['5172','6014']:
        act=bpy.data.actions['Exercise_'+exercise];slot=act.slots.new(id_type='KEY',name='Pose-only shoulder ownership');keys.animation_data.action=act;keys.animation_data.action_slot=slot
        for frame in range(151):
            for(name,_),value in zip(STATES,values(frame,exercise)):
                keys.key_blocks[name].value=value;keys.key_blocks[name].keyframe_insert('value',frame=frame+1)
        for layer in act.layers:
            for strip in layer.strips:
                for bag in strip.channelbags:
                    if bag.slot_handle==slot.handle:
                        for fc in bag.fcurves:
                            for point in fc.keyframe_points:point.interpolation='LINEAR'
    select(body,rig,'5172');scene.frame_set(1)
    return data
