"""Final source-keyed neutral proof and NORMAL reference refresh; source immutable."""
import bpy,sys,json,numpy as np,gzip,hashlib
from pathlib import Path
from mathutils import Vector
F=Path(__file__).resolve().parent;sys.path.insert(0,str(F/'shoulder-specialist'));import corrective
bpy.ops.wm.open_mainfile(filepath=str(F/'source.blend'));b=bpy.data.objects['SK_BlenderStudioHuman'];r=bpy.data.objects['RIG_BlenderStudioHuman'];s=bpy.context.scene;cam=s.camera;sha=hashlib.sha256((F/'source.blend').read_bytes()).hexdigest()
def points():
 bpy.context.view_layer.update();e=b.evaluated_get(bpy.context.evaluated_depsgraph_get());m=e.to_mesh();p=np.array([v.co[:]for v in m.vertices]);e.to_mesh_clear();return p
# Full source-domain geometric NORMAL witnesses include true POSITION-boundary one-ring effects.
def normals(coords):
 m=bpy.data.meshes.new('TemporaryNORMAL');m.from_pydata(coords,[],[list(p.vertices)for p in b.data.polygons])
 for p,original in zip(m.polygons,b.data.polygons):p.use_smooth=original.use_smooth
 m.update();n=np.array([v.normal[:]for v in m.vertices]);bpy.data.meshes.remove(m);return n
base=normals([v.co[:]for v in b.data.vertices]);targets={name:(normals([v.co[:]for v in b.data.shape_keys.key_blocks[name].data])-base).tolist()for name,_ in corrective.STATES}
for ID in ['5172','6014']:
 P=F.parent/'assets'/ID;corrective.select(b,r,ID);views=json.loads((P/'cameras.json').read_text());states=[(0,'start-open'),(19,'mid-swing'),(37.5,'right-over-cross'),(75,'return-open'),(112.5,'left-over-cross'),(150,'loop-return')]if ID=='5172'else[(0,'start-low'),(9,'rising-step'),(18.75,'left-knee-overhead'),(37.5,'return-low'),(56.25,'right-knee-overhead'),(150,'loop-return')];proof=[]
 for f,label in states:
  s.frame_set(int(f)+1,subframe=f%1);before=points()
  for view in views:
   cam.location=view['position'];cam.rotation_euler=(Vector(view['target'])-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=view['scale']/(850/900);s.render.filepath=str(P/f"neutral-final-{label}-{view['label']}.png");bpy.ops.render.render(write_still=True);assert np.array_equal(before,points());proof.append({'frame':f,'seconds':f/30,'phase':label,'view':view['label'],'file':Path(s.render.filepath).name,'pre_post_render_skin_delta_m':0})
 early=json.loads((P/'early-report.json').read_text());early.update(source_sha256=sha,status='Rootaccepted native shoulder component integrated; final full-cycle gates separate.',proofs=proof);(P/'early-report.json').write_text(json.dumps(early,indent=2)+'\n')
 with gzip.open(P/'normal-reference.json.gz','wt')as out:json.dump({'source_sha256':sha,'basis':base.tolist(),'targets':targets},out,separators=(',',':'))
print('FINAL_PROOFS',sha)
