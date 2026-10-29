"""Derive bounded semantic rollback masks from original skin weights and topology."""
from collections import deque
from pathlib import Path
import hashlib
import json

import bpy
import numpy as np

P = Path(__file__).resolve().parent
F = P.parent / "kneeling-family"
source = P.parents[2] / "bodyweight-five/bodyweight-five.blend"
assert hashlib.sha256(source.read_bytes()).hexdigest() == "fbf635733118dc190fdb3cefabcde7fe4367bbccfa40aa3495a2ab2e7537d070"
bpy.ops.wm.open_mainfile(filepath=str(source))
b = bpy.data.objects["SK_BlenderStudioHuman"]
r = bpy.data.objects["RIG_BlenderStudioHuman"]
R = np.array([v.co[:] for v in b.data.vertices])
names = [g.name for g in b.vertex_groups]
W = np.zeros((len(R), len(names)))
for v in b.data.vertices:
    for g in v.groups:
        W[v.index, g.group] = g.weight
E = np.array([e.vertices[:] for e in b.data.edges])
adj = [[] for _ in R]
for u, v in E:
    adj[u].append(int(v))
    adj[v].append(int(u))

def weights(name):
    return W[:, names.index(name)]

def depth(mask):
    d = np.full(len(R), -1, int)
    q = deque()
    for i in np.flatnonzero(mask):
        if any(not mask[j] for j in adj[i]):
            d[i] = 0
            q.append(int(i))
    while q:
        i = q.popleft()
        for j in adj[i]:
            if mask[j] and d[j] < 0:
                d[j] = d[i] + 1
                q.append(j)
    return d

old = json.loads((F / "fold3-binding-report.json").read_text())
transfer = json.loads((F / "binding4-report.json").read_text())
transfer_ids = np.zeros(len(R), bool)
transfer_ids[[row["id"] for row in transfer["vertices"]]] = True
head_neck = weights("Head") + weights("Neck") > 0
support = set()
support_report = json.loads((F / "support2-solve.json").read_text())
for ids in support_report["knee_source_ids"].values():
    support.update(ids)
for ids in support_report["reference_1512_patch_ids"].values():
    support.update(ids)
for rows in json.loads((F / "fold3-proof-report.json").read_text())["metrics"].values():
    for row in rows:
        support.update(row["forehead_ids"])
protected_groups = [n for n in names if n in ["Head", "Neck"] or "Hand" in n or "Foot" in n or "ToeBase" in n
                    or any(digit in n for digit in ["Thumb", "Index", "Middle", "Ring", "Little"])]
support.update(np.flatnonzero(W[:, [names.index(n) for n in protected_groups]].sum(1) > 0).tolist())
protected = np.zeros(len(R), bool)
protected[list(support)] = True
domains = []
current = W.copy()
for row in old["edits"]:
    current[row["source_index"]] = 0
    for name, value in row["new"].items():
        current[row["source_index"], names.index(name)] = value
for row in transfer["vertices"]:
    current[row["id"]] = 0
    for name, value in row["after"].items():
        current[row["id"], names.index(name)] = value

def quintic(x):
    return x * x * x * (10 + x * (-15 + 6 * x))

def sparse_blend(c, o, alpha):
    """C1 endpoint interpolation with at most four simultaneous influences."""
    if alpha == 0:
        return c.copy()
    if alpha == 1:
        return o.copy()
    ci = set(np.flatnonzero(c > 0).tolist())
    oi = set(np.flatnonzero(o > 0).tolist())
    if len(ci | oi) <= 4:
        return (1 - alpha) * c + alpha * o
    # Free only the necessary slots before adding original-only groups. Route
    # their mass into the strongest shared original group; this avoids a
    # discontinuous top-four projection along the spatial feather.
    anchor = max(ci & oi, key=lambda k: (o[k], names[k]))
    bridge = c.copy()
    remove = sorted(ci - oi, key=lambda k: (c[k], names[k]))[:len(ci | oi) - 4]
    for k in remove:
        bridge[anchor] += bridge[k]
        bridge[k] = 0
    if alpha <= .5:
        t = quintic(2 * alpha)
        return (1 - t) * c + t * bridge
    t = quintic(2 * alpha - 1)
    return (1 - t) * bridge + t * o

