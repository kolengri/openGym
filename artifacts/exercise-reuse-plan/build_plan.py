#!/usr/bin/env python3
"""Reproducible, text-only reuse planning. No production clip equivalence is inferred."""
import csv
import gzip
import hashlib
import html
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent

# Ordered, deliberately separate mechanical controllers. Compound patterns win first.
FAMILIES = [
    ("self_myofascial_release", r"massage|foam roll|myofascial|\broll (?:calf|glute|hip|lat|quad|hamstring|back)"),
    ("neck_motion", r"neck|cervical"),
    ("compound_sequence", r"burpee|clean.{0,15}(?:press|jerk)|snatch|turkish get|thruster|man maker|devil.?s press|complex|combination"),
    ("clean", r"\bclean\b"),
    ("jerk_push_press", r"\bjerk\b|push press"),
    ("ninety_ninety_hip_stretch", r"90 to 90|90/90"),
    ("heel_touch", r"heel touch"),
    ("wrist_extension", r"reverse wrist curl|wrist extension"),
    ("wrist_flexion", r"wrist curl|wrist flexion"),
    ("wrist_rotation", r"wrist rotation|wrist twist|pronation|supination"),
    ("finger_grip", r"finger|gripper|hand grip|hand squeeze"),
    ("elbow_flexion", r"biceps|bicep|hammer curl|spider curl|preacher curl|concentration curl|zottman|reverse curl|drag curl|bayesian curl"),
    ("elbow_extension", r"triceps|tricep|skull crush|tate press|jm press|pushdown|push down"),
    ("knee_flexion", r"leg curl|legcurl|hamstring curl|nordic|inverse leg curl"),
    ("knee_extension", r"leg extension|legextension|knee extension"),
    ("shoulder_rear_raise", r"rear delt|reverse fly|rear fly|reverse pec"),
    ("chest_fly", r"chest fly|pec fly|flye|\bfly\b|cross.?over|pec deck"),
    ("push_up", r"push[ -]?up|press[ -]?up"),
    ("dip", r"\bdips?\b"),
    ("vertical_pull", r"pull[ -]?up|chin[ -]?up|pulldown|pull down|lat pull|sternum chin|gorilla chin"),
    ("upright_row", r"upright row|sumo high pull"),
    ("horizontal_pull", r"\brow\b|rowing|face pull"),
    ("overhead_press", r"shoulder press|overhead press|military press|arnold press|pike press|z press"),
    ("chest_press", r"bench press|chest press|floor press|incline press|decline press|squeeze press|guillotine press"),
    ("pullover", r"pullover|pull over|straight arm.*pull"),
    ("shoulder_lateral_raise", r"lateral raise|side raise|iron cross"),
    ("shoulder_front_raise", r"front raise|front shoulder raise"),
    ("shoulder_rotation", r"internal rotation|external rotation|rotator cuff|cuban|shoulder rotation"),
    ("scapular_motion", r"shrug|scapular|serratus"),
    ("squat", r"squat"),
    ("lunge", r"lunge"),
    ("step_up_down", r"step[ -]?up|step[ -]?down"),
    ("leg_press", r"leg press|negative press"),
    ("hip_hinge", r"deadlift|good morning|romanian|stiff leg|hip hinge|rack pull|pull through"),
    ("hip_extension_bridge", r"hip thrust|glute bridge|butt bridge|hip bridge|frog pump"),
    ("hip_extension_kickback", r"kickback|kick back|donkey kick|hip extension"),
    ("hip_abduction", r"abduct|clamshell|clam shell|fire hydrant"),
    ("hip_adduction", r"adduct|copenhagen"),
    ("calf_raise", r"calf raise|heel raise|donkey calf|calf press"),
    ("ankle_dorsiflexion", r"tibialis|reverse calf|toe raise|dorsiflex"),
    ("leg_raise", r"leg raise|knee raise|leg lift|knee lift|captain.?s chair"),
    ("trunk_flexion", r"crunch|sit[ -]?up|situp|curl[ -]?up|jack[ -]?knife|cocoon|v[ -]?up"),
    ("hip_rotation_mobility", r"hip (?:rotation|rotator)|hip twist|hip circle"),
    ("trunk_rotation", r"twist|wood[ -]?chop|rotation|rotational|windmill|wiper"),
    ("trunk_lateral_flexion", r"side bend|lateral bend|side flexion"),
    ("trunk_extension", r"back extension|hyperextension|hyper extension|superman|reverse hyper"),
    ("plank", r"plank|hollow body|hollow hold|dead bug|bird dog"),
    ("rollout", r"roll[ -]?out|ab wheel"),
    ("hip_flexion_running", r"mountain climber|high knee|march"),
    ("loaded_carry", r"carry|farmers|farmer.?s|yoke walk|suitcase walk|waiter.?s walk"),
    ("swing", r"\bswing\b"),
    ("jump_hop_bound", r"jump|\bhop\b|bound|plyometric|pogo"),
    ("locomotion_run", r"\brun\b|running|sprint|jog"),
    ("locomotion_walk", r"walk|walking|treadmill"),
    ("crawl", r"crawl"),
    ("cardio_pedal", r"bike|cycling|bicycle|elliptical|ergometer"),
    ("cardio_step", r"stepmill|stepper|stair"),
    ("rope_motion", r"battle rope|battling rope|rope climb|rope pull|rope wave"),
    ("throw_slam", r"throw|slam|toss|shot put"),
    ("combat", r"punch|boxing|kick|karate"),
    ("sled_push_pull", r"sled|prowler|tank push"),
    ("neck_motion", r"neck|cervical"),
    ("ankle_foot_mobility", r"ankle|foot|feet|toe"),
    ("shoulder_arm_mobility", r"shoulder|arm circle|arm swing|arm stretch|chest stretch|pectoral stretch|lat stretch"),
    ("spinal_mobility", r"cat|cow|cobra|spine|spinal|thoracic|child.?s pose|child pose|back stretch|back twist"),
    ("hip_leg_mobility", r"hip|hamstring|glute|quadriceps|quad stretch|groin|butterfly|pigeon|piriformis|lizard|calf stretch|leg stretch|seated forward|standing forward"),
    ("yoga_balance", r"yoga|pose|warrior|triangle|tree|lotus|downward dog|sun salutation|handstand|headstand|planche"),
    ("self_myofascial_release", r"massage|foam roll|roller|myofascial"),
    # Generic curl is intentionally last, after wrist/leg/trunk-specific matches.
    ("elbow_flexion", r"\bcurl\b"),
]
FAMILIES = [(k, re.compile(v)) for k, v in FAMILIES]

