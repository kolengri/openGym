"""Independent native/linear surface and topology checks; no source mutation."""
import bpy,sys,json,hashlib,math
from pathlib import Path
import numpy as np
P=Path(__file__).resolve().parent
sys.path.insert(0,str(P.parents[1]));import authoring as a
bpy.ops.wm.open_mainfile(filepath=str(P/'source.blend'))
body=bpy.data.objects['SK_BlenderStudioHuman'];rig=bpy.data.objects['RIG_BlenderStudioHuman'];scene=bpy.context.scene
assert a.binding_hash(body,rig)=='227ede3fc31d1a2b47ff40f20a4a7288fe7bb36179add23bae953993826c8b7b'
R=np.array([v.co for v in body.data.vertices]);N=len(R)
# Interpolated rest positions identify the same physical patch on the native
# subdivided skin, independently of original cage vertex identity.
attr=body.data.attributes.new('_QA_REST','FLOAT_VECTOR','POINT');attr.data.foreach_set('vector',R.astype(np.float32).ravel())
mods=[(m,m.show_viewport,m.show_render) for m in body.modifiers]
def get_skin(f,path):
 for m,v,r in mods:m.show_viewport=v if path=='native' else m.type=='ARMATURE'
 scene.frame_set(f+1);bpy.context.view_layer.update()
 ob=body.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ob.to_mesh()
 xyz=np.array([ob.matrix_world@v.co for v in me.vertices]);rest=np.empty(len(me.vertices)*3,np.float32);me.attributes['_QA_REST'].data.foreach_get('vector',rest);rest=rest.reshape(-1,3)
 me.calc_loop_triangles();tri=np.array([t.vertices for t in me.loop_triangles]);ob.to_mesh_clear()
 return xyz,rest,tri
base,_r,_t=get_skin(0,'linear')
sem={
 'opposite_hip':(R[:,0]<-.025)&(R[:,0]>-.17)&(R[:,2]>.83)&(R[:,2]<1.03)&(R[:,1]>.07),
 'lumbar_contour':(abs(R[:,0])<.10)&(R[:,2]>1.04)&(R[:,2]<1.18)&(R[:,1]>.05),
 'upper_back':(abs(R[:,0])<.20)&(R[:,2]>1.22)&(R[:,2]<1.46)&(R[:,1]>.05),
 'occiput':(abs(R[:,0])<.12)&(R[:,2]>1.58)&(R[:,1]>.04),
}
for side,sg in [('L',1),('R',-1)]:
 sem['back_of_hand_'+side]=(sg*R[:,0]>.37)&(R[:,2]>.68)&(R[:,2]<.97)
 sem['foot_'+side]=(sg*R[:,0]>.13)&(R[:,2]<.18)
centers={}
for n,mask in sem.items():
 ids=np.where(mask)[0];idx=ids[np.argmin(base[ids,2])];centers[n]=R[idx]
peak_xyz,_,_=get_skin(75,'linear')
opp_ids=np.where(sem['opposite_hip'])[0]
peak_center=R[opp_ids[np.argmin(peak_xyz[opp_ids,2])]]
centers['opposite_hip']=(centers['opposite_hip']+peak_center)*.5
TOL={'floor_penetration_m':.004,'support_gap_m':.012,'maximum_lumbar_contour_clearance_m':.025,'near_distance_m':.020,'minimum_near_fraction':.20,'static_patch_tangential_drift_m':.025,'linear_native_contact_gap_difference_m':.012}
rows=[];refs=[];fail=[];motion=[];first={};loop={};bounds=[]
# Thirty-one samples cover both entry/return arcs and the whole hold.
for f in ([0,30,60,75,90,120,150] if '--repair' in sys.argv else range(0,151,5)):
 linear,_,_=get_skin(f,'linear')
 # A foot rolls/slides during flexion. Its actual floor patch transitions from
 # posterior heel to the external foot border; record the phase's real indices.
 phase_centers=centers.copy()
 for n in ['foot_L','foot_R']:
  ids=np.where(sem[n])[0];idx=ids[np.argmin(linear[ids,2])];phase_centers[n]=R[idx]
 patches={n:np.where(mask&(np.linalg.norm(R-phase_centers[n],axis=1)<(.050 if n=='opposite_hip' else .032)))[0] for n,mask in sem.items()}
 ref={'id':'1906','frame':f,'global_floor_z':float(linear[:,2].min()),'patches':{}}
 for path in ['native','linear']:
  xyz,rest,tri=get_skin(f,path);c={};bounds.append(xyz)
  for n,ids in patches.items():
   if path=='linear': selected=ids
   else:
    # Dense native samples within 12mm of the exact original patch coordinates.
    distance=np.min(np.linalg.norm(rest[:,None,:]-R[ids][None,:,:],axis=2),axis=1)
    selected=np.where(distance<.012)[0]
   z=xyz[selected,2];near=(z>=-TOL['floor_penetration_m'])&(z<=TOL['near_distance_m'])
   selected_mask=np.zeros(len(xyz),bool);selected_mask[selected]=True
   face_ids=np.where(np.all(selected_mask[tri],axis=1))[0]
   areas=np.linalg.norm(np.cross(xyz[tri[face_ids,1]]-xyz[tri[face_ids,0]],xyz[tri[face_ids,2]]-xyz[tri[face_ids,0]]),axis=1)*.5
   nearfaces=np.all(np.abs(xyz[tri[face_ids],2])<=TOL['near_distance_m'],axis=1)
   key=(path,n);centroid=xyz[selected].mean(axis=0)
   if key not in first:first[key]=centroid
   drift=float(np.linalg.norm((centroid-first[key])[:2]))
   c[n]={'count':len(selected),'min_z':float(z.min()),'max_z':float(z.max()),'mean_z':float(z.mean()),'near_fraction':float(near.mean()),'surface_area_m2':float(areas.sum()),'near_area_m2':float(areas[nearfaces].sum()),'tangential_drift_m':drift}
   gap_limit=TOL['maximum_lumbar_contour_clearance_m'] if n=='lumbar_contour' else TOL['support_gap_m']
   if z.min()>gap_limit or near.mean()<TOL['minimum_near_fraction']:fail.append(f'{path} frame{f} {n} support gap/fraction')
   if n not in ['foot_L'] and drift>.025:fail.append(f'{path} frame{f} {n} tangential drift')
   if path=='linear':ref['patches'][n]={'indices':ids.tolist(),'min_z':float(z.min()),'max_z':float(z.max())}
  rows.append({'id':'1906','frame':f,'path':path,'global_floor_z':float(xyz[:,2].min()),'patches':c})
  if xyz[:,2].min() < -TOL['floor_penetration_m']:fail.append(f'{path} frame{f} floor penetration')
  if path=='linear' and f in [0,150]:loop[f]=xyz
 refs.append(ref)
 hip=rig.pose.bones['Hips'];l=rig.pose.bones['LeftUpLeg'];k=rig.pose.bones['LeftLeg'];foot=rig.pose.bones['LeftFoot']
 right=rig.pose.bones['RightUpLeg'];rk=rig.pose.bones['RightLeg'];rf=rig.pose.bones['RightFoot']
 motion.append({'frame':f,'left_knee_internal_degrees':math.degrees((l.head-k.head).angle(foot.head-k.head)),'right_knee_internal_degrees':math.degrees((right.head-rk.head).angle(rf.head-rk.head)),'pelvis_head':list(hip.head),'pelvis_quaternion':list(hip.matrix.to_quaternion())})
