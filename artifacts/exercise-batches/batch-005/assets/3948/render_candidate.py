"""Distinct final repair evidence; no source mutation or preview-only smoothing."""
from pathlib import Path
import bpy,json,hashlib
from mathutils import Vector
P=Path(__file__).resolve().parent;bpy.ops.wm.open_mainfile(filepath=str(P/'source.blend'));s=bpy.context.scene;body=bpy.data.objects['SK_BlenderStudioHuman'];cd=s.camera.data;cam=s.camera
for m in body.modifiers:assert m.show_render==(m.type=='ARMATURE')
rows=[]
for name,f,pos,target,width,wire in [('repair-candidate-parallel-side',75,(5,0,.9),(0,0,.9),2.05,False),('repair-candidate-parallel-rear',75,(2.5,5,1.8),(0,0,.9),2.05,False),('repair-candidate-parallel-oblique',75,(3.8,-5,2),(0,0,.9),2.05,False),('repair-candidate-entry-side',37,(5,0,.9),(0,0,.9),2.05,False),('repair-candidate-shoulder-start',0,(3.8,-5,2),(0,0,1.30),1.05,False),('repair-candidate-plantar-entry',37,(3.8,-5,.7),(0,.03,.10),.85,False),('repair-candidate-parallel-wire',75,(3.8,-5,2),(0,0,.9),2.05,True)]:
 s.frame_set(f+1);cam.location=pos;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();cd.ortho_scale=width;wo=None
 if wire:
  wo=body.copy();wo.data=body.data.copy();s.collection.objects.link(wo);mat=bpy.data.materials.new('ReviewWire');mat.diffuse_color=(.015,.015,.015,1);wo.data.materials.clear();wo.data.materials.append(mat);wm=wo.modifiers.new('ReviewWire','WIREFRAME');wm.thickness=.00045;wm.offset=1
 name=name.replace('repair-candidate','corrective25');file=P/(name+'.png');s.render.filepath=str(file);bpy.ops.render.render(write_still=True)
 if wo:
  me=wo.data;bpy.data.objects.remove(wo,do_unlink=True);bpy.data.meshes.remove(me)
 rows.append({'file':file.name,'sha256':hashlib.sha256(file.read_bytes()).hexdigest(),'frame':f,'armature_only_linear':True,'wire':wire})
(P/'corrective25-proof-manifest.json').write_text(json.dumps({'source_sha256':hashlib.sha256((P/'source.blend').read_bytes()).hexdigest(),'acceptance':'Candidate evidence. Local skin-fold defects remain; see surface-contact-report.json.','stills':rows},indent=2)+'\n')
