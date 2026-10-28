"""Independent native/GLB linear skin and original-index contact evidence."""
import hashlib,json,math,struct,sys
from pathlib import Path
import bpy,numpy as np
from mathutils import Matrix,Quaternion,Vector
from mathutils.bvhtree import BVHTree
P=Path(__file__).resolve().parent
sys.path.insert(0,str(P.parents[1]));import authoring as a
bpy.ops.wm.open_mainfile(filepath=str(P/'source.blend'))
body=bpy.data.objects['SK_BlenderStudioHuman'];rig=bpy.data.objects['RIG_BlenderStudioHuman'];scene=bpy.context.scene
source_sha=hashlib.sha256((P/'source.blend').read_bytes()).hexdigest()
rest=np.array([v.co[:] for v in body.data.vertices]);polys=[list(p.vertices) for p in body.data.polygons]
groupnames={g.index:g.name for g in body.vertex_groups}
weights={n:np.array([sum(g.weight for g in v.groups if groupnames[g.group]==n) for v in body.data.vertices]) for n in groupnames.values()}
mods={m.name:(m.show_viewport,m.show_render) for m in body.modifiers}

# Parse the exported binary independently of Blender's native skin evaluation.
data=(P/'motion.glb').read_bytes();jlen=struct.unpack_from('<I',data,12)[0];doc=json.loads(data[20:20+jlen]);bstart=20+jlen+8;binary=data[bstart:]
component={5126:np.float32,5125:np.uint32,5123:np.uint16,5121:np.uint8,5122:np.int16,5120:np.int8};sizes={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT4':16}
def accessor(i):
 ac=doc['accessors'][i];view=doc['bufferViews'][ac['bufferView']];dt=np.dtype(component[ac['componentType']]);n=sizes[ac['type']];offset=view.get('byteOffset',0)+ac.get('byteOffset',0);stride=view.get('byteStride',dt.itemsize*n)
 arr=np.ndarray((ac['count'],n),dtype=dt,buffer=binary,offset=offset,strides=(stride,dt.itemsize)).copy()
 if ac.get('normalized') and ac['componentType']!=5126:arr=arr/np.iinfo(dt).max
 return arr
nodes=doc['nodes'];parents={child:i for i,n in enumerate(nodes) for child in n.get('children',[])}
animation=doc['animations'][0]
channels=[]
for ch in animation['channels']:
 sampler=animation['samplers'][ch['sampler']];channels.append((ch['target']['node'],ch['target']['path'],accessor(sampler['input']).ravel(),accessor(sampler['output']),sampler.get('interpolation','LINEAR')))
primitive=doc['meshes'][0]['primitives'][0];attributes=primitive['attributes'];local=accessor(attributes['POSITION']);source_ids=np.rint(accessor(attributes['_SOURCE_INDEX']).ravel()).astype(int);joints=accessor(attributes['JOINTS_0']).astype(int);skinweights=accessor(attributes['WEIGHTS_0']);triangles=accessor(primitive['indices']).ravel().reshape(-1,3).astype(int)
skin=doc['skins'][0];ibms=accessor(skin['inverseBindMatrices']).reshape(-1,4,4).transpose(0,2,1)
assert len(np.unique(source_ids))==10582 and source_ids.min()==0 and source_ids.max()==10581
assert len(triangles)==21160 and len(skin['joints'])==51
assert len(doc['animations'])==1 and animation['name']=='Exercise_3244'
assert abs(max(float(c[2][-1]) for c in channels)-5)<1e-6

def glb_world(t):
 trs={i:{'translation':n.get('translation',[0,0,0]),'rotation':n.get('rotation',[0,0,0,1]),'scale':n.get('scale',[1,1,1])} for i,n in enumerate(nodes)}
 for ni,path,times,values,interpolation in channels:
  assert interpolation in ['LINEAR','STEP']
  ix=min(len(times)-2,max(0,int(np.searchsorted(times,t,side='right')-1))) if len(times)>1 else 0
  u=float(np.clip((t-times[ix])/(times[ix+1]-times[ix]),0,1)) if len(times)>1 else 0
  v=values[ix] if len(times)==1 or interpolation=='STEP' else values[ix]*(1-u)+values[ix+1]*u
  if path=='rotation' and len(times)>1 and interpolation=='LINEAR':
   aa=values[ix];bb=values[ix+1];q=Quaternion((float(aa[3]),float(aa[0]),float(aa[1]),float(aa[2]))).slerp(Quaternion((float(bb[3]),float(bb[0]),float(bb[1]),float(bb[2]))),u);v=[q.x,q.y,q.z,q.w]
  trs[ni][path]=v
 world={}
 def get(i):
  if i in world:return world[i]
  if 'matrix' in nodes[i]:m=np.array(nodes[i]['matrix']).reshape(4,4).T
  else:
   tr=trs[i];q=tr['rotation'];rot=np.array(Quaternion((float(q[3]),float(q[0]),float(q[1]),float(q[2]))).to_matrix());m=np.eye(4);m[:3,:3]=rot@np.diag(tr['scale']);m[:3,3]=tr['translation']
  world[i]=get(parents[i])@m if i in parents else m;return world[i]
 for i in range(len(nodes)):get(i)
 return world

def runtime(t,full=False):
 world=glb_world(t);matrices=np.array([world[j] for j in skin['joints']])@ibms
 hp=np.c_[local,np.ones(len(local))];p=np.zeros((len(local),3))
 for k in range(4):p+=np.einsum('nij,nj->ni',matrices[joints[:,k]],hp)[:,:3]*skinweights[:,k,None]
 # glTF Y-up -> original Blender Z-up
 p=p[:,[0,2,1]]*np.array([1,-1,1])
 if full:return p
 original=np.zeros((10582,3));original[source_ids]=p;return original

def runtime_normals(t):
 world=glb_world(t);matrices=np.array([world[j] for j in skin['joints']])@ibms
 normals=accessor(attributes['NORMAL']);n=np.zeros((len(local),3))
 for k in range(4):n+=np.einsum('nij,nj->ni',matrices[joints[:,k],:3,:3],normals)*skinweights[:,k,None]
 n=n[:,[0,2,1]]*np.array([1,-1,1]);n/=np.linalg.norm(n,axis=1)[:,None]
 return n

def native(frame,linear=False):
 for m in body.modifiers:m.show_viewport=(m.type=='ARMATURE') if linear else mods[m.name][0]
 scene.frame_set(frame+1);bpy.context.view_layer.update();ev=body.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=ev.to_mesh();p=np.array([body.matrix_world@v.co for v in mesh.vertices]);return ev,mesh,p

# Freeze actual local floor-facing original quads, separately for every support.
frames=[0,15,30,45,60,75,90,105,120,135,150]
base=runtime(0);patches={}
def freeze(name,mask,rationale):
 choices=[(i,face) for i,face in enumerate(polys) if all(mask[j] for j in face)]
 assert choices,name
 idx,face=min(choices,key=lambda pair:(float(base[pair[1],2].min()),float(np.median(base[pair[1],2]))))
 patches[name]={'indices':face,'polygon':idx,'rationale':rationale}
for side,suffix,sign in [('Left','L',1),('Right','R',-1)]:
 freeze('ventral_pelvis_'+suffix,(rest[:,2]>.83)&(rest[:,2]<1.07)&(rest[:,1]<.035)&(rest[:,0]*sign>.015)&(rest[:,0]*sign<.21),'Anterior pelvic skin remains planted through all phases; not a posterior-glute proxy.')
 freeze('anterior_thigh_'+suffix,weights[side+'UpLeg']>.7,'Local anterior thigh skin supporting the prone leg, separate from pelvis and knee.')
 freeze('anterior_shin_'+suffix,(weights[side+'Leg']>.7)&(rest[:,2]<.43),'Local anterior lower-leg support, separate from foot dorsum.')
 freeze('foot_dorsum_'+suffix,weights[side+'Foot']+weights[side+'ToeBase']>.7,'Actual dorsal foot contact in pointed prone feet; not a falsely flat sole.')
 freeze('palm_heel_'+suffix,weights[side+'Hand']>.7,'Actual palm heel, independent of finger-tip and wrist bone targets.')
 for digit in ['Thumb','Index','Middle','Ring','Little']:
  freeze(digit.lower()+'_pad_'+suffix,weights[side+digit+'3']+weights[side+digit+'2']>.7,'Distal articulated finger pad kept near floor; not the whole hand minimum.')

# Propagate each frozen patch into native subdivision through a scalar mask.
for name,patch in patches.items():
 attr=body.data.attributes.new(name='QA_'+name,type='FLOAT',domain='POINT');v=np.zeros(10582,np.float32);v[patch['indices']]=1;attr.data.foreach_set('value',v)

def metrics(p,ids):
 z=p[ids,2];return {'min_z':float(z.min()),'max_z':float(z.max()),'median_z':float(np.median(z)),'near_fraction':float(np.mean(abs(z)<=.012)),'penetration_m':float(max(0,-z.min())),'centroid_xy':p[ids,:2].mean(axis=0).tolist()}

# Actual body/hand clearance against a cropped torso skin; six-ray majority avoids
# interpreting a remote open crop boundary as a closed volume.
torso_mask=weights['Hips']+weights['Spine']+weights['Spine1']>.65
torso_faces=[f for f in polys if all(torso_mask[j] for j in f)]
hand_mask=np.zeros(10582,bool)
for name,w in weights.items():
 if any(part in name for part in ['Hand','Thumb','Index','Middle','Ring','Little']):hand_mask|=w>.5
hand_ids=np.flatnonzero(hand_mask)
rays=[Vector(v).normalized() for v in [(1,.37,.39),(-.23,1,.29),(.17,-.31,1),(-1,-.37,-.39),(.23,-1,-.29),(-.17,.31,-1)]]
def inside(bvh,point):
 odd=0
 for ray in rays:
  origin=Vector(point);hits=0
  for _ in range(48):
   hit,_,_,_=bvh.ray_cast(origin,ray,3)
   if hit is None:break
   hits+=1;origin=hit+ray*.000002
  odd+=hits%2
 return odd>=4

references=[];poses=[];native_rows=[];linear_rows=[];max_parity=0;clearance_rows=[];global_min=1
for frame in frames:
 t=frame/30;runtime_p=runtime(t)
 ev,mesh,linear_p=native(frame,True);parity=float(np.linalg.norm(linear_p-runtime_p,axis=1).max());max_parity=max(max_parity,parity);ev.to_mesh_clear()
 poses.append({'id':'3244','frame':frame,'joints':{b.name:list(rig.matrix_world@b.head) for b in rig.pose.bones}})
 refs={name:{'indices':patch['indices'],'min_z':float(linear_p[patch['indices'],2].min()),'max_z':float(linear_p[patch['indices'],2].max())} for name,patch in patches.items()}
 references.append({'id':'3244','frame':frame,'global_floor_z':float(linear_p[:,2].min()),'patches':refs})
 linear_rows.append({'frame':frame,'global_min_z':float(runtime_p[:,2].min()),'native_cage_max_error_m':parity,'patches':{name:metrics(runtime_p,patch['indices']) for name,patch in patches.items()}})
 global_min=min(global_min,float(runtime_p[:,2].min()))
 ev,mesh,np_native=native(frame,False);native_patches={}
 for name in patches:
  attr=mesh.attributes['QA_'+name];mask=np.array([x.value for x in attr.data])>.25;ids=np.flatnonzero(mask);assert len(ids)
  native_patches[name]=metrics(np_native,ids)
 native_rows.append({'frame':frame,'vertices':len(np_native),'global_min_z':float(np_native[:,2].min()),'patches':native_patches});ev.to_mesh_clear()
 bvh=BVHTree.FromPolygons([Vector(p) for p in runtime_p],torso_faces,all_triangles=False)
 distances=[bvh.find_nearest(Vector(runtime_p[i]))[3] for i in hand_ids]
 close=[int(i) for i,d in zip(hand_ids,distances) if d<.02]
 contained=[i for i in close if inside(bvh,runtime_p[i])]
 clearance_rows.append({'frame':frame,'minimum_hand_torso_distance_m':float(min(distances)),'hand_vertices_inside_torso_crop':contained})

loop_error=float(np.linalg.norm(runtime(0)-runtime(5),axis=1).max())
# Dense runtime floor sweep uses actual GLB channels at all151 authored samples.
dense_global=[float(runtime(i/30)[:,2].min()) for i in range(151)]
# Patch tangential drift independent of global-root or joint minima.
drift={name:max(float(np.linalg.norm(np.array(row['patches'][name]['centroid_xy'])-np.array(linear_rows[0]['patches'][name]['centroid_xy']))) for row in linear_rows) for name in patches}
limits={'floor_penetration_m':.004,'contact_near_band_m':.012,'minimum_near_fraction':.2,'maximum_planted_patch_drift_m':.005,'native_cage_export_parity_m':.00002,'loop_skin_error_m':.00002}
linear_support=all(v['min_z']<=.012 and v['min_z']>=-.004 and v['near_fraction']>=.2 for row in linear_rows for v in row['patches'].values())
native_support=all(v['min_z']<=.012 and v['min_z']>=-.004 and v['near_fraction']>=.2 for row in native_rows for v in row['patches'].values())
checks={'linear_supports':linear_support,'native_supports':native_support,'linear_whole_skin_floor':min(dense_global)>=-.004,'native_whole_skin_floor':min(r['global_min_z'] for r in native_rows)>=-.004,'export_native_cage_parity':max_parity<.00002,'seamless_skin_loop':loop_error<.00002,'planted_patch_drift':max(drift.values())<.005,'hands_clear_of_torso':all(not r['hand_vertices_inside_torso_crop'] for r in clearance_rows)}
# Base topology/weights/UV checker on unchanged source. It does not replace posed checks.
sys.path.insert(0,'/Users/kolengri/.codex/skills/blender-asset-qa/scripts');import qa_check
base_qa=qa_check.run(objects=[body.name],profile='game',no_modifiers=True)
(P/'asset-qa.json').write_text(json.dumps(base_qa,indent=2)+'\n')
qa={'id':'3244','source_sha256':source_sha,'motion_sha256':hashlib.sha256(data).hexdigest(),'ok':all(checks.values()) and base_qa['pass'],'checks':checks,'limits':limits,'tolerance_basis':'Illustration approximations at1.8m body scale, not clinical limits or exact collision guarantees.12mm near-contact band,4mm penetration,5mm tangential drift.','frozen_original_patches':patches,'native':native_rows,'exported_linear':linear_rows,'max_export_native_cage_error_m':max_parity,'loop_skin_error_m':loop_error,'dense_export_global_floor_min_m':min(dense_global),'planted_patch_maximum_xy_drift_m':drift,'hand_torso_clearance':clearance_rows,'native_pipeline':'Original inherited corrective-smooth/subdivision, separately evaluated; masks propagated from frozen original source faces.','runtime_pipeline':'Independent glTF binary accessor/channel/IBM evaluation with linear skin weights.','base_qa_pass':base_qa['pass'],'base_qa_warnings':base_qa['warnings'],'base_qa_errors':base_qa['errors']}
(P/'pose-samples.json').write_text(json.dumps(poses,indent=2)+'\n');(P/'runtime-surface-reference.json').write_text(json.dumps({'source_sha256':source_sha,'source_vertices':10582,'samples':references},indent=2)+'\n');(P/'pose-contact-qa.json').write_text(json.dumps(qa,indent=2)+'\n')
print(json.dumps({'ok':qa['ok'],'checks':checks,'max_export_native_cage_error_m':max_parity,'loop_skin_error_m':loop_error,'runtime_floor_min':min(dense_global),'native_floor_min':min(r['global_min_z'] for r in native_rows),'minimum_hand_torso_clearance_m':min(r['minimum_hand_torso_distance_m'] for r in clearance_rows),'base_qa_pass':base_qa['pass'],'base_qa_errors':base_qa['errors'],'base_qa_warnings':base_qa['warnings']}))
# Curated exported-skin stills are generated from actual glTF primitive triangles.
for m in body.modifiers:m.show_viewport=False;m.show_render=False
body.hide_render=True
runtime_mesh=bpy.data.meshes.new('QA_ExportedSkin');runtime_mesh.from_pydata(runtime(0,True).tolist(),[],triangles.tolist());runtime_mesh.update();runtime_body=bpy.data.objects.new('QA_ExportedSkin',runtime_mesh);scene.collection.objects.link(runtime_body);runtime_mesh.materials.append(body.data.materials[0])
for p in runtime_mesh.polygons:p.use_smooth=True
cam=scene.camera;camera_defs=json.loads((P/'cameras.json').read_text())
for label,t,c in [('start',0,0),('peak',2.5,0),('return',5,0),('peak',2.5,1)]:
 p=runtime(t,True);runtime_mesh.vertices.foreach_set('co',p.astype(np.float32).ravel());runtime_mesh.update();runtime_mesh.normals_split_custom_set_from_vertices(runtime_normals(t).tolist());cdef=camera_defs[c];cam.location=cdef['position'];cam.rotation_euler=(Vector(cdef['target'])-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=cdef['scale'];scene.render.filepath=str(P/('exported-'+label+'-'+cdef['label']+'-solid.png'));bpy.ops.render.render(write_still=True)
wiremod=runtime_body.modifiers.new('QA_Wire','WIREFRAME');wiremod.thickness=.0008;wiremod.use_replace=False;wiremod.material_offset=1
wiremat=bpy.data.materials.new('QA_ExportedWire_Dark');wiremat.diffuse_color=(.04,.05,.06,1);runtime_mesh.materials.append(wiremat)
scene.render.filepath=str(P/'exported-peak-oblique-wire.png');bpy.ops.render.render(write_still=True)
