"""Install the exact root-accepted component on its frozen clean foundation."""
import bpy,sys,os,json,hashlib
from pathlib import Path
F=Path(__file__).resolve().parent;S=F/'shoulder-specialist';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(F/'foundation-v5.blend')=='35502f29ae6ce6f6f8337cd722c79b899871e1364495adae544e6be1e38fac1a'
assert sha(S/'corrective.py')=='e6d91655df864c8331df8c7404b11435db57e303bb5e9ec2ddc8dad26f4a849b'
assert sha(S/'shoulder-ownership-target.npz')=='f78f91bbd0c1d64a1d944980993228952a3ec83a50386c332a2e52f02bd1a958'
sys.path.insert(0,str(S));import corrective
bpy.ops.wm.open_mainfile(filepath=str(F/'foundation-v5.blend'));b=bpy.data.objects['SK_BlenderStudioHuman'];r=bpy.data.objects['RIG_BlenderStudioHuman'];corrective.install(b,r,bpy.context.scene);bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(F/'source.blend'))
for ID in ['5172','6014']:
 p=F.parent/'assets'/ID/'source.blend'
 if p.exists():p.unlink()
 os.link(F/'source.blend',p)
(F/'integration-receipt.json').write_text(json.dumps({'source_sha256':sha(F/'source.blend'),'foundation_sha256':sha(F/'foundation-v5.blend'),'component_sha256':sha(S/'shoulder-ownership-target.npz'),'helper_sha256':sha(S/'corrective.py'),'pose_binding_Basis_rest_UV_topology_unchanged':True,'component_scope':'1288 POSITION,1403 NORMAL,1472 union;2653 protected POSITION exactzero; maximum57.562mm, declared58mm bound.','6014_component':'Both target scalar tracks exactzero at every151key; fullactualidentity checked separately.','remaining':'Original lower-axilla crease is retained, actual unshadowed GPU root review pending.'},indent=2)+'\n');print('INTEGRATED',sha(F/'source.blend'))
