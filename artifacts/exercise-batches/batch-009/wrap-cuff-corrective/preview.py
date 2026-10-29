"""Early native shape packet only; no final QA/export or production mutation."""
import sys
sys.dont_write_bytecode=True
import bpy,numpy as np,json,hashlib
from pathlib import Path
from mathutils import Vector
F=Path(__file__).resolve().parent;sys.path[:0]=[str(F),str(F.parent.parent/'batch-008/standing-dynamic')];import corrective
from self_clearance import SelfClearance
report=json.loads((F/('construction.json'if (F/'construction.json').exists()else'accepted-construction.json')).read_text());source=F/'inputs-contact/source.blend'
assert corrective.sha(source)==report['source_sha256']
bpy.ops.wm.open_mainfile(filepath=str(source));b=bpy.data.objects['SK_BlenderStudioHuman'];r=bpy.data.objects['RIG_BlenderStudioHuman'];s=bpy.context.scene
for m in b.modifiers:
 m.show_viewport=m.show_render=m.type=='ARMATURE'
 if m.type=='ARMATURE':assert m.use_deform_preserve_volume
clear=SelfClearance(b,r);archive=F/('target-position.npz'if (F/'target-position.npz').exists()else'accepted-position.npz');data=corrective.install(b,r,s,archive,report['archive_sha256']);tag=report['archive_sha256'][:12]+'-direct-p';out=F/'proofs'/tag;out.mkdir(parents=True,exist_ok=False)
act=bpy.data.actions['Exercise_3995'];r.animation_data.action=act;r.animation_data.action_slot=next(x for x in act.slots if x.target_id_type=='OBJECT');keys=b.data.shape_keys;keys.animation_data.action=act;keys.animation_data.action_slot=next(x for x in act.slots if x.target_id_type=='KEY')
def points():
 bpy.context.view_layer.update();e=b.evaluated_get(bpy.context.evaluated_depsgraph_get());me=e.to_mesh();p=np.array([v.co[:]for v in me.vertices]);e.to_mesh_clear();return p
cam=s.camera;s.render.engine='BLENDER_WORKBENCH';s.render.resolution_x=s.render.resolution_y=1000;s.render.resolution_percentage=100;s.render.film_transparent=True;s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGBA';s.display.shading.light='STUDIO';s.display.shading.color_type='MATERIAL';s.display.shading.show_cavity=False;s.display.shading.show_shadows=False;s.display.shading.show_specular_highlight=False;s.view_settings.view_transform='Standard';s.view_settings.look='None';cam.data.type='ORTHO';cam.data.ortho_scale=1.02
views=[('front',(2.3,-4,1.75)),('side',(4.,0,1.65)),('rear',(-2.3,4,1.75))];rows=[]
for frame,label in [(0.,'neutral'),(32.,'intermediate'),(37.5,'held')]:
 s.frame_set(int(frame)+1,subframe=frame%1);keys.key_blocks[corrective.KEY].value=0.;base=points();keys.key_blocks[corrective.KEY].value=corrective.value(frame,'3995');p=points();metrics,issues=clear.sample(p);protected=data['protected_source_ids'];delta=p-base;area=np.linalg.norm(np.cross(p[np.array(clear.torso)[:,1]]-p[np.array(clear.torso)[:,0]],p[np.array(clear.torso)[:,2]]-p[np.array(clear.torso)[:,0]]),axis=1)*.5
 row={'frame':frame,'label':label,'value':keys.key_blocks[corrective.KEY].value,'maximum_posed_delta_m':float(np.linalg.norm(delta,axis=1).max()),'protected_maximum_position_difference_m':float(np.linalg.norm(delta[protected],axis=1).max()),'minimum_torso_triangle_area_m2':float(area.min()),'metrics':metrics,'issues':issues,'proofs':[]}
 for view,pos in views:
  cam.location=pos;cam.rotation_euler=(Vector((0,-.02,1.37))-cam.location).to_track_quat('-Z','Y').to_euler();s.render.filepath=str(out/f'{label}-{view}.png');bpy.ops.render.render(write_still=True);row['proofs'].append(str(Path(s.render.filepath).relative_to(F)))
 rows.append(row);print('PREVIEW',label,row['value'],row['maximum_posed_delta_m'],issues,flush=True)
 bpy.context.view_layer.update()
s.frame_set(38,subframe=.5);keys.key_blocks[corrective.KEY].value=1.;bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(F/f'candidate-{tag}.blend'))
(F/f'preview-{tag}.json').write_text(json.dumps({'source_sha256':report['source_sha256'],'position_archive_sha256':report['archive_sha256'],'scope':'Early native sparse shape packet; final contact freeze, NORMAL archive, game QA, integrated151 and runtime pending.','samples':rows},indent=2)+'\n')
