"""Encode transparent VP9 WebM masters/previews and white MP4 fallbacks."""
import argparse,json,subprocess
from pathlib import Path
P=Path(__file__).resolve().parent
FFMPEG='/opt/homebrew/bin/ffmpeg'
parser=argparse.ArgumentParser();parser.add_argument('--exercise',nargs='+');args=parser.parse_args()
items=json.loads((P/'clips.json').read_text());selected=set(args.exercise or [item['id'] for item in items])
if selected-{item['id'] for item in items}:parser.error('Unknown clip selection')
subprocess.run(['swift',str(P/'compose_frames.swift'),str(P),*sorted(selected)],check=True)
reports=[]
for clip in items:
    if clip['id'] not in selected:continue
    identifier=clip['id'];count=clip['frames']
    for preview in [False,True]:
        fps=15 if preview else 30;width,height=(640,320) if preview else (1536,768)
        frames=P/(('preview-frames-' if preview else 'combined-frames-')+identifier)
        output=P/(identifier+('-preview' if preview else '')+'.webm')
        command=[FFMPEG,'-y','-framerate',str(fps),'-i',str(frames/'%04d.png'),
            '-frames:v',str(count//2 if preview else count),'-c:v','libvpx-vp9',
            '-pix_fmt','yuva420p','-b:v','90000' if preview else '0','-crf','43' if preview else '27',
            '-row-mt','1','-auto-alt-ref','0','-deadline','good','-cpu-used','4','-an',str(output)]
        with (P/(output.stem+'-webm-encode.log')).open('w') as log:
            subprocess.run(command,check=True,stdout=log,stderr=subprocess.STDOUT)
        record=dict(file=str(output),bytes=output.stat().st_size,width=width,height=height,
                    fps=fps,frames=count//2 if preview else count,duration_seconds=clip['duration'],
                    audio=False,alpha=True,encoder='libvpx-vp9 / yuva420p')
        output.with_suffix('.webm.json').write_text(json.dumps(record,indent=2)+'\n');reports.append(record)
    output=P/(identifier+'.mp4');frames=P/('combined-frames-'+identifier)
    command=[FFMPEG,'-y','-framerate','30','-i',str(frames/'%04d.png'),
        '-f','lavfi','-i','color=c=white:s=1536x768:r=30',
        '-filter_complex','[1:v][0:v]overlay=shortest=1:format=auto,format=yuv420p[out]',
        '-map','[out]','-frames:v',str(count),'-c:v','libx264','-preset','fast','-crf','20',
        '-movflags','+faststart','-an',str(output)]
    with (P/(identifier+'-mp4-encode.log')).open('w') as log:
        subprocess.run(command,check=True,stdout=log,stderr=subprocess.STDOUT)
    record=dict(file=str(output),bytes=output.stat().st_size,width=1536,height=768,fps=30,
                frames=count,duration_seconds=clip['duration'],audio=False,alpha=False,encoder='libx264 / white background')
    output.with_suffix('.json').write_text(json.dumps(record,indent=2)+'\n');reports.append(record)
if (P/'encoding-report.json').exists():
    prior=json.loads((P/'encoding-report.json').read_text())
    reports=[record for record in prior if Path(record['file']).stem.split('-')[0] not in selected]+reports
(P/'encoding-report.json').write_text(json.dumps(reports,indent=2)+'\n')
print('Encoded transparent masters/previews and white MP4 fallbacks for:',','.join(sorted(selected)))
