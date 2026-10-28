"""Expose the selected left glute and right anterior hip in complementary views.

View-only postprocessing after native pose QA; no Blender or GLB asset is edited.
"""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
path = HERE / 'camera-presets.json'
cameras = json.loads(path.read_text())
for identifier in ['10565', '6560']:
    cameras[identifier][0]['position'][0] = -3.4
    cameras[identifier][0]['scale'] = 2.1
    cameras[identifier][1]['position'][0] = 4.5
    cameras[identifier][1]['label'] = 'Front-left glute and floor supports'
path.write_text(json.dumps(cameras, indent=2) + '\n')

manifest_path = HERE / 'delivery-manifest.json'
if manifest_path.exists():
    manifest = json.loads(manifest_path.read_text())
    script = str(Path(__file__).resolve().relative_to(ROOT))
    paths = [item['path'] for item in manifest['curated_files']]
    if script not in paths:
        paths.append(script)
    manifest['curated_files'] = [dict(path=name, bytes=(ROOT / name).stat().st_size,
        sha256=hashlib.sha256((ROOT / name).read_bytes()).hexdigest()) for name in paths]
    manifest['runtime_camera_refinement'] = (
        'After native QA, opposite complementary views expose the selected front-left '
        'glute and trailing-right anterior hip. Native/GLB/action hashes are unchanged; '
        'the primary reruns actual Three.js camera and interaction checks.')
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
print('Refined only the two90/90 runtime camera pairs.')
