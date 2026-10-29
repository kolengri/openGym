"""Source-ID skin contact evidence for local pose decisions; not grasp acceptance."""
import bpy,sys,numpy as np,json
from pathlib import Path
sys.dont_write_bytecode=True
from mathutils import Vector
from mathutils.bvhtree import BVHTree
F=Path(__file__).resolve().parent;sys.path[:0]=[str(F),str(F.parent.parent/'batch-003')];import authoring as a
a.initialize();source=np.array([v.co[:]for v in a.body.data.vertices]);norm=np.array([v.normal[:]for v in a.body.data.vertices]);b=a.body;r=a.rig;gn={g.index:g.name for g in b.vertex_groups}
def ids(prefix):return np.array([v.index for v in b.data.vertices if sum(g.weight for g in v.groups if any(gn[g.group].startswith(n)for n in prefix))>.7],int)
parts={s+'_arm':ids([s+p for p in['Arm','ForeArm','Hand','Index','Middle','Ring','Little','Thumb']])for s in['Left','Right']}
for s,sign in [('Left',1),('Right',-1)]:
 parts[s+'_palm']=np.array([i for i in ids([s+'Hand'])if .88<source[i,2]<.94 and -sign*norm[i,0]>.4]);parts[s+'_hand']=ids([s+'Hand',s+'Index',s+'Middle',s+'Ring',s+'Little',s+'Thumb']);parts[s+'_digits']=ids([s+'Index',s+'Middle',s+'Ring',s+'Little',s+'Thumb'])
parts['Left_palm']=np.array(json.loads((F/'native-back-contact-solve.json').read_text())['palm_ids']);parts['back']=np.flatnonzero((abs(source[:,0])<.28)&(source[:,1]>.025)&(source[:,2]>1.15)&(source[:,2]<1.51));parts['head']=np.flatnonzero((source[:,2]>1.54)&(abs(source[:,0])<.17))
for ID in['1987','1986']:
 P=F.parent/'assets'/ID;bpy.ops.wm.open_mainfile(filepath=str(P/'source.blend'));b=bpy.data.objects['SK_BlenderStudioHuman'];r=bpy.data.objects['RIG_BlenderStudioHuman'];s=bpy.context.scene;r.animation_data.action=bpy.data.actions['Exercise_'+ID];r.animation_data.action_slot=r.animation_data.action.slots[0];b.data.calc_loop_triangles();tri=np.array([t.vertices[:]for t in b.data.loop_triangles]);rows=[]
 for frame in[30,45,60,75,105,120]:
  s.frame_set(frame+1);bpy.context.view_layer.update();ev=b.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh();xyz=np.array([v.co[:]for v in me.vertices]);ev.to_mesh_clear();vec=[Vector(p)for p in xyz];trees={k:BVHTree.FromPolygons(vec,tri[np.all(np.isin(tri,ids),axis=1)].tolist())for k,ids in parts.items()if k in['Left_arm','Right_arm','back','head']};row={'frame':frame,'joints':{n:list(r.pose.bones[n].head)for n in['LeftArm','LeftForeArm','LeftHand','RightArm','RightForeArm','RightHand']}}
  for hand,target in[('Left_palm','back'),('Left_hand','back'),('Left_digits','back'),('Left_hand','head'),('Right_palm','Left_arm'),('Right_digits','Left_arm'),('Right_hand','head')]:
   near=[]
   for i in parts[hand]:
    q,n,face,dist=trees[target].find_nearest(vec[i]);near.append((dist,float((vec[i]-q).dot(n)),int(i),list(xyz[i]),list(q)))
   near.sort();row[hand+'_to_'+target]={'minimum':near[0],'min_close_signed_distance_m':min([n[1]for n in near if n[0]<.04],default=None),'median_distance_m':float(np.median([n[0]for n in near])),'ids_over4mm_inside_within40mm':[n[2]for n in near if n[0]<.04 and n[1]<-.004],'closest5':near[:5]}
  rows.append(row)
 (P/'contact-diagnosis.json').write_text(json.dumps({'patches':{k:v.tolist()for k,v in parts.items()},'samples':rows},indent=2)+'\n');print(ID,json.dumps(rows[3]))
