"""Assemble existing rendered PNGs in clip order without copying image bytes."""
from pathlib import Path
import json
P=Path(__file__).resolve().parent;out=P/'combined-frames';out.mkdir(exist_ok=True)
for file in out.glob('[0-9][0-9][0-9][0-9].png'):file.unlink()
index=0;segments=[]
for clip in ['LateralShuffle','SquatPreview','ArmRaisePreview']:
 files=sorted((P/'frames'/clip).glob('[0-9][0-9][0-9][0-9].png'));assert files,clip
 start=index
 for file in files:
  (out/f'{index:04d}.png').symlink_to(file.resolve());index+=1
 segments.append({'clip':clip,'start_seconds':start/30,'end_seconds':index/30,'frames':len(files)})
(P/'video-segments.json').write_text(json.dumps({'fps':30,'frames':index,'duration_seconds':index/30,'segments':segments},indent=2)+'\n');print(json.dumps({'frames':index,'seconds':index/30}))
