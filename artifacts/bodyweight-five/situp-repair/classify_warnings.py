"""Locate unchanged QA warning pairs without altering the QA gate or skill files."""
import bpy,inspect,json,sys,hashlib
from pathlib import Path
P=Path(__file__).resolve().parent
sys.path.insert(0,str(Path.home()/'.codex/skills/blender-asset-qa/scripts'));import qa_check
code=inspect.getsource(qa_check.run)
code=code.replace('    island_info = {}','    tri_source_faces=[]; tri_face_sets=[]\n    island_info = {}',1)
code=code.replace('        bm_t = bm.copy()',"        qa_face_layer=bm.faces.layers.int.new('QA_SourceFace')\n        for qa_face in bm.faces:qa_face[qa_face_layer]=qa_face.index\n        bm_t = bm.copy()\n        qa_face_layer=bm_t.faces.layers.int['QA_SourceFace']\n        qa_set_layer=bm_t.faces.layers.int.get('.sculpt_face_set')",1)
code=code.replace('            tri_meta.append((oi, gid_base + g, f.normal.copy()))',"            tri_meta.append((oi, gid_base + g, f.normal.copy()))\n            tri_source_faces.append(f[qa_face_layer]);tri_face_sets.append(f[qa_set_layer] if qa_set_layer else None)",1)
needle='    contact = _describe(contact_pairs)'
replacement="""    global QA_WARNING_DETAILS
    QA_WARNING_DETAILS=[{'native_quad_ids':[tri_source_faces[i],tri_source_faces[j]],'native_triangle_ids':[i,j],'source_face_sets':[tri_face_sets[i],tri_face_sets[j]],'centers_world_m':[[float(v) for v in sum((verts[k] for k in tris[t]), Vector())/3] for t in [i,j]],'triangle_areas_m2':[float((verts[tris[t][1]]-verts[tris[t][0]]).cross(verts[tris[t][2]]-verts[tris[t][0]]).length/2) for t in [i,j]]} for i,j in sorted(contact_pairs)]
"""+needle
assert needle in code;exec(code.replace(needle,replacement,1),qa_check.__dict__)
results={}
for label,path in [('baseline',P/'trials/accepted-before.blend'),('candidate',P/'trials/candidate.blend')]:
 bpy.ops.wm.open_mainfile(filepath=str(path));rig=bpy.data.objects['RIG_BlenderStudioHuman'];rig.animation_data.action=bpy.data.actions['Exercise_0001'];bpy.context.scene.frame_set(1);bpy.context.view_layer.update()
 result=qa_check.run(objects=['SK_BlenderStudioHuman'],profile='game')
 results[label]={'blend_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'warning_pairs':qa_check.QA_WARNING_DETAILS,'gate_pass':result['pass'],'warnings':result['warnings'],'errors':result['errors']}
baseline_pairs={tuple(sorted(r['native_quad_ids'])) for r in results['baseline']['warning_pairs']}
for row in results['candidate']['warning_pairs']:row['same_native_quad_pair_in_baseline']=tuple(sorted(row['native_quad_ids'])) in baseline_pairs
(P/'warning-correspondence.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps({'baseline_back_pairs':len(results['baseline']['warning_pairs']),'candidate_back_pairs':len(results['candidate']['warning_pairs']),'candidate_regions':[row['source_face_sets'] for row in results['candidate']['warning_pairs']],'candidate_centers':[row['centers_world_m'][0] for row in results['candidate']['warning_pairs']],'same_quad_pairs':sum(row['same_native_quad_pair_in_baseline'] for row in results['candidate']['warning_pairs'])}))
