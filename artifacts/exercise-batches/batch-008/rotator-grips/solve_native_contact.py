"""One bounded contact solve evaluating reachable IK and actual DQ back each step."""
import bpy,sys,json,numpy as np
from pathlib import Path
sys.dont_write_bytecode=True
from mathutils import Vector
from mathutils.bvhtree import BVHTree
F=Path(__file__).resolve().parent;sys.path[:0]=[str(F),str(F.parent.parent/'batch-003'),str(F.parent.parent/'batch-007/arm-circle-family'),str(F.parents[2]/'mannequin-mpfb-prototype/local-topology-repair/dependencies/venv/lib/python3.13/site-packages')]
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation
import authoring as a
a.initialize();import motion,shoulder_binding,plantar_binding
b,r,s=a.body,a.rig,a.scene;shoulder_binding.apply(b);plantar_binding.apply(b)
for m in b.modifiers:
 m.show_viewport=m.show_render=m.type=='ARMATURE'
 if m.type=='ARMATURE':m.use_deform_preserve_volume=True
R=np.array([v.co[:]for v in b.data.vertices]);N=np.array([v.normal[:]for v in b.data.vertices]);gn={g.index:g.name for g in b.vertex_groups};hands=np.array([v.index for v in b.data.vertices if sum(g.weight for g in v.groups if gn[g.group].startswith('Left')and any(p in gn[g.group]for p in['Hand','Thumb','Index','Middle','Ring','Little']))>.7]);palm=np.array([v.index for v in b.data.vertices if sum(g.weight for g in v.groups if gn[g.group]=='LeftHand')>.95 and N[v.index,0]<-.6 and .885<v.co.z<.935]);back=(np.abs(R[:,0])<.28)&(R[:,1]>.025)&(R[:,2]>1.15)&(R[:,2]<1.51);head=(R[:,2]>1.54)&(np.abs(R[:,0])<.17);b.data.calc_loop_triangles();tri=np.array([t.vertices[:]for t in b.data.loop_triangles]);btf=tri[np.all(back[tri],axis=1)].tolist();htf=tri[np.all(head[tri],axis=1)].tolist();pi=np.array([np.flatnonzero(hands==i)[0]for i in palm]);
# Frozen initial recipe; rerunning does not depend on subsequently authored constants.
initial={'wrist_entry':[.1270622,.1404466,1.4842083],'wrist_hold':[.1270622,.1504466,1.4742083],'hand_quaternion_wxyz':[.75130967,-.33255412,-.39845048,.40765028]};wr=np.array(initial['wrist_hold']);hq=Rotation.from_quat(np.roll(initial['hand_quaternion_wxyz'],-1));s.frame_set(76)

def data(x):
 motion.OVERHEAD_WRIST_HOLD=(wr+x[:3]).tolist();motion.OVERHEAD_WRIST_ENTRY=(np.array(initial['wrist_entry'])+x[:3]).tolist();q=(Rotation.from_rotvec(x[3:])*hq).as_quat();motion.OVERHEAD_HAND_GOAL=np.roll(q,1).tolist();motion.pose(a,'1986',75);bpy.context.view_layer.update();ev=b.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh();p=np.array([v.co[:]for v in me.vertices]);ev.to_mesh_clear();vec=[Vector(q)for q in p];bt=BVHTree.FromPolygons(vec,btf);ht=BVHTree.FromPolygons(vec,htf);near=[bt.find_nearest(vec[int(i)])for i in hands];sg=np.array([(p[i]-np.array(n[0])).dot(n[1])for i,n in zip(hands,near)]);ds=np.array([n[3]for n in near]);hn=[ht.find_nearest(vec[int(i)])for i in hands];hs=np.array([(p[i]-np.array(n[0])).dot(n[1])for i,n in zip(hands,hn)]);hd=np.array([n[3]for n in hn]);return sg,ds,hs,hd

def residual(x):
 sg,ds,hs,hd=data(x);return np.r_[np.maximum(.001-sg,0)*8,np.maximum(.002-hs,0)*(hd<.04)*8,(ds[pi]-.003)*.5,x[:3]*.02,x[3:]*.001]
sol=least_squares(residual,np.array([.0001]*6),bounds=([-.04,-.02,-.035,-.26,-.26,-.26],[.04,.05,.025,.26,.26,.26]),diff_step=.02,xtol=1e-8,ftol=1e-8,gtol=1e-8,max_nfev=100)
sg,ds,hs,hd=data(sol.x);report={'method':'Single bounded least-squares contact-frame solve with reachable arm IK and reevaluated actual DQ back at every residual. Frozen explicit initial recipe. Whole-hand original skin outside1mm offset and central original palm contact objective; no mesh or binding changes.','input_pose':initial,'original_source_sha256':a.SOURCE_SHA,'palm_ids':palm.tolist(),'whole_hand_ids':hands.tolist(),'success':bool(sol.success),'evaluations':sol.nfev,'translation_delta_m':sol.x[:3].tolist(),'rotation_delta_radians':sol.x[3:].tolist(),'wrist_entry_authored_m':motion.OVERHEAD_WRIST_ENTRY,'wrist_hold_authored_m':motion.OVERHEAD_WRIST_HOLD,'hand_quaternion_wxyz':motion.OVERHEAD_HAND_GOAL,'minimum_signed_back_m':float(sg.min()),'palm_distance_min_m':float(ds[pi].min()),'palm_distance_median_m':float(np.median(ds[pi])),'minimum_signed_head_within40mm_m':float(hs[hd<.04].min())if np.any(hd<.04)else None,'cost':float(sol.cost)};(F/'native-back-contact-solve.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items()if not k.endswith('_ids')}))
