"""All151 actual native source preservation for hand-only3531 repair."""
import bpy,json,numpy as np,re,hashlib
from pathlib import Path
F=Path(__file__).resolve().parent;original={};maximum_bone=0;maximum_skin=0;hand=None
for variant,path in [('original',F/'fist-baseline-3531.blend'),('repaired',F.parent/'assets/3531/source.blend')]:
 bpy.ops.wm.open_mainfile(filepath=str(path));b=bpy.data.objects['SK_BlenderStudioHuman'];r=bpy.data.objects['RIG_BlenderStudioHuman'];s=bpy.context.scene;names={g.index:g.name for g in b.vertex_groups};nonhand=[v.index for v in b.data.vertices if not any(any(k in names[g.group]for k in ['Hand','Index','Middle','Ring','Little','Thumb'])for g in v.groups)];bones=[p.name for p in r.pose.bones if not re.fullmatch('(Left|Right)(Index|Middle|Ring|Little|Thumb)[123]',p.name)]
 for frame in range(151):
  s.frame_set(frame+1);bpy.context.view_layer.update();mat=np.array([r.pose.bones[n].matrix[:]for n in bones]);e=b.evaluated_get(bpy.context.evaluated_depsgraph_get());me=e.to_mesh();skin=np.array([me.vertices[i].co[:]for i in nonhand]);e.to_mesh_clear()
  if variant=='original':original[frame]=(mat,skin)
  else:maximum_bone=max(maximum_bone,float(np.max(abs(mat-original[frame][0]))));maximum_skin=max(maximum_skin,float(np.max(abs(skin-original[frame][1]))))
assert maximum_bone==0 and maximum_skin==0
out={'ok':True,'frames':151,'source_sha256':hashlib.sha256((F.parent/'assets/3531/source.blend').read_bytes()).hexdigest(),'original_source_sha256':hashlib.sha256((F/'fist-baseline-3531.blend').read_bytes()).hexdigest(),'maximum_all_nonfinger_bone_matrix_error':maximum_bone,'maximum_all_nonhand_skin_error_m':maximum_skin,'preserved_bones':bones,'preserved_source_vertex_count':len(nonhand),'timing_support_wrist_body_exact':True};(F/'fist-native-preservation.json').write_text(json.dumps(out,indent=2)+'\n');print(out)
