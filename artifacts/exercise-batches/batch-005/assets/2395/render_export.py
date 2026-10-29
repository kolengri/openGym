"""Curated actual exported-DQ geometry views; Three normals are tested separately."""
import json,sys,hashlib
import numpy as np
from pathlib import Path
import bpy
from mathutils import Vector
P=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P/'source.blend'))
scene=bpy.context.scene;source_mode='--source' in sys.argv
if not source_mode:
    for object in list(bpy.data.objects):
        if object.type in ['MESH','ARMATURE']:bpy.data.objects.remove(object,do_unlink=True)
    for action in list(bpy.data.actions):bpy.data.actions.remove(action)
    scene.render.fps=30;bpy.ops.import_scene.gltf(filepath=str(P/'motion.glb'))
for object in bpy.data.objects:
    if object.type!='MESH':continue
    for modifier in object.modifiers:
        modifier.show_viewport=modifier.show_render=modifier.type=='ARMATURE'
        if modifier.type=='ARMATURE':modifier.use_deform_preserve_volume=True
cameras=json.loads((P/'cameras.json').read_text());cameras.append({'label':'review-rear','position':[2.8,.6,-3.2],'target':[0,.05,.3],'scale':2.35});camera=scene.camera
scene.display.shading.show_shadows=False;scene.display.shading.show_cavity=False;scene.display.shading.show_specular_highlight=False
phases=[(0,'start-side',1),(12.5,'blend-oblique',0),(37.5,'right-cross-oblique',0),(112.5,'left-cross-oblique',0),(150,'return-side',1)]
if '--blend-only' in sys.argv:phases=[(12.5,'blend-oblique',0)]
if '--rear-only' in sys.argv:phases=[(0,'start-rear',2),(37.5,'right-cross-rear',2)]
if '--with-details' in sys.argv:phases += [(37.5,'right-cross-armpit',0),(112.5,'left-cross-armpit',0)]
receipts=[]
if '--rear-only' in sys.argv and (P/'render-readback.json').exists():receipts=[r for r in json.loads((P/'render-readback.json').read_text())['samples']if r['file']not in ['exported-dq-start-rear.png','exported-dq-right-cross-rear.png']]
def surface_snapshot():
    result={}
    for obj in bpy.data.objects:
        if obj.type!='MESH':continue
        ev=obj.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=ev.to_mesh();result[obj.name]=np.array([v.co[:]for v in mesh.vertices]);ev.to_mesh_clear()
    return result
for frame,label,view_index in phases:
    view=cameras[view_index];camera.location=view['position'];camera.rotation_euler=(Vector(view['target'])-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.ortho_scale=view['scale']
    scene.frame_set(int(frame)+(1 if source_mode else 0),subframe=frame%1);bpy.context.view_layer.update()
    if label.endswith('armpit'):
        rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');target=rig.matrix_world@((rig.pose.bones['LeftArm'].head+rig.pose.bones['RightArm'].head+rig.pose.bones['Spine1'].head)/3)
        direction=(Vector(view['position'])-Vector(view['target'])).normalized();camera.location=target+direction*5;camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.ortho_scale=1.05
    prefix='dq-cage'if source_mode else'exported-dq'
    scene.render.filepath=str(P/f'{prefix}-{label}.png')
    before=surface_snapshot()
    if frame==phases[0][0]:bpy.ops.render.render(write_still=False)
    bpy.ops.render.render(write_still=True)
    after=surface_snapshot();delta=max(float(np.max(abs(before[name]-after[name])))for name in before);assert delta<1e-8,delta
    receipts.append({'frame':frame,'file':Path(scene.render.filepath).name,'maximum_pre_post_render_surface_delta_m':delta})
(P/'render-readback.json').write_text(json.dumps({'id':'2395','source_sha256':hashlib.sha256((P/'source.blend').read_bytes()).hexdigest(),'motion_sha256':hashlib.sha256((P/'motion.glb').read_bytes()).hexdigest(),'pass':True,'samples':receipts},indent=2)+'\n')
print('ACTUAL_EXPORTED_DQ_GEOMETRY_PROOFS_READY')
