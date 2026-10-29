"""Replace the generated garment cloud with regular quad meshes and preserve the source rig."""
import bpy,bmesh,math,json,sys
import numpy as np
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent;OUT=P.parent/'athlete-clean-v2';OUT.mkdir(exist_ok=True)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=str(P/'athlete-rigged.glb'))
body=bpy.data.objects['char1'];rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE');body.name='SK_Athlete';rig.name='RIG_Athlete'
source_faces=len(body.data.polygons)
source_world=np.asarray([tuple(body.matrix_world@v.co) for v in body.data.vertices])
def section(z,side=0):
 mask=(np.abs(source_world[:,2]-z)<.012)&(np.abs(source_world[:,0])<.245)
 if side:mask&=side*(source_world[:,0]-.015)>.025
 pts=source_world[mask]
 if len(pts)<8:return None
 lo,hi=np.quantile(pts[:,:2],[.005,.995],axis=0)
 return (lo+hi)/2,(hi-lo)/2
# Preserve custom corner normals while removing only the fused garment region.
normals=[tuple(n.vector) for n in body.data.corner_normals];bm=bmesh.new();bm.from_mesh(body.data);bm.faces.ensure_lookup_table();layer=bm.loops.layers.float_vector.new('source_normal')
for f in bm.faces:
 for loop,index in zip(f.loops,body.data.polygons[f.index].loop_indices):loop[layer]=normals[index]
drop=[]
for f in bm.faces:
 c=body.matrix_world@f.calc_center_median()
 if .679<c.z<1.065 and abs(c.x)<.24:drop.append(f)
bmesh.ops.delete(bm,geom=drop,context='FACES')
loose=[v for v in bm.verts if not v.link_faces]
if loose:bmesh.ops.delete(bm,geom=loose,context='VERTS')
bm.to_mesh(body.data);bm.free();body.data.update()
attr=body.data.attributes.get('source_normal')
body.data.normals_split_custom_set([tuple(v.vector) for v in attr.data]);body.data.attributes.remove(attr)
# Keep the upper deltoid/chest supported by the clavicle when the arm is raised.
# Meshy's automatic weights otherwise rotate the whole shoulder cap into the axilla.
shoulder_weights_changed=0
for vertex in body.data.vertices:
 p=body.matrix_world@vertex.co
 if not(1.28<p.z<1.52 and .12<abs(p.x)<.36):continue
 side='Left' if p.x>0 else 'Right';arm=body.vertex_groups.get(side+'Arm');clavicle=body.vertex_groups.get(side+'Shoulder');spine=body.vertex_groups.get('Spine')
 if not(arm and clavicle and spine):continue
 weights={g.group:g.weight for g in vertex.groups};amount=weights.get(arm.index,0)*.85*max(0,min(1,(p.z-1.28)/.17))
 if abs(p.x)<.19:amount=weights.get(arm.index,0)*.95
 if amount<.001:continue
 weights[arm.index]=weights.get(arm.index,0)-amount;weights[clavicle.index]=weights.get(clavicle.index,0)+amount*.8;weights[spine.index]=weights.get(spine.index,0)+amount*.2
 keep=sorted(weights.items(),key=lambda item:-item[1])[:4];total=sum(w for _,w in keep)
 for index in [group.group for group in vertex.groups]:body.vertex_groups[index].remove([vertex.index])
 for index,weight in keep:
  if weight>1e-6:body.vertex_groups[index].add([vertex.index],weight/total,'REPLACE')
 shoulder_weights_changed+=1
def material(name,color,roughness=.7):
 m=bpy.data.materials.new(name);bs=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED');bs.inputs['Base Color'].default_value=(*color,1);bs.inputs['Roughness'].default_value=roughness;m.diffuse_color=(*color,1);return m
