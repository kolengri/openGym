"""Inspect all151 actual loaded-GLB skin samples, including contacts and floor."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from igl.copyleft import cgal

HERE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--samples-dir", type=Path, default=HERE)
    args = parser.parse_args()
    input_path = HERE / "verification-input.npz"
    provenance = json.loads((HERE / "verification-input-provenance.json").read_text())
    assert hashlib.sha256(input_path.read_bytes()).hexdigest() == provenance["sha256"]
    source = np.load(input_path)
    initial, faces, ids = source["positions"].astype(np.float64), source["triangles"], source["source_ids"]
    glute, hip_faces = source["inferior_glute"], source["hip_faces"]
    hand_faces, leg_faces = source["hand_faces"], source["leg_faces"]
    sample_path = args.samples_dir / "runtime-linear-samples.bin"
    samples = np.fromfile(sample_path, dtype="<f4").reshape((151, len(ids), 3)).astype(np.float64)
    assert np.isfinite(samples).all()
    supports = {key.removeprefix("support_"): source[key] for key in source.files if key.startswith("support_")}
    records = []
    for frame, positions in enumerate(samples):
        _, _, intersections, _, _ = cgal.remesh_self_intersections(
            np.ascontiguousarray(positions), np.ascontiguousarray(faces, dtype=np.int64), detect_only=True)
        hip_pairs = intersections[hip_faces[intersections].any(axis=1)] if len(intersections) else intersections
        hand_leg = [pair.tolist() for pair in intersections
                    if (hand_faces[pair[0]] and leg_faces[pair[1]]) or (hand_faces[pair[1]] and leg_faces[pair[0]])]
        tri = positions[faces]
        area = np.linalg.norm(np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]), axis=1) / 2
        lowest = int(np.argmin(positions[:, 2]))
        records.append({"frame": frame, "time": frame / 30,
                        "whole_skin_min_z_m": float(positions[lowest, 2]),
                        "lowest_source_id": int(ids[lowest]),
                        "inferior_glute_min_z_m": float(positions[glute, 2].min()),
                        "support_min_z_m": {name: float(positions[mask, 2].min()) for name, mask in supports.items()},
                        "global_exact_pair_count": len(intersections), "hip_pairs": hip_pairs.tolist(),
                        "hand_leg_pairs": hand_leg, "minimum_triangle_area_m2": float(area.min())})
        if frame in [0, 30, 60, 90, 150]:
            print(json.dumps({key: value for key, value in records[-1].items()
                              if key not in ["hip_pairs", "hand_leg_pairs"]}
                             | {"hip_pair_count": len(hip_pairs), "hand_leg_pair_count": len(hand_leg)}), flush=True)
    all_floor = min(row["whole_skin_min_z_m"] for row in records)
    glute_gap = max(row["inferior_glute_min_z_m"] for row in records)
    report = {"status": "surface_pass_pending_actual_visual_review", "frames": 151,
              "sample_sha256": hashlib.sha256(sample_path.read_bytes()).hexdigest(),
              "verification_input_sha256": provenance["sha256"],
              "checks": {"all_hip_roi_descendants_and_replacement_faces_clear": all(not r["hip_pairs"] for r in records),
                         "all_complete_hand_vs_leg_faces_clear": all(not r["hand_leg_pairs"] for r in records),
                         "whole_skin_floor_penetration_below_0p35mm": all_floor >= -.00035,
                         "actual_inferior_glute_gap_below_2mm": glute_gap <= .002,
                         "all_feet_remain_within_1mm_of_floor": all(abs(r["support_min_z_m"][name]) <= .001 for r in records for name in ["foot.L", "foot.R"]),
                         "no_zero_area_faces": all(r["minimum_triangle_area_m2"] > 0 for r in records)},
              "maximum_bind_difference_m": float(np.linalg.norm(samples[0] - initial, axis=1).max()),
              "maximum_loop_difference_m": float(np.linalg.norm(samples[-1] - initial, axis=1).max()),
              "minimum_whole_skin_z_m": all_floor, "maximum_inferior_glute_gap_m": glute_gap,
              "first_failed_hip_frame": next((r["frame"] for r in records if r["hip_pairs"]), None),
              "first_failed_hand_frame": next((r["frame"] for r in records if r["hand_leg_pairs"]), None),
              "baseline_contact_disclosure": "Global counts include the pre-existing axilla/knee crease contacts. No global intersection-free claim.",
              "samples": records, "promotion_map": {}}
    if not all(report["checks"].values()):
        report["status"] = "surface_failed_pending_targeted_repair"
    (args.samples_dir / "surface-verification.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: value for key, value in report.items() if key != "samples"}))
    if not all(report["checks"].values()):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
