"""Create a small inline review page using immutable published asset URLs."""
import argparse
import json
from pathlib import Path
import re

parser=argparse.ArgumentParser()
parser.add_argument('--revision',required=True)
args=parser.parse_args()
if not re.fullmatch('[0-9a-f]{40}',args.revision):
    parser.error('revision must be an immutable full commit SHA')
root=Path(__file__).resolve().parent
base=f'https://raw.githubusercontent.com/kolengri/openGym/{args.revision}/artifacts/bodyweight-five/'
config=dict(modelUrl=base+'bodyweight-five.glb',
    textureUrls={key:base+f'web-textures/{key}.png' for key in ['neutral','5965','5915','5887','0001','9066']},
    cameraPresets=json.loads((root/'camera-presets.json').read_text()))
prefix=(root/'threejs-viewer.html').read_text().split('<script id="runtime-data"',1)[0]
prefix=prefix.replace('</style>','''
:root{--foreground:light-dark(#18232c,#eff3f6);--muted-foreground:light-dark(#53616e,#a8b5c1);--border:light-dark(#d4dce2,#465460);--secondary:light-dark(#e2edf2,#263f4d);color-scheme:light dark}
body{margin:0;padding:0;background:transparent;color:var(--foreground);font:14px/1.5 system-ui,sans-serif}main{margin:0;max-width:none}nav{gap:8px}select,button{font:inherit;padding:6px;color:var(--foreground);background:var(--secondary);border:1px solid var(--border);border-radius:6px}p{color:var(--muted-foreground);font-size:12px}#view-labels{font-size:12px}.viewer-stage{margin:8px auto}
</style>''')
import_map={'imports':{'three':'https://cdn.jsdelivr.net/npm/three@0.186.1/build/three.module.js',
                       'three/addons/':'https://cdn.jsdelivr.net/npm/three@0.186.1/examples/jsm/'}}
html=prefix+'<script type="importmap">'+json.dumps(import_map)+'</script>'
html+='<script id="runtime-data" type="application/json">'+json.dumps(config)+'</script>'
html+='<script type="module">'+(root/'runtime_viewer.js').read_text()+'</script></html>'
assert len(html.encode())<512_000
(root/'threejs-online-viewer.html').write_text(html)
print(json.dumps({'bytes':len(html.encode()),'revision':args.revision}))
