"""Actual one-ring/Jacobian evidence for the conservative baseline-normal flag."""
from pathlib import Path
import sys,json,hashlib,math
sys.dont_write_bytecode=True
import bpy,numpy as np
from mathutils import Vector,Quaternion
from mathutils.bvhtree import BVHTree
P=Path(__file__).resolve().parent;sys.path.insert(0,str(P));import twist_motion as m
from bilateral_geometry import face_sets
a=m.prepare();d,params=m.pose(24/30);b=a.body;R=np.array([v.co[:]for v in b.data.vertices]);T,LF,RF=face_sets(b);f=17419;star=np.flatnonzero(np.any(np.isin(T,T[f]),axis=1));key=b.data.shape_keys.key_blocks['TwistHipVolume'];lead=b.data.shape_keys.key_blocks['ThighContactLead'];coords=np.array([v.co[:]for v in key.data],np.float32);kv=float(key.value);lv=float(lead.value);hip=np.load(P/'hip-volume-component.npz');hipcoords=hip['source_basis']+hip['position_delta'];modes=[]
Q=[]
for i in T[f]:
 terms=[(g.weight,(a.rig.pose.bones[b.vertex_groups[g.group].name].matrix@a.rest[b.vertex_groups[g.group].name].inverted()).to_quaternion())for g in b.data.vertices[int(i)].groups];ref=max(terms,key=lambda x:x[0])[1];q=Quaternion(sum((np.array(q)*w*(-1 if q.dot(ref)<0 else 1)for w,q in terms),np.zeros(4)));q.normalize();Q.append(q)
restcross=np.cross(R[T[f,1]]-R[T[f,0]],R[T[f,2]]-R[T[f,0]]);restnormal=restcross/np.linalg.norm(restcross);transport=sum((np.array(q@Vector(restnormal))for q in Q));transport/=np.linalg.norm(transport);edgefaces={}
for j,t in enumerate(T):
 for x,y in [(t[0],t[1]),(t[1],t[2]),(t[2],t[0])]:edgefaces.setdefault(tuple(sorted((int(x),int(y)))),[]).append(j)
for mode in ['basis','hip_only','combined_without_lead','final']:
 key.data.foreach_set('co',(hipcoords if mode=='hip_only'else coords).ravel());key.value=0 if mode=='basis'else kv;lead.value=lv if mode=='final'else 0.;bpy.context.view_layer.update();X=m.points();cross=np.cross(X[T[:,1]]-X[T[:,0]],X[T[:,2]]-X[T[:,0]]);norm=cross/np.maximum(np.linalg.norm(cross,axis=1)[:,None],1e-30);tree=BVHTree.FromPolygons(X.tolist(),T.tolist(),all_triangles=True);localtree=BVHTree.FromPolygons(X.tolist(),T[star].tolist(),all_triangles=True);pairs=[(int(star[i]),int(j))for i,j in localtree.overlap(tree)if not set(T[star[i]])&set(T[j])];dihedral=[]
 for i,j in [(T[f,0],T[f,1]),(T[f,1],T[f,2]),(T[f,2],T[f,0])]:
  for neighbor in edgefaces[tuple(sorted((int(i),int(j))))]:
   if neighbor!=f:dihedral.append({'neighbor_face':neighbor,'normal_angle_degrees':float(np.degrees(np.arccos(np.clip(norm[f]@norm[neighbor],-1,1))))})
 # Full rank material map completion: rest tangents+restN to actual edges+
 # average unit-DQ transported restN. Its signed determinant is a directional
 # diagnostic; tangential singular values and local surface evidence accompany it.
 A=np.column_stack((R[T[f,1]]-R[T[f,0]],R[T[f,2]]-R[T[f,0]],restnormal));B=np.column_stack((X[T[f,1]]-X[T[f,0]],X[T[f,2]]-X[T[f,0]],transport));J=B@np.linalg.inv(A)
 modes.append({'mode':mode,'face_area_m2':float(np.linalg.norm(cross[f])/2),'face_normal':norm[f].tolist(),'whole_star_areas_m2':(np.linalg.norm(cross[star],axis=1)/2).tolist(),'source_star_faces':star.tolist(),'source_star_triangle_ids':T[star].tolist(),'actual_star_positions':{str(i):X[i].tolist()for i in np.unique(T[star])},'nonadjacent_star_vs_whole_body_pairs':pairs,'neighbor_dihedrals':dihedral,'source_deformation_jacobian':J.tolist(),'Jacobian_singular_values':np.linalg.svd(J,compute_uv=False).tolist(),'signed_material_completion_det':float(np.linalg.det(J)),'normal_dot_average_DQ_transport':float(norm[f]@transport)})
key.data.foreach_set('co',coords.ravel());key.value=kv;lead.value=lv;bpy.context.view_layer.update();X=m.points();bones={p.name:np.array(p.matrix)for p in a.rig.pose.bones};proof=[];a.scene.render.resolution_x=900;a.scene.render.resolution_y=900;a.scene.render.resolution_percentage=100
for view,pos in [('side',(3.8,-.2,1)),('oblique',(3.3,-4.5,2))]:
 cam=a.scene.camera;cam.location=pos;cam.rotation_euler=(Vector((0,-.35,.4))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=2.05;a.scene.render.filepath=str(P.parent/'assets/6121'/f'final-transit-f24-{view}.png');bpy.ops.render.render(write_still=True);assert np.array_equal(X,m.points())and all(np.array_equal(bones[p.name],np.array(p.matrix))for p in a.rig.pose.bones);proof.append({'path':a.scene.render.filepath,'sha256':hashlib.sha256(Path(a.scene.render.filepath).read_bytes()).hexdigest(),'skin_bone_render_readback_exact':True})
report={'frame':24,'source_face':f,'source_vertex_ids':T[f].tolist(),'source_rest_positions':R[T[f]].tolist(),'source_rest_area_m2':float(np.linalg.norm(restcross)/2),'weights':{str(i):{b.vertex_groups[g.group].name:g.weight for g in b.data.vertices[int(i)].groups}for i in T[f]},'averaged_DQ_material_normal':transport.tolist(),'hip_scalar':kv,'contact_lead_scalar':lv,'all_modes_same_FK':True,'modes':modes,'proofs':proof};(P/'face17419-diagnosis.json').write_text(json.dumps(report,indent=2)+'\n');print('FACE17419',json.dumps({k:v for k,v in report.items()if k!='modes'}),flush=True)
for v in modes:print('MODE',v['mode'],'area',v['face_area_m2'],'det',v['signed_material_completion_det'],'cross',v['nonadjacent_star_vs_whole_body_pairs'],'dihedrals',v['neighbor_dihedrals'],flush=True)
