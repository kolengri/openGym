from pathlib import Path
import bpy,numpy as np,json,hashlib
P=Path(__file__).resolve().parent;rows=[]
for file in sorted(P.glob('corrective25-*.png')):
 im=bpy.data.images.load(str(file),check_existing=False);px=np.empty(len(im.pixels),np.float32);im.pixels.foreach_get(px);rgba=px.reshape(im.size[1],im.size[0],4);a=rgba[:,:,3];corners=[float(a[y,x]) for y,x in [(0,0),(0,-1),(-1,0),(-1,-1)]];rows.append({'file':file.name,'sha256':hashlib.sha256(file.read_bytes()).hexdigest(),'width':im.size[0],'height':im.size[1],'channels':im.channels,'corner_alpha':corners,'minimum_alpha':float(a.min()),'maximum_alpha':float(a.max())});bpy.data.images.remove(im)
report={'ok':all(x['channels']==4 and max(x['corner_alpha'])==0 and x['maximum_alpha']==1 for x in rows),'scope':'Native neutral QA stills; root owns actual viewer alpha/background/playback evidence.','samples':rows};(P/'alpha-report.json').write_text(json.dumps(report,indent=2)+'\n');assert report['ok']
