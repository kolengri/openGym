"""Compact causal receipt from the final-source screen-space samples."""
import json,math
from pathlib import Path
P=Path(__file__).resolve().parent;d=json.loads((P/'panel-causal-samples.json').read_text());rows={tuple(r['pixel']):r for r in d['samples']};v=[x-y for x,y in zip(d['camera']['target'],d['camera']['position'])];length=math.sqrt(sum(x*x for x in v));v=[x/length for x in v];out=[]
for a,b in [((460,320),(465,320)),((460,335),(465,335)),((460,350),(465,350)),((455,365),(460,365))]:
 left,right=rows[a].copy(),rows[b].copy()
 for row in [left,right]:row.pop('fairing_ids',None)
 delta=[x-y for x,y in zip(right['world_hit'],left['world_hit'])]
 out.append({'pixels':[a,b],'near_thigh':left,'behind_waist':right,'world_separation_m':math.dist(left['world_hit'],right['world_hit']),'waist_depth_behind_thigh_m':sum(x*y for x,y in zip(delta,v))})
face_ids={str(row[side]['polygon'])for row in out for side in ['near_thigh','behind_waist']}
faces={k:d['faces'][k]for k in sorted(face_ids,key=int)}
for face in faces.values():
 for vertex in face['source_vertices']:vertex.pop('fairing',None)
report={'source_sha256':d['source_sha256'],'frame':37.5,'finding':'The long edge is a legitimate geometric occluding silhouette of rigid lateral/anterior thigh in front of separate waist skin, not a continuous attachment or normal seam. The earlier broad-sheet interpretation was incorrect. Flat and wire proofs preserve it. The actual posterior attachment is rounded by the accepted normalized static binding repair.','proofs':['panel-flat-peak.png','panel-wire-peak.png'],'residual_disclosure':'Minor straight low-poly thigh contour/notch remains; primary accepts the bounded body for user review. No camera concealment or hip pose-space fairing is used.','brackets':out,'representative_faces':faces}
(P/'panel-causal-report.json').write_text(json.dumps(report,indent=2)+'\n')
