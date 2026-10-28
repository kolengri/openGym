"""Trace authored 3D render frames into an actual path-only animated SVG."""
from pathlib import Path
import json,xml.etree.ElementTree as ET
import vtracer

P=Path(__file__).resolve().parent
NS='http://www.w3.org/2000/svg';ET.register_namespace('',NS)
tag=lambda n:'{'+NS+'}'+n
frames=sorted((P/'human-frames').glob('[0-9][0-9][0-9][0-9].png'))
assert len(frames)==68,len(frames)
dest=P/'vector-frames';dest.mkdir(exist_ok=True)
root=ET.Element(tag('svg'),{'width':'640','height':'640','viewBox':'0 0 640 640','version':'1.1','role':'img','aria-label':'Human mannequin squat with highlighted working muscle regions'})
ET.SubElement(root,tag('metadata')).text='Human geometry: Blender Studio Human Base Meshes v1.4.1, CC0. Motion: Carnegie Mellon Graphics Lab Motion Capture Database, subject13 capture30, adapted to this body. Source capture funded by NSF EIA-0196217. Muscle colors are illustrative, not measured activation. SVG contains vector paths only.'
duration=len(frames)/30
counts=[]
for i,frame in enumerate(frames):
    output=dest/(frame.stem+'.svg')
    vtracer.convert_image_to_svg_py(str(frame),str(output),colormode='color',hierarchical='stacked',mode='spline',filter_speckle=3,color_precision=6,layer_difference=12,corner_threshold=60,length_threshold=3.5,max_iterations=10,splice_threshold=45,path_precision=2)
    document=ET.parse(output).getroot();counts.append(sum(1 for _ in document.iter(tag('path'))))
    group=ET.SubElement(root,tag('g'),{'id':'frame'+str(i),'visibility':'visible' if i==0 else 'hidden'})
    for child in list(document):group.append(child)
    times=[0,i/len(frames),(i+1)/len(frames),1]
    values=['hidden','visible','hidden','hidden']
    if i==0:times=[0,1/len(frames),1];values=['visible','hidden','hidden']
    ET.SubElement(group,tag('animate'),{'attributeName':'visibility','calcMode':'discrete','dur':f'{duration:.9f}s','repeatCount':'indefinite','keyTimes':';'.join(f'{t:.9f}' for t in times),'values':';'.join(values)})
out=P/'human-squat.svg';ET.ElementTree(root).write(out,encoding='utf-8',xml_declaration=True)
assert not any(e.tag in [tag('image'),tag('script')] for e in root.iter())
report={'frames':len(frames),'fps':30,'duration_seconds':duration,'svg_bytes':out.stat().st_size,'path_counts':counts,'embedded_raster_images':0,'scripts':0,'tracer':'vtracer0.6.15','source':'Blender Studio human geometry and adapted CMU13_30 motion; surface colors are illustrative.'}
(P/'vector-report.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='path_counts'}))
