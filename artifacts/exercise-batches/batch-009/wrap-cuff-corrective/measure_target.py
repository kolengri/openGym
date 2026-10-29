"""Exact pair-local sparse target diagnosis, distinct from integrated acceptance."""
import sys
sys.dont_write_bytecode=True
import bpy,numpy as np,json,collections
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
F=Path(__file__).resolve().parent;sys.path.insert(0,str(F.parent.parent/'batch-008/standing-dynamic'));from self_clearance import SelfClearance
from triangle_intersection import intersect
D=np.load(F/'capture.npz');A=np.load(F/('target-position.npz'if (F/'target-position.npz').exists()else'accepted-position.npz'));R=D['rest'];P=D['positions'][-1];Q=P.copy();Q[A['source_ids']]=A['posed_target'];names=json.loads((F/'capture.json').read_text())['bones'];W=D['weights'];bpy.ops.wm.open_mainfile(filepath=str(F/'inputs-contact/source.blend'));b=bpy.data.objects['SK_BlenderStudioHuman'];r=bpy.data.objects['RIG_BlenderStudioHuman'];clear=SelfClearance(b,r);rows={};mask=np.zeros(len(R));mask[A['source_ids']]=A['mask']
for label,AA,BB in [('arms',clear.arm['Left'],clear.arm['Right']),('Ltorso',clear.distal['Left'],clear.torso),('Rtorso',clear.distal['Right'],clear.torso)]:
 pairs=[];v=[Vector(q)for q in Q];ab=BVHTree.FromPolygons(v,AA,all_triangles=True);bb=BVHTree.FromPolygons(v,BB,all_triangles=True)
 for ai,bi in ab.overlap(bb):
  a,bt=AA[ai],BB[bi]
  if set(a)&set(bt)or not intersect([v[i]for i in a],[v[i]for i in bt]):continue
  pairs.append({'a':a,'b':bt,'owners':[[names[W[i].argmax()]for i in tri]for tri in [a,bt]],'source':[[R[i].astype(float).tolist()for i in tri]for tri in [a,bt]],'target':[[Q[i].astype(float).tolist()for i in tri]for tri in [a,bt]],'mask':[[float(mask[i])for i in tri]for tri in [a,bt]]})
 rows[label]=pairs;print(label,len(pairs),collections.Counter('/'.join(collections.Counter(p['owners'][j]).most_common(1)[0][0]for j in [0,1])for p in pairs))
(F/'target-crossings.json').write_text(json.dumps(rows,indent=2)+'\n')

np.savez_compressed(F/'clearance-domains.npz',left_arm=np.array(clear.arm['Left']),right_arm=np.array(clear.arm['Right']),left_distal=np.array(clear.distal['Left']),right_distal=np.array(clear.distal['Right']),torso=np.array(clear.torso))