skin=material('M_PelvisSkin',(.56,.38,.25),.65);fabric=material('M_ShortsFabric',(.045,.055,.070),.83);waistband=material('M_Waistband',(.027,.033,.044),.87)
def smooth(t):t=max(0,min(1,t));return t*t*(3-2*t)
def create_pants_surface(name,hem,top,offset,mat,is_garment=False):
 verts=[];faces=[];uvs=[];upper_faces=[];N=48;Q=N//4;C=8;steps=12;cx=.015
 def add(p):verts.append(Vector(p));return len(verts)-1
 def face(indices,uv):faces.append(indices);uvs.append(uv)
 rings={}
 for side in [-1,1]:
  rings[side]=[]
  for level in range(steps+1):
   t=level/steps;z=hem+(.890-hem)*t;center=cx+side*(.128-.016*t);rx=.078+.025*t+offset;ry=.094+.025*t+offset;cy=.003;ring=[]
   fitted=section(z,side)
   if fitted is not None:
    middle,radii=fitted;center=float(middle[0]);cy=float(middle[1]);rx=float(radii[0])+offset;ry=float(radii[1])+offset
   for j in range(N):
    theta=2*math.pi*j/N;inward=max(0,-side*math.cos(theta));zz=z-(.085 if is_garment else .061)*t**5*inward**2
    co,si=math.cos(theta),math.sin(theta);power=.80
    ring.append(add((center+rx*math.copysign(abs(co)**power,co),cy+ry*math.copysign(abs(si)**power,si),zz)))
   rings[side].append(ring)
   if level:
    old=rings[side][-2];u0=0 if side==-1 else .5
    for j in range(N):
     k=(j+1)%N;face([old[j],old[k],ring[k],ring[j]],[(u0+.44*j/N,.6*(level-1)/steps),(u0+.44*(j+1)/N,.6*(level-1)/steps),(u0+.44*(j+1)/N,.6*t),(u0+.44*j/N,.6*t)])
 left=rings[-1][-1];right=rings[1][-1];bridge=[]
 for row in range(N//2+1):
  a=right[(Q+row)%N];b=left[(Q-row)%N];line=[a]
  for column in range(1,C):
   u=column/C;p=verts[a].lerp(verts[b],u);p.z-=(.065 if is_garment else .050)*math.sin(math.pi*u)**2*math.cos(math.pi*row/(N//2))**2;line.append(add(p))
  line.append(b);bridge.append(line)
 for row in range(N//2):
  for column in range(C):face([bridge[row][column],bridge[row+1][column],bridge[row+1][column+1],bridge[row][column+1]],[(.46+.04*column/C,.6*row/(N//2)),(.46+.04*column/C,.6*(row+1)/(N//2)),(.46+.04*(column+1)/C,.6*(row+1)/(N//2)),(.46+.04*(column+1)/C,.6*row/(N//2))])
 boundary=[right[j%N] for j in range(3*Q,5*Q+1)]+bridge[0][1:-1]+[left[j] for j in range(Q,3*Q+1)]+list(reversed(bridge[-1][1:-1]))
 angles=[math.atan2(verts[i].y-.003,verts[i].x-cx) for i in boundary];prev=boundary
 # The last two narrow rings form a clean, even waistband.
 levels=[.912,.937,.965,.990,1.012,1.035,top-.016,top-.008,top]
 for level,z in enumerate(levels):
  if z<=.891:continue
  ring=[]
  for index,theta in zip(boundary,angles):
   rx=.213-.045*smooth((z-.94)/(top-.94));ry=.142-.016*smooth((z-.97)/(top-.97))
   rx+=offset;ry+=offset
   # Blend from the two-leg outline into one smooth waist circumference.
   t=smooth((z-.89)/.11);p=verts[index];co,si=math.cos(theta),math.sin(theta);x=(1-t)*p.x+t*(cx+rx*math.copysign(abs(co)**.80,co));y=(1-t)*p.y+t*(.003+ry*math.copysign(abs(si)**.80,si));zz=z+.006*math.sin(theta)*smooth((z-.99)/.07)
   ring.append(add((x,y,zz)))
  for j in range(len(boundary)):
   k=(j+1)%len(boundary);face([prev[j],prev[k],ring[k],ring[j]],[(j/len(boundary),.65+.34*level/len(levels)),((j+1)/len(boundary),.65+.34*level/len(levels)),((j+1)/len(boundary),.65+.34*(level+1)/len(levels)),(j/len(boundary),.65+.34*(level+1)/len(levels))]);upper_faces.append((len(faces)-1,z))
  prev=ring
 mesh=bpy.data.meshes.new(name+'Mesh');inv=body.matrix_world.inverted();mesh.from_pydata([inv@p for p in verts],[],faces);mesh.update();ob=bpy.data.objects.new(name,mesh);bpy.context.scene.collection.objects.link(ob)
 ob.parent=rig;ob.matrix_parent_inverse=body.matrix_parent_inverse.copy();ob.matrix_basis=body.matrix_basis.copy();ob.data.materials.append(mat)
 if is_garment:
  ob.data.materials.append(waistband)
  for index,z in upper_faces:
   if z>=top-.016:ob.data.polygons[index].material_index=1
 uv=mesh.uv_layers.new(name='UVMap')
 for poly,coords in zip(mesh.polygons,uvs):
  poly.use_smooth=True
  for loop,coord in zip(poly.loop_indices,coords):uv.data[loop].uv=coord
 groups={name:ob.vertex_groups.new(name=name) for name in ['Hips','LeftUpLeg','RightUpLeg']}
 for i,p in enumerate(verts):
  hip=smooth((p.z-.81)/.17);side=smooth((p.x-cx+.045)/.09);weights={'Hips':hip,'LeftUpLeg':(1-hip)*side,'RightUpLeg':(1-hip)*(1-side)}
  for name,weight in weights.items():
   if weight>1e-6:groups[name].add([i],weight,'REPLACE')
 modifier=ob.modifiers.new('Armature','ARMATURE');modifier.object=rig
 subdivision=ob.modifiers.new('SmoothQuadSurface','SUBSURF');subdivision.levels=1;subdivision.render_levels=1
 if is_garment:
  shell=ob.modifiers.new('FabricThickness','SOLIDIFY');shell.thickness=.0015/.01;shell.offset=0;shell.use_even_offset=True
 return ob,{'vertices':len(verts),'quads':len(faces),'boundary_loop_vertices':len(boundary)}
pelvis,pelvis_info=create_pants_surface('SK_CleanPelvis',.663,1.071,-.004,skin)
shorts,shorts_info=create_pants_surface('SK_CleanShorts',.651,1.080,.011,fabric,True)
asset=bpy.data.collections.new('ASSET_Athlete');bpy.context.scene.collection.children.link(asset)
for ob in [body,rig,pelvis,shorts]:
 for c in list(ob.users_collection):c.objects.unlink(ob)
 asset.objects.link(ob)
for ob in list(bpy.context.scene.objects):
 if ob not in [body,rig,pelvis,shorts]:bpy.data.objects.remove(ob,do_unlink=True)
if '--with-handface' in sys.argv:
 sys.path.insert(0,str(P));from repair_hands_face import repair
 handface=repair(body,rig,OUT);(OUT/'handface-report.json').write_text(json.dumps(handface,indent=2))
bpy.context.view_layer.update()
for image in bpy.data.images:
 if image.source=='FILE' and image.has_data:image.pack()
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'athlete-clean.blend'))
sys.path.insert(0,str(Path.home()/'.codex/skills/blender-asset-qa/scripts'));import qa_check
qa=qa_check.run(objects=[body.name,pelvis.name,shorts.name],profile='game',uv=True,max_tris=100000,eps=.00001,tol=.012);(OUT/'asset-qa.json').write_text(json.dumps(qa,indent=2))
report={'source_faces':source_faces,'source_garment_faces_removed':len(drop),'body_faces':len(body.data.polygons),'pelvis':pelvis_info,'shorts':shorts_info,'shoulder_weights_changed':shoulder_weights_changed,'bones':len(rig.data.bones),'qa_errors':qa['errors'],'qa_warnings':qa['warnings']};(OUT/'build-report.json').write_text(json.dumps(report,indent=2));print('@@BUILD@@'+json.dumps(report))
assert qa['pass'],qa['errors']
sys.path.insert(0,str(Path.home()/'.codex/skills/blender-export-pipelines/scripts'));import export_asset
export=export_asset.run(preset='gltf',collection=asset.name,out=str(OUT/'athlete-clean.glb'),set=['export_animations=false']);(OUT/'export.json').write_text(json.dumps(export,indent=2));assert export['ok'],export
