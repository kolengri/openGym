#!/usr/bin/env python3
"""Independently validate serialized briefs against current repository JSON sources."""

import functools
import gzip
import hashlib
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]


@functools.cache
def document(path):
    return json.loads((ROOT / path).read_text())


def main():
    with gzip.open(OUT / "briefs.jsonl.gz", "rt") as source:
        briefs = [json.loads(line) for line in source]
    aliases = json.loads((OUT / "aliases.json").read_text())
    report = json.loads((OUT / "coverage-report.json").read_text())
    rows = {p.stem: json.loads(p.read_text()) for p in (ROOT / "catalogue/exercises").glob("*.json")}
    by_id = {b["id"]: b for b in briefs}
    canonical = {b["id"]: b for b in briefs if b["record_kind"] == "canonical"}
    checks = 0
    refs = 0
    errors = []

    def require(condition, message):
        nonlocal checks
        checks += 1
        if not condition:
            errors.append(message)

    def walk(value):
        nonlocal refs
        if isinstance(value, dict):
            if {"path", "pointer", "quote"}.issubset(value):
                try:
                    original = document(value["path"])
                    for part in value["pointer"].split("/")[1:]:
                        part = part.replace("~1", "/").replace("~0", "~")
                        original = original[int(part)] if isinstance(original, list) else original[part]
                    require(original == value["quote"], f"Evidence value changed: {value['path']}#{value['pointer']}")
                except (KeyError, ValueError, IndexError, OSError) as exc:
                    require(False, f"Evidence not resolvable: {value['path']}#{value['pointer']}: {exc}")
                refs += 1
            for v in value.values():
                walk(v)
        elif isinstance(value, list):
            for v in value:
                walk(v)

    require(len(briefs) == len(by_id) == len(rows) == 6554, "Expected all 6,554 source records exactly once")
    packed = (OUT / "briefs.jsonl.gz").read_bytes()
    require(packed[4:8] == b"\0\0\0\0" and not packed[3] & 8, "Gzip has nondeterministic time/filename headers")
    if (OUT / "briefs.jsonl").exists():
        require(gzip.decompress(packed) == (OUT / "briefs.jsonl").read_bytes(), "Compressed JSONL differs from local raw copy")
    require(set(rows) == set(by_id), "Serialized brief IDs differ from source IDs")
    require(len(canonical) == 5632 and len(aliases) == 922, "Canonical/alias counts changed")
    for b in briefs:
        ident = b["id"]
        row = rows[ident]
        target = b["canonical_id"]
        require(target in canonical, f"Missing canonical target: {ident}")
        require(b["source"]["original_record"] == row, f"Original source record not retained: {ident}")
        require(b["source"]["sha256"] == hashlib.sha256((ROOT / b["source"]["path"]).read_bytes()).hexdigest(), f"Source hash stale: {ident}")
        require([s["text"] for s in b["movement"]["phases"]] == rows[target]["instructions"], f"Incomplete/reordered movement steps: {ident}")
        require([s["step_number"] for s in b["movement"]["phases"]] == list(range(1, len(rows[target]["instructions"]) + 1)), f"Invalid step numbering: {ident}")
        for field in ("starting_position", "arms_hands", "legs_feet"):
            f = b[field]
            require(bool(f["cues"]) or (f["status"] == "missing_in_source" and bool(f["missing_detail"])), f"Undisclosed missing cue: {ident}/{field}")
        require(bool(b["muscles"]["primary"]) and "secondary" in b["muscles"], f"Missing muscle labels: {ident}")
        require(b["status"] == ("needs_review" if b["review_reasons"] else "source_complete_for_storyboard"), f"Misleading review status: {ident}")
        require(b["animation_ready"] is False, f"Unreviewed animation marked ready: {ident}")
        for field in ("starting_position", "arms_hands", "legs_feet", "equipment_contacts"):
            p = b["authored_staging"][field]
            require(bool(p["proposal"]) and bool(p["status"]) and "authoring_basis" in p, f"Missing authored staging contract: {ident}/{field}")
            require(p["source_verified"] == (p["status"] == "source_cue_reuse"), f"Authored choice falsely source verified: {ident}/{field}")
        require(b["storyboard_readiness"]["status"] == ("blocked_on_source_resolution" if b["storyboard_readiness"]["blockers"] else "proposal_ready_for_review"), f"Wrong storyboard readiness: {ident}")
        if b["record_kind"] == "alias":
            require(row["variantOf"] == b["alias_resolution"]["resolution_chain"][1], f"Incorrect alias edge: {ident}")
            for field in ("starting_position", "movement", "arms_hands", "legs_feet", "equipment_scene", "muscles", "review_reasons", "source_constraints", "authored_staging", "source_completeness", "storyboard_readiness"):
                require(b[field] == canonical[target][field], f"Alias inherited fields differ: {ident}/{field}")
        walk(b)
    expected_aliases = {ident: row["variantOf"] for ident, row in rows.items() if "variantOf" in row}
    require({a["id"]: a["resolution_chain"][1] for a in aliases} == expected_aliases, "Alias edge table differs from current catalogue")
    require(any(p["prop_id"] == "bench_hyper45" and p["status"] == "conflict" for p in canonical["0002"]["equipment_scene"]["props"]), "0002 bench false-positive not flagged")
    selected = sorted([b for b in canonical.values() if b["equipment_scene"]["equipment_free_candidate"]], key=lambda b: (b["name"].casefold(), b["id"]))[:5]
    selected_ids = [b["id"] for b in selected]
    require(selected_ids == ["5965", "5915", "5887", "0001", "9066"], "First-five selection changed")
    require(json.loads((OUT / "selected-first-five.json").read_text())["briefs"] == selected, "Selected samples differ from full deliverable")
    require(any(r["code"] == "movement_pattern_unspecified" for r in canonical["5965"]["review_reasons"]), "Unspecified 5965 footfall pattern was not retained as a gap")
    require(any(r["code"] == "arms_hands_missing" for r in canonical["9066"]["review_reasons"]), "Missing 9066 arm cue was not retained as a gap")
    for ident in ("0034", "0035", "0036", "0025"):
        require("initial_body_support_unresolved" not in canonical[ident]["storyboard_readiness"]["blockers"], f"Explicit supported-lying setup falsely blocked: {ident}")
    require(canonical["0833"]["authored_staging"]["pose_class"] == "standing", "Heels hanging off a platform misclassified as a hanging body")
    require(canonical["0009"]["storyboard_readiness"]["status"] == "proposal_ready_for_review", "Documented generic machine contacts blocked by inventory subtype classification")
    selected_document = json.loads((OUT / "selected-first-five.json").read_text())
    override = selected_document["authoring_overrides"]["5965"]
    require(override["source_verified"] is False and "two quick lateral shuffle steps" in override["movement_interpretation"], "Selected pilot interpretation missing or falsely source-verified")
    walk(override)
    require("animation_authoring_override" not in canonical["5965"], "Pilot-only interpretation leaked into canonical source brief")
    # Inspect the actual embedded payload, not just the generator's memory.
    page = (OUT / "index.html").read_text()
    embedded = page.split('<script id="data" type="application/json">', 1)[1].split('</script>', 1)[0]
    index = json.loads(embedded)
    require({b["id"] for b in index["briefs"]} == set(canonical), "HTML index coverage differs from canonical JSONL")
    require(index["aliases"] == aliases, "HTML alias navigation differs from alias table")
    require("__DATA__" not in page, "HTML template substitution failed")
    require(len(page.encode()) < 6_000_000, "HTML index is no longer lightweight; move full records to detail chunks")
    chunk_rows = {}
    for p in sorted((OUT / "details").glob("chunk-*.json.gz")):
        with gzip.open(p, "rt") as source:
            detail = json.load(source)
        for b in detail["briefs"]:
            require(b["id"] not in chunk_rows, f"Duplicate record in detail chunks: {b['id']}")
            chunk_rows[b["id"]] = b
    require(chunk_rows == canonical, "Detail JSON chunks differ from canonical JSONL")
    detail_pages = {}
    for summary in index["briefs"]:
        b = canonical[summary["id"]]
        require(summary["source_status"] == b["status"] and summary["storyboard_status"] == b["storyboard_readiness"]["status"], f"Index readiness stale: {b['id']}")
        page_path, fragment = summary["detail_page"].split("#")
        if page_path not in detail_pages:
            detail_pages[page_path] = (OUT / page_path).read_text()
        doc = detail_pages[page_path]
        require(f'<article id="{fragment}">' in doc, f"Broken readable record link: {b['id']}")
        require(summary["detail_json"] == page_path.replace(".html", ".json.gz") and (OUT / summary["detail_json"]).is_file(), f"Compressed detail JSON link inconsistent: {b['id']}")
    for source in report["input_files"]:
        require(hashlib.sha256((ROOT / source["path"]).read_bytes()).hexdigest() == source["sha256"], f"Input hash changed: {source['path']}")
    receipt = {
        "passed": not errors, "assertions": checks, "evidence_references_checked": refs,
        "records": len(briefs), "canonical": len(canonical), "aliases": len(aliases),
        "first_five_ids": selected_ids, "errors": errors,
        "files": [{"path": str(p.relative_to(ROOT)), "bytes": p.stat().st_size,
                   "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
                  for p in sorted(OUT.rglob("*")) if p.is_file() and p.name != "verification.json"
                  and p.name != "briefs.jsonl" and p.suffix not in {".log", ".pyc"}
                  and not (p.parent.name == "details" and p.suffix == ".json")],
    }
    (OUT / "verification.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({k: v for k, v in receipt.items() if k != "files"}, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