# Flags are candidate-planning bins, never the authoritative movement specification.
# Complete ordered source instructions remain in every JSON mapping row.
AXES = {
    "inclination": r"incline|decline|flat bench|horizontal|vertical|45.degree|90.degree",
    "laterality": r"alternat(?:e|ing)|unilateral|bilateral|single[ -](?:arm|leg)|one[ -](?:arm|leg)|both (?:arms|legs)|each (?:arm|leg)|opposite|same side",
    "grip_orientation": r"overhand|underhand|neutral grip|reverse grip|mixed grip|wide grip|close grip|narrow grip|palms (?:facing )?(?:up|down|inward|outward|forward|backward|each other)|supinat\w*|pronat\w*|thumbs? (?:up|down)|hammer grip",
    "support_contact": r"hands? (?:on|behind|under|against)[^.;,]{0,55}|feet (?:flat|on|off|planted)[^.;,]{0,40}|legs? (?:raised|up)|chest.support|back (?:against|on)|forearms? on|knees? on|elbows? on|seated|sitting|standing|kneeling|lying|hanging|supine|prone",
    "load_position": r"overhead|front rack|back rack|goblet|zercher|suitcase|behind (?:the |your )?(?:back|neck|head)|at (?:your |the )?(?:chest|shoulders?|sides?|hips?)|on (?:your |the )?(?:shoulders?|chest|hips?)",
    "range": r"\b\d+(?:[./-]\d+)?\s*(?:degree|°|percent|%|inch|cm|second|sec|reps?)s?\b|half|quarter|partial|full range|deep|parallel|straight (?:arms|legs)|bent (?:arms|legs|knees)|lockout",
    "temporal_mode": r"isometric|static|hold|pause|slow(?:ly)?|negative|eccentric|explosive|ballistic|jump|hop|bounce|sprint|pulse|dynamic|rhythmic",
    "cable_path": r"high pulley|low pulley|chest.height|shoulder.height|ankle.height|cable (?:above|below|behind|in front)|from (?:above|below)|cross.?body",
}
AXES = {k: re.compile(v) for k, v in AXES.items()}
PROTECTED = {
    "4007": "Legs raised with knees at 90 degrees; do not reuse feet-planted 6428 unchanged.",
    "6428": "Feet planted; do not reuse raised-leg 4007 unchanged.",
    "10565": "90/90 forward hinge; hand contact is unspecified. Shared hip setup with 6560 is only a candidate.",
    "6560": "90/90 hinge explicitly has hands on floor. Preserve hand support; not identical to 10565.",
}
IDENTITY_EXCLUSIONS = {"id", "femaleVariant", "maleVariant", "textSource"}


