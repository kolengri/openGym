"""Current immutable component: sampled native clearance, exterior and game QA."""
import sys
sys.dont_write_bytecode=True
import bpy,numpy as np,json,hashlib
from pathlib import Path
F=Path(__file__).resolve().parent;sys.path[:0]=[str(F),str(F.parent)];from self_clearance import SelfClearance;import corrective
bpy.ops.wm.open_mainfile(filepath=str(F/'foundation.blend'));b=bpy.data.objects['SK_BlenderStudioHuman'];r=bpy.data.objects['RIG_BlenderStudioHuman'];s=bpy.context.scene
for m in b.modifiers:
    m.show_viewport=m.show_render=m.type=='ARMATURE'
    if m.type=='ARMATURE':m.use_deform_preserve_volume=True
c=SelfClearance(b,r);capture=np.load(F/'capture.npz');data=corrective.install(b,r,s);exterior=np.setdiff1d(np.arange(10582),data['source_ids']);protected=data['protected_source_ids'];b.data.calc_loop_triangles();tri=np.array([t.vertices[:]for t in b.data.loop_triangles]);rows=[];fail=[]
for j,f in enumerate(capture['frames']):
    corrective.select(b,r,'5172');s.frame_set(int(f)+1,subframe=f%1);bpy.context.view_layer.update();e=b.evaluated_get(bpy.context.evaluated_depsgraph_get());me=e.to_mesh();p=np.array([v.co[:]for v in me.vertices]);e.to_mesh_clear();base=capture['positions'][j]
    same=np.array_equal(p[exterior],base[exterior]);sameprotected=np.array_equal(p[protected],base[protected]);assert same and sameprotected,f
    metrics,issues=c.sample(p);fail+=issues;area=np.linalg.norm(np.cross(p[tri[:,1]]-p[tri[:,0]],p[tri[:,2]]-p[tri[:,0]]),axis=1)/2;assert area.min()>1e-12
    rows.append({'frame':float(f),'metrics':metrics,'failures':issues,'outside_POSITION_native_skin_bit_exact':same,'protected2653_native_skin_bit_exact':sameprotected,'minimum_triangle_area_m2':float(area.min()),'minimum_floor_z_m':float(p[:,2].min())})
sys.path.insert(0,str(Path.home()/'.codex/skills/blender-asset-qa/scripts'));import qa_check
qa=[]
for f in [19,37.5,112.5]:
    corrective.select(b,r,'5172');s.frame_set(int(f)+1,subframe=f%1);bpy.context.view_layer.update();qa.append({'frame':f,'report':qa_check.run(objects=[b.name],profile='game')})
q={'pass':all(x['report']['pass']for x in qa),'samples':qa};(F/'game-qa.json').write_text(json.dumps(q,indent=2)+'\n');assert q['pass']
report={'ok':not fail,'source_foundation_sha256':hashlib.sha256((F/'foundation.blend').read_bytes()).hexdigest(),'component_archive_sha256':hashlib.sha256((F/corrective.ARCHIVE).read_bytes()).hexdigest(),'sampled_5172_states':len(rows),'all151_5172_and_decoded_scope':'Original author owns final151/native/actualdecoded/DQNORMAL/export verification after integration.','no_global_collision_claim':True,'game_qa_errors':sum(len(x['report']['errors'])for x in qa),'samples':rows,'failures':fail}
(F/'native-current-checks.json').write_text(json.dumps(report,indent=2)+'\n');assert not fail,fail
print('CURRENT_CHECKS_PASS',len(rows))
