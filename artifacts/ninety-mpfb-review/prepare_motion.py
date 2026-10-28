"""Build clip-specific linear deformation groups from native joint samples."""
import argparse
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent


def evaluate(positions, trajectories, weights):
    result = np.zeros((len(trajectories), len(positions), 3), dtype=np.float64)
    for joint in range(trajectories.shape[1]):
        selected = np.array([i for i, w in enumerate(weights) if w.get(joint, 0) > 0])
        if not len(selected):
            continue
        mass = np.array([weights[i][joint] for i in selected])
        transformed = np.einsum("tab,vb->tva", trajectories[:, joint, :3, :3], positions[selected])
        transformed += trajectories[:, joint, :3, 3][:, None, :]
        result[:, selected] += transformed * mass[None, :, None]
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--motion", type=Path, required=True)
    args = parser.parse_args()
    source = np.load(args.motion)
    times = source["times"].astype(np.float64)
    names = source["bone_names"].tolist()
    matrices = source["bone_world_matrices"].astype(np.float64)
    assert matrices.shape == (151, len(names), 4, 4)
    assert len(times) == 151 and times[0] == 0 and abs(times[-1] - 5) < 1e-6
    assert (np.diff(times) > 0).all() and np.isfinite(matrices).all()
    mesh = json.loads((HERE / "mesh-input.json").read_text())
    positions = np.array(mesh["positions"], dtype=np.float64)
    used = sorted(set().union(*(w for w in mesh["weights"])))
    indices = np.array([names.index(name) for name in used])
    delta = matrices[:, indices] @ np.linalg.inv(matrices[0, indices])[None, :]
    assert np.abs(delta[0] - np.eye(4)).max() < 1e-10
    delta[0] = np.eye(4)
    representatives, memberships, lookup = [], [], {}
    tolerance = 2e-6
    for joint, name in enumerate(used):
        group = next((g for g, ref in enumerate(representatives)
                      if np.abs(delta[:, joint] - delta[:, ref]).max() <= tolerance), None)
        if group is None:
            group = len(representatives)
            representatives.append(joint)
            memberships.append([])
        memberships[group].append(name)
        lookup[name] = group
    trajectories = delta[:, representatives]
    grouped, pruned, lost = [], [], []
    full = [{used.index(name): value for name, value in w.items()} for w in mesh["weights"]]
    for weights in mesh["weights"]:
        merged = {}
        for name, value in weights.items():
            group = lookup[name]
            merged[group] = merged.get(group, 0) + value
        grouped.append(merged)
        top = sorted(merged.items(), key=lambda item: (-item[1], item[0]))[:4]
        total = sum(value for _, value in top)
        lost.append(1 - total)
        pruned.append({joint: value / total for joint, value in top})
    expected = evaluate(positions, delta, full)
    grouped_samples = evaluate(positions, trajectories, grouped)
    final_samples = evaluate(positions, trajectories, pruned)
    coalescing_error = np.linalg.norm(grouped_samples - expected, axis=2)
    pruning_error = np.linalg.norm(final_samples - grouped_samples, axis=2)
    (HERE / "expected-linear-samples.bin").write_bytes(final_samples.astype("<f4").tobytes())
    runtime = {"times": times.tolist(), "trajectories": trajectories.tolist(),
               "bind_trajectories": matrices[:, indices[representatives]].tolist(),
               "groups": memberships, "weights": pruned, "clip_name": "Exercise_10565"}
    (HERE / "motion-input.json").write_text(json.dumps(runtime, separators=(",", ":")) + "\n")
    report = {
        "status": "prepared_pending_actual_glb_skinning_and_contact_review",
        "native_used_bones": len(used), "runtime_deformation_groups": len(memberships),
        "groups": memberships, "matrix_coalescing_tolerance": tolerance,
        "coalescing_surface_error_maximum_m": float(coalescing_error.max()),
        "coalescing_surface_error_p99_m": float(np.quantile(coalescing_error, .99)),
        "top_four_pruning_mass_maximum": float(max(lost)),
        "top_four_pruning_surface_error_maximum_m": float(pruning_error.max()),
        "top_four_pruning_surface_error_p99_m": float(np.quantile(pruning_error, .99)),
        "frames": 151, "vertices": len(positions), "duration_seconds": float(times[-1]),
        "expected_samples": {"path": "expected-linear-samples.bin", "dtype": "little-endian-float32",
                             "shape": [151, len(positions), 3], "space": "BlenderZup mesh local"},
        "source_rig_edited": False,
        "runtime_rig": "Independent clip-specific deformation groups with native sampled joint transforms and seated inverse binds; source anatomical rig remains the authoring model.",
        "native_skin_boundary": "SeatedP0 is baked from repaired native skin. Subsequent standardlinear joint skinning does not reproduce nativeBbone curves or maskedPreserveVolume exactly.",
        "no_vertex_cache_in_delivery": True, "promotion_map": {},
    }
    (HERE / "motion-preparation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: value for key, value in report.items() if key not in ["groups", "expected_samples"]}))


if __name__ == "__main__":
    main()