def packed(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def digest(value):
    return hashlib.sha256(packed(value).encode()).hexdigest()[:16]


def write_json(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def gz_jsonl(name, rows):
    # Stable gzip header makes repeated generation byte-identical.
    with open(OUT / name, "wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as zipped:
            for row in rows:
                zipped.write((packed(row) + "\n").encode())


def source_fields(source):
    yield "/name", source["name"]
    yield "/description", source["description"]
    for i, value in enumerate(source["instructions"]):
        yield f"/instructions/{i}", value


def classify(source):
    title = source["name"].lower()
    for family, rule in FAMILIES:
        match = rule.search(title)
        if match:
            return family, match.group(), "medium: title pattern; inspect ordered source before sharing motion"
    return "individual_review", "", "low: no supported mechanical family rule"


def title_subtype(source):
    """Keep all semantic name residue: a pike push-up can never become a normal push-up.

    Only display-only view/figure labels, the equipment enum and already represented
    equipment words are removed. Variant/version numbers remain unknown distinctions.
    """
    title = source["name"].lower()
    title = re.sub(r"\b(?:front|back|side|rear)\s+(?:view|pov)\b|\b(?:male|female)\b", " ", title)
    equipment_words = r"\b(?:dumbbells?|barbells?|kettlebells?|ez barbell|ez bar|cable|band|resistance band|smith|lever|leverage machine|bodyweight|body weight|weighted|suspension|bottle)\b"
    title = re.sub(equipment_words, " ", title)
    return re.sub(r"[^a-z0-9°/]+", " ", title).strip()


GENERATOR_CONTRACTS = {
    "elbow_flexion": {
        "reuse": "Elbow-flexion phase curve, fixed upper-arm frame option, coupled or independent hand targets, return/pause/side sequencing.",
        "parameters": "Supported pose, upper-arm direction, shoulder contribution, elbow ROM, forearm rotation, grip width, load contact, left/right timing, preacher/incline supports.",
        "split": "Standing/seated/preacher/spider/incline support or shoulder frames; shared-bar vs independent loads; hammer/supinated/reverse grips; alternating vs simultaneous; stretch-only forms.",
    },
    "squat": {
        "reuse": "Pelvis trajectory and knee/hip bend scaffold, planted-foot IK, lowering/rising/hold/landing stages.",
        "parameters": "Stance width/toe direction, depth, trunk lean, load location, foot supports, unilateral balance, machine constraints, timing.",
        "split": "Split/pistol/assisted and bilateral supports; front/back/goblet loads; jump/landing vs slow squat; Smith/hack/pendulum/belt axes; painful or unspecified range is never invented.",
    },
    "horizontal_pull": {
        "reuse": "Scapula/shoulder/elbow target coordination, pull/return phase scaffold and resistance endpoint connection.",
        "parameters": "Torso inclination, seat/chest support, hand spacing/orientation, elbow plane, endpoint height, anchor, cable routing and bilateral coupling.",
        "split": "Chest-supported/seated/bent-over/inverted support; unilateral vs bilateral; free load vs cable vs lever; axis or contact changes. Upright rows belong to a separate family.",
    },
    "chest_press": {
        "reuse": "Coordinated upper-arm/forearm press/return targets with torso support frame and optional shared-load constraint.",
        "parameters": "Bench angle, elbow plane, grip, ROM, hand spacing, independent/shared load, torso/feet supports, machine handle path.",
        "split": "Flat/incline/decline/floor/standing frames; bar vs independent dumbbells; one-arm stability; machine pivot vs free path; reverse/neutral/wide grip and pauses remain explicit profiles.",
    },
    "overhead_press": {
        "reuse": "Overhead shoulder/elbow trajectory scaffold, torso stabilization, lockout/return phase sequencing.",
        "parameters": "Seat/standing support, scapular/shoulder path, grip, front/behind load path, independent hand timing, machine axes and ROM.",
        "split": "Seated/standing and one-/two-arm frames; behind-neck paths; Arnold rotation; push-press/jerk ballistic leg drive are a separate family, never implicit retiming.",
    },
    "hip_hinge": {
        "reuse": "Hip-hinge/trunk-frame scaffold with pelvis trajectory, planted-foot constraints and linked hand/load targets.",
        "parameters": "Knee bend, stance, hip depth, torso angle, hand/load location, ROM endpoint, unilateral support and resistance path.",
        "split": "Romanian/stiff/conventional/sumo/trap/behind-back/good-morning and single-leg mechanics need explicit sub-generators; rack pulls retain partial range; lever/cable axes remain distinct.",
    },
    "push_up": {
        "reuse": "Closed-chain hand/foot support solving, torso frame and elbow-flexion press phases.",
        "parameters": "Hand/foot surfaces and heights, support count, body line, hand orientation/width, elbow plane, tempo and transition phases.",
        "split": "Pike/planche/hindu/cobra/kneeling/decline/incline/ball forms retain distinct paths/support graphs; hand-release/plyometric variants require explicit release/landing events.",
    },
    "vertical_pull": {
        "reuse": "Hanging or seated torso setup, shoulder/elbow pull/return phases and hand-anchor constraints.",
        "parameters": "Grip, hand spacing, body support/assistance, torso lean, load path, leg placement, ROM and side coordination.",
        "split": "Pull-up body travel vs pulldown handle travel; assisted support; unilateral loading, kipping/ballistic and static hangs; pulley/machine axes are explicit.",
    },
    "trunk_flexion": {
        "reuse": "Segmented trunk-flexion curve and controlled return/hold stages with supported pelvis frame.",
        "parameters": "Hip flexion, foot/leg supports, hand position, torso range, load placement, bench angle, tempo and side order.",
        "split": "Crunch vs sit-up vs reverse-crunch/leg-driven action; planted vs raised legs; shortened/negative/weighted variants. Identical instruction boilerplate does not erase name/description differences.",
    },
    "ninety_ninety_hip_stretch": {
        "reuse": "Seated 90/90 hip setup, forward-hinge hold and side-switch scaffold.",
        "parameters": "Front/side leg geometry, trunk hinge range, hand support graph, hold duration and transition order.",
        "split": "10565 has unspecified hands, 6560 explicitly hands on floor. Do not silently use a floor hand constraint for both.",
    },
}


def parameters(brief, prop_ids, prop_by_id):
    source = brief["source"]["original_record"]
    evidence = {}
    for key, rule in AXES.items():
        evidence[key] = [
            {"pointer": pointer, "quote": value, "matched_cues": sorted(set(m.group() for m in rule.finditer(value.lower())))}
            for pointer, value in source_fields(source) if rule.search(value.lower())
        ]
    flags = {key: sorted({cue for row in rows for cue in row["matched_cues"]}) for key, rows in evidence.items()}
    # Exact source names retained in evidence; bins only expose controller candidates.
    parent_props = sorted({prop_by_id[p]["parent_id"] or p for p in prop_ids})
    machines = [p for p in parent_props if prop_by_id[p]["category"] == "machine"]
    load = source["equipment"]
    signature = {
        "pose": brief["authored_staging"]["pose_class"],
        "category": source["category"],
        "load_control": load,
        "scene_bases": parent_props,
        "machine_axes_separate": machines,
        "flags": flags,
        "protected": source["id"] if source["id"] in PROTECTED else None,
    }
    return signature, evidence


def main():
    inputs = [
        ROOT / "artifacts/exercise-animation-briefs/briefs.jsonl.gz",
        ROOT / "artifacts/exercise-animation-briefs/aliases.json",
        ROOT / "artifacts/exercise-props-inventory/inventory.json",
        ROOT / "artifacts/exercise-props-inventory/exercise-coverage.json",
        ROOT / "artifacts/exercise-props-inventory/summary.json",
    ]
    with gzip.open(inputs[0], "rt") as stream:
        briefs = [json.loads(line) for line in stream]
    aliases = json.loads(inputs[1].read_text())
    props = json.loads(inputs[2].read_text())
    coverage = json.loads(inputs[3].read_text())
    prop_summary = json.loads(inputs[4].read_text())
    canonical = sorted((b for b in briefs if b["record_kind"] == "canonical"), key=lambda b: b["id"])
    by_id = {b["id"]: b for b in canonical}
    prop_by_id = {p["canonical_id"]: p for p in props}
    coverage_by_id = {r["exercise_id"]: r for r in coverage}
    assert len(by_id) == len(canonical) == 5632
    assert len(briefs) == 6554 and len(aliases) == 922
    assert set(by_id) == set(coverage_by_id)
    assert not set(by_id) & {a["id"] for a in aliases}
    assert all(a["canonical_id"] in by_id for a in aliases)
    assert len({a["id"] for a in aliases}) == len(aliases)
    alias_hashes = {}
    for alias in aliases:
        chain = alias["resolution_chain"]
        assert chain[0] == alias["id"] and chain[-1] == alias["canonical_id"]
        assert len(chain) == len(set(chain)), "Alias cycle"
        for index, alias_id in enumerate(chain[:-1]):
            raw = (ROOT / "catalogue/exercises" / f"{alias_id}.json").read_bytes()
            assert json.loads(raw)["variantOf"] == chain[index + 1]
            alias_hashes[alias_id] = hashlib.sha256(raw).hexdigest()
    assert {p.stem for p in (ROOT / "catalogue/exercises").glob("*.json")} == set(by_id) | {a["id"] for a in aliases}

    exact_groups, instructions_groups = defaultdict(list), defaultdict(list)
    source_hashes = {}
    for b in canonical:
        s = b["source"]["original_record"]
        raw = (ROOT / b["source"]["path"]).read_bytes()
        actual = json.loads(raw)
        assert actual == s, f"Catalogue and brief disagree for {b['id']}"
        source_hashes[b["id"]] = hashlib.sha256(raw).hexdigest()
        exact_groups[packed({k: v for k, v in s.items() if k not in IDENTITY_EXCLUSIONS})].append(b["id"])
        instructions_groups[packed(s["instructions"])].append(b["id"])
    exact_owner = {i: min(ids) for ids in exact_groups.values() for i in ids}
    duplicate_groups = [ids for ids in exact_groups.values() if len(ids) > 1]
    assert {tuple(ids) for ids in duplicate_groups} == {("0576", "0577"), ("0655", "0656")}, "Reconcile changed exact pairs before regenerating narrative examples"
    repeated_instruction_groups = [ids for ids in instructions_groups.values() if len(ids) > 1]
    rows = []
    for b in canonical:
        s, i = b["source"]["original_record"], b["id"]
        family, match, confidence = classify(s)
        prop_ids = sorted(p["canonical_id"] for p in coverage_by_id[i]["props"])
        signature, axis_evidence = parameters(b, prop_ids, prop_by_id)
        signature["semantic_title_subtype"] = title_subtype(s)
        # Fine key intentionally retains every detected literal cue and apparatus base.
        # Coarse key permits editorially reviewed controller parameterization, not clip identity.
        coarse = dict(signature)
        coarse["flags"] = {key: sorted({
            re.sub(r"[^a-z0-9]+", "_", cue).strip("_") for cue in cues
        }) for key, cues in signature["flags"].items() if key not in {"support_contact", "range", "load_position"}}
        # Preserve categorical support, range and load modes in the coarse scenario too.
        for key in ("support_contact", "range", "load_position"):
            coarse["flags"][key] = sorted({
                cue for cue in signature["flags"][key]
                if not cue.startswith(("hands ", "hand ", "feet ", "at ", "on ", "behind "))
            })
        individual = i if family == "individual_review" else None
        fine_id = "profile-" + digest([family, signature, individual])
        coarse_id = "parameter-profile-" + digest([family, coarse, individual])
        # Scaffolds share implementation primitives, never drop individual profiles.
        # Unclassified exercises remain one task each in both template scenarios.
        scaffold = [family, signature["pose"], signature["category"], individual]
        contract = scaffold + [signature["load_control"], signature["scene_bases"]]
        rows.append({
            "exercise_id": i, "name": s["name"], "family": family,
            "family_confidence": confidence, "family_evidence": {"path": b["source"]["path"], "pointer": "/name", "quote": s["name"], "matched_pattern": match},
            "reuse_class": "exact_source_duplicate" if exact_owner[i] != i else ("individual_review" if individual else "parameterized_family_candidate"),
            "exact_source_owner": exact_owner[i],
            "candidate_literal_profile": fine_id, "candidate_parameter_profile": coarse_id,
            "candidate_pose_template": "pose-template-" + digest(scaffold),
            "candidate_apparatus_template": "apparatus-template-" + digest(contract),
            "candidate_is_approved_clip": False,
            "reason": "Exact editorial content can share one resolved authoring specification; aliases and muscle/view/material settings remain separate configuration." if exact_owner[i] != i else "Reuse the rig and controller scaffolding; source order, geometry, contacts and timing require per-ID adjudication before any clip is shared.",
            "protected_distinction": PROTECTED.get(i),
            "equipment": s["equipment"], "prop_ids": prop_ids,
            "prop_coverage_status": coverage_by_id[i]["status"],
            "supported_prop_ids": sorted(p["prop_id"] for p in b["equipment_scene"]["props"] if p["status"] == "instruction_or_needs_supported"),
            "inventory_candidate_prop_ids": sorted(p["prop_id"] for p in b["equipment_scene"]["props"] if p["status"] != "instruction_or_needs_supported"),
            "parameter_signature": signature, "parameter_evidence": axis_evidence,
            "source_guards": {"name": s["name"], "description": s["description"], "ordered_instructions": s["instructions"], "hold": s.get("hold"), "needs": s.get("needs"), "target": s["target"], "secondary_muscles": s["secondaryMuscles"], "muscle_map": s.get("muscleMap")},
            "source_review_status": b["status"], "source_review_reasons": b["review_reasons"],
            "storyboard_status": b["storyboard_readiness"]["status"],
            "storyboard_blockers": b["storyboard_readiness"]["blockers"],
            "source_path": b["source"]["path"], "source_sha256": source_hashes[i],
        })

    # An exact-source pair may classify into distinct bins through external heuristic state;
    # the conservative scenario always adjudicates those two shared specifications once.
    exact_reductions = len(canonical) - len(exact_groups)
    scenarios = {}
    for label, key in [("literal_cue_profiles", "candidate_literal_profile"), ("parameterized_profiles", "candidate_parameter_profile")]:
        groups = defaultdict(list)
        for row in rows:
            groups[row[key]].append(row["exercise_id"])
        scenarios[label] = {
            "candidate_distinct_profiles": len(groups), "possible_duplicate_profile_reduction": len(rows) - len(groups),
            "multi_id_groups": sum(len(ids) > 1 for ids in groups.values()),
            "ids_in_multi_id_groups": sum(len(ids) for ids in groups.values() if len(ids) > 1),
            "status": "unvalidated planning scenario; each divergent source guard requires a parameter solution or split",
        }
    for label, key in [("shared_pose_templates", "candidate_pose_template"), ("apparatus_specific_templates", "candidate_apparatus_template")]:
        groups = defaultdict(list)
        for row in rows:
            groups[row[key]].append(row["exercise_id"])
        scenarios[label] = {
            "candidate_template_tasks": len(groups), "possible_repeated_scaffold_tasks_avoided": len(rows) - len(groups),
            "multi_id_groups": sum(len(ids) > 1 for ids in groups.values()),
            "ids_in_multi_id_groups": sum(len(ids) for ids in groups.values() if len(ids) > 1),
            "status": "estimated generator/scaffold tasks; all per-ID semantic/contact profiles survive; not a clip-equivalence claim",
        }

    prop_rows = []
    for p in props:
        unresolved = p["category"] == "unresolved"
        relation, parent = p["relation"], p["parent_id"]
        if unresolved:
            action = "Resolve implement identity and geometry before authoring; no assumed shared model."
        elif relation == "variant":
            action = "Reuse parent components and expose declared settings; verify contact/axis/load geometry before treating as configuration-only."
        elif relation == "attachment":
            action = "Build a reusable attachment module with its own contact/anchor; not a standalone parent apparatus."
        elif p["category"] == "machine":
            action = "Separate machine mechanism contract; share materials/fasteners/pads only until axis, travel and supports are checked."
        else:
            action = "One reusable base asset with per-exercise dimensions, placement and contact configuration."
        prop_rows.append({
            "prop_id": p["canonical_id"], "name": p["english_name"], "category": p["category"],
            "relation": relation, "parent_id": parent,
            "build_status": "unresolved" if unresolved else "buildable_inventory_candidate",
            "reuse_action": action, "confidence": "high for inventory relationship; geometry not validated",
            "exercise_count": p["exercise_count"], "exercise_ids": p["exercise_ids"],
            "evidence_tier": p["evidence_tier"], "tier_exercise_counts": p["tier_exercise_counts"],
            "source_evidence": p["examples"],
        })
    assert all(set(p["exercise_ids"]) <= set(by_id) for p in prop_rows)
    assert all(not p["parent_id"] or p["parent_id"] in prop_by_id for p in prop_rows)
    for prop in prop_rows:
        assert len(prop["exercise_ids"]) == len(set(prop["exercise_ids"])) == prop["exercise_count"]
        assert set(prop["exercise_ids"]) == {row["exercise_id"] for row in coverage if any(p["canonical_id"] == prop["prop_id"] for p in row["props"])}, prop["prop_id"]
    bases = [p for p in prop_rows if p["relation"] == "base" and p["build_status"] != "unresolved"]
    variants = [p for p in prop_rows if p["relation"] == "variant"]
    attachments = [p for p in prop_rows if p["relation"] == "attachment"]
    unresolved = [p for p in prop_rows if p["build_status"] == "unresolved"]
    machine_bases = [p for p in bases if p["category"] == "machine"]

    families = []
    for family, count in Counter(r["family"] for r in rows).most_common():
        members = [r for r in rows if r["family"] == family]
        families.append({
            "family": family, "exercise_count": count,
            "literal_cue_profiles": len({r["candidate_literal_profile"] for r in members}),
            "parameterized_profiles": len({r["candidate_parameter_profile"] for r in members}),
            "pose_templates": len({r["candidate_pose_template"] for r in members}),
            "apparatus_templates": len({r["candidate_apparatus_template"] for r in members}),
            "ids": [r["exercise_id"] for r in members],
            "examples": [{"id": r["exercise_id"], "name": r["name"], "source": r["source_path"]} for r in members[:8]],
            "approval": "candidate; family membership does not establish identical clips",
        })
    generator_recipes = []
    for family, contract in GENERATOR_CONTRACTS.items():
        members = [r for r in rows if r["family"] == family]
        # Pick examples spanning poses and apparatus, rather than first adjacent IDs only.
        examples, seen = [], set()
        for row in members:
            signature = row["parameter_signature"]
            variation = (signature["pose"], signature["load_control"], tuple(signature["scene_bases"]))
            if variation in seen:
                continue
            seen.add(variation)
            source = row["source_guards"]
            examples.append({"id": row["exercise_id"], "source_path": row["source_path"], "name": row["name"],
                "pose": signature["pose"], "equipment": row["equipment"], "props": row["prop_ids"],
                "description_evidence": {"pointer": "/description", "quote": source["description"]},
                "ordered_instruction_evidence": [{"pointer": f"/instructions/{j}", "quote": text} for j, text in enumerate(source["ordered_instructions"])],
                "source_review_status": row["source_review_status"], "review_codes": [r["code"] for r in row["source_review_reasons"]]})
            if len(examples) == 8:
                break
        generator_recipes.append({"family": family, "affected_candidate_exercises": len(members),
            "source_complete_for_storyboard": sum(r["source_review_status"] == "source_complete_for_storyboard" for r in members),
            "pose_template_candidates": len({r["candidate_pose_template"] for r in members}),
            "apparatus_template_candidates": len({r["candidate_apparatus_template"] for r in members}),
            "confidence": "medium: explicit named mechanics with supplied instruction evidence; shared generator design is proposed, not verified",
            "reusable_generator": contract["reuse"], "explicit_profile_parameters": contract["parameters"],
            "split_or_review_guards": contract["split"], "ids": [r["exercise_id"] for r in members], "source_examples": examples})
    catalogue_digest = hashlib.sha256(packed(source_hashes).encode()).hexdigest()
    summary = {
        "schema_version": "1.0.0", "source_basis": "Local English text and inventory only; no licensed media, embeddings or external requests.",
        "input_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs},
        "catalogue_content_sha256": catalogue_digest,
        "alias_source_content_sha256": hashlib.sha256(packed(alias_hashes).encode()).hexdigest(),
        "counts": {"catalogue_records": len(briefs), "canonical_exercises": len(canonical), "figure_aliases": len(aliases),
            "exact_editorial_duplicate_groups": len(duplicate_groups), "exact_editorial_reductions": exact_reductions,
            "distinct_editorial_specs_after_confirmed_reuse": len(exact_groups),
            "identical_instruction_groups": len(repeated_instruction_groups),
            "identical_instruction_only_potential_reduction_UNSAFE": sum(len(ids) - 1 for ids in repeated_instruction_groups),
            "family_buckets_including_individual_review": len(families),
            "individual_review_exercises": sum(r["family"] == "individual_review" for r in rows),
            "source_status": dict(Counter(r["source_review_status"] for r in rows)),
            "storyboard_status": dict(Counter(r["storyboard_status"] for r in rows)),
            "prop_coverage_status": dict(Counter(r["prop_coverage_status"] for r in rows)),
            "prop_rows": len(props), "buildable_base_props": len(bases), "prop_variants": len(variants), "prop_attachments": len(attachments), "unresolved_props": len(unresolved),
            "machine_base_contracts": len(machine_bases),
            "prop_exercise_incidences": sum(len(p["exercise_ids"]) for p in props),
            "unique_prop_affected_exercises": len({i for p in props for i in p["exercise_ids"]}),
        },
        "confirmed_reuse": {"alias_reference_tasks_avoided": len(aliases), "canonical_spec_tasks_avoided": exact_reductions,
            "canonical_duplicate_groups": duplicate_groups,
            "ready_shared_clips_confirmed": 0,
            "meaning": "References/specifications can share authoring. Neither identical text nor an alias proves a production clip is ready; unresolved mechanics must first be resolved."},
        "scenarios": scenarios,
        "base_clip_forecast": {"status": "conditional seed/generator task bracket; not approved or measured final clip count",
            "initial_seed_generator_lower": scenarios["shared_pose_templates"]["candidate_template_tasks"],
            "initial_seed_generator_upper": scenarios["apparatus_specific_templates"]["candidate_template_tasks"],
            "literal_profile_scenario": scenarios["literal_cue_profiles"]["candidate_distinct_profiles"],
            "source_safe_ceiling": len(exact_groups),
            "assumptions": ["One seed/generator demonstration per family/pose/category (lower) or additionally resistance/scene bases (upper); one individually reviewed seed per unclassified exercise.", "The shared generator accepts explicit per-ID motion subtype, contacts, grip, side order, amplitude and timing. Unsupported subtypes split the generator; separate final clips can still be baked for every ID.", "Every source difference is reviewed; no source gap permits invented mechanics. The bracket assumes parameter/controller implementation and may rise toward 5,630 separately resolved specifications if it fails.", "This counts repeated scaffold/seed authoring tasks only, excluding per-ID profiles, review, support solving, apparatus construction, rendering, and exports."]},
        "review_reason_counts": dict(Counter(reason["code"] for r in rows for reason in r["source_review_reasons"])),
        "props": {"base_ids": [p["prop_id"] for p in bases], "variant_ids": [p["prop_id"] for p in variants], "attachment_ids": [p["prop_id"] for p in attachments], "unresolved_ids": [p["prop_id"] for p in unresolved], "distinct_machine_contract_ids": [p["prop_id"] for p in machine_bases]},
        "upstream_inventory_issues": prop_summary["issues"],
        "checks": {"all_canonical_ids_assigned_once": len(rows) == len({r["exercise_id"] for r in rows}) == len(canonical), "aliases_excluded_from_motion_mapping": not bool({a["id"] for a in aliases} & {r["exercise_id"] for r in rows}), "aliases_resolve_to_canonical": True, "live_alias_chains_match": True, "whole_catalogue_partition_reconciles": True, "live_catalogue_matches_briefs": True, "prop_partition_reconciles": len(bases) + len(variants) + len(attachments) + len(unresolved) == len(props), "prop_parent_ids_valid": True, "prop_incidence_lists_match_coverage": True, "exact_duplicate_pairs_reconciled": True, "protected_heel_touch_and_90_90_remain_separate": True, "family_totals_reconcile": True},
    }
    row_by_id = {r["exercise_id"]: r for r in rows}
    for a, b in [("4007", "6428"), ("10565", "6560")]:
        assert row_by_id[a]["candidate_parameter_profile"] != row_by_id[b]["candidate_parameter_profile"]
        assert exact_owner[a] != exact_owner[b]
    assert sum(f["exercise_count"] for f in families) == len(canonical)
    assert all(summary["checks"].values())
    gz_jsonl("exercise-mapping.jsonl.gz", rows)
    write_json("summary.json", summary)
    write_json("families.json", families)
    write_json("props-reuse.json", prop_rows)
    write_json("generator-recipes.json", generator_recipes)
    write_json("reference-reuse.json", {"aliases": aliases, "exact_editorial_duplicates": duplicate_groups, "identical_instructions_NOT_equivalent": repeated_instruction_groups})
    write_csv(rows)
    write_report(summary, families, props, generator_recipes)
    write_html(summary, families, props)
    write_json("verification.json", {
        "command": "python3 artifacts/exercise-reuse-plan/build_plan.py", "status": "passed",
        "checks": summary["checks"], "check_count": len(summary["checks"]),
        "artifact_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(OUT.iterdir()) if p.is_file() and p.name != "verification.json"},
        "html_bytes": (OUT / "summary.html").stat().st_size,
        "visual_preview": "Not performed here; primary owns html_preview/html_render integration.",
        "limits": "Counts and evidence reconciled locally; no production clip, machine geometry, or anatomical animation approval is implied.",
    })
    print(json.dumps({"counts": summary["counts"], "scenarios": scenarios, "checks": summary["checks"]}, indent=2))


def write_csv(rows):
    fields = ["exercise_id", "name", "family", "reuse_class", "exact_source_owner", "candidate_pose_template", "candidate_apparatus_template", "candidate_literal_profile", "candidate_parameter_profile", "family_confidence", "equipment", "prop_ids", "source_review_status", "storyboard_status", "protected_distinction", "source_path", "source_sha256"]
    with (OUT / "exercise-mapping.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: ";".join(row[k]) if isinstance(row[k], list) else row[k] for k in fields})


def write_report(summary, families, props, generator_recipes):
    c, scenarios = summary["counts"], summary["scenarios"]
    lo, hi = [scenarios[k]["candidate_template_tasks"] for k in ("shared_pose_templates", "apparatus_specific_templates")]
    fine, parameterized = [scenarios[k]["candidate_distinct_profiles"] for k in ("literal_cue_profiles", "parameterized_profiles")]
    top_props = sorted(props, key=lambda p: p["exercise_count"], reverse=True)[:12]
    text = f"""# Exercise and apparatus reuse plan

The catalogue contains **{c['catalogue_records']:,} records: {c['canonical_exercises']:,} canonical exercises and {c['figure_aliases']:,} figure aliases**. Reuse the original CC0 mannequin, its 51-bone rig, shared scene/material/muscle-cue system and view controls. Configure main/additional muscle surfaces in the approved soft warm palette, stretches cyan and inactive surfaces neutral. These are shared infrastructure, not a new clip per body, muscle or view.

## Confirmed references and editorial duplication

- The **922 figure aliases** resolve to canonical IDs. Do not author 922 extra movement specifications. An alias may still need per-record presentation metadata.
- **{c['exact_editorial_duplicate_groups']} exact canonical pairs** can share one resolved specification: **0576/0577** (lever chest press), **0655/0656** (push-up on stability ball). Comparison includes every original field except ID, figure links and provenance; muscle maps, equipment, needs, hold, description and all ordered instructions are included. These save **{c['exact_editorial_reductions']} specification authoring tasks**, leaving **{c['distinct_editorial_specs_after_confirmed_reuse']:,}** canonical specifications.
- Both pairs retain source review gaps. **Zero identical production clips have been validated by this report.** Resolve missing geometry once for each pair before reuse; preserve each ID and its metadata.
- Identical ordered instructions alone occur in **{c['identical_instruction_groups']} groups**, suggesting **{c['identical_instruction_only_potential_reduction_UNSAFE']} unsafe reductions**. These are review leads, not savings. For example 0001/0260/0508/0634 share instruction text across different named sit-up/crunch mechanics; 0367/1441 use the same instructions despite opposite wrist-curl intent. Do not merge.

## Three different layers of reuse

1. **Shared generator/template:** the expensive motion scaffolding (pose setup, world-bone targets, two-joint IK, support constraints, repetition/hold/side-switch sequencing) is authored once per compatible contract. A curl generator can retain separate hand/load paths without requiring independent animation code for every curl. Existing world-bone pose/two-joint IK helpers are compatible reusable infrastructure; this report does not modify or certify them.
2. **Distinct parameter/contact profile:** every exercise retains its exact movement subtype, support contacts, grip, load location, amplitude, timing, muscle map and ordered source guards. These profiles are configuration/validation work, not necessarily independent hand-authored animations. The conservative profile comparison yields **{parameterized:,}–{fine:,} candidate distinct profiles**; semantic name residue is retained so a pike push-up cannot accidentally become an ordinary push-up or a punch become a kick.
3. **Exact identical final clip:** none is validated here. 922 references and two source-identical pairs establish specification reuse, not geometry-correct ready clips. Separate final baked clips can be exported from a shared generator for every ID.

### Conditional base seed / generator workload

For planning the **initial authored generator demonstrations**, budget **{lo:,}–{hi:,} candidate tasks**, rather than 5,632 independent scaffold implementations. The lower scenario groups by family + supported pose + exercise category; the upper also separates resistance type and apparatus bases. Both retain one individual task for each unclassified ID. The potential saving is **{5632-hi:,}–{5632-lo:,} repeated scaffold/seed authoring tasks**, not hours, costs, per-ID review tasks or a reduction in final export count. This bracket assumes a parameterized procedural authoring system; it is not a validated number of interchangeable base clips. Supporting a new subtype may still require new generator logic or a split. The fallback is **5,630** separately resolved specifications if modular parameterization cannot satisfy the guards. A narrower production-clip forecast would require representative motion/contact validation, which this text-only plan does not provide.

The literal profile scenario retains detected contact/range/load-position wording; the parameterized profile scenario moves some such literal wording into per-ID settings. Both retain semantic title subtypes, pose, category, resistance, scene bases, machine identity, laterality, inclination, grip and timing modes. Neither is a sufficient mathematical description of motion. Exact ordered instructions, description, review reasons and evidence pointers accompany **every ID** in the gzip mapping. Non-detected distinctions remain authoritative in that source text. Every differing guard must become an explicit parameter, distinct opcode/sub-generator, or a split. No automatic merges or clips are produced.

There are **{c['family_buckets_including_individual_review']} family buckets**, including **{c['individual_review_exercises']} individual-review IDs** with no supported family rule. All family matches are title-pattern candidates (medium confidence); unmatched items remain individual (low confidence). A family is a reusable controller/scaffold, not an identical clip. Numeric family sizes below count affected exercises, not base clips.

| Candidate controller/scaffold | Affected canonical IDs | Pose templates | Apparatus templates |
| --- | ---: | ---: | ---: |
"""
    for family in families[:18]:
        text += f"| {family['family']} | {family['exercise_count']} | {family['pose_templates']} | {family['apparatus_templates']} |\n"
    text += """
High-value production approach: author a reusable controller for elbow flexion, pushing, pulling, squat/hinge and trunk motion, then author supported pose/contact variants. Keep shoulder/elbow coordination, body support and load paths editable rather than copying an entire animation into every ID. Reuse a timed hold stage and side-switch scaffolding for stretches, without assuming stretch and contraction share a motion. Generic dynamic, ballistic, eccentric-only and static forms remain distinct configurations or seeds. Reuse a mirror operation only after verifying handedness, apparatus symmetry and unilateral supports; this report claims no confirmed mirror savings.

### Concrete generator contracts and affected exercises

The counts below are candidates for sharing implementation scaffolds, with source examples and all member IDs in `generator-recipes.json`. They are not validated interchangeable motions. Each contract defines explicit per-ID parameters and split conditions, rather than treating similar names as identical animations.

"""
    for recipe in generator_recipes:
        text += f"**{recipe['family']} — {recipe['affected_candidate_exercises']} candidates** ({recipe['source_complete_for_storyboard']} source-complete for storyboard). Reuse: {recipe['reusable_generator']} Parameters: {recipe['explicit_profile_parameters']} Split/review: {recipe['split_or_review_guards']}\n\n"
    text += """

### Explicit distinctions that block naive reuse

- **4007 vs 6428:** same heel-touch scaffold, but 4007 holds the legs raised at 90 degrees; 6428 keeps the feet planted. They have separate parameter/contact profiles.
- **10565 vs 6560:** reusable 90/90 hip setup and forward hinge are plausible, but 6560 explicitly places hands on the floor and 10565 does not specify that contact. Keep separate pending adjudication; never fill the unspecified hand position by copying.
- Incline/decline, seated/standing, alternating/bilateral/unilateral, full/partial ROM, hold/tempo/ballistic, grip/palm orientation, support contacts, cable anchor/path, machine pivot/travel and load position are review axes. All are carried in the source guards; extracted flags are incomplete by design.
- Matching equipment enum or muscle target does not establish matching kinematics. Title/description vs instruction contradictions require review even when the upstream brief labels the source complete (e.g. 0454 spider curl description vs standing preacher-style steps).

## Apparatus reuse

"""
    text += f"""The inventory partitions exactly into **{c['buildable_base_props']} buildable base assets + {c['prop_variants']} variants + {c['prop_attachments']} attachments + {c['unresolved_props']} unresolved = {c['prop_rows']} rows**. Upstream calls 170 rows `base`; six of those are unresolved, so 170 is not the buildable base count. A sensible production backlog is **164 base contracts, 31 variant configurations/adaptations and 11 attachment modules**, with six blocked identities. Treating variants as configuration can avoid **up to 31 standalone base-model tasks**, subject to geometry review; it does not remove variant contact/axis work. Attachments are reusable assets but still require their own modeling and connection definitions.

**{c['machine_base_contracts']} machine base contracts remain distinct.** Share pads, seats, plates, stack parts, fasteners and materials, but do not claim one generic machine. Vertical/horizontal/angled leg press, seated/lying/kneeling leg curl, incline/flat/decline chest press, chest-supported/seated/T-bar row, cable tower and Smith rails have different axes, support geometry or load paths. Each is listed in `summary.json:props.distinct_machine_contract_ids`. Plate-loaded/stack/outdoor variants are candidate component reuse; a stack and lever's mechanics are not interchangeable by appearance.

| Reusable prop | Canonical exercises referencing it | Relationship |
| --- | ---: | --- |
"""
    for p in top_props:
        text += f"| {p['english_name']} | {p['exercise_count']} | {p['relation']} |\n"
    text += f"""
These prop counts overlap. **{c['prop_exercise_incidences']:,} prop/exercise incidences cover {c['unique_prop_affected_exercises']:,} distinct canonical exercises**; never sum the table as exercise coverage. A shared bench supports flat/incline/decline settings; separately preserve preacher/hyperextension/GHD supports. A cable station is reusable, with height, anchor, cable routing and handle contacts explicitly configured; rope, straight/V/lat handles and ankle cuff are separate modules. Dumbbell/barbell/kettlebell assets are reused across many exercises, but changing a load does not prove the movement can share a clip. Inventory title/description/inferred matches remain candidates; the mapping separately lists instruction-supported props.

Unresolved prop identities: **{', '.join(summary['props']['unresolved_ids'])}**. Keep all 92 exercises with unresolved geometry blocked from final apparatus sign-off, even where another prop in their scene is known. No-prop-documented is a text status, not proof of no apparatus. Floors are shared scene geometry, not 1,487 independent models.

## Gaps and acceptance

**{c['source_status'].get('needs_review', 0):,} / 5,632** canonical briefs have source review reasons; {c['source_status'].get('source_complete_for_storyboard', 0):,} are source-complete for storyboard, which still does not mean production-ready. **159** authored storyboards are blocked on source resolution; 5,473 have proposals ready for review. Authored staging remains a proposal. Named poses, unsupported apparatus geometry, missing limb placements and ambiguous terms are carried through unchanged. All upstream prop issues are preserved in `summary.json`. No licensed GymVisual media, video/frame sequence, paid API, embeddings or network upload was used.

Production order: resolve one representative specification per confirmed source pair; pilot high-coverage controllers with contrasting pose/contact variants; verify guard preservation; then approve a family-level reuse recipe and batch only those covered cases. Review the difficult members before projecting savings. Existing animation batches remain separately owned and are not modified by this plan.

## Files and reproduction

- `exercise-mapping.csv`: one row for every canonical ID, readable family/seed/prop/source mapping. IDs are strings; preserve leading zeros when importing.
- `exercise-mapping.jsonl.gz`: the same 5,632 assignments with full ordered source guards, evidence, source hashes, parameter axes and review blockers.
- `reference-reuse.json`: all 922 canonical-reference mappings, two exact editorial pairs and instruction-duplicate review leads.
- `families.json`, `props-reuse.json`: family membership and per-prop base/variant/attachment task actions with evidence.
- `generator-recipes.json`: concrete curl/squat/row/press/hinge/push-up/pull/trunk/stretch generator contracts, split guards, source-quoted examples and affected IDs.
- `summary.json`: counts, assumptions, input hashes, partitions, upstream issues and reconciliation checks.
- `summary.html`: compact self-contained comparison for preview; counts labelled by evidence level.
- `verification.json`: 12 passed reconciliation checks, artifact hashes and the remaining visual/production verification limits.

Run from the workspace: `python3 artifacts/exercise-reuse-plan/build_plan.py`. Standard library only. The script checks every live catalogue record against its brief, exact ID coverage, no alias overlap, canonical alias destinations, prop parent validity, prop partitions, family totals and protected non-merges. A changed input fails or regenerates a visibly different hash. It writes only this directory. Outputs describe an authoring proposal; they do not edit runtime/catalogue/animation assets.
"""
    (OUT / "README.md").write_text(text)


def write_html(summary, families, props):
    c, scenarios = summary["counts"], summary["scenarios"]
    lo, hi = [scenarios[k]["candidate_template_tasks"] for k in ("shared_pose_templates", "apparatus_specific_templates")]
    profiles = scenarios["literal_cue_profiles"]["candidate_distinct_profiles"]
    confirmed_rows = [
        ("Naive: one task per record", 6554, "baseline", "Includes 922 figure aliases"),
        ("Confirmed: canonical references", 5632, "confirmed", "922 redundant movement specifications avoided"),
        ("Confirmed: exact editorial specs", 5630, "confirmed", "2 further shared specifications; 0 shared clips validated"),
    ]
    estimate_rows = [
        ("Baseline: independent scaffolds", 5632, "baseline", "Hypothetical one scaffold implementation per canonical ID"),
        ("Estimate: apparatus templates", hi, "estimate", "Scaffold tasks only; distinct exercise profiles retained"),
        ("Estimate: shared pose templates", lo, "estimate", "More generator parameterization; per-ID contacts and review remain"),
    ]
    def bars(chart_rows, baseline):
        return "".join(f'<div class="chart-row"><div class="label">{html.escape(label)}</div><div class="track"><div class="bar {kind}" style="width:{value/baseline*100:.2f}%"></div></div><strong>{value:,}</strong><small>{html.escape(note)}</small></div>' for label, value, kind, note in chart_rows)
    table = "".join(f"<tr><td>{html.escape(f['family'].replace('_',' '))}</td><td>{f['exercise_count']}</td><td>{f['apparatus_templates']}</td></tr>" for f in families[:12])
    doc = f"""<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Exercise reuse: evidence and estimates</title>
<style>
:root{{color-scheme:light dark;--fg:var(--color-text-primary,var(--text-primary,CanvasText));--muted:var(--color-text-secondary,var(--text-secondary,GrayText));--line:var(--color-border-secondary,var(--border-color,#a0a5ab55));--blue:#5485a6;--gold:#c49443;--track:#87939b22}}
*{{box-sizing:border-box}}body{{background:transparent;color:var(--fg);font:15px/1.5 system-ui,sans-serif;margin:0;padding:20px;max-width:1080px}}h1{{font-size:clamp(23px,4vw,34px);line-height:1.15;margin:0 0 12px}}h2{{font-size:20px;margin:26px 0 10px}}p{{margin:8px 0 16px}}.muted,small{{color:var(--muted)}}.metrics{{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;border-block:1px solid var(--line);padding:15px 0;margin:22px 0}}.metrics strong{{display:block;font-size:27px}}.chart-row{{display:grid;grid-template-columns:265px 1fr 70px;gap:8px 14px;margin:19px 0}}.chart-row small{{grid-column:2/4;line-height:1.25}}.chart-row strong{{text-align:right}}.track{{background:var(--track);height:22px}}.bar{{height:100%;min-width:2px}}.baseline{{background:#87939b}}.confirmed{{background:var(--blue)}}.estimate{{background:repeating-linear-gradient(120deg,var(--gold),var(--gold) 7px,#c4944380 7px,#c4944380 11px)}}.legend{{font-size:13px;color:var(--muted)}}table{{width:100%;border-collapse:collapse}}th,td{{text-align:left;border-bottom:1px solid var(--line);padding:7px}}td:not(:first-child),th:not(:first-child){{text-align:right}}.columns{{display:grid;grid-template-columns:1fr 1fr;gap:30px}}ul{{padding-left:20px}}li{{margin:7px 0}}code{{font-size:12px}}@media(max-width:728px){{body{{padding:14px}}.metrics{{grid-template-columns:1fr 1fr}}.chart-row{{grid-template-columns:1fr 64px}}.label{{grid-column:1/3}}.track{{grid-column:1}}.chart-row small{{grid-column:1/3}}.columns{{grid-template-columns:1fr;gap:0}}table{{font-size:13px}}}}
</style><main><h1>Reuse the rig, assets and motion controllers.<br>Approve clips only after checking the mechanics.</h1><p class="muted">Text-only production plan · 6,554 catalogue records reconciled · all 5,632 canonical IDs assigned exactly once</p>
<div class="metrics"><div><strong>922 + 2</strong>confirmed redundant specification tasks</div><div><strong>{lo:,}–{hi:,}</strong>estimated initial scaffold/seed tasks</div><div><strong>164 / 31 / 11</strong>prop bases / variants / attachments</div><div><strong>0</strong>identical production clips validated</div></div>
<h2>Confirmed: separate movement specifications</h2><p>Reference and editorial identity are verified locally. Shared source gaps still need resolution.</p>{bars(confirmed_rows,6554)}<p class="legend">Solid blue = confirmed reference/editorial reuse. This does not validate ready clips.</p>
<h2>Estimated: reusable scaffold implementations</h2><p>This is a separate layer of work. Amber bars count generator/scaffold tasks, while <strong>all per-ID motion/contact profiles and review remain</strong>. These estimates are never a final clip-count promise.</p>{bars(estimate_rows,5632)}<p class="legend">Striped amber = heuristic scaffold scenarios. Source-safe ceiling: 5,630 separate specifications; {profiles:,} conservative candidate profiles remain distinct.</p>
<div class="columns"><section><h2>What can be shared now</h2><ul><li>One original CC0 mannequin, 51-bone rig, scene/view controls, world-bone/IK helpers and muscle cues.</li><li>922 figure aliases reference canonical mechanics.</li><li>Exact source pairs: 0576/0577 and 0655/0656. Resolve their shared source gaps once.</li><li>Reusable apparatus base assets, materials, pads, fasteners and attachment modules.</li></ul></section><section><h2>What remains conditional</h2><ul><li>{5632-hi:,}–{5632-lo:,} potential repeated scaffold tasks avoided if generators preserve every subtype/contact profile.</li><li>{c['source_status'].get('needs_review',0):,} briefs retain source gaps; 92 exercises retain unresolved prop geometry.</li><li>{c['machine_base_contracts']} machine bases keep distinct axis/travel/support contracts. Six prop identities remain unresolved.</li><li>31 prop variants may avoid standalone base meshes; configuration and geometry review still remain.</li></ul></section></div>
<h2>High-coverage candidate motion scaffolds</h2><p class="muted">Shared template → distinct parameter/contact profile → possibly distinct final clip. Affected IDs are never counted as identical clips.</p><table><thead><tr><th>Family</th><th>Affected IDs</th><th>Apparatus templates</th></tr></thead><tbody>{table}</tbody></table>
<h2>Guardrails carried into every mapping row</h2><p>4007 has raised legs; 6428 has planted feet. 6560 explicitly uses hands on the floor; 10565 leaves that contact unspecified. All four stay separate. Preserve incline/decline, pose, laterality, grip, ROM, tempo/hold/ballistic intent, load location, support contacts, cable paths and machine axes.</p><p>37 groups share instruction text despite distinct names or intent. They are review leads, never confirmed clip savings. Full ordered instructions, source hashes, evidence and blockers are retained in the gzip mapping.</p>
<h2>Reconciliations</h2><p><strong>6,554 = 5,632 + 922</strong> records · <strong>212 = 164 + 31 + 11 + 6</strong> prop rows · one canonical assignment per ID · no alias overlap · all alias destinations valid · live catalogue matches briefs · protected non-merges passed.</p><p class="muted">Reproduce with <code>python3 artifacts/exercise-reuse-plan/build_plan.py</code>. Details: README.md, summary.json, exercise-mapping.csv and exercise-mapping.jsonl.gz. No licensed media, video/frame sequences, paid API or network upload used.</p></main></html>"""
    (OUT / "summary.html").write_text(doc)
    assert len(doc.encode()) < 512 * 1024


if __name__ == "__main__":
    main()
