"""Collect QA warning locations; the original gate and thresholds are unmodified."""
import inspect


def install(qa_check):
    code = inspect.getsource(qa_check.run)
    code = code.replace('    island_info = {}', '    tri_source_faces=[]; tri_face_sets=[]\n    island_info = {}', 1)
    code = code.replace('        bm_t = bm.copy()', "        qa_face_layer=bm.faces.layers.int.new('QA_SourceFace')\n        for qa_face in bm.faces:qa_face[qa_face_layer]=qa_face.index\n        bm_t = bm.copy()\n        qa_face_layer=bm_t.faces.layers.int['QA_SourceFace']\n        qa_set_layer=bm_t.faces.layers.int.get('.sculpt_face_set')", 1)
    code = code.replace('            tri_meta.append((oi, gid_base + g, f.normal.copy()))', '            tri_meta.append((oi, gid_base + g, f.normal.copy()))\n            tri_source_faces.append(f[qa_face_layer]);tri_face_sets.append(f[qa_set_layer] if qa_set_layer else None)', 1)
    needle = '    contact = _describe(contact_pairs)'
    replacement = """    global QA_WARNING_DETAILS, QA_ERROR_DETAILS
    QA_WARNING_DETAILS=[{'evaluated_quad_ids':[tri_source_faces[i],tri_source_faces[j]],'triangle_ids':[i,j],'source_face_sets':[tri_face_sets[i],tri_face_sets[j]],'centers_world_m':[[float(v) for v in sum((verts[k] for k in tris[t]), Vector())/3] for t in [i,j]]} for i,j in sorted(contact_pairs)]
    QA_ERROR_DETAILS=[{'evaluated_quad_ids':[tri_source_faces[i],tri_source_faces[j]],'triangle_ids':[i,j],'source_face_sets':[tri_face_sets[i],tri_face_sets[j]],'centers_world_m':[[float(v) for v in sum((verts[k] for k in tris[t]), Vector())/3] for t in [i,j]]} for i,j in sorted(zf_pairs)]
""" + needle
    assert needle in code
    exec(code.replace(needle, replacement, 1), qa_check.__dict__)
