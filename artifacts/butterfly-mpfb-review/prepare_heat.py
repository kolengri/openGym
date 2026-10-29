"""Transfer neutral MPFB adductor surface fields through explicit source provenance."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "artifacts/mannequin-muscle-atlas"))
from muscle_atlas import _build_fields


def read(path):
    return json.loads(path.read_text())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cage", type=Path, required=True)
    parser.add_argument("--new-vertex-provenance", type=Path)
    parser.add_argument("--output-dir", type=Path, default=HERE)
    args = parser.parse_args()
    neutral_path = ROOT / "artifacts/mannequin-mpfb-prototype/neutral-cage.npz"
    registration_path = ROOT / "artifacts/ninety-mpfb-review/mesh-preparation.json"
    reference_path = ROOT / "artifacts/ninety-mpfb-review/heat-regions.json"
    reference_mesh_path = ROOT / "artifacts/ninety-mpfb-review/mesh-input.json"
    neutral, cage = np.load(neutral_path), np.load(args.cage)
    registration = read(registration_path)
    co = neutral["positions"].astype(np.float64)
    mapped = co.copy()
    mapped[:, 2] = np.interp(co[:, 2], registration["new_z"], registration["old_z"])
    mapped[:, 0] *= np.interp(co[:, 2], registration["new_z"], registration["x_ratios"])
    mapped[:, 1] += np.interp(co[:, 2], registration["new_z"], registration["y_offsets"])
    fields, _ = _build_fields(mapped)
    names = [f"{name}.{side}" for name in ["adductor_longus", "adductor_magnus_visible"] for side in ["L", "R"]]
    lookup = {int(source): index for index, source in enumerate(neutral["source_ids"])}
    provenance = {int(item["source_id"]): item for item in read(args.new_vertex_provenance)} if args.new_vertex_provenance else {}
    ids = cage["source_ids"]
    assert len(ids) == len(cage["positions"]) and len(set(ids.tolist())) == len(ids)
    assert all(int(source) in (lookup if source >= 0 else provenance) for source in ids)
    reference = read(reference_path)
    reference_ids = read(reference_mesh_path)["native_source_ids"]
    regions, comparison = {}, {}
    for name in names:
        seed = fields[name]
        old = dict(zip(reference["regions"][name]["indices"], reference["regions"][name]["weights"]))
        differences = [abs(float(seed[lookup[source]]) - old.get(index, 0)) for index, source in enumerate(reference_ids)
                       if source >= 0 and (seed[lookup[source]] > .005 or index in old)]
        comparison[name] = max(differences, default=0)
        assert comparison[name] <= .00000051, (name, "Neutral field registration changed")
        values = np.zeros(len(ids))
        for vertex, source in enumerate(ids):
            if source >= 0:
                values[vertex] = seed[lookup[int(source)]]
            else:
                candidates = provenance[int(source)]["candidates"]
                assert len({item["birth_triangle"] for item in candidates}) == len(candidates)
                values[vertex] = np.mean([np.dot(item["barycentric"], [seed[lookup[int(s)]] for s in item["source_corner_ids"]]) for item in candidates])
        assert np.isfinite(values).all() and (values >= 0).all() and (values <= 1).all()
        selected = np.flatnonzero(values > .005)
        assert len(selected), name
        regions[name] = {"indices": selected.tolist(), "weights": values[selected].round(6).tolist()}
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "heat-regions.json").write_text(json.dumps({"sourceVertices": len(ids), "regions": regions}, separators=(",", ":")) + "\n")
    inputs = [Path(__file__), ROOT / "artifacts/mannequin-muscle-atlas/muscle_atlas.py",
              neutral_path, registration_path, reference_path, reference_mesh_path, args.cage]
    if args.new_vertex_provenance:
        inputs.append(args.new_vertex_provenance)
    report = {"status": "prepared_pending_actual_runtime_zone_review", "source_vertices": len(ids),
              "selected_regions": names, "region_seed_counts": {name: len(value["indices"]) for name, value in regions.items()},
              "existing_registration_maximum_error": comparison,
              "new_vertex_policy": "Equal contribution once per distinct incident birth triangle, matching the skin-weight transfer.",
              "notice": "Artist-authored visible adductor surface fields. Deep origins are omitted; no measured temperature or recruitment claim.",
              "input_sha256": {str(path.resolve().relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in inputs}}
    (args.output_dir / "heat-preparation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
