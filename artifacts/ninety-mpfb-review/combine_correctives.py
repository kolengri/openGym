"""Combine independently owned, disjoint pose targets without changing their driver."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--groin", type=Path, required=True)
    parser.add_argument("--support", type=Path, required=True)
    parser.add_argument("--weight-override", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    motion_hash = digest(HERE / "motion-input.json")
    weight_hash = digest(args.weight_override)
    parts = [json.loads(path.read_text()) for path in [args.groin, args.support]]
    for part in parts:
        assert part["sourceMotionSha256"] == motion_hash
        assert part["weightOverrideSha256"] == weight_hash
        assert len(part["targets"]) == 2
    assert np.allclose(parts[0]["times"], parts[1]["times"], rtol=0, atol=1e-7)
    assert np.allclose(parts[0]["weights"], parts[1]["weights"], rtol=0, atol=1e-7)
    domains = [set().union(*(target["deltas"] for target in part["targets"])) for part in parts]
    assert not domains[0].intersection(domains[1]), "Corrective ownership overlaps"
    targets = []
    for index, angle in enumerate([10, 20]):
        deltas = {**parts[0]["targets"][index]["deltas"], **parts[1]["targets"][index]["deltas"]}
        assert all(np.isfinite(delta).all() and np.linalg.norm(delta) <= .0080001 for delta in deltas.values())
        targets.append({"name": f"Hinge{angle}Contact", "deltas": deltas})
    result = {"times": parts[0]["times"], "weights": parts[0]["weights"], "targets": targets,
              "sourceMotionSha256": motion_hash, "weightOverrideSha256": weight_hash,
              "components": [{"path": str(path), "sha256": digest(path)} for path in [args.groin, args.support]],
              "composition": "Disjoint relative rest-space targets; the original two-target driver is preserved.",
              "promotion_map": {}}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, separators=(",", ":")) + "\n")
    print(json.dumps({"status": "composed_pending_actual_glb_and_shape_checks",
                      "vertices": [len(domain) for domain in domains], "sha256": digest(args.output)}))


if __name__ == "__main__":
    main()
