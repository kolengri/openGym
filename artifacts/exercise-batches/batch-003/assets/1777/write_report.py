"""Collect final artifact-contract receipts without external Python dependencies."""
import hashlib
import json
import struct
import zlib
from pathlib import Path

P = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def first_pixel_alpha(path):
    png = path.read_bytes()
    assert png[:8] == b'\x89PNG\r\n\x1a\n'
    depth, color = png[24:26]
    assert (depth, color) == (8, 6)
    compressed, offset = b'', 8
    while offset < len(png):
        length, kind = struct.unpack_from('>I4s', png, offset)
        if kind == b'IDAT':
            compressed += png[offset+8:offset+8+length]
        offset += length+12
    # All PNG predictors for the first pixel use zero left/prior samples.
    return zlib.decompress(compressed)[4]


clip = json.loads((P/'clip.json').read_text())
clip['unresolved_asset_issues'] = [{
    'id': '1777-LIVE-APPEARANCE-REVIEW', 'status': 'pending_primary_visual_acceptance',
    'description': 'Plain LBS export retained. Raw Blender-import shading is not a faithful Three.js appearance proof. Primary actual WebGL smoke compiled both modes without errors and observed no material armpit band with the approved material; final front/side intermediate/peak review remains primary-owned. The frozen 58-normal-target trial is excluded from the canonical asset.'}]
clip['authored_choices']['grip'] = 'Loose articulated bilateral interlaced finger hooks; right wrist offset 14 mm along the finger row and 20 mm along palm normal keeps actual surfaces from crossing. Palms turn outward/up during the rise. Illustration spacing, not an anatomical prescription.'
clip['authored_choices']['arm_orientation'] = 'Minimum-rotation upper arm; forearm frame transported from upper arm before elbow flexion to avoid the independent antiparallel shortest-arc roll.'
(P/'clip.json').write_text(json.dumps(clip, indent=2)+'\n')
contact = json.loads((P/'surface-contact-report.json').read_text())
parity = json.loads((P/'export-parity-report.json').read_text())
qa = json.loads((P/'asset-qa.json').read_text())
glb = (P/'motion.glb').read_bytes()
length = struct.unpack_from('<I', glb, 12)[0]
doc = json.loads(glb[20:20+length])
FILES = ['source.blend', 'motion.glb', 'clip.json', 'cameras.json', 'pose-samples.json', 'runtime-surface-reference.json']
for name in FILES:
    assert (P/name).is_file() and (P/name).stat().st_size > 0
assert len(json.loads((P/'cameras.json').read_text())) == 2
samples = json.loads((P/'pose-samples.json').read_text())
assert len(samples) == 11 and all(len(s['joints']) == 51 and s['id'] == '1777' for s in samples)
assert contact['source_sha256'] == parity['source_sha256'] == qa['source_sha256'] == sha(P/'source.blend')
assert len(doc['animations']) == len(doc['meshes']) == len(doc['skins']) == len(doc['materials']) == 1
assert len(doc.get('images', [])) == 0
proofs = []
for name in ['early-start-oblique.png', 'early-peak-oblique.png', 'early-return-oblique.png', 'early-entry-oblique.png',
             'early-peak-side.png', 'early-peak-hands.png', 'native-peak-wire.png', 'linear-peak-wire.png',
             'linear-peak-oblique.png', 'linear-peak-side.png', 'export-start-oblique.png', 'export-peak-oblique.png',
             'export-return-oblique.png', 'export-entry-oblique.png', 'export-peak-side.png', 'export-peak-hands.png']:
    alpha = first_pixel_alpha(P/name)
    assert alpha == 0
    proofs.append({'path': name, 'sha256': sha(P/name), 'viewed_by_author': True, 'heat_off': True, 'corner_alpha': alpha})
mins = {path: min(r['global_floor_z'] for r in contact['samples'] if r['path'] == path) for path in ['native', 'linear']}
feet = {path: {name: {
    'min_z': min(r['supports'][name]['min_z'] for r in contact['samples'] if r['path'] == path),
    'max_z': max(r['supports'][name]['max_z'] for r in contact['samples'] if r['path'] == path),
    'min_near_fraction': min(r['supports'][name]['near_fraction'] for r in contact['samples'] if r['path'] == path),
    'max_tangential_drift_m': max(r['supports'][name]['tangential_drift_m'] for r in contact['samples'] if r['path'] == path)
    } for name in ['heel_L', 'forefoot_L', 'heel_R', 'forefoot_R']} for path in ['native', 'linear']}
summary = {
    'id': '1777', 'status': 'authored_for_primary_review',
    'geometry_contact_export_checks_pass': contact['ok'] and parity['ok'] and qa['pass'],
    'production_approved': False,
    'files': {name: {'bytes': (P/name).stat().st_size, 'sha256': sha(P/name)} for name in FILES},
    'blender': '5.2.3 LTS, Apple M5, background -t 2', 'binding_hash': contact['binding_hash'],
    'source_topology': {'vertices': 10582, 'triangles': 21160, 'bones': 51, 'continuous_body_islands': 1,
                        'neutral_materials': 1, 'color_textures': 0, 'uv_and_weights': 'Unchanged original source'},
    'export': {k: v for k, v in parity.items() if k != 'samples'},
    'support_floor_min_z_m': mins, 'support_patches': feet,
    'minimum_sampled_hand_head_clearance_m': min(r['hand_head_clearance_m'] for r in contact['samples']),
    'maximum_sampled_cross_hand_intersections': max(r['cross_hand_triangle_intersections'] for r in contact['samples']),
    'rotation_continuity': contact['rotation_continuity'],
    'accepted_inherited_warnings': [
        'Native evaluated skin reports 10 hidden back-to-back triangle pairs at start and 11 at hold; linear cage has no QA warnings. These are inherited local body folds, no topology repair authorized or made.',
        'Original UV tile coordinates are preserved; no color texture is used.'],
    'unresolved_asset_issues': clip['unresolved_asset_issues'],
    'scope_limits': [
        'Contact, hand clearance and triangle intersection evidence samples 11 poses, not continuous collision certification.',
        'Actual shared Three.js playback, field appearance, touch/orbit/zoom/reset and live transparent-canvas checks belong to primary integration and have not been performed in this asset slice.',
        'Existing export stills were raw Blender reimports; their normal transport is not a faithful Three.js-normal acceptance proof. Primary is comparing original LBS and its existing DQ adapter in the actual shared browser.',
        'Native CorrectiveSmooth/Multires skin and exported original-cage LBS skin are separately inspected; they are not claimed visually identical.',
        'No clinical, technique, muscle activation or catalogue-wide production certification.'],
    'proofs': proofs, 'generated_videos': 0, 'generated_frame_sequences': 0}
(P/'qa-summary.json').write_text(json.dumps(summary, indent=2)+'\n')
print(json.dumps({'files': summary['files'], 'support_floor_min': mins, 'contact_ok': contact['ok'], 'export_ok': parity['ok'], 'asset_qa_pass': qa['pass']}, indent=2))