def as_weights(row):
    return {names[k]: float(row[k]) for k in np.flatnonzero(row > 0)}

final_domains = []
all_alpha = np.zeros(len(R))
all_result = current.copy()

def solve_domain(name, envelope, core):
    d = depth(envelope)
    boundary = envelope & (d == 0)
    assert not np.any(core & boundary)
    unknown = np.flatnonzero(envelope & ~boundary & ~core)
    lookup = {int(i): j for j, i in enumerate(unknown)}
    L = np.zeros((len(unknown), len(unknown)))
    rhs = np.zeros(len(unknown))
    for i, k in lookup.items():
        L[k, k] = len(adj[i])
        for j in adj[i]:
            if j in lookup:
                L[k, lookup[j]] -= 1
            elif core[j]:
                rhs[k] += 1
    potential = np.zeros(len(R))
    potential[core] = 1
    if len(unknown):
        potential[unknown] = np.linalg.solve(L, rhs)
    assert potential.min() >= -1e-12 and potential.max() <= 1 + 1e-12
    potential = np.clip(potential, 0, 1)
    alpha = quintic(potential)
    alpha[core] = 1
    alpha[boundary | ~envelope] = 0
    ids = np.flatnonzero(alpha > 0)
    assert not np.any(all_alpha[ids] > 0)
    rows = []
    for i in ids:
        value = sparse_blend(current[i], W[i], alpha[i])
        assert np.count_nonzero(value > 0) <= 4
        # Preserve original float weights exactly at the core; their stored
        # normalization has float32 roundoff rather than exact arithmetic one.
        assert abs(value.sum() - 1) < 1e-6
        if core[i]:
            assert np.array_equal(value, W[i])
        all_result[i] = value
        all_alpha[i] = alpha[i]
        rows.append({"id": int(i), "blend": float(alpha[i]),
                     "original_weights": as_weights(W[i]), "replacement_weights": as_weights(value)})
    final_domains.append({"name": name, "envelope_ids": np.flatnonzero(envelope).tolist(),
                          "core_ids": np.flatnonzero(core).tolist(),
                          "zero_boundary_ids": np.flatnonzero(boundary).tolist(),
                          "feather_ids": [int(i) for i in ids if not core[i]],
                          "harmonic_residual": float(abs(L @ potential[unknown] - rhs).max()) if len(unknown) else 0,
                          "vertices": rows})

for side, sign in [("Left", 1), ("Right", -1)]:
    inherited = next(d for d in old["domains"] if d["domain"] == side + "_shoulder_harmonic")
    shoulder_domain = np.zeros(len(R), bool)
    shoulder_domain[inherited["source_indices"]] = True
    # The inherited shoulder envelope reaches down into the waist repair.
    # Preserve that entire existing partition; only the independently derived
    # lateral-femur domain below may roll back any binding4-edited vertex.
    shoulder_domain &= ~protected & ~transfer_ids
    shoulder_core = shoulder_domain & (weights(side + "Shoulder") > 0) & (weights(side + "Arm") > 0)
    sh_depth = depth(shoulder_domain)
    femur = weights(side + "UpLeg")
    # The original skin assigns a strict majority to this femur. The lateral
    # half-space is defined by the source femoral head, not an authored box.
    hip_domain = (transfer_ids & (femur > W.sum(1) - femur)
                  & (sign * R[:, 0] > sign * r.data.bones[side + "UpLeg"].head_local.x)
                  & ~protected)
    hip_depth = depth(hip_domain)
    solve_domain(side + "_shoulder", shoulder_domain, shoulder_core & (sh_depth >= 2))
    solve_domain(side + "_lateral_femur", hip_domain, hip_domain & (hip_depth >= 2))
    domains.append({
        "side": side,
        "shoulder_domain_ids": np.flatnonzero(shoulder_domain).tolist(),
        "shoulder_core_ids": np.flatnonzero(shoulder_core).tolist(),
        "hip_domain_ids": np.flatnonzero(hip_domain).tolist(),
        "hip_depth": {str(i): int(hip_depth[i]) for i in np.flatnonzero(hip_domain)},
        "shoulder_witness_depth": {str(i): int(sh_depth[i]) for i in ([9583, 8398] if side == "Left" else [4287, 3141])},
        "hip_witness_depth": {str(i): int(hip_depth[i]) for i in ([8580, 8690] if side == "Left" else [3323, 3432])},
        "shoulder_core_depth_histogram": {str(i): int(np.count_nonzero(sh_depth[shoulder_core] == i)) for i in np.unique(sh_depth[shoulder_core])},
    })