for m,v,r in mods:m.show_viewport=v;m.show_render=r
assert max(np.linalg.norm(loop[0]-loop[150],axis=1))<1e-6
# Native and linear topology QA use the installed mandatory gate.
sys.path.insert(0,str(Path.home()/'.codex/skills/blender-asset-qa/scripts'));import qa_check
qa=[]
for path in ['native','linear']:
 for f in ([75] if '--repair' in sys.argv else [0,75]):
  for m,v,r in mods:m.show_viewport=v if path=='native' else m.type=='ARMATURE'
  scene.frame_set(f+1);bpy.context.view_layer.update()
  q=qa_check.run(objects=[body.name],profile='game')
  qa.append({'path':path,'frame':f,'qa':q})
  if not q['pass']:fail.append(f'{path} frame{f} asset QA errors: {q["errors"]}')
sha=hashlib.sha256((P/'source.blend').read_bytes()).hexdigest()
(P/'asset-qa.json').write_text(json.dumps({'source_sha256':sha,'pass':all(q['qa']['pass'] for q in qa),'checks':qa},indent=2)+'\n')
(P/'runtime-surface-reference.json').write_text(json.dumps({'source_sha256':sha,'source_vertices':N,'coordinate_frame':'Blender world metres; original cage SOURCE_INDEX','samples':refs},separators=(',',':'))+'\n')
report={'ok':not fail,'source_sha256':sha,'binding_hash':a.binding_hash(body,rig),'tolerances':TOL,'tolerance_basis':'Declared authored approximation at 1.8m scale. Curved soft-skin supports use a 12mm closest-gap band and 4mm maximum penetration. Lumbar contour clearance is separately limited to25mm; it is not flattened to the floor. No continuous collision or clinical guarantee. Lumbar contour remains anatomically curved.','patch_definition':'Coherent 32mm rest-space neighborhoods (50mm opposite glute centered between start/hold low sites) on actual original-index skin; dense native patch uses interpolated rest coordinates within12mm of that neighborhood. Foot patch follows the actual heel-to-outer-border transition. Fixed support drift is measured from start.','paths':{'native':'Original Armature + JointSurfaceCorrective + Multires1','linear':'Original Armature only, actual glTF skin target'},'failures':fail,'loop_max_vertex_error_m':float(np.max(np.linalg.norm(loop[0]-loop[150],axis=1))),'motion':motion,'samples':rows}
(P/'surface-contact-report.json').write_text(json.dumps(report,indent=2)+'\n')
# Full linear original-index vertices make the exported LBS comparison independent.
verts=[]
for f in [0,15,30,45,60,75,90,105,120,135,150]:
 xyz,_,_=get_skin(f,'linear');verts.append({'frame':f,'vertices':xyz.tolist()})
(P/'linear-vertex-reference.json').write_text(json.dumps(verts,separators=(',',':'))+'\n')
print(json.dumps({'ok':not fail,'failures':fail,'samples':len(rows),'qa':len(qa)}))
