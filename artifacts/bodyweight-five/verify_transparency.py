"""Decode every delivered VP9-alpha frame and verify real transparent pixels."""
from fractions import Fraction
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

P=Path(__file__).resolve().parent
parser=argparse.ArgumentParser();parser.add_argument('--exercise',nargs='+');args=parser.parse_args()
items=json.loads((P/'clips.json').read_text());selected=set(args.exercise or [item['id'] for item in items])
if selected-{item['id'] for item in items}:parser.error('Unknown clip selection')
reports=[]
for clip in items:
    if clip['id'] not in selected:continue
    for preview in [False,True]:
        path=P/(clip['id']+('-preview' if preview else '')+'.webm')
        meta=json.loads(subprocess.check_output(['/opt/homebrew/bin/ffprobe','-v','error',
            '-show_streams','-show_format','-of','json',str(path)]))
        assert not any(s['codec_type']=='audio' for s in meta['streams']),path
        stream=next(s for s in meta['streams'] if s['codec_type']=='video')
        width,height=(640,320) if preview else (1536,768)
        count=clip['frames']//2 if preview else clip['frames'];fps=15 if preview else 30
        assert (stream['width'],stream['height'])==(width,height),(path,stream)
        assert Fraction(stream['r_frame_rate'])==fps,(path,stream)
        assert abs(float(meta['format']['duration'])-clip['duration'])<.08,(path,meta)
        process=subprocess.Popen(['/opt/homebrew/bin/ffmpeg','-v','error','-c:v','libvpx-vp9',
            '-i',str(path),'-vf','alphaextract','-pix_fmt','gray','-f','rawvideo','pipe:1'],
            stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        decoded=0;samples=[];size=width*height
        while True:
            plane=process.stdout.read(size)
            if not plane:break
            assert len(plane)==size,(path,'Truncated alpha plane')
            assert plane[0]==plane[width-1]==plane[-1]==0,(path,decoded,'Opaque corner')
            assert b'\xff' in plane,(path,decoded,'No opaque body')
            if decoded in {0,count//4,count//2,3*count//4,count-1}:
                fraction=plane.count(0)/size
                assert .2<fraction<.995,(path,decoded,fraction)
                samples.append(dict(frame=decoded,fully_transparent_fraction=fraction))
            decoded+=1
        error=process.stderr.read().decode();status=process.wait()
        assert status==0,(path,error)
        assert decoded==count,(path,decoded,count)
        reports.append(dict(file=path.name,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                            width=width,height=height,fps=fps,all_frames_decoded=decoded,
                            corner_alpha=0,opaque_body=True,samples=samples))
if (P/'transparency-verification.json').exists():
    prior=json.loads((P/'transparency-verification.json').read_text())
    reports=[record for record in prior['clips'] if Path(record['file']).stem.split('-')[0] not in selected]+reports
(P/'transparency-verification.json').write_text(json.dumps(dict(ok=True,revalidated_ids=sorted(selected),
    scope='Actual libvpx-vp9 decoding of every WebM master and preview; unchanged clips retain prior hash-bound receipts; empty corners have alpha0 and body has opaque pixels.',
    clips=reports),indent=2)+'\n')
print('Verified alpha and decoded',sum(r['all_frames_decoded'] for r in reports),'frames across',len(reports),'WebM files')
