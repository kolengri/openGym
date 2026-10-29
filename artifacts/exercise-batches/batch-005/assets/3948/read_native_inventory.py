"""Read the frozen source without modifying its state on disk."""
from pathlib import Path
import bpy,numpy as np,json,hashlib
P=Path(__file__).resolve().parent;bpy.ops.wm.open_mainfile(filepath=str(P/'source.blend'));b=bpy.data.objects['SK_BlenderStudioHuman'];r=bpy.data.objects['RIG_BlenderStudioHuman'];s=bpy.context.scene
rows=[]
for f in [0,37,75]:
 s.frame_set(f+1);bpy.context.view_layer.update();ev=b.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh();X=np.array([ev.matrix_world@v.co for v in me.vertices]);ev.to_mesh_clear();rows.append({'frame':f,'dimensions_xyz_m':np.ptp(X,axis=0).tolist(),'bounds':[X.min(0).tolist(),X.max(0).tolist()],'active_native_bone_action':r.animation_data.action.name,'active_native_key_action':b.data.shape_keys.animation_data.action.name,'key_values':{k.name:k.value for k in b.data.shape_keys.key_blocks if k.name!='Basis'}})
assert r.animation_data.action.name=='Exercise_3948' and b.data.shape_keys.animation_data.action.name=='Exercise_3948'
channels={}
for act in bpy.data.actions:
 curves=[]
 for layer in act.layers:
  for strip in layer.strips:
   for bag in strip.channelbags:
    for fc in bag.fcurves:curves.append((fc.data_path,fc.array_index,[(float(k.co.x),float(k.co.y)) for k in fc.keyframe_points]))
 channels[act.name]=sorted(curves)
assert channels['Exercise_3948']==channels['Exercise_4714']
report={'source_sha256':hashlib.sha256((P/'source.blend').read_bytes()).hexdigest(),'blender':bpy.app.version_string,'source_vertices':len(b.data.vertices),'source_faces':len(b.data.polygons),'source_triangles':21160,'bones':len(r.data.bones),'materials':len(b.data.materials),'actions':sorted(channels),'native_action_channels_identical':True,'channels_per_action':{k:len(v) for k,v in channels.items()},'key_names':list(b.data.shape_keys.key_blocks.keys()),'maximum_influences':max(len(v.groups) for v in b.data.vertices),'maximum_weight_error':max(abs(sum(g.weight for g in v.groups)-1) for v in b.data.vertices),'native_armature_only':all(m.show_viewport==(m.type=='ARMATURE') and m.show_render==(m.type=='ARMATURE') for m in b.modifiers),'modifiers':[{'name':m.name,'type':m.type,'enabled':m.show_viewport} for m in b.modifiers],'samples':rows};(P/'native-inventory.json').write_text(json.dumps(report,indent=2)+'\n');assert report['native_armature_only']
