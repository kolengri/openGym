"""Curated proof of decoded GLB positions and actual Three.js normal equation."""
import bpy,json,sys,numpy as np,hashlib
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent;sys.path.insert(0,str(P));from glb_runtime import Runtime
from glb_normals import to_blender
final='--candidate' not in sys.argv
r=Runtime(P/('motion.glb' if final else 'candidate-motion.glb'));bpy.ops.wm.read_factory_settings(use_empty=True);s=bpy.context.scene;s.render.engine='BLENDER_WORKBENCH';s.render.resolution_x=1000;s.render.resolution_y=900;s.render.resolution_percentage=100;s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGBA';s.render.film_transparent=True
sh=s.display.shading;sh.light='STUDIO';sh.color_type='MATERIAL';sh.show_shadows=False;sh.show_cavity=False;sh.show_specular_highlight=False;s.view_settings.view_transform='Standard';s.view_settings.look='None'
camdata=bpy.data.cameras.new('LBSNormalReview');cam=bpy.data.objects.new('LBSNormalReview',camdata);s.collection.objects.link(cam);s.camera=cam;camdata.type='ORTHO'
cs={'close':{'position':[2.6,-2.5,4.8],'target':[.27,-.23,.17],'scale':1.03},'side':{'position':[2.6,.65,1.65],'target':[.25,-.16,.16],'scale':1.0},'overview':json.loads((P/'cameras.json').read_text())[0]};mat=bpy.data.materials.new('Neutral');mat.diffuse_color=(.6,.62,.64,1)
cs['contact']={'position':[4,0,.45],'target':[0,0,.10],'scale':2.10}
curve=bpy.data.curves.new('Z0_Datum','CURVE');curve.dimensions='3D';curve.bevel_depth=.001;sp=curve.splines.new('POLY');pts=[(-.65,-1,0),(.65,-1,0),(.65,1,0),(-.65,1,0),(-.65,-1,0)];sp.points.add(len(pts)-1)
for point,v in zip(sp.points,pts):point.co=(*v,1)
datum=bpy.data.objects.new('Z0_Datum',curve);s.collection.objects.link(datum);dm=bpy.data.materials.new('DatumNeutral');dm.diffuse_color=(.28,.28,.28,1);curve.materials.append(dm);datum.hide_render=True
rows=[]
proofs=[('start-close',0,'close'),('entry-close',1,'close'),('peak-close',2.5,'close'),('peak-side',2.5,'side'),('peak-overview',2.5,'overview'),('return-close',4,'close'),('end-close',5,'close')]
if final:proofs += [('start-oblique',0,'overview'),('peak-oblique',2.5,'overview'),('return-oblique',5,'overview'),('peak-contact-side',2.5,'contact'),('start-contact-side',0,'contact')]
for label,t,view in proofs:
 datum.hide_render=view!='contact';sample=r.sample(t);mesh=bpy.data.meshes.new('ActualLBS');mesh.from_pydata(to_blender(sample['positions']).tolist(),[],r.tri.tolist());mesh.update()
 for face in mesh.polygons:face.use_smooth=True
 mesh.normals_split_custom_set_from_vertices(to_blender(sample['normals']).tolist());mesh.materials.append(mat);ob=bpy.data.objects.new('ActualLBS',mesh);s.collection.objects.link(ob);c=cs[view];cam.location=c['position'];cam.rotation_euler=(Vector(c['target'])-cam.location).to_track_quat('-Z','Y').to_euler();camdata.ortho_scale=c['scale'];prefix='export' if final and label in ['start-oblique','peak-oblique','return-oblique','peak-side','peak-contact-side','start-contact-side'] else ('lbs-final' if final else 'lbs-candidate');s.render.filepath=str(P/f'{prefix}-{label}.png');bpy.ops.render.render(write_still=True);bpy.data.objects.remove(ob,do_unlink=True);bpy.data.meshes.remove(mesh)
 error=np.degrees(np.arccos(np.clip(np.sum(sample['normals']*sample['geometric_normals'],axis=1),-1,1)));rows.append({'label':label,'time':t,'morph_weights':sample['morph_weights'],'max_normal_vs_geometric_angle_degrees':float(error.max())})
(P/('lbs-final-proof.json' if final else 'lbs-candidate-proof.json')).write_text(json.dumps({'glb_sha256':hashlib.sha256((P/('motion.glb' if final else 'candidate-motion.glb')).read_bytes()).hexdigest(),'method':'Actual candidate GLB binary positions+animation+morphs and Three.js blendednormal equation decoded; render-only mesh receives posed positions and explicit posed normals. No asset geometry changes or invalid Blender morph-normal import assumption.','samples':rows},indent=2)+'\n')
