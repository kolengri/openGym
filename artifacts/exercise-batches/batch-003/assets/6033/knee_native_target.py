"""Original cage CorrectiveSmooth target over complete local knee neighborhoods."""
import bpy
import numpy as np
MAX_LOCAL_DISPLACEMENT_M=.030

def coordinates(body):
    bpy.context.view_layer.update()
    evaluated=body.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh=evaluated.to_mesh()
    result=np.array([v.co[:] for v in mesh.vertices])
    evaluated.to_mesh_clear()
    return result

def local_mask(body,rig):
    rest=np.array([v.co[:] for v in body.data.vertices]);mask=np.zeros(len(rest))
    def feather(values,inner,outer):
        t=np.clip((np.abs(values)-inner)/(outer-inner),0,1)
        return 1-t*t*(3-2*t)
    for side in ['Left','Right']:
        knee=rig.data.bones[side+'Leg'].head_local
        # Full circumference: no anterior/outside test, and no dome term.
        side_mask=feather(rest[:,0]-knee.x,.085,.125)*feather(rest[:,2]-knee.z,.065,.15)
        mask=np.maximum(mask,side_mask)
    return mask

def capture(body,rig):
    saved=[(m,m.show_viewport,m.show_render) for m in body.modifiers]
    arm=next(m for m in body.modifiers if m.type=='ARMATURE')
    original_volume=arm.use_deform_preserve_volume
    try:
        arm.use_deform_preserve_volume=True
        for m,_,_ in saved:m.show_viewport=m.show_render=m.type=='ARMATURE'
        base=coordinates(body)
        for m,_,_ in saved:m.show_viewport=m.show_render=m.type in ['ARMATURE','CORRECTIVE_SMOOTH']
        native=coordinates(body)
        assert len(base)==len(native)==len(body.data.vertices)==10582
        mask=local_mask(body,rig)
        delta=(native-base)*mask[:,None]
        maximum=float(np.linalg.norm(delta,axis=1).max())
        assert maximum<=MAX_LOCAL_DISPLACEMENT_M+1e-7,maximum
        return base,base+delta,mask,{
            'method':'Exact original-cage CorrectiveSmooth displacement over the complete local knee circumference, smoothly feathered into thigh/calf. No outside-bisector exclusion or dome term.',
            'maximum_displacement_m':maximum,'authorized_bound_m':MAX_LOCAL_DISPLACEMENT_M,
            'changed_original_vertex_ids':np.flatnonzero(np.linalg.norm(delta,axis=1)>1e-8).tolist(),
            'core':'Full local knee circumference, sourceZ within65mm of the rest knee and sourceX within85mm; smooth falloff to150/125mm respectively.',
            'non_armature_target_modifiers':['CORRECTIVE_SMOOTH'],'subdivision_used':False}
    finally:
        arm.use_deform_preserve_volume=original_volume
        for m,viewport,render in saved:m.show_viewport,m.show_render=viewport,render
        bpy.context.view_layer.update()
