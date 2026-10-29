"""Check relaxed hands against the actual torso/leg skin through the clip."""
import bpy,json,numpy as np,hashlib,sys
from pathlib import Path
from mathutils.bvhtree import BVHTree
P=Path(__file__).resolve().parent;bpy.ops.wm.open_mainfile(filepath=str(P/'source.blend'));b=bpy.data.objects['SK_BlenderStudioHuman'];s=bpy.context.scene
R=np.array([v.co for v in b.data.vertices]);a=b.data.attributes.new('_QA_REST','FLOAT_VECTOR','POINT');a.data.foreach_set('vector',R.astype(np.float32).ravel());states=[(m,m.show_viewport) for m in b.modifiers];rows=[];fail=[]
for path in ['native','linear']:
 for m,state in states:m.show_viewport=state if path=='native' else m.type=='ARMATURE'
 for f in ([30,75,120] if '--repair' in sys.argv else range(0,151,5)):
  s.frame_set(f+1);bpy.context.view_layer.update();ob=b.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ob.to_mesh();xyz=[ob.matrix_world@v.co for v in me.vertices];rest=np.empty(len(xyz)*3,np.float32);me.attributes['_QA_REST'].data.foreach_get('vector',rest);rest=rest.reshape(-1,3);me.calc_loop_triangles();tri=np.array([t.vertices for t in me.loop_triangles]);main=(np.abs(rest[:,0])<.26)|(rest[:,2]<.70);maintri=tri[np.all(main[tri],axis=1)];tree=BVHTree.FromPolygons(xyz,maintri,all_triangles=True);hands={}
  for side,sign in [('L',1),('R',-1)]:
   ids=np.where((sign*rest[:,0]>.37)&(rest[:,2]>.70)&(rest[:,2]<.95))[0];distances=[];signed=[]
   for i in ids:
    co,normal,index,d=tree.find_nearest(xyz[i]);distances.append(d);signed.append((xyz[i]-co).dot(normal))
   hands[side]={'surface_samples':len(ids),'minimum_distance_m':min(distances),'minimum_signed_distance_m':min(signed),'maximum_penetration_m':max(0,-min(signed))}
   if min(signed)<-.003:fail.append(f'{path} frame{f} hand{side} body penetration')
  rows.append({'path':path,'frame':f,'hands':hands});ob.to_mesh_clear()
r={'ok':not fail,'source_sha256':hashlib.sha256((P/'source.blend').read_bytes()).hexdigest(),'maximum_permitted_penetration_m':.003,'method':'Nearest actual torso/leg triangles and their outward normals; articulated hand/finger surfaces sampled on native and linear skins at the recorded affected poses. Arm attachment surfaces excluded. No intended hand/body contact.','limitations':'Sampled nearest-surface signed-distance approximation, not continuous collision proof.','failures':fail,'samples':rows};(P/'hand-clearance-report.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'ok':r['ok'],'failures':fail,'minimum_gap_m':min(h['minimum_distance_m'] for row in rows for h in row['hands'].values())}))
