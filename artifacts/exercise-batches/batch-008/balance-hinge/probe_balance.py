"""Five native source volume-centroid/support witnesses; a homogeneous-skin proxy only."""
import bpy,numpy as np,json,sys
from pathlib import Path
F=Path(__file__).resolve().parent;P=F.parent/'assets/3214';bpy.ops.wm.open_mainfile(filepath=str(P/'source.blend'));b=bpy.data.objects['SK_BlenderStudioHuman'];r=bpy.data.objects['RIG_BlenderStudioHuman'];b.data.calc_loop_triangles();T=np.array([t.vertices[:]for t in b.data.loop_triangles]);R=np.array([v.co[:]for v in b.data.vertices]);out=[]
sys.path.insert(0,str(F));from balance_geometry import measure;import motion
for f in [0,20,33,108,150]:
 bpy.context.scene.frame_set(f+1);bpy.context.view_layer.update();e=b.evaluated_get(bpy.context.evaluated_depsgraph_get());me=e.to_mesh();X=np.array([v.co[:]for v in me.vertices]);e.to_mesh_clear();v=np.einsum('ij,ij->i',X[T[:,0]],np.cross(X[T[:,1]],X[T[:,2]]))/6;com=(v[:,None]*X[T].sum(1)/4).sum(0)/v.sum();side='Right' if f<75 else'Left';sgn=-1 if side=='Right'else 1;ids=np.concatenate([np.flatnonzero((((1 if side_=='Left' else -1)*R[:,0])>.12)&(R[:,2]<.012))for side_ in motion.state(f)['grounded']]);knees={s:180-np.degrees((r.pose.bones[s+'UpLeg'].head-r.pose.bones[s+'Leg'].head).angle(r.pose.bones[s+'Foot'].head-r.pose.bones[s+'Leg'].head))for s in ['Left','Right']};out.append({'balance_proxy':measure(X,T,ids),'frame':f,'homogeneous_volume_centroid_m':com.tolist(),'supportXYbounds':[X[ids,:2].min(0).tolist(),X[ids,:2].max(0).tolist()],'knee_flexion_degrees':knees})
(P/'early-balance-diagnostic.json').write_text(json.dumps(out,indent=2)+'\n');print('BALANCE',json.dumps(out))