report = {"original_source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(), "domains": domains,
          "protected_source_ids": sorted(support)}
(P / "rollback-domain-inspection.json").write_text(json.dumps(report, indent=2) + "\n")
required = [4287, 3141, 9583, 8398, 3323, 8580, 3432, 8690]
assert np.all(all_alpha[required] == 1)
assert np.all(all_alpha[protected] == 0)
assert np.array_equal(all_result[all_alpha == 0], current[all_alpha == 0])
upperwaist = transfer_ids & (R[:, 2] >= 1.04)
assert np.all(all_alpha[upperwaist] == 0)
mask_report = {
    "original_source": str(source.relative_to(P.parents[3])),
    "original_source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
    "base_binding": "kneeling-family/binding4-source.blend; no joint5 smoothing-derived shape key",
    "method": "Existing inherited shoulder envelope minus original Neck/Head, contact protection, and ALL binding4 waist-repair IDs. Shoulder core: original same Shoulder and Arm both positive and graph boundary depth>=2. Hip envelope: binding4-edited vertices, original same UpLeg strictly exceeds all other original weights combined, lateral to original femoral-head X plane, minus contact protection. Hip core: graph boundary depth>=2. Domain boundary at depth0 is exact zero; other feather vertices solve the original unweighted edge-graph Dirichlet Laplacian. Remap potential with 6t^5-15t^4+10t^3; core exact one and exterior exact zero.",
    "four_influence_interpolation": "When current+original group union<=4, interpolate with blend. Otherwise free the minimum number of slots by smoothly moving the smallest current-only weights into the strongest shared original group during blend0..0.5, then smoothly interpolate this bridge to original during0.5..1; both subintervals use quintic smootherstep. Replacement weights below are authoritative, so no top4 truncation is needed.",
    "protected_source_ids": sorted(support),
    "domains": final_domains,
    "checks": {
        "required_witnesses_exact_original": required,
        "protected_changed_count": int(np.count_nonzero(all_alpha[protected])),
        "upperwaist_at_or_above_original_transfer_end_1_04m_changed_count": int(np.count_nonzero(all_alpha[upperwaist])),
        "exterior_weights_bitwise_exact": bool(np.array_equal(all_result[all_alpha == 0], current[all_alpha == 0])),
        "changed_vertices": int(np.count_nonzero(all_alpha)),
        "maximum_influences": int(np.count_nonzero(all_result > 0, axis=1).max()),
        "normalization_max_error": float(abs(all_result.sum(1) - 1).max()),
    },
    "remaining_uncertainty": "This is a deterministic semantic rollback candidate, not a visually accepted pose. Same-pose shoulder/hip proofs and support/exterior readback remain required; no asset was edited or pose rebuilt.",
}
(P / "rollback-mask.json").write_text(json.dumps(mask_report, indent=2) + "\n")
print(json.dumps({"domains": [{"name": d["name"], "envelope": len(d["envelope_ids"]), "core": len(d["core_ids"]),
                                  "feather": len(d["feather_ids"]), "residual": d["harmonic_residual"]} for d in final_domains],
                  "checks": mask_report["checks"]}, indent=2))
