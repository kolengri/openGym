"""Diagnostic local original-cage native CorrectiveSmooth target."""
import bpy
import numpy as np


def coordinates(body):
    evaluated=body.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh=evaluated.to_mesh()
    points=np.array([v.co[:] for v in mesh.vertices])
    evaluated.to_mesh_clear()
    return points


def smooth_feather(value,inner,outer):
    t=np.clip((np.asarray(value)-inner)/(outer-inner),0,1)
    return 1-t*t*(3-2*t)


def local_mask(body,rig):
    points=np.array([v.co[:] for v in body.data.vertices]);mask=np.zeros(len(points))
    for side in ['Left','Right']:
        knee=np.array(rig.data.bones[side+'Leg'].head_local)
        delta=points-knee
        knee_mask=smooth_feather(abs(delta[:,0]),.085,.125)*smooth_feather(abs(delta[:,2]),.065,.15)
        mask=np.maximum(mask,knee_mask)
        for bone,radii in [(side+'Arm',(.15,.18,.18)),(side+'ForeArm',(.12,.13,.13))]:
            centre=np.array(rig.data.bones[bone].head_local)
            distance=np.linalg.norm((points-centre)/np.array(radii),axis=1)
            arm_mask=smooth_feather(distance,.45,1)
            # Keep central lumbar and back support entirely outside these keys.
            arm_mask*=smooth_feather(-abs(points[:,0]),-.13,-.10)
            mask=np.maximum(mask,arm_mask)
    return mask


def flank_mask(body):
    points=np.array([v.co[:]for v in body.data.vertices]);x,y,z=points.T
    # Posterior lateral lumbosacral/flank pocket. The existing central lumbar
    # arch and entire pelvic support region (sourceZ<1.02) are exactly excluded.
    return (smooth_feather(-abs(x),-.09,-.04)*smooth_feather(abs(x),.20,.26)*
            smooth_feather(-z,-1.05,-1.02)*smooth_feather(z,1.30,1.36)*
            smooth_feather(-y,-.07,-.015))


def capture(body,rig):
    flags=[(m,m.show_viewport,m.show_render)for m in body.modifiers]
    for modifier in body.modifiers:
        modifier.show_viewport=modifier.show_render=modifier.type=='ARMATURE'
        if modifier.type=='ARMATURE':modifier.use_deform_preserve_volume=True
    bpy.context.view_layer.update();base=coordinates(body)
    for modifier in body.modifiers:
        modifier.show_viewport=modifier.show_render=modifier.type in ['ARMATURE','CORRECTIVE_SMOOTH']
    bpy.context.view_layer.update();native=coordinates(body)
    assert len(base)==len(native)==10582
    mask=local_mask(body,rig);delta=(native-base)*mask[:,None]
    for modifier,viewport,render in flags:modifier.show_viewport=viewport;modifier.show_render=render
    bpy.context.view_layer.update()
    lengths=np.linalg.norm(delta,axis=1)
    maximum_id=int(lengths.argmax());bone=min([s+b for s in ['Left','Right']for b in ['Arm','ForeArm','Leg']],key=lambda name:np.linalg.norm(np.array(rig.data.bones[name].head_local)-np.array(body.data.vertices[maximum_id].co)))
    return base,base+delta,{'method':'Original-resolution native CorrectiveSmooth displacement retained only in compact whole-knee and shoulder/elbow neighborhoods. No dome, topology, weight change or global smoothing.','changed_original_vertex_ids':np.flatnonzero(lengths>1e-8).tolist(),'maximum_displacement_m':float(lengths.max()),'maximum_original_id':maximum_id,'maximum_source_coordinate':list(body.data.vertices[maximum_id].co),'maximum_nearest_source_joint':bone,'non_armature_target_modifiers':['CORRECTIVE_SMOOTH'],'subdivision_used':False}
