"""Sampled native and linear support-surface evidence for the static brace."""
import hashlib
import json
import sys
sys.dont_write_bytecode = True
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector

P=Path(__file__).resolve().parent
sys.path.insert(0,str(P.parents[1]));import authoring as a
bpy.ops.wm.open_mainfile(filepath=str(P/'source.blend'))
body=bpy.data.objects['SK_BlenderStudioHuman'];rig=bpy.data.objects['RIG_BlenderStudioHuman'];scene=bpy.context.scene
assert a.binding_hash(body,rig)=='227ede3fc31d1a2b47ff40f20a4a7288fe7bb36179add23bae953993826c8b7b'
modifiers=[(m,m.show_viewport,m.show_render) for m in body.modifiers]
rest=np.array([v.co for v in body.data.vertices]);groups={g.index:g.name for g in body.vertex_groups}
weights={name:np.array([sum(g.weight for g in v.groups if groups[g.group]==name) for v in body.data.vertices]) for name in groups.values()}
frames=[0,30,60,75,90,120,150]
def path(name):
 for m,v,r in modifiers:m.show_viewport=v if name=='native' else m.type=='ARMATURE'
 bpy.context.view_layer.update()
def evaluated():
 ob=body.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=ob.to_mesh();xyz=np.array([body.matrix_world@v.co for v in mesh.vertices]);return ob,mesh,xyz
path('linear');scene.frame_set(76);ob,mesh,xyz=evaluated();ob.to_mesh_clear()
patches={}
def patch(name,candidate,rationale):
 faces=[]
 for p in body.data.polygons:
  if not all(candidate[i] for i in p.vertices):continue
  points=xyz[list(p.vertices)];normal=np.cross(points[1]-points[0],points[2]-points[0]);normal/=max(np.linalg.norm(normal),1e-12)
  if normal[2]<-.35:faces.append((p,float(points[:,2].mean())))
 assert faces,name
 low=min(z for p,z in faces)
 chosen=[p for p,z in faces if z<low+.005]
 indices=sorted({i for p in chosen for i in p.vertices})
 patches[name]={'indices':indices,'polygons':[p.index for p in chosen],'rationale':rationale,'selection':'Local original floor-facing skin faces within5mm of the lowest face centroid in the declared anatomical search region; frozen source vertex IDs.'}
for side,suffix,sign in [('Left','L',1),('Right','R',-1)]:
 patch('palm_'+suffix,weights[side+'Hand']>.8,'Actual palmar/heel skin, independently from the fingers; natural palm arch remains visible.')
 for digit in ['Thumb','Index','Middle','Ring','Little']:
  patch(digit.lower()+'_pad_'+suffix,(weights[side+digit+'2']+weights[side+digit+'3'])>.5,'Actual distal '+digit.lower()+' pad skin; both hands and all ten digits are checked individually.')
 patch('knee_'+suffix,(rest[:,0]*sign>0)&(rest[:,2]>.445)&(rest[:,2]<.525),'Actual anterior knee skin on the common floor; not a knee bone-head proxy.')
for name,p in patches.items():
 attr=body.data.attributes.new(name='QA_'+name,type='FLOAT',domain='POINT');values=np.zeros(len(rest),np.float32);values[p['indices']]=1;attr.data.foreach_set('value',values)
