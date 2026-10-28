#!/usr/bin/env python3
"""Build auditable, text-only animation briefs; never read exercise media.

Run from any directory. Uses the Python standard library; writes only beside itself.
The extraction rules organize source cues, not anatomical or kinematic ground truth.
"""

from __future__ import annotations

import collections
import functools
import gzip
import hashlib
import html
import json
import re
import shutil
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
CAT = ROOT / "catalogue/exercises"
INV = "artifacts/exercise-props-inventory/exercise-coverage.json"
MAP = "frontend/src/lib/exercise-muscle-map.json"
SCHEMA = "1.0.0"


@functools.cache
def read(rel):
    return json.loads((ROOT / rel).read_text())


def write(name, data):
    (OUT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def gzip_copy(path):
    """No timestamp or original filename in gzip headers; reproducible on this runtime."""
    with path.open("rb") as src, Path(str(path) + ".gz").open("wb") as dest:
        with gzip.GzipFile(filename="", mode="wb", fileobj=dest, mtime=0, compresslevel=9) as compressed:
            shutil.copyfileobj(src, compressed)


def match(pattern, text):
    return bool(re.search(pattern, text, re.I))


def ref(path, pointer, quote):
    return {"path": path, "pointer": pointer, "quote": quote}


def cue(text, evidence, **extra):
    return {"text": text, "evidence": evidence, **extra}


# A full source step remains atomic: conjunctions often carry important positioning cues.
ARMS = r"\b(?:arms?|forearms?|shoulders?|shoulder blades?|hands?|elbows?|wrists?|palms?|fingers?|thumbs?|grip|grasp|hold(?:ing)? (?:a |the )?(?:bar|handle|dumbbell|kettlebell))\b"
LEGS = r"\b(?:legs?|feet|foot|knees?|ankles?|heels?|toes?|thighs?|hips?|pelvis|stance|calves|calf)\b"
ARM_POSE = r"\b(?:arms?|hands?|elbows?|wrists?|palms?|fingers?|thumbs?|grip|grasp)\b"
LEG_POSE = r"\b(?:feet|foot|knees?|ankles?|heels?|toes?|stance|legs? (?:straight|bent|extended|apart|together)|(?:one|single) leg)\b"
SETUP = r"^(?:(?:to (?:begin|start)|begin|start|starting|initially)[,:]?\s+)?(?:stand|sit|seated|lie|lay|kneel|hang|position|place|grasp|grab|grip|hold|cross|interlace|rest|brace|face|find|straddle|support|set|attach|secure|anchor|adjust|loop|wrap|get|assume|take (?:a |an )?(?:stance|position))\b|\b(?:start|begin) (?:in|on|with|by)\b"
POSE = r"\b(?:stand(?:ing)?|sit(?:ting)?|seated|lie|lying|kneel(?:ing)?|hang(?:ing)?|plank|downward dog|all fours|supine|prone|athletic stance|split stance|lunge position|squat position|on your (?:back|side|stomach))\b"
MOVE = r"\b(?:bend|lower|raise|lift|curl|press|push(?:ing)?|pull(?:ing)?|rotate|twist|lean|jump|hop|step|walk|run|sprint|shuffle|plant|cut|swing|kick|drive|extend(?:ing)?|flex|roll(?:ing)?|reach(?:ing)?|open|close|squeeze|climb|pedal(?:ing)?|bounce|slide|move|bring|return|straighten|lunge|squat|descend|ascend|hinge|throw|rise|touch|arch|reset|pick up)\b"
CONTACT = r"\b(?:floor|ground|walls?|bench(?:es)?|seats?|chairs?|platforms?|box(?:es)?|steps?|bars?|handles?|pedals?|pads?|mats?|supports?|rails?|racks?|cables?|bands?|straps?|rings?|balls?|cones?|hurdles?|ladders?|anchors?|machines?|dumbbells?|kettlebells?|barbells?|ropes?|pool|water|partner|poles?|towels?|sticks?|rollers?|blocks?|plates?|sled|trampoline|doors?|fence|posts?|bags?|bottles?|wheels?|treadmill|stairs|staircase|sheet|bosu|sandbag)\b"
CONTACT_VERB = r"\b(?:on|onto|against|under|over|from|in|into|touch|contact|flat|plant|place|position|rest|support|hold|grasp|grip|hang|attach|anchor|secure|press|push|pull|stand|sit|lie|kneel)\b"
NEGATION = r"\b(?:without|no need|do not use|don't use|imaginary|imagine|as if)\b"
OPTIONAL = r"\b(?:optional|if needed|if desired|for comfort|can use|may use|can also|such as)\b"


def phase_tags(text):
    tags = []
    if match(SETUP, text):
        tags.append("setup_or_position")
    if match(MOVE, text):
        tags.append("movement")
    if match(r"\b(?:hold|pause|stay|maintain|keep|breathe|relax)\b", text):
        tags.append("hold_or_constraint")
    if match(r"\b(?:return|back to|starting position|switch|other side|other leg|alternate|alternating)\b", text):
        tags.append("return_or_side_change")
    if match(r"\b(?:repeat|repetitions?|reps?|seconds?|minutes?|breaths?|tempo|slowly|quick|explosive|controlled)\b", text):
        tags.append("timing_or_repetition")
    return tags or ["unclassified_source_step"]


def position_field(cues, note, context_cues=None):
    return {"status": "source_cues_present" if cues else "missing_in_source",
            "cues": cues, "missing_detail": None if cues else note,
            "context_cues": context_cues or [],
            "context_interpretation": "Title/description context is retained separately; it does not establish detailed instruction-step geometry."}


def source_ref(row, field, quote=None):
    pointer = "/" + re.sub(r"\[(\d+)\]", r"/\1", field)
    value = row
    for part in pointer.split("/")[1:]:
        value = value[int(part)] if isinstance(value, list) else value[part]
    if quote is not None and quote != value:
        raise ValueError(f"Stale inventory quote: {row['id']} {field}")
    return ref(f"catalogue/exercises/{row['id']}.json", pointer, value)


def adjudicate_props(row, inv_row, inv_index, labels):
    props = []
    text = " ".join(row["instructions"])
    for j, prop in enumerate(inv_row["props"]):
        evidence = prop["evidence"]
        direct = [e for e in evidence if e["field"].startswith(("instructions[", "needs["))]
        metadata = [e for e in evidence if e["field"] == "equipment"]
        descriptive = [e for e in evidence if e["field"] == "description"]
        reason = None
        # Known generalizable false positive: 45-degree title does not establish a bench.
        if (prop["canonical_id"].startswith("bench") and not direct and not descriptive
                and match(r"\bstand(?:ing)?\b", " ".join(row["instructions"][:2]))
                and not match(r"\b(?:bench|pad|preacher|support|seat)\b", text)):
            status = "conflict"
            reason = "Inventory infers a bench from the title, while the source starts standing and never documents bench contact. Do not add the bench."
        elif direct:
            if all(e["tier"] == "optional" for e in direct):
                status = "optional_or_alternative"
            elif all(e["tier"] == "inferred" for e in direct):
                status = "inferred_unverified"
            else:
                status = "instruction_or_needs_supported"
        elif metadata:
            status = "equipment_metadata_supported"
        elif descriptive and any(e["tier"] == "explicit" for e in descriptive):
            status = "description_supported"
        elif any(e["tier"] == "optional" for e in evidence):
            status = "optional_or_alternative"
        else:
            status = "title_or_inference_unverified"
        props.append({
            "prop_id": prop["canonical_id"], "label": labels[prop["canonical_id"]],
            "status": status, "review_reason": reason,
            "source_evidence": [source_ref(row, e["field"], e["quote"]) for e in evidence],
            "inventory_evidence": ref(INV, f"/{inv_index}/props/{j}", prop),
            "original_inventory_tiers": sorted({e["tier"] for e in evidence}),
            "contact_geometry": "Use the source contact cues; exact attachment and geometry are not inferred from a prop name.",
        })
    return props


def authored_staging(brief, row):
    """Offer reversible blocking choices without presenting them as source facts.

    These choices place an actor for a storyboard; they do not repair missing exercise
    mechanics. Dimensions, numerical joint angles and machine settings remain unset.
    """
    setup = brief["starting_position"]["cues"]
    candidates = [(s["text"], s["evidence"]) for s in setup]
    candidates += [(s["text"], s["evidence"]) for s in brief["movement"]["phases"][:3]
                   if s not in setup and match(SETUP + "|" + POSE, s["text"])]
    candidates += [(row[f], [source_ref(row, f)]) for f in ("name", "description")]
    poses = [
        ("downward_dog", r"\b(?:downward dog|3 leg dog|three.legged dog)\b"),
        ("side_plank", r"\bside plank\b"),
        ("forearm_plank", r"\b(?:forearm plank|plank on (?:your )?forearms)\b"),
        ("wall_sit", r"\bwall sit\b"),
        ("bar_support", r"\b(?:position|support|hold).{0,45}(?:on|between).{0,25}(?:parallel bars|dip bars|rings)\b"),
        ("planche_lean", r"\bplanche lean\b"),
        ("plank", r"\b(?:plank|chaturanga|push[- ]?up|press[- ]?up)\b"),
        ("inverted_row", r"\binverted row\b"),
        ("supine", r"\b(?:supine|lie.{0,25}(?:on|with).{0,12}(?:your |the )?back|lying.{0,15}(?:on )?(?:your |the )?back|on your back|facing up|face[- ]up|back (?:pressed |flat )?(?:against|on) (?:the |a )?bench)\b"),
        ("side_lying", r"\b(?:side[- ]lying|lying on (?:your |the )?side|lie on (?:your |the )?side)\b"),
        ("prone", r"\b(?:prone|face[- ]down|facing down|lying on (?:your |the )?stomach|lie on (?:your |the )?stomach)\b"),
        ("seated", r"\b(?:seated|sit on|sit at|sit in|sit down|sit upright|sit with|sit tall|sitting)\b"),
        ("quadruped", r"\b(?:all fours|quadruped|hands and knees)\b"),
        ("kneeling", r"\b(?:kneel|kneeling|half[- ]kneeling|tall kneeling)\b"),
        ("hanging", r"^(?:hang|hanging)\b|\b(?:hang from|hanging from|dead hang|hang with)\b"),
        ("standing", r"\b(?:stand|standing|stance|one leg hop|single leg hop|single leg squat)\b"),
    ]
    pose, basis = "unresolved", []
    for text, evidence in candidates:
        for kind, pattern in poses:
            if match(pattern, text):
                pose, basis = kind, evidence
                break
        if pose != "unresolved":
            break
    if pose == "unresolved":
        for text, evidence in candidates:
            if match(r"\b(?:lie|lying|lay)\b", text):
                pose, basis = "supported_lying", evidence
                break
            if (match(r"\b(?:thighs?|hips?|knees?|feet|foot|forearms?|upper arms?|torso|chest|abdomen|waist|back|body|yourself)\b", text)
                    and match(r"\b(?:bench|pads?|seat|support|machine|floor|platform|box|step|wall)\b", text)
                    and match(r"\b(?:on|against|over|under|rest|resting|secured|position|set up)\b", text)):
                pose, basis = "source_defined_support", evidence
                break
    if pose == "unresolved":
        # A named squat/deadlift/locomotion action supplies a reversible ground-based
        # blocking context, not a complete or source-verified starting joint pose.
        action_candidates = candidates + [(s["text"], s["evidence"]) for s in brief["movement"]["phases"][:3]]
        for text, evidence in action_candidates:
            if match(r"\b(?:squats?|deadlifts?|lunges?|jump(?:s|ing)?|hop(?:s|ping)?|walk(?:s|ing)?|run(?:s|ning)?|sprints?|shuffl(?:e|ing)|standing|stand|step (?:back|onto)|hinge (?:at|forward)|hip hinge|hips? hinged)\b", text):
                pose, basis = "standing", evidence
                break
    pose_choice_basis = "source_classification"
    if pose == "unresolved" and (row["target"] in ("forearms", "sternocleidomastoid") or match(r"\b(?:finger|thumb|wrist|neck)\b", row["name"])):
        pose, basis, pose_choice_basis = "standing", [source_ref(row, "name")], "authored_neutral_global_pose_for_local_joint_drill"
    if pose == "unresolved" and row["equipment"] in ("cable", "band", "resistance band", "suspension trainer"):
        pose, basis, pose_choice_basis = "standing", [source_ref(row, "equipment")], "authored_grounded_default_for_unspecified_cable_band_or_suspension_posture"

    def proposal(text, status, evidence=basis, rationale=""):
        return {"proposal": text, "status": status,
                "authoring_basis": {"type": "source_cues" if status == "source_cue_reuse" else "reversible_staging_choice",
                                    "evidence": evidence, "rationale": rationale},
                "source_verified": status == "source_cue_reuse", "requires_owner_review": True}

    defaults = {
        "standing": (
            "Use a balanced standing blocking pose, preserving any source-documented stance, support foot and torso lean. When standing itself is an authored default, review that reversible choice before motion production.",
            "Let the upper arms rest near the torso, elbows soft and hands relaxed; allow small balance movements that do not add a new exercise action.",
            "Use a comfortable hip-width stance with soft knees unless the source specifies a single-leg, split or wider stance; keep the documented support foot grounded."),
        "seated": (
            "Sit on the support named in the source, with the torso balanced and the source's documented lean preserved; do not add an unmentioned bench or machine.",
            "Rest relaxed hands beside the thighs until the source's arm movement begins; use documented handles or loads when present.",
            "For an otherwise unspecified seated setup, place the feet in a stable comfortable support position; preserve any source-defined footrests, pedals, leg pads or floor contact."),
        "supine": (
            "Use the source's face-up lying support and torso orientation.",
            "Rest the arms beside the torso with relaxed hands on the documented support surface; this is a balance/staging choice, not an added pressing action.",
            "For an unspecified unloaded face-up setup, bend the knees comfortably and ground the soles; preserve any source-defined straight-leg or elevated-leg action."),
        "prone": (
            "Use the source's face-down lying support and keep its documented torso alignment.",
            "Rest the arms beside the torso with relaxed hands clear of the moving body segment, unless a source-defined load or control requires a grip.",
            "Keep the legs comfortably extended and quiet on the documented support; retain any source-defined leg motion or restraints."),
        "side_lying": (
            "Lie on the source-indicated side on its documented support; choose the right side first only when the source leaves laterality open.",
            "Use the lower arm as a comfortable head support and rest the upper hand lightly in front of the torso for balance; do not turn that contact into a new exercise action.",
            "Stack the legs comfortably, with a slight bend in the lower support leg if needed for balance; preserve the source's working-leg motion."),
        "quadruped": (
            "Use a hands-and-knees setup with the torso level and the source's documented spine position.",
            "Place open palms on the support under the shoulders, with relaxed forward-facing fingers; this exact placement is an authored staging choice.",
            "Place the knees under the hips on the documented support and let the lower legs rest comfortably; preserve any source-defined lifted limb."),
        "kneeling": (
            "Use the source's kneeling setup on its documented floor, pad or support; retain any explicitly half-kneeling or single-knee arrangement.",
            "Rest relaxed hands beside the torso until the source's arm action starts; preserve documented load, handle or support contacts.",
            "Settle the documented knee or knees on their support, with comfortable lower-leg placement; do not invent machine pad spacing or a missing half-kneeling side."),
        "hanging": (
            "Hang from the source-defined overhead support; do not invent a new bar, anchor height or grip orientation.",
            "Grip the source-defined support with neutral wrists and a closed hand contact; retain any documented grip width or palm direction.",
            "Keep the feet clear of the lower support surface and the legs quiet in a comfortable alignment; preserve source-defined knee bends or leg raises."),
        "inverted_row": (
            "Place the body beneath the source-defined pulling support with the torso aligned; the source must determine the support and load-bearing contacts.",
            "Use a closed hand contact around the documented bar or handles, keeping wrists neutral; preserve any source-defined grip orientation.",
            "Use stable foot contact with the documented lower support and preserve the source's bent- or straight-leg instruction; do not infer bar height or torso angle."),
        "plank": (
            "Use a high-plank blocking pose on the documented support, with a long aligned torso; preserve any source-defined low-plank or lifted-leg modification.",
            "Place open palms about shoulder-width apart below the shoulders, fingers forward and wrists comfortably aligned; source-defined elbow motion remains authoritative.",
            "Use toe support under the documented support leg or legs and keep the pelvis level; when a lifted-leg source leaves the first side open, stage the right leg first and then mirror."),
        "downward_dog": (
            "Use an inverted-V blocking pose with the hips lifted, a long spine and the source-defined hand/foot support.",
            "Place open palms shoulder-width apart on the floor, fingers comfortably spread forward; use the source's hand-pressure cue without inventing a force value.",
            "Set the feet about hip-width apart with comfortable knee softness and heels reaching toward the support without forcing contact; if the first lift side is unspecified, stage the right leg then mirror."),
        "side_plank": (
            "Use the source-defined side-plank support and align the torso sideways over its documented support arm or forearm.",
            "Retain whichever hand or forearm support the source establishes; stage the free hand relaxed at the hip unless the source gives another action. An unspecified support-arm form requires review.",
            "Stack the feet comfortably on the documented support or preserve the source's staggered-foot/raised-leg variation; do not substitute a two-arm front plank."),
        "forearm_plank": (
            "Use the source-defined forearm-plank setup with the torso aligned over its documented forearm and lower-body support.",
            "Rest the forearms on the documented support with the elbows below the shoulders and relaxed hands; do not replace the forearm contact with palms.",
            "Use source-defined toe or knee support, keeping the pelvis aligned; preserve any documented lifted-leg or side-changing action."),
        "supported_lying": (
            "Use the source's lying setup on its named bench, floor or other support; keep the source's head, torso and limb cues rather than inventing a different support.",
            "Use the source's load/control contact and moving-arm cues as the initial blocking guide; keep wrists neutral and leave an unstated grip orientation for owner review.",
            "Retain the source's foot restraints, floor contacts or leg motion. If no lower-body placement is given, use a quiet comfortable arrangement on the named support and review its exact orientation."),
        "source_defined_support": (
            "Use the source's documented body-to-pad, bench or apparatus setup; preserve those named support points without inventing machine dimensions or a new body support.",
            "Preserve any source-defined grip, crossed-arm position or moving-arm cue. Otherwise rest the arms clear of the moving segment in a comfortable balance position for owner review.",
            "Preserve the source's documented knee, thigh, hip or foot support points; leave unspecified pad settings and finer leg geometry for owner review rather than inventing dimensions."),
        "wall_sit": (
            "Use the source's wall-supported sitting posture, with the back resting against the named wall and the source's knee/hip position retained.",
            "Rest the arms comfortably beside the torso or lightly in front for balance; do not add a push against the thighs or wall unless the source asks for it.",
            "Use stable floor contact under the source-defined support foot or feet and keep each knee aligned with its foot; preserve any single-leg modification."),
        "bar_support": (
            "Use the source's upright support on the named parallel bars, dip bars or rings; the arms carry the documented support and the torso stays aligned.",
            "Keep a closed hand contact on the source-defined supports with neutral wrists; preserve the source's extended-arm setup and elbow path.",
            "Keep the feet clear of the floor in a quiet comfortable alignment, with a soft knee bend if needed for clearance; preserve any documented leg or assistance-pad support."),
        "planche_lean": (
            "Use the source's deep planche lean with hands under the shoulders; keep the source's foot support until its explicit feet-lift phase.",
            "Use open hand contact under the shoulders on the source-defined floor support, with a comfortable authored palm/finger orientation; preserve the source's shoulder protraction cue.",
            "Keep the feet supported on the source-defined floor before the lift phase, then follow the source's feet-lift and controlled lower; exact lifted-body geometry remains for owner review."),
    }
    unresolved = "The source does not establish a reliable initial body pose. Preserve its setup step as a staging placeholder and resolve support geometry before authoring motion."
    start_default, arm_default, leg_default = defaults.get(pose, (unresolved,
        "Keep a hand/arm placement placeholder until the initial body support and any handle/load contact are resolved; do not invent an exercise action.",
        "Keep a leg/foot placement placeholder until the initial body support is resolved; do not invent a standing, seated or lying support."))
    explicit_pose = any(match(POSE, s["text"]) for s in setup) or (bool(setup) and pose == "source_defined_support" and any(e["pointer"].startswith("/instructions/") for e in basis))
    start = proposal(" ".join(s["text"] for s in setup), "source_cue_reuse", [e for s in setup for e in s["evidence"]]) if explicit_pose else proposal(start_default, "authored_from_source_context" if pose != "unresolved" else "unresolved", rationale="Body-pose class uses cited setup/action or title/description context, or an explicitly authored neutral default; detailed placement is a reversible proposal. Basis: " + pose_choice_basis + ".")
    initial_arms = [s for s in setup if match(ARM_POSE, s["text"])]
    initial_legs = [s for s in setup if match(LEG_POSE, s["text"])]
    # Reuse complete source sentences where available; otherwise supply a reversible
    # starting placement. The original moving-limb constraints remain in the phases.
    arms = proposal(" ".join(s["text"] for s in initial_arms), "source_cue_reuse", [e for s in initial_arms for e in s["evidence"]]) if initial_arms else proposal(arm_default, "authored_from_source_posture" if pose != "unresolved" else "unresolved", rationale="Initial arm position was not explicit; this is a neutral staging choice compatible with the inferred support pose.")
    legs = proposal(" ".join(s["text"] for s in initial_legs), "source_cue_reuse", [e for s in initial_legs for e in s["evidence"]]) if initial_legs else proposal(leg_default, "authored_from_source_posture" if pose != "unresolved" else "unresolved", rationale="Initial leg placement was not explicit; this is a reversible balance/support choice, not a replacement for source movement.")

    # Closed grip is a functional staging contact, never an invented palm orientation,
    # handle height, loading value or apparatus-specific joint geometry.
    functional_grip = match(r"\b(?:hands?|grip|grasp|grab|handles?)\b|\bhold.{0,30}(?:dumbbell|barbell|kettlebell|bar|weight|band)", " ".join(row["instructions"]))
    if not initial_arms and functional_grip and row["equipment"] in ("dumbbell", "barbell", "kettlebell", "ez barbell", "cable", "band"):
        arms = proposal("Use a closed hand contact around the source-defined load or control with wrists neutral. Preserve any grip orientation, hand count, handle position and arm path stated in the phases; unspecified grip/handle geometry remains for review.", "authored_functional_contact", [source_ref(row, "equipment")], "The declared equipment requires a control/load contact, but its precise grip geometry is not supplied here.")

    # First-five direction was explicitly authorized as authored staging. These choices
    # are intentionally distinct from the unresolved exact drill mechanics.
    if row["id"] == "5965":
        arms = proposal("Begin with both elbows softly bent near the sides, forearms loosely forward and hands relaxed; swing the arms naturally with the source's quick stepping.", "authored_from_source_limb_cue", [source_ref(row, "instructions[3]")], "The moving-arm cue is reused as a reversible initial blocking pose; exact elbow angles are not specified.")
        legs = proposal("Begin with the feet comfortably under the hips, knees slightly bent and weight light on the balls of the feet. Preserve quick, light steps; the exact one-then-two footfall sequence remains unresolved.", "authored_from_source_limb_cue", [source_ref(row, "instructions[0]"), source_ref(row, "instructions[2]")], "Athletic stance and forefoot support are sourced; initial foot spacing is a reversible staging choice.")
    if row["id"] == "5915":
        arms = proposal(defaults["plank"][1], "authored_from_named_pose", [source_ref(row, "instructions[0]"), source_ref(row, "instructions[2]")], "High plank supplies the pose name; hand width, orientation and initial placement are explicit authored choices.")
        legs = proposal("Begin with the right leg lifted behind the torso, the left toes supporting on the floor and the hips level; after the source-defined lower/press sequence, lower the right foot and mirror on the left.", "authored_laterality_and_contacts", [source_ref(row, "instructions[0]"), source_ref(row, "instructions[1]"), source_ref(row, "instructions[4]")], "Lifted-leg action and side switch are sourced; first side and precise support contacts are authored staging.")
    if row["id"] == "5887":
        arms = proposal(defaults["downward_dog"][1], "authored_from_named_pose", [source_ref(row, "instructions[0]"), source_ref(row, "instructions[1]")], "Hand width and floor pressure are sourced; precise palm orientation and finger placement are authored staging.")
        legs = proposal(defaults["downward_dog"][2], "authored_from_named_pose", [source_ref(row, "instructions[0]"), source_ref(row, "instructions[2]"), source_ref(row, "instructions[4]")], "Downward dog and a straight rear leg lift are sourced; initial foot spacing, heel treatment and first side are authored choices.")
    if row["id"] == "9066":
        legs = proposal("Begin supported on the right foot, with the right knee softly bent and tracking over that foot. Keep the left foot clear and the free leg relaxed; mirror the source's hop pattern on the left after completing the right-side pattern.", "authored_laterality_and_contacts", [source_ref(row, "instructions[0]"), source_ref(row, "instructions[4]"), source_ref(row, "instructions[5]")], "Single-leg support, soft knee and knee-over-foot alignment are sourced; the first side and free-leg staging are authored choices.")

    supported = [p for p in brief["equipment_scene"]["props"] if p["status"] not in ("conflict", "title_or_inference_unverified", "inferred_unverified")]
    contacts = proposal(
        "Retain every explicit contact in equipment_scene.contacts. Use only the documented prop choices: " + (", ".join(p["label"] for p in supported) or "no additional prop is established") + ". " +
        ("For this standing proposal, the support foot or feet contact a level ground plane; that ground plane is an authored scene choice when the source does not name it. " if pose == "standing" else "") +
        ("For this floor-support pose, stage the documented hand, forearm, foot or knee supports on a level ground plane unless the source names another surface; this is an authored support choice. " if pose in ("plank", "forearm_plank", "side_plank", "downward_dog", "quadruped") else "") +
        "Do not assign unknown apparatus dimensions, pad settings, attachment heights or load values.",
        "authored_scene_blocking", basis, "Scene support follows the source posture; unsupported inventory candidates are excluded from this proposal, not silently asserted.")
    blockers = [r["code"] for r in brief["review_reasons"] if r["code"] in {
        "movement_pattern_unspecified", "movement_or_hold_unclassified"}]
    reason_codes = {r["code"] for r in brief["review_reasons"]}
    source_text = " ".join(row["instructions"])
    generic_machine = match(r"\b(?:machine|cable|band|ergometer|rope|rings?|suspension)\b", row["equipment"]) and bool(brief["equipment_scene"]["contacts"]["cues"])
    generic_machine = generic_machine or (row["equipment"] == "assisted" and match(r"\b(?:pad|handles?|machine)\b", source_text))
    if "prop_not_instruction_verified" in reason_codes and not supported and not generic_machine and pose != "source_defined_support":
        blockers.append("unverified_apparatus_without_supported_base")
    if "equipment_not_mapped" in reason_codes and row["equipment"] != "assisted":
        blockers.append("equipment_not_mapped")
    if "inventory_unresolved" in reason_codes and not match(r"\b(?:weight|load|ball|rope|partner|object|plate|bell)\b", source_text):
        blockers.append("resistance_or_apparatus_not_realized_in_steps")
    if pose == "unresolved":
        blockers.append("initial_body_support_unresolved")
    for label, field in (("arms_hands", arms), ("legs_feet", legs)):
        if field["status"] == "unresolved":
            blockers.append(label + "_staging_unresolved")
    return {
        "pose_class": pose, "pose_choice_basis": pose_choice_basis, "starting_position": start, "arms_hands": arms, "legs_feet": legs, "equipment_contacts": contacts,
        "movement_policy": "Use the complete ordered source phases and retain all individual constraints. No missing footfall sequence, load path, apparatus setting, timing or joint range is invented by these placement proposals.",
        "status": "blocked_on_source_resolution" if blockers else "proposal_ready_for_review",
        "blockers": sorted(set(blockers)),
        "interpretation": "Usable blocking proposals where source posture/contact allows them; authored placements are reversible choices, not verified exercise mechanics or production-ready animation.",
    }


def make_brief(row, inv_row, inv_index, labels, muscle_maps):
    ident = row["id"]
    path = f"catalogue/exercises/{ident}.json"
    steps = [cue(t, [ref(path, f"/instructions/{i}", t)], step_number=i + 1,
                 tags=phase_tags(t)) for i, t in enumerate(row["instructions"])]
    # Include all initial setup steps; later setup-like instructions are kept as phase cues.
    setup = []
    for i, step in enumerate(steps):
        if ("setup_or_position" in step["tags"] or (i == 0 and match(POSE, step["text"]))) and (i == 0 or setup):
            setup.append(step)
        else:
            break
    arms = [s for s in steps if match(ARMS, s["text"])]
    legs = [s for s in steps if match(LEGS, s["text"])]
    contacts = [s for s in steps if match(CONTACT, s["text"]) and match(CONTACT_VERB, s["text"])]
    props = adjudicate_props(row, inv_row, inv_index, labels)
    reasons = []

    def context(pattern):
        return [cue(row[field], [source_ref(row, field)], source_field=field)
                for field in ("name", "description") if match(pattern, row[field])]

    def issue(code, message, evidence=None):
        reasons.append({"code": code, "message": message, "evidence": evidence or []})

    if not setup or not any(match(POSE, s["text"]) for s in setup):
        issue("starting_body_pose_missing", "The initial setup does not explicitly establish the body's supported pose; do not invent it.")
    if not arms:
        issue("arms_hands_missing", "No explicit arm/hand cue was found in the instruction steps.")
    elif not any(match(ARM_POSE, s["text"]) for s in setup):
        issue("starting_arms_hands_missing", "Arm/hand movement cues exist, but initial hand placement or arm position is not explicitly stated.")
    if not legs:
        issue("legs_feet_missing", "No explicit leg/foot cue was found in the instruction steps.")
    elif not any(match(LEG_POSE, s["text"]) for s in setup):
        issue("starting_legs_feet_missing", "Leg/hip cues exist, but initial leg/foot placement is not explicitly stated.")
    if not any("movement" in s["tags"] or "hold_or_constraint" in s["tags"] for s in steps):
        issue("movement_or_hold_unclassified", "The extractor did not identify a movement or a hold; inspect the complete original steps.")
    for prop in props:
        if prop["status"] == "conflict":
            issue("prop_text_conflict", prop["review_reason"], prop["source_evidence"] + [steps[0]["evidence"][0]])
        elif prop["status"] in ("title_or_inference_unverified", "inferred_unverified"):
            issue("prop_not_instruction_verified", f"{prop['label']} remains an inventory candidate; its use/contact is not established by instructions or equipment metadata.", prop["source_evidence"])
    if row["equipment"] != "body weight" and not props:
        issue("equipment_not_mapped", "The equipment metadata names external equipment but the inherited inventory has no mapped prop.", [source_ref(row, "equipment")])
    if inv_row["status"] not in ("mapped_props", "no_prop_documented_in_text"):
        issue("inventory_unresolved", f"Inherited inventory status: {inv_row['status']}.", [ref(INV, f"/{inv_index}/status", inv_row["status"])])
    named_pose = [s for s in setup if match(r"\b(?:plank|downward dog|all fours|chaturanga|[a-z]+ pose)\b", s["text"])]
    if named_pose:
        issue("named_pose_requires_geometry", "A named pose is a source cue, not a full joint/contact specification. Resolve its missing geometry before keyframing.", [e for s in named_pose for e in s["evidence"]])
    vague_pattern = [s for s in steps if match(r"\b(?:set pattern|given pattern|prescribed pattern|as shown|as demonstrated)\b", s["text"])]
    if vague_pattern:
        issue("movement_pattern_unspecified", "The source refers to an unspecified pattern or demonstration; the exact sequence must be authored and reviewed.", [e for s in vague_pattern for e in s["evidence"]])

    source_muscles = {
        "primary": [{"name": row["target"], "evidence": [source_ref(row, "target")]}],
        "secondary": [{"name": name, "evidence": [source_ref(row, f"secondaryMuscles[{i}]")]} for i, name in enumerate(row["secondaryMuscles"])],
        "interpretation": "Source training labels, not measured activation, contraction intensity, or necessarily anatomical muscles (for example cardiovascular system, ankles, core).",
    }
    display = muscle_maps.get(ident)
    if display is not None:
        source_muscles["catalogue_display_map"] = {
            "value": display,
            "evidence": [ref(MAP, f"/{ident}", display)],
            "interpretation": "Existing application display metadata, preserved separately from the raw training labels; no activation measurements inferred.",
        }
    brief = {
        "schema_version": SCHEMA, "id": ident, "canonical_id": ident, "record_kind": "canonical",
        "name": row["name"], "category": row["category"], "body_part": row["bodyPart"],
        "status": "needs_review" if reasons else "source_complete_for_storyboard",
        "animation_ready": False,
        "starting_position": position_field(setup, "No explicit initial setup cue was identified in the initial instruction steps; inspect original instructions and contextual cues.", context(POSE)),
        "movement": {"status": "source_steps_present" if steps else "missing_in_source", "phases": steps,
                     "phase_interpretation": "Ordered original instruction steps with heuristic tags; a step can combine setup, motion and constraints. Not generated keyframes."},
        "arms_hands": position_field(arms, "Initial and/or moving arm/hand placement is not specified in the source steps.", context(ARMS)),
        "legs_feet": position_field(legs, "Initial and/or moving leg/foot placement is not specified in the source steps.", context(LEGS)),
        "equipment_scene": {
            "declared_equipment": {"value": row["equipment"], "evidence": [source_ref(row, "equipment")]},
            "needs": {"value": row.get("needs", []), "evidence": [source_ref(row, "needs")] if "needs" in row else []},
            "props": props,
            "contacts": position_field(contacts, "No explicit scene contact cue identified; absence is not proof of free-space motion.", context(CONTACT)),
            "prop_summary": "documented_or_candidate_props" if props else "no_prop_documented_in_text",
            "equipment_free_candidate": row["equipment"] == "body weight" and not props,
            "interpretation": "Body weight describes resistance, not scene contents. Inventory is a candidate list, not verified geometry. Floor/ground contacts are retained even for equipment-free candidates.",
        },
        "muscles": source_muscles,
        "source_constraints": {
            "hold": row.get("hold", False), "hold_explicit": "hold" in row,
            "timing_and_ranges": [s for s in steps if match(r"\d|\b(?:breaths?|seconds?|minutes?|degrees?|slowly|quick|briefly|moment|controlled|explosive|natural)\b", s["text"])],
            "interpretation": "Retain source timing/range cues. No universal tempo, joint angle, side order or anatomical precision is invented.",
        },
        "review_reasons": reasons,
        "production_review_required": [
            "Approve complete contact/pose geometry, range of motion and timing for this individual exercise.",
            "Approve safe joint motion and visible primary/secondary muscle highlights; text labels do not supply muscle activation curves.",
        ],
        "source": {"path": path, "sha256": hashlib.sha256((ROOT / path).read_bytes()).hexdigest(),
                   "text_source": row.get("textSource"), "original_record": row},
        "derivation": "Deterministic text extraction with heuristic cue classification and separately labeled reversible authored staging. Source cues are quoted; props are adjudicated conservatively. No licensed images or videos were read.",
    }
    brief["source_completeness"] = {"status": brief["status"], "review_reason_count": len(reasons)}
    brief["authored_staging"] = authored_staging(brief, row)
    brief["storyboard_readiness"] = {"status": brief["authored_staging"]["status"], "blockers": brief["authored_staging"]["blockers"]}
    return brief


def pointer_value(path, pointer):
    data = read(path)
    for part in pointer.split("/")[1:]:
        part = part.replace("~1", "/").replace("~0", "~")
        data = data[int(part)] if isinstance(data, list) else data[part]
    return data


def validate(briefs, rows, aliases, coverage):
    errors = []
    checked_refs = 0
    cache = {}

    def walk(value):
        nonlocal checked_refs
        if isinstance(value, dict):
            if set(("path", "pointer", "quote")).issubset(value):
                key = (value["path"], value["pointer"])
                try:
                    if key not in cache:
                        cache[key] = pointer_value(*key)
                    if cache[key] != value["quote"]:
                        errors.append(f"Evidence mismatch: {key}")
                    checked_refs += 1
                except (KeyError, IndexError, FileNotFoundError, ValueError) as exc:
                    errors.append(f"Invalid evidence: {key}: {exc}")
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    ids = [b["id"] for b in briefs]
    if len(ids) != len(set(ids)) or set(ids) != set(rows):
        errors.append("Catalog IDs are missing or duplicated")
    canonical = {b["id"]: b for b in briefs if b["record_kind"] == "canonical"}
    for brief in briefs:
        if brief["canonical_id"] not in canonical:
            errors.append(f"Unresolved canonical: {brief['id']}")
        for field in ("starting_position", "arms_hands", "legs_feet"):
            if not brief[field]["cues"] and brief[field]["status"] != "missing_in_source":
                errors.append(f"Undisclosed missing {field}: {brief['id']}")
        if [p["text"] for p in brief["movement"]["phases"]] != rows[brief["canonical_id"]]["instructions"]:
            errors.append(f"Original instructions not preserved: {brief['id']}")
        if brief["source"]["original_record"] != rows[brief["id"]]:
            errors.append(f"Original record changed: {brief['id']}")
        for field in ("starting_position", "arms_hands", "legs_feet", "equipment_contacts"):
            if not brief["authored_staging"][field]["proposal"]:
                errors.append(f"Missing staging proposal or explicit placeholder: {brief['id']} {field}")
        walk(brief)
    inherited = {a["alias_id"]: a["canonical_exercise_id"] for a in read("artifacts/exercise-props-inventory/aliases.json")}
    if {a["id"]: a["canonical_id"] for a in aliases} != inherited:
        errors.append("Alias mapping disagrees with previous inventory")
    if set(coverage) != set(canonical):
        errors.append("Props inventory canonical coverage mismatch")
    # Regression checks for the consequential false-positive and equipment-free boundary.
    bench = canonical["0002"]["equipment_scene"]["props"]
    if not any(p["prop_id"] == "bench_hyper45" and p["status"] == "conflict" for p in bench):
        errors.append("0002 bench conflict was lost")
    selected = sorted((b for b in canonical.values() if b["equipment_scene"]["equipment_free_candidate"]), key=lambda b: (b["name"].casefold(), b["id"]))[:5]
    if [b["id"] for b in selected] != ["5965", "5915", "5887", "0001", "9066"]:
        errors.append("First-five selection changed; inspect current source/inventory")
    return {"passed": not errors, "errors": errors, "evidence_references_checked": checked_refs,
            "unique_evidence_locations_checked": len(cache), "all_original_instructions_preserved": not any("instructions" in e for e in errors),
            "all_records_covered_uniquely": len(ids) == len(set(ids)) == len(rows),
            "all_alias_targets_resolve": all(a["canonical_id"] in canonical for a in aliases),
            "catalogue_media_opened": False}, selected


def source_corpus_hash(paths):
    digest = hashlib.sha256()
    for path in sorted(paths):
        rel = str(path.relative_to(ROOT))
        digest.update(rel.encode() + b"\0" + path.read_bytes() + b"\0")
    return digest.hexdigest()


def selected_authoring_overrides(canonical):
    return {
        "5965": {
            "status": "prepared_for_animation_authoring_with_explicit_interpretation",
            "source_verified": False,
            "movement_interpretation": "Take two quick lateral shuffle steps toward screen-left (the mannequin's anatomical right), then return to the starting area within one loop. Keep the source's light forefoot contacts and natural bent-arm swing. An opposite-side repetition can be authored separately.",
            "authoring_basis": {
                "type": "primary_authorized_pilot_interpretation",
                "evidence": [source_ref(canonical["5965"]["source"]["original_record"], "instructions[1]")],
                "rationale": "The source's one-then-two pattern is unspecified. The primary explicitly chose two lateral shuffle steps plus return for this first-five animation pilot; this is not a source-verified exercise definition.",
            },
            "retained_source_gap": "movement_pattern_unspecified",
            "scope": "Selected first-five pilot only; canonical briefs and catalogue instructions remain unchanged.",
            "production_motion_review_required": True,
        }
    }


def main():
    paths = sorted(CAT.glob("*.json"))
    rows = {p.stem: json.loads(p.read_text()) for p in paths}
    coverage_list = read(INV)
    coverage = {r["exercise_id"]: (i, r) for i, r in enumerate(coverage_list)}
    labels = {r["canonical_id"]: r["english_name"] for r in read("artifacts/exercise-props-inventory/inventory.json")}
    muscle_maps = read(MAP)
    canonical = {}
    aliases = []
    for ident, row in sorted(rows.items()):
        if "variantOf" not in row:
            idx, inv = coverage[ident]
            canonical[ident] = make_brief(row, inv, idx, labels, muscle_maps)
    briefs = list(canonical.values())
    for ident, row in sorted(rows.items()):
        if "variantOf" not in row:
            continue
        chain = [ident]
        target = row["variantOf"]
        while "variantOf" in rows[target]:
            if target in chain:
                raise ValueError(f"Alias cycle: {chain}")
            chain.append(target)
            target = rows[target]["variantOf"]
        alias = {"id": ident, "canonical_id": target, "resolution_chain": chain + [target],
                 "evidence": [source_ref(rows[x], "variantOf") for x in chain]}
        aliases.append(alias)
        base = canonical[target]
        briefs.append({**base, "id": ident, "canonical_id": target, "record_kind": "alias",
                       "alias_resolution": alias,
                       "source": {"path": f"catalogue/exercises/{ident}.json",
                                  "sha256": hashlib.sha256((CAT / f"{ident}.json").read_bytes()).hexdigest(),
                                  "original_record": row,
                                  "inherited_text_path": base["source"]["path"],
                                  "text_source": base["source"]["text_source"]}})
    briefs.sort(key=lambda b: b["id"])
    validation, selected = validate(briefs, rows, aliases, coverage)
    if not validation["passed"]:
        raise ValueError(json.dumps(validation, indent=2))
    with (OUT / "briefs.jsonl").open("w") as handle:
        for brief in briefs:
            handle.write(json.dumps(brief, ensure_ascii=False, separators=(",", ":")) + "\n")
    gzip_copy(OUT / "briefs.jsonl")
    write("aliases.json", aliases)
    write("selected-first-five.json", {"selection": "Canonical records only; body weight resistance and zero inherited inventory prop candidates; casefolded English name then ID; no guarantee that all required props are documented.", "ids": [b["id"] for b in selected], "briefs": selected, "pilot_authoring_status": "All five have explicit staging choices; 5965 uses a separately labeled primary-authorized movement interpretation.", "authoring_overrides": selected_authoring_overrides(canonical)})
    reasons = collections.Counter(r["code"] for b in canonical.values() for r in b["review_reasons"])
    statuses = collections.Counter(b["status"] for b in canonical.values())
    prop_statuses = collections.Counter(p["status"] for b in canonical.values() for p in b["equipment_scene"]["props"])
    report = {
        "schema_version": SCHEMA, "catalogue_record_count": len(rows), "canonical_count": len(canonical),
        "alias_count": len(aliases), "canonical_status_counts": dict(statuses),
        "all_record_status_counts": dict(collections.Counter(b["status"] for b in briefs)),
        "canonical_storyboard_readiness_counts": dict(collections.Counter(b["storyboard_readiness"]["status"] for b in canonical.values())),
        "storyboard_blocker_counts": dict(collections.Counter(code for b in canonical.values() for code in b["storyboard_readiness"]["blockers"]).most_common()),
        "authored_staging_field_status_counts": dict(collections.Counter(b["authored_staging"][field]["status"] for b in canonical.values() for field in ("starting_position", "arms_hands", "legs_feet", "equipment_contacts"))),
        "animation_ready_count": 0,
        "readiness_definition": "source_complete_for_storyboard means all automatic cue checks passed and no listed source/inventory gap was detected. It is not biomechanical review, motion validation, or production animation approval.",
        "review_reason_counts_canonical": dict(reasons.most_common()), "prop_adjudication_counts": dict(prop_statuses),
        "first_five_ids": [b["id"] for b in selected],
        "selected_pilot_authoring_overrides": ["5965"],
        "source_corpus_sha256": source_corpus_hash(paths),
        "input_files": [{"path": p, "sha256": hashlib.sha256((ROOT / p).read_bytes()).hexdigest()} for p in [INV, "artifacts/exercise-props-inventory/inventory.json", "artifacts/exercise-props-inventory/aliases.json", MAP]],
        "validation": validation,
        "limitations": [
            "Source text is normalized and supplemented with labeled reversible staging proposals; neither is verification that the exercise text or proposed pose is anatomically correct or safe.",
            "Heuristic cue and phase extraction can miss paraphrases or conflate position and movement. Original steps and complete original records are retained for review.",
            "An inventory prop supported by a text mention still needs placement/contact review. Optional/alternative language can describe multiple scene choices.",
            "The props inventory is not a verified ontology. Only a narrow standing/bench contradiction is automatically rejected; unrecognized contradictions can remain.",
            "Absence of documented props does not establish prop-free execution; body weight is a resistance label.",
            "Named poses do not supply exact geometry. Labeled posture-based staging proposals may supply initial hand/foot placements and a first side; no missing footfall sequence, apparatus-specific dimensions, numerical joint angles, activation curves or tempo are invented.",
            "Aliases inherit motion and muscle cues from their canonical record; figure identity does not imply a separate movement or new anatomy.",
            "Raw target and secondaryMuscles labels are preserved. Existing catalogue display maps are included separately, without synthesizing physiological activation measurements.",
            "No licensed Gym Visual media was opened, copied, analyzed, or used as AI input. Only repository text/JSON sources were read.",
        ],
    }
    write("coverage-report.json", report)
    write("review-queue.json", [{"id": b["id"], "name": b["name"], "source_reasons": b["review_reasons"], "storyboard_readiness": b["storyboard_readiness"]} for b in canonical.values() if b["review_reasons"] or b["storyboard_readiness"]["blockers"]])
    build_docs(canonical, aliases, selected, report)
    print(json.dumps({"records": len(briefs), "canonical": len(canonical), "aliases": len(aliases), "source_completeness": dict(statuses), "storyboard_readiness": report["canonical_storyboard_readiness_counts"], "validation": validation, "first_five": report["first_five_ids"]}, indent=2))


def build_detail_page(path, briefs, name):
    esc = html.escape

    def references(evidence):
        return ", ".join(f'<a href="../../../{esc(e["path"])}">{esc(Path(e["path"]).name + "#" + e["pointer"])}</a>' for e in evidence)

    def source_cues(field):
        main = "<ul>" + "".join(f'<li>{esc(c["text"])} <small>Step {c["step_number"]}; {references(c["evidence"])}</small></li>' for c in field["cues"]) + "</ul>" if field["cues"] else '<p class="gap">' + esc(field["missing_detail"]) + "</p>"
        context = "".join(f'<p><small>Title/description context: {esc(c["text"])}; {references(c["evidence"])}</small></p>' for c in field["context_cues"])
        return main + context

    parts = ['<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Animation brief details</title><style>body{font:16px/1.5 system-ui,sans-serif;max-width:1000px;margin:30px auto;padding:0 20px;background:#10171c;color:#e7eef2}a{color:#a2e1f0}article{overflow-wrap:anywhere;border-top:2px solid #476471;padding:24px 0 40px;scroll-margin-top:12px}h3{color:#b5dbe5}small{color:#c1d0d6}li{margin:8px 0}.gap{border-left:3px solid #d4ae73;padding-left:12px}code{overflow-wrap:anywhere}details{margin:18px 0}summary{cursor:pointer}</style><h1>Exercise animation brief details</h1><p><a href="../index.html">Search all exercises</a> · <a href="../README.md">Method and limitations</a></p><p>Source facts and authored proposals are separate. All proposals require owner review; none is certified production animation.</p>']
    chunk_number = int(name.split("-")[1])
    paging = []
    if chunk_number:
        paging.append(f'<a href="chunk-{chunk_number - 1:03d}.html">Previous 100 records</a>')
    if len(briefs) == 100:
        paging.append(f'<a href="chunk-{chunk_number + 1:03d}.html">Next 100 records</a>')
    parts += ['<p>' + ' · '.join(paging) + '</p>']
    for b in briefs:
        staging = b["authored_staging"]
        parts += [f'<article id="{b["id"]}"><h2>{b["id"]} — {esc(b["name"])}</h2>',
                  f'<p><a href="../index.html#{b["id"]}">Index</a> · <a href="{name}.json.gz">Full JSON chunk download (.gz; find ID {b["id"]} after decompression)</a> · <a href="../../../{b["source"]["path"]}">Source record</a></p>',
                  f'<p>Source completeness: <code>{b["status"]}</code>. Storyboard proposal: <code>{b["storyboard_readiness"]["status"]}</code>. Pose class: <code>{staging["pose_class"]}</code>.</p>',
                  '<p>' + esc(b["source"]["original_record"]["description"]) + '</p>', '<h3>Proposed staging</h3>']
        for field in ("starting_position", "arms_hands", "legs_feet", "equipment_contacts"):
            p = staging[field]
            parts += [f'<h4>{esc(field.replace("_", " ").title())}</h4><p>{esc(p["proposal"])}</p><p><small>{p["status"]}; source verified: {str(p["source_verified"]).lower()}. {esc(p["authoring_basis"]["rationale"])} {references(p["authoring_basis"]["evidence"])}</small></p>']
        parts += ['<h3>Complete ordered source instructions</h3><ol>']
        parts += [f'<li>{esc(p["text"])} <small>{references(p["evidence"])}</small></li>' for p in b["movement"]["phases"]]
        parts += ['</ol><details><summary>Extracted position and contact cues</summary>']
        for field in ("starting_position", "arms_hands", "legs_feet"):
            parts += ['<h4>' + esc(field.replace('_', ' ').title()) + '</h4>', source_cues(b[field])]
        parts += ['<h4>Scene contacts</h4>', source_cues(b["equipment_scene"]["contacts"]), '</details>']
        parts += ['<h3>Equipment / working muscle labels</h3>', '<p>Declared equipment: ' + esc(b["equipment_scene"]["declared_equipment"]["value"]) + '.</p>']
        props = b["equipment_scene"]["props"]
        parts += ['<ul>' + ''.join(f'<li>{esc(p["label"])}: <code>{p["status"]}</code>. {esc(p["review_reason"] or "")} <small>{references(p["source_evidence"])}</small></li>' for p in props) + '</ul>' if props else '<p>No additional prop documented; this is not proof of prop-free execution.</p>']
        parts += ['<p>Primary training labels: ' + esc(', '.join(m['name'] for m in b['muscles']['primary'])) + '. Secondary: ' + esc(', '.join(m['name'] for m in b['muscles']['secondary'])) + '.</p><p><small>' + esc(b['muscles']['interpretation']) + '</small></p>']
        parts += ['<h3>Source gaps / review items</h3>']
        parts += [f'<p class="gap"><code>{r["code"]}</code>: {esc(r["message"])} <small>{references(r["evidence"])}</small></p>' for r in b["review_reasons"]] or ['<p>No source gap detected by automatic checks.</p>']
        parts += ['<p>Remaining storyboard blockers: ' + esc(', '.join(b['storyboard_readiness']['blockers']) or 'none detected; owner pose/motion review remains required') + '.</p>', '<p><small>' + esc(staging['movement_policy']) + '</small></p></article>']
    parts += ['</html>']
    path.write_text('\n'.join(parts))


def build_docs(canonical, aliases, selected, report):
    def quoted(cues):
        return "\n".join(f"- {s['text']} (step {s['step_number']})" for s in cues) or "- Missing in source; requires authoring/review."

    md = ["# First five equipment-free candidates", "", "Deterministic alphabetical selection from canonical records with body-weight metadata and no inherited inventory prop candidates. This is a source-text filter, not verification of prop-free execution. All five still require animation production review.", ""]
    for b in selected:
        md += [f"## {b['id']} — {b['name']}", "", f"Source: [catalogue JSON](../../{b['source']['path']}). Brief status: `{b['status']}`.", "", "### Starting position", "", quoted(b["starting_position"]["cues"]), "", "### Arms / hands", "", quoted(b["arms_hands"]["cues"]), "", "### Legs / feet", "", quoted(b["legs_feet"]["cues"]), "", "### Ordered source movement / constraints", "", quoted(b["movement"]["phases"]), "", "### Equipment and contacts", "", "Declared resistance: body weight. No additional prop documented by the inherited inventory. Source contact cues:", "", quoted(b["equipment_scene"]["contacts"]["cues"]), "", "### Working muscle labels", "", "Primary: " + ", ".join(x["name"] for x in b["muscles"]["primary"]) + ". Secondary: " + ", ".join(x["name"] for x in b["muscles"]["secondary"]) + ". Source labels describe training emphasis, not measured activation.", "", "### Review items", "", "\n".join("- " + r["message"] for r in b["review_reasons"]) or "- No gap detected by the automatic checks. Manual motion/contact review remains required.", ""]
        md += ["### Proposed storyboard staging", "", f"Readiness: `{b['storyboard_readiness']['status']}`. These are reversible authored choices wherever source placement is incomplete; they do not erase the source gaps above.", ""]
        for field in ("starting_position", "arms_hands", "legs_feet", "equipment_contacts"):
            p = b["authored_staging"][field]
            md += [f"- **{field}** (`{p['status']}`): {p['proposal']}"]
        md += ["", "Remaining motion/source blockers: " + (", ".join(b["storyboard_readiness"]["blockers"]) or "none detected; owner pose/motion review is still required") + ".", ""]
        if b["id"] in selected_authoring_overrides(canonical):
            override = selected_authoring_overrides(canonical)[b["id"]]
            md += ["### Selected pilot authoring interpretation", "", override["movement_interpretation"], "", "Status: `" + override["status"] + "`. **Authored interpretation, not source-verified.** " + override["authoring_basis"]["rationale"], "", override["scope"], ""]
    (OUT / "selected-first-five.md").write_text("\n".join(md))
    # Lightweight summaries stay in the offline index. Full data and readable records are
    # paginated in 100-record chunks, so the browser never parses the entire JSONL at once.
    details = OUT / "details"
    details.mkdir(exist_ok=True)
    summaries = []
    ordered = sorted(canonical.values(), key=lambda b: b["id"])
    expected = set()
    for offset in range(0, len(ordered), 100):
        chunk = ordered[offset:offset + 100]
        name = f"chunk-{offset // 100:03d}"
        expected.update((name + ".json", name + ".html"))
        (details / f"{name}.json").write_text(json.dumps({"schema_version": SCHEMA, "briefs": chunk}, ensure_ascii=False, separators=(",", ":")) + "\n")
        gzip_copy(details / f"{name}.json")
        expected.add(name + ".json.gz")
        build_detail_page(details / f"{name}.html", chunk, name)
        for b in chunk:
            summaries.append({"id": b["id"], "name": b["name"], "category": b["category"],
                              "source_status": b["status"], "storyboard_status": b["storyboard_readiness"]["status"],
                              "review_codes": [r["code"] for r in b["review_reasons"]],
                              "blockers": b["storyboard_readiness"]["blockers"], "pose": b["authored_staging"]["pose_class"],
                              "muscles": [m["name"] for k in ("primary", "secondary") for m in b["muscles"][k]],
                              "equipment_free_candidate": b["equipment_scene"]["equipment_free_candidate"],
                              "source_path": b["source"]["path"], "detail_page": f"details/{name}.html#{b['id']}",
                              "detail_json": f"details/{name}.json.gz"})
    for stale in details.glob("chunk-*.*"):
        if stale.name not in expected and stale.name.endswith((".json", ".html", ".json.gz")):
            stale.unlink()
    payload = json.dumps({"briefs": summaries, "aliases": aliases, "report": report}, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
    template = (OUT / "index-template.html").read_text()
    (OUT / "index.html").write_text(template.replace("__DATA__", payload))
    states = report["canonical_status_counts"]
    (OUT / "README.md").write_text(f"""# Exercise animation briefs

All **{len(canonical):,} canonical exercises** and **{len(aliases):,} aliases** are covered ({report['catalogue_record_count']:,} unique IDs).
The source checks find **{states.get('source_complete_for_storyboard', 0):,} source-complete storyboards** and **{states.get('needs_review', 0):,} canonical briefs with source gaps**. Separately, **{report['canonical_storyboard_readiness_counts'].get('proposal_ready_for_review', 0):,} staging proposals are ready for owner review** and **{report['canonical_storyboard_readiness_counts'].get('blocked_on_source_resolution', 0):,} need source/motion resolution**. Missing initial limb cues alone do not block a proposal when a reversible posture-based placement is available. **Zero are certified animation-ready**.

## Browse and consume

- [Offline searchable index](index.html): search names/IDs, filter source completeness or storyboard readiness, then follow record links to readable 100-record pages and matching JSON chunks. Aliases resolve to canonical briefs. Open directly in a browser; no server or network needed.
- [briefs.jsonl.gz](briefs.jsonl.gz): authoritative deterministic gzip JSONL, one complete brief per source ID, including inherited fields for aliases. Generation also leaves a locally ignored raw `briefs.jsonl` for convenient use.
- `details/chunk-*.html` and matching `.json.gz` downloads: all canonical descriptions, source evidence and authored proposals, paginated in 100-record chunks; use index record links.
- [aliases.json](aliases.json): all alias chains and source pointers.
- [coverage-report.json](coverage-report.json): counts, source hashes, checks and limitations.
- [review-queue.json](review-queue.json): canonical review items with evidence.
- [First five readable samples](selected-first-five.md) and [full sample JSON](selected-first-five.json).
- [Production guide](production-guide.md) and [generation contract](generation-contract.json): known failures, prevention, remediation and observable acceptance requirements for every future animation. Source completeness is not animation approval.
- `prepare_generation.py --exercise 0001`: assemble a canonical exercise's complete source brief, aliases, constraints, open findings, selected pilot choices and muscle mappings into `artifacts/exercise-generation/0001.json` before authoring. Use `--require-ready` to reject known/source blockers; a packet never implies production approval.
- [Third-party notices](THIRD_PARTY_NOTICES.md).

## Reproduce

```sh
python3 artifacts/exercise-animation-briefs/generate.py
node artifacts/exercise-animation-briefs/check-index.mjs
node artifacts/exercise-animation-briefs/check-browser.mjs
python3 artifacts/exercise-animation-briefs/verify.py
```

Generation and data validation use the Python standard library; the index behavior check uses Node's built-in modules. The browser check reuses the workspace's existing Playwright Core and Chromium installation (override with `BRIEFS_PLAYWRIGHT` pointing to Playwright Core's `index.mjs` and `BRIEFS_CHROME` pointing to a Chromium executable). No network, app changes or exercise-media reads are needed; all deliverables are written inside this directory. `index-template.html` is the maintained index shell; `index.html` is generated. Source files and the generator have deterministic ordering. No generation timestamp is embedded. Gzip output has zero modification time and no filename header. Raw `briefs.jsonl` and raw detail `.json` chunks are locally ignored by this directory's `.gitignore`; gzip files are the authoritative durable machine-readable copies, avoiding raw duplicate JSON in Git. The HTML index links to existing `.gz` downloads and readable offline pages.

## Field contract

Each row has `starting_position`, ordered `movement.phases`, `arms_hands`, `legs_feet`, `equipment_scene` (declared resistance, needs, prop candidates and scene/contact cues), `muscles` (primary and secondary source labels), `review_reasons`, `production_review_required`, and the **complete original source record**. Empty cue lists carry `missing_in_source` and a reason. Every extracted cue cites a repository path, RFC 6901 JSON pointer, verbatim value and human-readable 1-based step number where applicable. Aliases preserve their stub in `source.original_record`; inherited cues point to their canonical source.

Phases are complete original steps with heuristic labels, not fabricated biomechanical phases. Setup and limb cues retain individual placement instructions. Timing, breathing, angles, side changes and constraints stay in the original steps. An explicit `hold` flag is preserved separately from the ordinary verb “hold.” Missing initial arm/foot placement may receive a reversible authored staging choice under `authored_staging`, with `authoring_basis`, `status`, source evidence, rationale and a `source_verified` flag. These choices do not overwrite source gaps or original cues. Canonical briefs do not invent missing exercise footfall sequences, apparatus dimensions, universal cadence or numerical joint angles. The selected pilot file separately carries the explicitly authorized 5965 two-lateral-shuffle-steps-and-return interpretation; its source gap remains intact.

`source_completeness` tracks automatic source-cue checks; source truth and animation safety remain unverified. `storyboard_readiness` is separate: a proposal can be ready for review despite missing initial hand/foot cues when a labeled reversible staging choice supplies them. Unknown body support, missing motion mechanics and unresolved apparatus remain blockers. Position cues may describe motion rather than the full initial pose, so missing starting limb geometry is explicitly flagged. Named poses require geometric interpretation even when their name is well-known.

The supplied props inventory is reused as a candidate list, with its evidence preserved. Title-only and inferred candidates remain unverified. Body-weight metadata does not prove absence of a box, bench, wall, cones, floor contacts or attachments. In exercise **0002**, the title-derived 45-degree bench is explicitly marked **conflict**: the instructions start standing and never use a bench. Do not silently copy that candidate into an animation.

Muscle labels are training metadata, not measured activation. Existing explicit display maps from `frontend/src/lib/exercise-muscle-map.json` are carried separately and can be more precise than the raw labels. Physiological weights/activation curves and extra anatomical assertions are not generated.

## Verification and limits

Generation checks every source ID, alias target, unchanged instruction array, original record and evidence pointer/quote; it also guards the 0002 conflict and first-five selection (`5965`, `5915`, `5887`, `0001`, `9066`). `verify.py` independently checks serialized deliverables, detail chunks and page anchors against current sources and reports a receipt. `check-index.mjs` executes the embedded index JavaScript with a minimal DOM stub to check filtering, pagination and alias navigation; it is complemented by `check-browser.mjs`, which opens the actual offline files in isolated headless Chromium and checks search, pagination, alias navigation, detail pages, compressed download links and mobile overflow.

Heuristics can miss paraphrases and additional contradictions. The source review queue is useful triage, not proof that unflagged records are complete or correct. Posture defaults are proposals, can miss exercise-specific exceptions and require owner review; the retained original phases remain authoritative. The first five include source gaps (notably 5965's unspecified one-two pattern and 9066's unspecified arms/hands). Full limitations and exact coverage are in `coverage-report.json`.

Only catalogue text/JSON and inventory metadata were used. No licensed Gym Visual still or animation was opened or fed to an AI system. Repository text licensing and the original ExerciseDB MIT notice are preserved in `THIRD_PARTY_NOTICES.md`.
""")
    notice = (ROOT / "NOTICE.md").read_text()
    exercise_section = notice[notice.index("## Exercise text"):notice.index("## Gym check-in")].rstrip() + "\n"
    (OUT / "THIRD_PARTY_NOTICES.md").write_text("# Text provenance and notices\n\nopenGym — Copyright (C) 2026 Duarte Santos. Original openGym text and this derived repository material remain under the repository's GNU AGPL v3.0; see [LICENSE](../../LICENSE) and [NOTICE.md](../../NOTICE.md).\n\nNo exercise media is included or used. See [media restrictions](../../catalogue/media/NOTICE.md).\n\n" + exercise_section)


if __name__ == "__main__":
    main()
