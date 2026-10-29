"""All151 native POSITION/NORMAL/51-bone identity for three GPU-accepted actions."""
import bpy,json,numpy as np,hashlib
from pathlib import Path
F=Path(__file__).resolve().parent;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();current=F/'source.blend';data={};reports={}
baselines=[(F/'held-wrap-right-over/source.blend','999b57f13525bf76d0180161c8acb9bb87d9e1ab9ff4a2ff446ba65f44cc7e53',['1404','4515']),(F/'held-wrap-tangent-88c2da9b3095/source.blend','88c2da9b30955e3793637fe5f8a086e0ca7339d395cf20997d6b3fdcac817c1e',['1405','3995'])]
for variant,path,IDs in [('accepted',p,ids)for p,h,ids in baselines]+[('final',current,['1404','4515','1405','3995'])]:
 if variant=='accepted':assert sha(path)==next(h for p,h,ids in baselines if p==path)
 bpy.ops.wm.open_mainfile(filepath=str(path));b=bpy.data.objects['SK_BlenderStudioHuman'];r=bpy.data.objects['RIG_BlenderStudioHuman'];s=bpy.context.scene;keys=b.data.shape_keys
 for ID in IDs:
  act=bpy.data.actions['Exercise_'+ID];r.animation_data.action=act;r.animation_data.action_slot=next(x for x in act.slots if x.target_id_type=='OBJECT');keys.animation_data.action=act;keys.animation_data.action_slot=next(x for x in act.slots if x.target_id_type=='KEY');skinerr=normalerr=matrixerr=endpoint_matrixerr=0.
  for f in range(151):
   s.frame_set(f+1);bpy.context.view_layer.update()
   if ID=='3995':
    mat=np.array([pb.matrix for pb in r.pose.bones],np.float32)
    if variant=='accepted':data[ID,f]=mat
    else:
     error=float(np.max(abs(mat-data[ID,f])));matrixerr=max(matrixerr,error)
     if f in [0,37,38,75,112,113,150]:endpoint_matrixerr=max(endpoint_matrixerr,error)
    continue
   assert max(abs(k.value)for k in list(keys.key_blocks)[1:])==0;e=b.evaluated_get(bpy.context.evaluated_depsgraph_get());m=e.to_mesh();p=np.array([v.co[:]for v in m.vertices],np.float32);n=np.array([v.normal[:]for v in m.vertices],np.float32);e.to_mesh_clear();mat=np.array([pb.matrix for pb in r.pose.bones],np.float32)
   if variant=='accepted':data[ID,f]=(p,n,mat)
   else:
    oldp,oldn,oldm=data[ID,f];skinerr=max(skinerr,float(np.linalg.norm(p-oldp,axis=1).max()));normalerr=max(normalerr,float(np.linalg.norm(n-oldn,axis=1).max()));matrixerr=max(matrixerr,float(np.max(abs(mat-oldm))))
  if variant=='final'and ID=='3995':
   assert endpoint_matrixerr==0;reports[ID]={'id':ID,'all151_51bone_matrix_max_element_error':matrixerr,'kinematics_exact_to_frozen_88c2':matrixerr==0,'held_open_endpoint_51bone_matrix_max_element_error':endpoint_matrixerr,'intermediate_FK_identity_is_diagnostic':True,'accepted_source_sha256':baselines[1][1],'final_source_sha256':sha(current)}
  elif variant=='final':
   assert skinerr==normalerr==matrixerr==0;reports[ID]={'id':ID,'all151_native_POSITION_max_error_m':skinerr,'all151_native_NORMAL_max_vector_error':normalerr,'all151_51bone_matrix_max_element_error':matrixerr,'all_morph_weights_zero_all151':True,'accepted_source_sha256':next(h for p,h,ids in baselines if ID in ids),'final_source_sha256':sha(current),'receipt_reuse':'Actual all151 native skin, normals and51bone matrices; accepted GLB lineages are checked separately by actual Three/DQ decoding.'}
(F/'accepted-native-identity.json').write_text(json.dumps(reports,indent=2)+'\n');print('ACCEPTED_NATIVE_IDENTITY',reports)