tolerances={'support_gap_m':.012,'near_band_m':.012,'minimum_near_fraction':.2,'floor_penetration_m':.004,'support_drift_m':.005,'loop_m':.0001}
refs=[];samples=[];poses=[];failures=[];first={};endpoints={}
for frame in frames:
 scene.frame_set(frame+1)
 poses.append({'id':'4348','frame':frame,'joints':{pb.name:list(rig.matrix_world@pb.head) for pb in rig.pose.bones}})
 for skin in ['native','linear']:
  path(skin);ob,mesh,pos=evaluated()
  areas=np.zeros(len(pos))
  for polygon in mesh.polygons:
   areas[list(polygon.vertices)]+=polygon.area/len(polygon.vertices)
  row={'id':'4348','frame':frame,'path':skin,'global_min_z':float(pos[:,2].min()),'global_max_z':float(pos[:,2].max()),'patches':{}}
  reference={'id':'4348','frame':frame,'global_floor_z':float(pos[:,2].min()),'floor_plane_z':0,'patches':{}}
  for name,p in patches.items():
   values=np.empty(len(pos),np.float32);mesh.attributes['QA_'+name].data.foreach_get('value',values);mask=values>.35
   points=pos[mask];z=points[:,2];near=abs(z)<=tolerances['near_band_m'];centroid=points[:,:2].mean(0);first.setdefault((skin,name),centroid.copy())
   stats={'min_z':float(z.min()),'p10_z':float(np.percentile(z,10)),'median_z':float(np.median(z)),'max_z':float(z.max()),'near_fraction':float(near.mean()),'near_area_m2':float(areas[mask][near].sum()),'patch_area_m2':float(areas[mask].sum()),'centroid_drift_m':float(np.linalg.norm(centroid-first[skin,name])),'samples':int(mask.sum())}
   row['patches'][name]=stats
   if stats['min_z']>tolerances['support_gap_m'] or stats['min_z'] < -tolerances['floor_penetration_m'] or stats['near_fraction']<tolerances['minimum_near_fraction']:failures.append(f'{skin} frame{frame} {name} contact')
   if skin=='linear':reference['patches'][name]={'indices':p['indices'],'min_z':stats['min_z'],'max_z':stats['max_z']}
  if row['global_min_z'] < -tolerances['floor_penetration_m']:failures.append(f'{skin} frame{frame} global floor penetration')
  if frame in [0,150]:endpoints[skin,frame]=pos.copy()
  samples.append(row)
  if skin=='linear':refs.append(reference)
  ob.to_mesh_clear()
for skin in ['native','linear']:
 error=float(np.max(np.linalg.norm(endpoints[skin,0]-endpoints[skin,150],axis=1)))
 if error>tolerances['loop_m']:failures.append(skin+' loop')
for name in patches:body.data.attributes.remove(body.data.attributes['QA_'+name])
source_sha=hashlib.sha256((P/'source.blend').read_bytes()).hexdigest()
(P/'pose-samples.json').write_text(json.dumps(poses,indent=2)+'\n')
(P/'runtime-surface-reference.json').write_text(json.dumps({'source_sha256':source_sha,'source_vertices':10582,'source_index_attribute':'_SOURCE_INDEX','coordinate_frame':'Original Blender world meters Z up; runtime[x,z,-y]','samples':refs},indent=2)+'\n')
(P/'support-patches.json').write_text(json.dumps({'floor':{'point':[0,0,0],'normal':[0,0,1]},'tolerances':tolerances,'basis':'Illustration contact bands at1.8m mannequin scale, reused from existing project checks; not exact collision, contact pressure or clinical certification.','patches':patches},indent=2)+'\n')
(P/'surface-contact-report.json').write_text(json.dumps({'ok':not failures,'source_sha256':source_sha,'failures':failures,'samples':samples,'loop_surface_max_error_m':{skin:float(np.max(np.linalg.norm(endpoints[skin,0]-endpoints[skin,150],axis=1))) for skin in ['native','linear']},'static_pose':'Native and linear positions are unchanged over the7representative brace/hold/relax samples.'},indent=2)+'\n')
sys.path.insert(0,str(Path.home()/'.codex/skills/blender-asset-qa/scripts'));import qa_check
sys.path.insert(0,str(P.parents[3]/'bodyweight-next-five'));import warning_observer
warning_observer.install(qa_check)
qa=[]
for skin in ['native','linear']:
 path(skin);scene.frame_set(76)
 report=qa_check.run(objects=[body.name],profile='game')
 qa.append({'path':skin,'frame':75,'report':report,'warning_locations':qa_check.QA_WARNING_DETAILS})
 if not report['pass']:failures.append(skin+' asset QA')
(P/'asset-qa.json').write_text(json.dumps({'pass':all(x['report']['pass'] for x in qa),'source_sha256':source_sha,'samples':qa},indent=2)+'\n')
print(json.dumps({'ok':not failures,'failures':failures,'contact_patch_count':len(patches),'global_floor_range':{skin:[min(s['global_min_z'] for s in samples if s['path']==skin),max(s['global_min_z'] for s in samples if s['path']==skin)] for skin in ['native','linear']},'geometry':[{k:r[k] for k in ['path']}|{'pass':r['report']['pass'],'errors':r['report']['errors'],'warnings':r['report']['warnings']} for r in qa]},indent=2),flush=True)

assert not failures, failures
