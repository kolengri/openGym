"""Targeted native regression for the demonstrated internal foot defect."""
from pathlib import Path
import json,math,hashlib
P=Path(__file__).resolve().parent
baseline=json.loads((P/'baseline-native-diagnosis.json').read_text());current=json.loads((P/'repaired-native-diagnosis.json').read_text())
assert current['source_sha256']==hashlib.sha256((P.parent/'source.blend').read_bytes()).hexdigest()
assert len(baseline['samples'])==len(current['samples'])==151
def edge_change(report,key):return max(row[key]for row in report['samples'])
def local_drift(report):
 q0=report['samples'][0]['leg_to_foot_quaternion']
 return max(min(math.dist(row['leg_to_foot_quaternion'],q0),math.dist([-v for v in row['leg_to_foot_quaternion']],q0))for row in report['samples'])
trajectory=max(math.dist(a['bone_heads'][name],b['bone_heads'][name])for a,b in zip(baseline['samples'],current['samples'])for name in ['LeftLeg','LeftFoot'])
old_ankle=edge_change(baseline,'ankle_edge_change_from_planted_max');new_ankle=edge_change(current,'ankle_edge_change_from_planted_max')
old_foot=edge_change(baseline,'foot_edge_change_from_planted_max');new_foot=edge_change(current,'foot_edge_change_from_planted_max')
gates={'ankle_edges_stable_relative_to_actual_planted_shape':new_ankle<.002,'forefoot_edges_stable_relative_to_actual_planted_shape':new_foot<.002,'no_ankle_relative_roll':local_drift(current)<2e-6,'no_shin_rotation_snap':current['maximum_late_frame_rotation_delta_degrees']['LeftLeg']<10,'ankle_and_knee_trajectory_retained':trajectory<1e-6}
assert old_ankle>.002 and old_foot>.002,'Regression must reach the rejected internal foot distortion.'
report={'foot_regression_pass':all(gates.values()),'source_sha256':current['source_sha256'],'rejected_source_sha256':baseline['source_sha256'],'frames':151,'gates':gates,'baseline_maximum_ankle_edge_change_from_planted':old_ankle,'repaired_maximum_ankle_edge_change_from_planted':new_ankle,'baseline_maximum_forefoot_edge_change_from_planted':old_foot,'repaired_maximum_forefoot_edge_change_from_planted':new_foot,'baseline_ankle_relative_quaternion_drift':local_drift(baseline),'repaired_ankle_relative_quaternion_drift':local_drift(current),'baseline_maximum_late_rotation_degrees':baseline['maximum_late_frame_rotation_delta_degrees'],'repaired_maximum_late_rotation_degrees':current['maximum_late_frame_rotation_delta_degrees'],'maximum_ankle_knee_trajectory_change_m':trajectory,'threshold_basis':'0.2% relative edge-shape drift bounds deformation of the preserved planted foot, not medical joint ranges. 10 degrees/sample bounds the authored smooth 152.35 degree hinge transport at 30 fps; current analytical maximum is 8.45 degrees/sample.','scope':'Actual native DQ skin, source-bound mixed ankle and whole-forefoot edges across all151 samples. Tests internal shape and roll directly. Grasp acceptance and final export remain separate.'}
(P/'native-foot-regression.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2));assert report['foot_regression_pass']
