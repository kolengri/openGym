"""Independent closest-surface witnesses for both press-palm placements."""
import bpy,json,sys,hashlib
from pathlib import Path
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
P=Path(__file__).resolve().parent;sys.path.insert(0,str(P));import candidate as c;import correctives as k
bpy.ops.wm.open_mainfile(filepath=str(P/'source.blend'));body=bpy.data.objects['SK_BlenderStudioHuman'];rig=bpy.data.objects['RIG_BlenderStudioHuman'];scene=bpy.context.scene;keys=body.data.shape_keys
names={g.index:g.name for g in body.vertex_groups};base=np.array([v.co[:] for v in body.data.vertices])
leg=set(v.index for v in body.data.vertices if any(names[g.group] in ['LeftUpLeg','LeftLeg','LeftFoot','LeftToeBase'] and g.weight>.15 for g in v.groups))
faces=[list(p.vertices) for p in body.data.polygons if all(i in leg for i in p.vertices)]
patches={}
whole_hands={side:[v.index for v in body.data.vertices if any(names[g.group].startswith(side) and any(t in names[g.group] for t in ['Hand','Thumb','Index','Middle','Ring','Little']) and g.weight>.5 for g in v.groups)] for side in ['Left','Right']}
right_set=set(whole_hands['Right']);right_faces=[list(p.vertices) for p in body.data.polygons if all(i in right_set for i in p.vertices)]
for side in ['Left','Right']:
 normal=Vector((-.895485,-.004443,-.445070)) if side=='Left' else Vector((.896018,-.003273,-.444006))
 ids=[v.index for v in body.data.vertices if any(names[g.group]==side+'Hand' and g.weight>.8 for g in v.groups)]
 values=np.array([(Vector(base[i])-rig.data.bones[side+'Hand'].head_local).dot(normal) for i in ids]);threshold=float(np.percentile(values,70));patches[side]=[i for i,value in zip(ids,values) if value>=threshold]
rows=[]
for ident in ['10565','6560']:
 for frame in range(151):
  t=frame/30
  action=bpy.data.actions['Exercise_'+ident];rig.animation_data.action=action;rig.animation_data.action_slot=next(v for v in action.slots if v.target_id_type=='OBJECT');keys.animation_data.action=action;keys.animation_data.action_slot=next(v for v in action.slots if v.target_id_type=='KEY');scene.frame_set(frame+1);co=k.sample(body);tree=BVHTree.FromPolygons([Vector(v) for v in co],faces)
  right_tree=BVHTree.FromPolygons([Vector(v) for v in co],right_faces)
  row={'id':ident,'seconds':t,'hands':{},'hand_to_hand_gap_m':min(right_tree.find_nearest(Vector(co[i]))[3] for i in whole_hands['Left'])}
  for side,ids in patches.items():
   nearest=[tree.find_nearest(Vector(co[i])) for i in ids]
   signed=[float((Vector(co[i])-hit[0]).dot(hit[1])) for i,hit in zip(ids,nearest)]
   row['hands'][side]={'patch':ids,'floor_min_z':float(co[ids,2].min()),'leg_signed_min_m':min(signed),'leg_signed_max_m':max(signed),'leg_unsigned_min_m':min(hit[3] for hit in nearest),'leg_unsigned_median_m':float(np.median([hit[3] for hit in nearest]))}
   whole_nearest=[tree.find_nearest(Vector(co[i])) for i in whole_hands[side]]
   whole_signed=[float((Vector(co[i])-hit[0]).dot(hit[1])) for i,hit in zip(whole_hands[side],whole_nearest) if hit[3]<.03]
   row['hands'][side]['whole_hand_near_leg_signed_min_m']=min(whole_signed) if whole_signed else None
   if ident=='10565' and side=='Right' and frame==50:
    detail=[]
    for i,hit in zip(whole_hands[side],whole_nearest):
     signed=float((Vector(co[i])-hit[0]).dot(hit[1]))
     if signed<-.004 and hit[3]<.04:
      up=tree.ray_cast(Vector(co[i])+Vector((0,0,.00001)),Vector((0,0,1)),.20);down=tree.ray_cast(Vector(co[i])-Vector((0,0,.00001)),Vector((0,0,-1)),.20)
      detail.append({'index':i,'position':co[i].tolist(),'rest':base[i].tolist(),'weights':{names[g.group]:g.weight for g in body.data.vertices[i].groups},'signed_m':signed,'nearest_point':list(hit[0]),'normal':list(hit[1]),'distance_m':hit[3],'ray_up_m':up[3],'ray_down_m':down[3]})
    (P/'right-hand-signed-witness.json').write_text(json.dumps(detail,indent=2)+'\n')
  rows.append(row)
(P/'hand-contact-probe.json').write_text(json.dumps(rows,indent=2)+'\n')
summary={'source_sha256':hashlib.sha256((P/'source.blend').read_bytes()).hexdigest(),'rows':len(rows),'hand_to_hand_gap_min_m':min(r['hand_to_hand_gap_m'] for r in rows),'press':{side:{'signed_min_m':min(r['hands'][side]['leg_signed_min_m'] for r in rows if r['id']=='10565'),'nearest_max_m':max(r['hands'][side]['leg_unsigned_min_m'] for r in rows if r['id']=='10565'),'whole_hand_near_leg_signed_min_m':min(r['hands'][side]['whole_hand_near_leg_signed_min_m'] for r in rows if r['id']=='10565' and r['hands'][side]['whole_hand_near_leg_signed_min_m'] is not None)} for side in ['Left','Right']}}
(P/'hand-contact-summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary))
