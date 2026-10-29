"""Refresh only root-integrated camera hashes and their manifest dependencies."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPOSITORY = ROOT.parents[2]
selection = json.loads((ROOT / 'selection.json').read_text())
directories = [ROOT / 'assets' / value for value in selection['exercise_ids']]
directories += [ROOT / value for value in selection['authoring_families']]
manifests = [(directory / 'curated-files.json').resolve() for directory in directories]
cameras = {(ROOT / 'assets' / value / 'cameras.json').resolve()
           for value in selection['exercise_ids']}
changed_manifests = set()


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def resolve_entry(path, base):
    return ((REPOSITORY if path.startswith('artifacts/') else base) / path).resolve()


def refresh(entry, base):
    if not isinstance(entry, dict) or entry.get('self') or 'sha256' not in entry:
        return
    path = resolve_entry(entry['path'], base)
    actual = digest(path)
    if actual == entry['sha256']:
        return
    assert path in cameras or path in changed_manifests, f'Unaccepted change: {path}'
    entry['sha256'] = actual
    if 'bytes' in entry:
        entry['bytes'] = path.stat().st_size


for manifest in manifests:
    original = manifest.read_bytes()
    packet = json.loads(original)
    if 'self_integrity' in packet:
        original_payload = {key: value for key, value in packet.items()
                            if key != 'self_integrity'}
        original_seal = hashlib.sha256(json.dumps(
            original_payload, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        assert original_seal == packet['self_integrity']['sha256'], f'Invalid input seal: {manifest}'
    for entry in packet.get('files', packet.get('included_files', [])):
        refresh(entry, manifest.parent)
    for path, expected in packet.get('sha256', {}).items():
        target = resolve_entry(path, manifest.parent)
        actual = digest(target)
        if actual != expected:
            assert target in cameras or target in changed_manifests, f'Unaccepted change: {target}'
            packet['sha256'][path] = actual
    refresh(packet.get('asset_manifest'), manifest.parent)
    for entry in packet.get('asset_manifests', []):
        refresh(entry, manifest.parent)
    if 'self_integrity' in packet:
        seal = packet.pop('self_integrity')
        # Existing author manifests use Python's compact, sorted canonical JSON.
        seal['sha256'] = hashlib.sha256(json.dumps(
            packet, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        packet['self_integrity'] = seal
    if packet != json.loads(original):
        manifest.write_text(json.dumps(packet, indent=2) + '\n')
        changed_manifests.add(manifest)

print(json.dumps({'updated_manifests': [str(path.relative_to(ROOT))
                                      for path in sorted(changed_manifests)],
                  'scope': 'Camera integration and dependent manifest hashes only'}))
