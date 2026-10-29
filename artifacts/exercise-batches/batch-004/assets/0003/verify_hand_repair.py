"""Verify the authorized 3 mm hand change against the frozen prior receipts."""
import hashlib
import json
import math
from pathlib import Path

P = Path(__file__).resolve().parent


def read(name):
    return json.loads((P / name).read_text())


def distance(a, b):
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


baseline = read('hand-repair-baseline.json')
poses = {sample['frame']: sample for sample in read('pose-samples.json')}
surface = read('runtime-surface-reference.json')
patches = {sample['frame']: sample['patches'] for sample in surface['samples']}
hands = read('hand-separation-report.json')
source_sha = hashlib.sha256((P / 'source.blend').read_bytes()).hexdigest()
assert surface['source_sha256'] == hands['source_sha256'] == source_sha

joint_errors = []
wrist_shifts = []
for sample in baseline['poses']:
    actual = poses[sample['frame']]['joints']
    joint_errors.extend(distance(position, actual[name])
                        for name, position in sample['joints'].items())
    wrist_shifts.extend(distance(position, actual[side + 'Hand'])
                        for side, position in sample['wrists'].items())

pelvic_errors = []
for sample in baseline['pelvic_patches']:
    for name, old in sample['patches'].items():
        current = patches[sample['frame']][name]
        assert old['indices'] == current['indices']
        assert len(old['positions']) == len(current['positions'])
        pelvic_errors.extend(distance(a, b) for a, b in
                             zip(old['positions'], current['positions']))

assert max(joint_errors) <= 1e-6
assert max(pelvic_errors) <= 1e-6
# Half-frame samples interpolate the baked arm quaternions, so the wrist joint
# shift need not be exactly the authored target displacement at those samples.
assert max(abs(value - .003) for value in wrist_shifts) <= 5e-6
assert min(sample['minimum_nearest_normal_signed_distance_m']
           for sample in hands['samples']) > 0

report = {
    'pass': True,
    'previous_source_sha256': baseline['source_sha256'],
    'source_sha256': source_sha,
    'baseline_receipt': 'hand-repair-baseline.json',
    'sample_frames': list(poses),
    'protected_joints_per_frame': len(baseline['poses'][0]['joints']),
    'maximum_protected_joint_change_m': max(joint_errors),
    'maximum_frozen_pelvic_surface_change_m': max(pelvic_errors),
    'pelvic_original_indices_unchanged': True,
    'wrist_shift_range_m': [min(wrist_shifts), max(wrist_shifts)],
    'maximum_wrist_shift_deviation_from_authored3mm_m': max(
        abs(value - .003) for value in wrist_shifts),
    'minimum_opposing_hand_unsigned_gap_m': min(
        sample['minimum_unsigned_distance_m'] for sample in hands['samples']),
    'minimum_opposing_hand_nearest_normal_signed_gap_m': min(
        sample['minimum_nearest_normal_signed_distance_m'] for sample in hands['samples']),
    'scope': 'Only the authorized head-relative lateral wrist targets moved 3 mm per side. '
             'The arm IK responds locally; protected torso, shoulder origins, leg joints '
             'and frozen original-ID pelvic supports remain unchanged within 1 micrometre. '
             'No new key, helper, weight, Basis, rest, UV or support-mask change.',
}
(P / 'hand-repair-verification.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
