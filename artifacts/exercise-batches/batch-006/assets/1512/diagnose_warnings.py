"""Locate the installed game checker's back-to-back warnings exactly."""
import bpy,bmesh,json,sys,hashlib
sys.dont_write_bytecode=True
from pathlib import Path
from mathutils.bvhtree import BVHTree
P=Path(__file__).resolve().parent
sys.path.insert(0,'/Users/kolengri/.codex/skills/blender-asset-qa/scripts');import qa_check
bpy.ops.wm.open_mainfile(filepath=str(P/'source.blend'));body=bpy.data.objects['SK_BlenderStudioHuman'];s=bpy.context.scene
rows=[]
for frame in [0,25,40,75,115]:
 s.frame_set(frame+1);bpy.context.view_layer.update();bm=qa_check._mesh_world(body,True);bmesh.ops.triangulate(bm,faces=bm.faces[:]);bm.verts.ensure_lookup_table()
 verts=[v.co.copy()for v in bm.verts];tris=[tuple(v.index for v in f.verts)for f in bm.faces];normals=[f.normal.copy()for f in bm.faces];sets=[set(t)for t in tris];tree=BVHTree.FromPolygons(verts,tris,epsilon=0);pairs=set()
 for ti,t in enumerate(tris):
  a,b,c=[verts[i]for i in t];n=normals[ti];cen=(a+b+c)/3
  if n.length<.5:continue
  for p in [cen,cen.lerp(a,.6),cen.lerp(b,.6),cen.lerp(c,.6)]:
   for _,_,tj,_ in tree.find_nearest_range(p,.001):
    if tj is None or tj==ti or sets[ti]&sets[tj]:continue
    n2=normals[tj]
    if n.dot(n2)>-.999:continue
    a2,b2,c2=[verts[i]for i in tris[tj]];q=p-n2*n2.dot(p-a2)
    if qa_check._point_in_tri(q,a2,b2,c2,n2):pairs.add(tuple(sorted([ti,tj])))
 data=[]
 for i,j in sorted(pairs):
  ids=sorted(sets[i]|sets[j]);data.append({'triangles':[list(tris[i]),list(tris[j])],'original_ids':ids,'source_coordinates':[list(body.data.vertices[k].co)for k in ids],'dominant_groups':[{body.vertex_groups[g.group].name:g.weight for g in body.data.vertices[k].groups}for k in ids]})
 rows.append({'frame':frame,'pairs':data});bm.free()
(P/'qa-warning-locations.json').write_text(json.dumps({'source_sha256':hashlib.sha256((P/'source.blend').read_bytes()).hexdigest(),'eps_m':.001,'samples':rows},indent=2)+'\n')
print(json.dumps(rows))
