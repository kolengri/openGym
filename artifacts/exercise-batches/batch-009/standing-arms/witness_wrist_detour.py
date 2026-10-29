"""Authorized anterior wrist detour: sparse skin and bone continuity."""
from pathlib import Path
F=Path(__file__).resolve().parent
exec(compile((F/'build.py').read_text().split('soles=')[0],str(F/'build.py'),'exec'))
sys.path.insert(0,str(OLD))
from clearance_checks import SelfClearance
clear=SelfClearance(b,r);globalq=[];localq=[];parents={pb.name:pb.parent.name for pb in r.pose.bones if pb.parent};selected=[side+part for side in ['Left','Right']for part in ['Arm','ForeArm','Hand']];samples=[];geometries={};witness_frames=sorted(set(list(range(39))+[19.5,20.5,21.5,22.5,23.5,24.5,25.5,26.5,27.5,28.5,75,150]))
for frame in range(151):
 d,st=motion.pose(a,frame,'3995',foundation.pose);bpy.context.view_layer.update();globalq.append([list(r.pose.bones[n].matrix.to_quaternion())for n in selected]);localq.append([list((r.pose.bones[parents[n]].matrix.inverted()@r.pose.bones[n].matrix).to_quaternion())for n in selected])
for frame in witness_frames:
 d,st=motion.pose(a,frame,'3995',foundation.pose)
 for key,value in zip(list(b.data.shape_keys.key_blocks)[1:],motion.morph_values(frame,'3995')):key.value=value
 bpy.context.view_layer.update();e=b.evaluated_get(bpy.context.evaluated_depsgraph_get());me=e.to_mesh();v=np.asarray([x.co[:]for x in me.vertices]);e.to_mesh_clear();metrics,issues=clear.sample(v);samples.append({'frame':frame,'p':st['amount'],'anterior_wrist_offset_m':st['left_wrist_anterior_offset_m'],'metrics':metrics,'issues':issues})
 if frame in [18,21,22,23,24,37]:geometries['f'+str(frame)]=v
steps={}
for space,values in [('global',globalq),('local',localq)]:
 q=np.asarray(values,dtype=np.float64);q/=np.linalg.norm(q,axis=2)[:,:,None];angles=np.degrees(2*np.arccos(np.clip(abs((q[1:]*q[:-1]).sum(2)),0,1)));steps[space]={name:{'maximum_degrees':float(angles[:,i].max()),'frame_pair':[int(angles[:,i].argmax()),int(angles[:,i].argmax()+1)]}for i,name in enumerate(selected)}
np.savez_compressed(F/'wrist-detour-sparse.npz',**geometries);report={'motion_sha256':sha(F/'motion.py'),'route_archive_sha256':sha(F/'coherent-route-coefficients.npz'),'scope':'One conservative-plane-derived anterior wrist detour; fixed lengths, transported chain and source forearm-local hand interpolation retained. No source/model saved or full151 meshQA.','continuity':steps,'samples':samples};(F/'wrist-detour-witness.json').write_text(json.dumps(report,indent=2)+'\n');print('WRIST_DETOUR_WITNESS',json.dumps({'continuity':steps,'armarm_counts':[(x['frame'],x['metrics']['left_arm_right_arm']['exact_triangle_crossings'])for x in samples]}))
