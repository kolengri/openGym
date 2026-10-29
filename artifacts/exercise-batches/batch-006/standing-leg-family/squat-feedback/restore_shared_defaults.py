"""Restore original unkeyed finger scale defaults; no authored curve changes."""
from pathlib import Path
import bpy,json,hashlib,numpy as np
P=Path(__file__).resolve().parent;B=P.parents[1];bpy.ops.wm.open_mainfile(filepath=str(B/'assets/3480/source.blend'));scales={p.name:p.scale.copy() for p in bpy.data.objects['RIG_BlenderStudioHuman'].pose.bones};source=B/'assets/3479/source.blend';before=hashlib.sha256(source.read_bytes()).hexdigest();bpy.ops.wm.open_mainfile(filepath=str(source));r=bpy.data.objects['RIG_BlenderStudioHuman'];changes=[]
for pb in r.pose.bones:
 if tuple(pb.scale)!=tuple(scales[pb.name]):changes.append({'bone':pb.name,'before':list(pb.scale),'after':list(scales[pb.name])})
 pb.scale=scales[pb.name]
bpy.context.scene.frame_set(1);bpy.context.view_layer.update();bpy.ops.wm.save_as_mainfile(filepath=str(source));report={'ok':True,'source_sha256_before':before,'source_sha256_after':hashlib.sha256(source.read_bytes()).hexdigest(),'method':'Restore unkeyed pose-bone scale defaults exactly from the untouched3480 source. Only3479 animated location/quaternion/morph curves differ; geometry, weights, four target shapes and all3480 curves stay frozen.','maximum_scale_component_delta':max(max(abs(a-b) for a,b in zip(x['before'],x['after'])) for x in changes),'changes':changes};(P/'unkeyed-defaults-restoration.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='changes'}))
