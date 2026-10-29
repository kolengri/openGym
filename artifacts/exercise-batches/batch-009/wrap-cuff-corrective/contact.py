"""Measure the held palm/upper-back relation and immutable contact handles."""
import sys
sys.dont_write_bytecode=True
import bpy,numpy as np,json
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
F=Path(__file__).resolve().parent;OLD=F.parent.parent/'batch-008/standing-dynamic';sys.path.insert(0,str(OLD));from self_clearance import SelfClearance
D=np.load(F/'capture.npz');R=D['rest'];T=D['triangles'];W=D['weights'];names=json.loads((F/'capture.json').read_text())['bones'];bpy.ops.wm.open_mainfile(filepath=str(F/'inputs-contact/source.blend'));b=bpy.data.objects['SK_BlenderStudioHuman'];r=bpy.data.objects['RIG_BlenderStudioHuman'];s=bpy.context.scene;act=bpy.data.actions['Exercise_3995'];r.animation_data.action=act;r.animation_data.action_slot=next(x for x in act.slots if x.target_id_type=='OBJECT');keys=b.data.shape_keys;keys.animation_data.action=act;keys.animation_data.action_slot=next(x for x in act.slots if x.target_id_type=='KEY');s.frame_set(38,subframe=.5);bpy.context.view_layer.update();P=D['positions'][-1];v=[Vector(q)for q in P];rows=[];seeds=set()
for side,sign in [('Left',1),('Right',-1)]:
 local=np.array([r.data.bones[side+'Hand'].matrix_local.inverted()@Vector(q)for q in R]);palmids=np.flatnonzero((W[:,names.index(side+'Hand')]>.5)&(local[:,1]>.025)&(local[:,1]<.125)&(-sign*local[:,0]>.002));back=(R[:,1]>.045)&(R[:,2]>1.20)&(R[:,2]<1.58)&(abs(R[:,0])>.07)&(abs(R[:,0])<.28)&(sign*R[:,0]<0);tris=T[np.all(back[T],axis=1)].tolist();bt=BVHTree.FromPolygons(v,tris,all_triangles=True);normal=r.pose.bones[side+'Hand'].matrix.to_quaternion()@Vector((-sign,0,0));hits=[]
 for i in palmids:
  loc,norm,ti,dist=bt.find_nearest(v[i]);signed=float((v[i]-loc).dot(norm));hits.append({'palm_source_id':int(i),'body_source_triangle':tris[ti],'palm_point':list(v[i]),'body_point':list(loc),'unsigned_distance_m':dist,'signed_distance_m':signed,'normal_dot':normal.dot(norm)})
 hits.sort(key=lambda h:h['unsigned_distance_m']);closest=hits[:8]
 for h in hits:
  if h['unsigned_distance_m']<.015 and h['normal_dot']<-.5:seeds.update(h['body_source_triangle'])
 skin_normal=D['normals'][-1][hits[0]['palm_source_id']];body_normal=D['normals'][-1][hits[0]['body_source_triangle']].mean(0);body_normal/=np.linalg.norm(body_normal)
 rows.append({'actual_palm_skin_normal':skin_normal.tolist(),'coherent_body_vertex_normal':body_normal.tolist(),'coherent_skin_normal_dot':float(skin_normal@body_normal),'side':side,'palm_source_ids':palmids.tolist(),'minimum_distance_m':hits[0]['unsigned_distance_m'],'median_distance_m':float(np.median([h['unsigned_distance_m']for h in hits])),'negative_signed_vertices':sum(h['signed_distance_m']<-.001 for h in hits),'closest':closest})
clear=SelfClearance(b,r);metrics,fail=clear.sample(P)
(F/'held-contact.json').write_text(json.dumps({'frame':37.5,'contact_patch_semantics':'Opposite-side posterior-origin source upper-back/deltoid patch: rest y>.045,z1.20..1.58,absx.07...28. Also report actual posed points/normals; source-patch membership alone is not posterior-world proof.','palms':rows,'protected_body_contact_seed_source_ids':sorted(seeds),'clearance':metrics,'clearance_failures':fail},indent=2)+'\n');print('CONTACT',[(q['side'],q['minimum_distance_m'],q['median_distance_m'],q['negative_signed_vertices'])for q in rows],'SEEDS',len(seeds),'CROSSINGS',fail)
