"""Three compact source-bound DQ keys; no native/runtime smoothing mismatch."""
import bpy,math,numpy as np
from mathutils import Quaternion,Vector

STATES=[('LocalStart',0),('LocalEntry',30),('LocalHold',75)]

def points(body):
    obj=body.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=obj.to_mesh()
    values=np.array([v.co[:]for v in mesh.vertices]);obj.to_mesh_clear();return values

def feather(value,inner,outer):
    u=np.clip((np.asarray(value)-inner)/(outer-inner),0,1)
    return 1-u*u*(3-2*u)

def rotation(body,rig,index,rest):
    terms=[(g.weight,(rig.pose.bones[body.vertex_groups[g.group].name].matrix@rest[body.vertex_groups[g.group].name].inverted()).to_quaternion())for g in body.data.vertices[index].groups if g.weight>1e-8]
    reference=max(terms,key=lambda item:item[0])[1];value=np.zeros(4)
    for weight,q in terms:value+=np.array(q)*weight*(-1 if q.dot(reference)<0 else 1)
    q=Quaternion(value);q.normalize();return q

def install(body,rig,scene,action,amount):
    original=np.array([v.co[:]for v in body.data.vertices]);rest={b.name:b.matrix_local.copy()for b in rig.data.bones}
    x,y,z=original.T
    waist=feather(-z,-.92,-.84)*feather(z,1.14,1.24)*feather(abs(x),.20,.25)*feather(y,.05,.13)
    mask=waist.copy()
    for side in ['Left','Right']:
        for bone,radii in [(side+'Arm',(.18,.18,.22)),(side+'Leg',(.13,.16,.17))]:
            centre=np.array(rig.data.bones[bone].head_local)
            local=feather(np.linalg.norm((original-centre)/np.array(radii),axis=1),.45,1)
            if bone.endswith('Arm'):local*=feather(-abs(x),-.12,-.08)
            mask=np.maximum(mask,local)
    # Retain65% of the stronger diagnostic target to preserve joint volume.
    mask*=.65
    deltas=[];reports=[]
    for name,frame in STATES:
        scene.frame_set(frame+1);bpy.context.view_layer.update()
        for mod in body.modifiers:mod.show_viewport=mod.show_render=mod.type=='ARMATURE'
        bpy.context.view_layer.update();base=points(body)
        for mod in body.modifiers:
            if mod.type=='CORRECTIVE_SMOOTH':
                mod.factor=1;mod.iterations=30;mod.show_viewport=mod.show_render=True
        bpy.context.view_layer.update();target=points(body)
        delta=np.zeros_like(original);world=(target-base)*mask[:,None]
        raw_lengths=np.linalg.norm(world,axis=1)
        # A smooth45mm displacement cap retains local detail without the
        # diagnostic target's knee/shoulder over-correction.
        world*=np.divide(.045*np.tanh(raw_lengths/.045),raw_lengths,out=np.ones_like(raw_lengths),where=raw_lengths>1e-12)[:,None]
        lengths=np.linalg.norm(world,axis=1)
        assert lengths.max()<.05,('Excessive local correction',name,float(lengths.max()),int(lengths.argmax()),original[int(lengths.argmax())].tolist(),float(waist[int(lengths.argmax())]))
        for index in np.flatnonzero(lengths>1e-8):delta[index]=rotation(body,rig,int(index),rest).inverted()@Vector(world[index])
        deltas.append(delta)
        reports.append({'name':name,'frame':frame,'changed_original_ids':np.flatnonzero(lengths>1e-8).tolist(),'diagnostic_maximum_before_cap_m':float(raw_lengths.max()),'maximum_rest_delta_m':float(np.linalg.norm(delta,axis=1).max()),'outside_mask_max_delta_m':float(np.linalg.norm(delta[mask==0],axis=1).max())})
        for mod in body.modifiers:mod.show_viewport=mod.show_render=mod.type=='ARMATURE'
        bpy.context.view_layer.update()
    body.shape_key_add(name='Basis',from_mix=False)
    for (name,frame),delta in zip(STATES,deltas):
        key=body.shape_key_add(name=name,from_mix=False);key.data.foreach_set('co',(original+delta).astype(np.float32).ravel());key.value=0
    assert np.array_equal(original,np.array([v.co[:]for v in body.data.vertices]))
    keys=body.data.shape_keys;keys.animation_data_create();slot=action.slots.new(id_type='KEY',name='Compact source-bound pose keys');keys.animation_data.action=action;keys.animation_data.action_slot=slot
    for f in range(151):
        scene.frame_set(f+1);u=amount(f/30)
        weights=[max(0,1-2*u),1-abs(2*u-1),max(0,2*u-1)]
        for (name,_),w in zip(STATES,weights):
            key=keys.key_blocks[name];key.value=w;key.keyframe_insert('value',frame=f+1)
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for fc in bag.fcurves:
                    for k in fc.keyframe_points:k.interpolation='LINEAR'
    scene.frame_set(1);bpy.context.view_layer.update()
    return {'method':'Three compact original-cage CorrectiveSmooth diagnostic targets mapped by inverse unit DQ rotation. Only65% diagnostic strength retained with smooth45mm tanh displacement cap. Only waist, knees and shoulder neighborhoods retained. No subdivision, floor guard, topology or Basis change. Native smoothing disabled in delivered source/export.','target_modifier':{'type':'CORRECTIVE_SMOOTH','factor':1,'iterations':30,'rest_source':'ORCO'},'source_domains':{'waist':'source Z0.84..1.24m, |X|<0.25m, full feather; plateauZ0.92..1.14,|X|<0.20; posteriorY>0.13m exactly excluded, featherY0.05..0.13m','joints':'ellipsoidal knees radii[0.13,0.16,0.17]m and shoulders[0.18,0.18,0.22]m, shoulder central|X|<0.08 excluded'},'keys':reports,'mask_original_ids':np.flatnonzero(mask>0).tolist(),'outside_domain_exact':all(r['outside_mask_max_delta_m']==0 for r in reports),'weights':'Nonnegative partition [max(0,1-2u),1-|2u-1|,max(0,2u-1)] for authored smooth entry/return u; one shared action slot.'}
