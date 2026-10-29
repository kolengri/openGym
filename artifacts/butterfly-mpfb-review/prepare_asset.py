"""Compose disjoint static hip and hand repairs for standard GLB authoring."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cage", type=Path, required=True)
    parser.add_argument("--weights", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=HERE / "runtime")
    args = parser.parse_args()
    native_path = HERE / "native-restaging/restaged-native-cage.npz"
    pad_path = HERE / "native-restaging/residual-contact/readback-target.npz"
    pad_qa_path = HERE / "native-restaging/residual-contact/readback-QA.json"
    review_path = HERE / "restaging-root-review.json"
    review = json.loads(review_path.read_text())
    assert review["status"] == "pose_accepted_for_bounded_local_repairs_only"
    assert digest(native_path) == review["evidence_sha256"][str(native_path.relative_to(ROOT))]
    pad_qa = json.loads(pad_qa_path.read_text())
    assert pad_qa["status"] == "saved_float32_pad_target_verified" and all(pad_qa["checks"].values())
    native, pad, cage = np.load(native_path), np.load(pad_path), np.load(args.cage)
    V, F, ids = (cage[key].copy() for key in ["positions", "triangles", "source_ids"])
    assert np.isfinite(V).all() and len(set(ids.tolist())) == len(ids)
    assert np.array_equal(native["source_ids"], pad["source_ids"])
    assert np.array_equal(native["triangles"], pad["triangles"])
    assert np.array_equal(pad["positions"], native["positions"] + pad["delta"])
    active = np.any(pad["delta"] != 0, axis=1)
    assert not active[~pad["active_mask"]].any()
    assert not active[~native["complete_hand_mask"]].any()
    assert np.linalg.norm(pad["delta"], axis=1).max() <= .00200001
    native_index = {int(source): index for index, source in enumerate(native["source_ids"])}
    output_index = {int(source): index for index, source in enumerate(ids)}
    assert all(int(source) in output_index for source in native["source_ids"][active])
    for old in np.flatnonzero(native["complete_hand_mask"]):
        vertex = output_index[int(native["source_ids"][old])]
        assert np.array_equal(V[vertex], native["positions"][old]), "Hip repair changes original hand skin"
    altered = np.zeros(len(V), dtype=bool)
    for old in np.flatnonzero(active):
        vertex = output_index[int(native["source_ids"][old])]
        assert np.array_equal(V[vertex], native["positions"][old]), "Hip repair overlaps a hand repair"
        V[vertex] += pad["delta"][old]
        altered[vertex] = True
    assert np.array_equal(V[~altered], cage["positions"][~altered])
    edges = np.concatenate([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]])
    unique, inverse, counts = np.unique(np.sort(edges, axis=1), axis=0, return_inverse=True, return_counts=True)
    assert (counts == 2).all() and len(V) - len(unique) + len(F) == 2
    orientations = np.bincount(inverse, weights=np.where(edges[:, 0] < edges[:, 1], 1, -1))
    assert not orientations.any() and len(np.unique(F)) == len(V)
    graph = coo_matrix((np.ones(len(unique)), (unique[:, 0], unique[:, 1])), shape=(len(V), len(V)))
    assert connected_components(graph, directed=False)[0] == 1
    triangles = V[F]
    face_normals = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
    assert (np.linalg.norm(face_normals, axis=1) > 0).all()
    normal_sum = np.zeros_like(V, dtype=np.float64)
    for corner in range(3):
        np.add.at(normal_sum, F[:, corner], face_normals)
    normal_sum /= np.linalg.norm(normal_sum, axis=1)[:, None]
    normals = cage["normals"].copy()
    affected_normals = np.unique(F[altered[F].any(axis=1)])
    normals[affected_normals] = normal_sum[affected_normals]
    assert np.isfinite(normals).all()
    raw_weights = json.loads(args.weights.read_text())
    assert len(raw_weights) == len(V)
    assert all(item and np.isfinite(list(item.values())).all() and min(item.values()) >= 0 for item in raw_weights)
    weights = [{name: value for name, value in item.items() if name.startswith("DEF-") and value > 0} for item in raw_weights]
    assert all(item and np.isfinite(list(item.values())).all() for item in weights)
    weights = [{name: value / sum(item.values()) for name, value in item.items()} for item in weights]
    def mask(name):
        return np.array([bool(native[name][native_index[int(source)]]) if source >= 0 else False for source in ids])
    birth, patch = cage["birth"], cage["patch_faces"].astype(bool)
    assert (((birth >= 0) & (birth < len(native["triangles"]))) | (birth == -1)).all()
    caps = birth < 0
    assert patch[caps].all()
    original_faces = native["triangles"]
    hip_faces = patch.copy()
    hip_faces[~caps] |= native["pelvis_mask"][original_faces].any(axis=1)[birth[~caps]]
    if "fairing_affected_faces" in cage.files:
        hip_faces |= cage["fairing_affected_faces"]
    hand_faces = mask("complete_hand_mask")[F].any(axis=1)
    arm_faces = (mask("complete_arm_mask") | mask("complete_hand_mask"))[F].any(axis=1)
    leg_faces = mask("complete_leg_mask")[F].any(axis=1) | caps
    args.output_dir.mkdir(parents=True, exist_ok=True)
    composed_path = args.output_dir / "composed-cage.npz"
    np.savez_compressed(composed_path, **{key: cage[key] for key in cage.files if key not in ["positions", "normals"]}, positions=V, normals=normals)
    mesh = {"positions": V.tolist(), "normals": normals.tolist(), "triangles": F.tolist(),
            "native_source_ids": ids.tolist(), "weights": weights, "source_vertices": len(V)}
    (args.output_dir / "mesh-input.json").write_text(json.dumps(mesh, separators=(",", ":")) + "\n")
    support_masks = {}
    for side in ["L", "R"]:
        support_masks["support_foot." + side] = np.array([any(value > 0 and name.startswith(("DEF-foot." + side, "DEF-toe." + side)) for name, value in item.items()) for item in raw_weights])
        assert support_masks["support_foot." + side].any()
    verification_path = args.output_dir / "verification-input.npz"
    np.savez_compressed(verification_path, positions=V, triangles=F, source_ids=ids,
                        inferior_glute=mask("inferior_glute_mask"), hip_faces=hip_faces,
                        hand_faces=hand_faces, arm_faces=arm_faces, leg_faces=leg_faces, **support_masks)
    inputs = [Path(__file__), args.cage, args.weights, native_path, pad_path, pad_qa_path, review_path]
    provenance = {"sha256": digest(verification_path), "source_sha256": {str(path.resolve().relative_to(ROOT)): digest(path) for path in inputs},
                  "selectors": "Frozen native source-indexed pelvic, complete-hand, complete-arm, complete-leg and inferior-glute masks. Replacement and generated handle caps are included in the hip domain. Foot supports use positive canonical native DEF-foot/DEF-toe family weights.",
                  "status": "static_composition_pending_exact_contacts_and_actual_runtime_review"}
    (args.output_dir / "verification-input-provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")
    report = {"status": provenance["status"], "source_vertices": len(V), "triangles": len(F),
              "closed_oriented_connected_euler_two": True, "hand_changed_vertices": int(altered.sum()),
              "hand_maximum_displacement_m": float(np.linalg.norm(pad["delta"], axis=1).max()),
              "hip_and_hand_targets_disjoint": True, "native_weights_edited": False,
              "runtime_weight_sums_normalized": True, "promotion_map": {}}
    (args.output_dir / "static-composition.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
