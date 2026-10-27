#!/usr/bin/env python3
"""Convert a supported local SQLite workout export to an openGym JSON backup.

Standard library only. Never uploads data or writes to the source database.
See docs/WORKOUT_MIGRATION.md for units, exclusions and restore semantics.
"""

import argparse
from collections import Counter, defaultdict
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import sys
import tempfile
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


class MigrationError(Exception):
    """A safe, value-free message suitable for the terminal."""


REQUIRED = {
    "program": "_id name comment userComment isAddedByUser user_id",
    "day": "_id program_id name comment userComment order_num",
    "exercise": ("_id day_id hasChild parent_id th_exercise_id rule order_num "
                 "restTime restTimeAfterWarming restTimeAfterExercise "
                 "isMeasureWeight isMeasureDistance isMeasureTime isMeasureReps"),
    "th_exercise": "_id name guide userComment",
    "training": "_id startDateTime finishDateTime name comment day_id user_id",
    "workout": ("_id training_id hasChild parent_id th_exercise_id rule comment order_num "
                "finishDateTime isMeasureWeight isMeasureDistance isMeasureTime isMeasureReps"),
    "set_": "_id workout_id weight reps time distance finishDateTime comment koef1 koef2",
}
OPTIONAL = {"bparam": "_id fixDateTime th_bparam_id size comment fixday_id user_id",
            "th_bparam": "_id title isAddedByUser", "fixday": "_id fixDateTime comment user_id"}
EXCLUDED = ("bphoto", "th_bpose", "fact", "note",
            "favoriteComment", "exIndividualSettings", "equip_cfg", "trmonth")
TIME_FACTORS = {"seconds": 1, "minutes": 60, "milliseconds": 0.001}
DISTANCE_FACTORS = {"meters": 0.001, "kilometers": 1, "miles": 1.609344}
RULE = re.compile(r"^\s*(\d+)(?:\s*[-–]\s*(\d+))?\s*[xх×*]\s*(\d+)(?:\s*[-–]\s*(\d+))?\s*$", re.I)
# Verified default names from GymUp's res_thBParam<ID> resources, not title matching guesses.
# Specific relaxed/strained circumferences retain their distinct custom fields.
GYMUP_MEASUREMENTS = {
    1: ("Weight", "bodyweight", "mass"), 2: ("Height", None, "length"),
    3: ("Fat percentage", "bodyFat", "percent"), 4: ("Relaxed chest", None, "length"),
    5: ("Waist", "waist", "length"), 6: ("Shoulders", "shoulders", "length"),
    7: ("Left relaxed biceps", None, "length"), 8: ("Right relaxed biceps", None, "length"),
    9: ("Left thigh", "thighLeft", "length"), 10: ("Right thigh", "thighRight", "length"),
    11: ("Left forearm", "forearmLeft", "length"), 12: ("Right forearm", "forearmRight", "length"),
    13: ("Left calf", "calfLeft", "length"), 14: ("Right calf", "calfRight", "length"),
    15: ("Neck", "neck", "length"), 16: ("Strained chest", None, "length"),
    17: ("Left strained biceps", None, "length"), 18: ("Right strained biceps", None, "length"),
    19: ("Pelvis", None, "length"),
}
SOURCE_FIELD_FAMILIES = ("exercise_rules", "day_names", "day_comments", "program_names", "program_comments", "program_info")
# IDs/labels come from the shipped muscleArray/muscleIdArray and equipment arrays.
# Canonical spellings and aliases follow frontend/src/lib/muscles.js.
GYMUP_MUSCLES = {
    1: ("Neck", "", "neck"), 2: ("Traps", "back", "trapezius"),
    3: ("Shoulders", "shoulders", "deltoids"), 4: ("Chest", "chest", "chest"),
    5: ("Lats", "back", "upper-back"), 6: ("Biceps", "upper arms", "biceps"),
    7: ("Triceps", "upper arms", "triceps"), 8: ("Forearms", "lower arms", "forearm"),
    9: ("Abdominals", "waist", "abs"), 10: ("Middle Back", "back", "upper-back"),
    11: ("Lower Back", "back", "lower-back"), 12: ("Glutes", "upper legs", "gluteal"),
    13: ("Abductors", "upper legs", "gluteal"), 14: ("Quadriceps", "upper legs", "quadriceps"),
    15: ("Adductors", "upper legs", "adductors"), 16: ("Hamstrings", "upper legs", "hamstring"),
    17: ("Calves", "lower legs", "calves"),
}
GYMUP_EQUIPMENT = {1: ("None", "custom"), 2: ("Barbell", "barbell"), 3: ("Dumbbell", "dumbbell"),
                   4: ("Kettlebells", "kettlebell"), 5: ("Machine", "custom"), 6: ("Cable", "cable"),
                   7: ("Bands", "band"), 9: ("Exercise Ball", "stability ball"), 10: ("Other", "custom")}


def number(value, label, default=0, negative=False):
    if value is None:
        return default
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise MigrationError("Invalid numeric field in " + label + ".")
    if not math.isfinite(value) or (value < 0 and not negative):
        raise MigrationError("Invalid numeric field in " + label + ".")
    return value


def text(value):
    if value is None:
        return ""
    if not isinstance(value, str):
        raise MigrationError("Invalid source text field.")
    return value


def notes(*values):
    return "\n\n".join(v for v in values if v)


def annotate(obj, *values):
    value = notes(obj.get("note", ""), *values)
    if value:
        obj["note"] = value


def timestamp(value, required=False):
    if value is None or value == 0:
        if required:
            raise MigrationError("Session has no valid start timestamp; no output written.")
        return None
    value = number(value, "timestamp")
    # This schema stores epoch milliseconds. Reject likely seconds and implausible dates.
    if value < 315532800000 or value >= 4133980800000 or int(value) != value:
        raise MigrationError("Timestamp must be epoch milliseconds between 1980 and 2100.")
    return int(value)


def stable_id(namespace, kind, *keys):
    value = json.dumps([namespace, kind, *keys], ensure_ascii=False, separators=(",", ":"))
    return "sq-" + kind + "-" + hashlib.sha256(value.encode("utf-8")).hexdigest()[:24]


def read_catalogue(path):
    """An explicitly supplied, verified source-id -> original-name JSON object."""
    with path.open(encoding="utf-8") as stream:
        value = json.load(stream)
    if not isinstance(value, dict):
        raise MigrationError("Catalogue must be a JSON object mapping source IDs to names.")
    out = {}
    for key, name in value.items():
        if not isinstance(key, str) or not key.isascii() or not key.isdecimal() or not isinstance(name, str) or not name.strip():
            raise MigrationError("Catalogue requires numeric source-ID keys and nonempty names.")
        identifier = int(key)
        if identifier in out:
            raise MigrationError("Catalogue contains duplicate numeric source IDs.")
        out[identifier] = name
    return out


def read_source_fields(path):
    with path.open(encoding="utf-8") as stream:
        value = json.load(stream)
    if not isinstance(value, dict) or set(value) != set(SOURCE_FIELD_FAMILIES):
        raise MigrationError("Source-fields bundle must contain exactly the supported resource families.")
    for entries in value.values():
        if not isinstance(entries, dict) or any(not isinstance(k, str) or not re.fullmatch(r"[1-9][0-9]*", k)
                                                or not isinstance(v, str) for k, v in entries.items()):
            raise MigrationError("Source-field resources require positive numeric keys and string values.")
    return value


def read_tables(db):
    available = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    for table, fields in REQUIRED.items():
        if table not in available:
            raise MigrationError("Unsupported source schema: required table " + table + " is absent.")
        actual = {r[1] for r in db.execute('PRAGMA table_info("' + table + '")')}
        if not set(fields.split()) <= actual:
            raise MigrationError("Unsupported source schema: required columns in " + table + " are absent.")
    tables = {}
    # Select only needed metadata. Never read preference values unrelated to units or any photos.
    for table, fields in REQUIRED.items():
        optional = {"training": ["avgPulse", "calories", "hard_sense"], "program": ["info"],
                    "th_exercise": ["mainMuscleWorked", "otherMuscles", "equipment", "type", "force", "mechanicsType"],
                    "workout": ["tonnage", "restTime", "restTimeAfterWarming", "restTimeAfterExercise", "hard_sense"],
                    "set_": ["hard_sense", "bindTime"]}.get(table, [])
        actual = {r[1] for r in db.execute('PRAGMA table_info("' + table + '")')}
        columns = fields.split() + [c for c in optional if c in actual and c not in fields.split()]
        tables[table] = [dict(r) for r in db.execute('SELECT ' + ','.join('"' + c + '"' for c in columns) + ' FROM "' + table + '" ORDER BY _id')]
        ids = [r["_id"] for r in tables[table]]
        if any(not isinstance(i, int) for i in ids) or len(set(ids)) != len(ids):
            raise MigrationError("Invalid or duplicate source identifiers in " + table + ".")
    tables["user"] = []
    for table, fields in OPTIONAL.items():
        tables[table] = []
        if table in available:
            actual = {r[1] for r in db.execute('PRAGMA table_info("' + table + '")')}
            if not set(fields.split()) <= actual:
                raise MigrationError("Unsupported source schema: required columns in " + table + " are absent.")
            tables[table] = [dict(r) for r in db.execute('SELECT ' + ','.join(fields.split()) + ' FROM "' + table + '" ORDER BY _id')]
            ids = [r["_id"] for r in tables[table]]
            if any(not isinstance(i, int) for i in ids) or len(set(ids)) != len(ids):
                raise MigrationError("Invalid or duplicate source identifiers in " + table + ".")
    if "user" in available:
        tables["user"] = [dict(r) for r in db.execute('SELECT _id FROM "user"')]
    units = []
    if "shared_prefs" in available:
        units = [r[0] for r in db.execute("SELECT value FROM shared_prefs WHERE name='unitSystem'")]
    if len(set(units)) > 1:
        raise MigrationError("Conflicting source unit metadata; resolve it before conversion.")
    tables["unit_system"] = units[0] if units else None
    tables["excluded"] = {t: db.execute('SELECT count(*) FROM "' + t + '"').fetchone()[0]
                          for t in EXCLUDED if t in available}
    return tables


def ordered(rows):
    """Keep source sibling order and flatten explicitly parented groups contiguously."""
    by_id = {r["_id"]: r for r in rows}
    children = defaultdict(list)
    for row in rows:
        parent = row["parent_id"]
        if parent not in (None, 0) and parent not in by_id:
            raise MigrationError("Missing exercise group parent reference.")
        children[parent if parent not in (None, 0) else None].append(row)
    seen = set()

    def walk(parent, group=None):
        for row in sorted(children[parent], key=lambda r: (number(r["order_num"], "exercise order"), r["_id"])):
            if row["_id"] in seen:
                raise MigrationError("Cyclic exercise group references.")
            seen.add(row["_id"])
            container = row["hasChild"] == 1
            if not container:
                yield row, group
            elif row["th_exercise_id"] is not None:
                raise MigrationError("Unsupported group carrying its own exercise reference.")
            yield from walk(row["_id"], row if container else group)
    out = list(walk(None))
    if len(seen) != len(rows):
        raise MigrationError("Cyclic or unreachable exercise group references.")
    return out


def source_metadata(row, fields):
    values = []
    for key in fields:
        if row.get(key) is not None:
            values.append(key + "=" + str(number(row[key], "source metadata", negative=True)))
    return "Source metadata (original units): " + ", ".join(values) if values else ""


def resolve_source_fields(src, chosen_programs, bundle, stats):
    if not bundle:
        return
    programs = {p["_id"]: p for p in src["program"]}
    days = {d["_id"]: d for d in src["day"]}

    def resolve(row, key, family):
        raw = text(row.get(key))
        if not re.fullmatch(r"[1-9][0-9]*", raw):
            return
        if raw not in bundle[family]:
            raise MigrationError("Unresolved bundled source resource reference.")
        row[key] = bundle[family][raw]
        row.setdefault("_resource_refs", []).append(key + "=" + raw)
        stats["source_resource_" + family + "_resolved"] += 1

    for p in programs.values():
        if p["_id"] not in chosen_programs or p["isAddedByUser"] == 1:
            continue
        token = text(p["name"])
        resolve(p, "name", "program_names")
        for key, family in [("comment", "program_comments"), ("info", "program_info")]:
            if p.get(key):
                resolve(p, key, family)
            elif token in bundle[family]:
                p[key] = bundle[family][token]
                stats["source_resource_" + family + "_resolved"] += 1
    for d in days.values():
        if d["program_id"] in chosen_programs and programs[d["program_id"]]["isAddedByUser"] != 1:
            resolve(d, "name", "day_names")
            resolve(d, "comment", "day_comments")
    for e in src["exercise"]:
        pid = days[e["day_id"]]["program_id"]
        if pid in chosen_programs and programs[pid]["isAddedByUser"] != 1:
            resolve(e, "rule", "exercise_rules")


def resource_notes(row):
    return "Original source resource references: " + ", ".join(row["_resource_refs"]) if row.get("_resource_refs") else ""


def exercise_metadata(template, stats):
    raw_primary = template.get("mainMuscleWorked")
    raw_secondary = text(template.get("otherMuscles"))
    primary = GYMUP_MUSCLES.get(raw_primary)
    secondary_ids = []
    if raw_secondary:
        if re.fullmatch(r"\s*[0-9]+(?:\s*[,;]\s*[0-9]+)*\s*[,;]?\s*", raw_secondary):
            secondary_ids = [int(v) for v in re.split(r"\s*[,;]\s*", raw_secondary.strip().rstrip(",;"))]
        else:
            stats["custom_exercises_unparsed_secondary_metadata"] += 1
    secondaries = []
    for identifier in secondary_ids:
        muscle = GYMUP_MUSCLES.get(identifier)
        if muscle and muscle[2] != "neck" and (not primary or muscle[2] != primary[2]) and muscle[2] not in secondaries:
            secondaries.append(muscle[2])
    primaries = [primary[2]] if primary and primary[2] != "neck" else []
    equipment = GYMUP_EQUIPMENT.get(template.get("equipment"))
    out = {"bp": primary[1] if primary else "", "tg": primary[2] if primary else "", "sm": secondaries,
           "primaries": primaries, "secondaries": secondaries, "muscleGroups": primaries + secondaries,
           "eq": equipment[1] if equipment else "custom"}
    description = []
    if primary:
        stats["custom_exercises_primary_muscle_preserved"] += 1
        description.append("Source primary muscle: " + primary[0] + ".")
        if not primaries:
            stats["custom_exercises_primary_muscle_not_drawable"] += 1
    elif raw_primary is not None:
        description.append("Unmapped source primary muscle ID: " + str(number(raw_primary, "muscle ID")))
    if raw_secondary:
        description.append("Original source secondary muscle IDs: " + raw_secondary)
    if secondaries:
        stats["custom_exercises_secondary_muscles_preserved"] += 1
    if equipment:
        description.append("Source equipment: " + equipment[0] + ".")
        stats["custom_exercises_equipment_preserved"] += 1
        if equipment[1] == "custom":
            stats["custom_exercises_equipment_requires_review"] += 1
    elif template.get("equipment") is not None:
        description.append("Unmapped source equipment ID: " + str(number(template["equipment"], "equipment ID")))
    description.append(source_metadata(template, ["type", "force", "mechanicsType"]))
    return out, notes(*description)


def convert_measurements(src, selected, unit, tz, namespace, catalogue, length_unit, stats):
    templates = {t["_id"]: t for t in src["th_bparam"]}
    days = {d["_id"]: d for d in src["fixday"]}
    bodyweight, measurements, custom, day_notes = {}, {}, {}, {}

    def calendar(at):
        return datetime.fromtimestamp(at / 1000, timezone.utc).astimezone(tz).date().isoformat()

    def keep_note(day, at, value):
        if not value:
            return
        old = day_notes.get(day, {})
        combined = notes(old.get("text", ""), value)
        if len(combined) > 500:
            raise MigrationError("Measurement/day comments exceed openGym's 500-character note limit; no output written.")
        day_notes[day] = {"text": combined, "_ts": max(old.get("_ts", 0), at)}

    for row in src["fixday"]:
        if row["user_id"] == selected:
            at = timestamp(row["fixDateTime"], required=True)
            keep_note(calendar(at), at, text(row["comment"]))
            stats["source_calendar_days"] += 1
    for row in src["bparam"]:
        if row["user_id"] != selected:
            stats["excluded_other_profile_body_readings"] += 1
            continue
        at = timestamp(row["fixDateTime"], required=True)
        day = calendar(at)
        tid = row["th_bparam_id"]
        if tid not in templates or (row["fixday_id"] is not None and row["fixday_id"] not in days):
            raise MigrationError("Missing body-measurement template or calendar reference.")
        template = templates[tid]
        name = text(template["title"]) or text(catalogue.get(tid))
        known = GYMUP_MEASUREMENTS.get(tid)
        # The default resource catalogue verifies the ID/type contract. Localised/custom titles
        # cannot independently establish units or distinguish body mass from a circumference.
        if template["isAddedByUser"] == 1 or not known or catalogue.get(tid, name) != known[0]:
            raise MigrationError("Body measurement type/units require a verified default GymUp --measurement-catalogue.")
        if not name:
            raise MigrationError("Body measurement has no verified title.")
        _, target, kind = known
        value = number(row["size"], "body measurement")
        if (kind == "percent" and not 0 <= value <= 100) or (kind != "percent" and value <= 0):
            raise MigrationError("Body measurement is outside its supported unit bounds.")
        if kind == "length":
            if length_unit not in ("cm", "in"):
                raise MigrationError("Length measurements require explicit --length-unit cm or in.")
            value *= 2.54 if length_unit == "in" else 1
        if target == "bodyweight":
            if day in bodyweight:
                raise MigrationError("Multiple source weigh-ins on one day cannot be represented without loss.")
            bodyweight[day] = {"d": day, "t": at, "w": value, "src": "import"}
            stats["bodyweight_readings"] += 1
        else:
            entry = measurements.setdefault(day, {"d": day, "t": at, "other": []})
            if entry["t"] != at:
                raise MigrationError("Different body-reading timestamps on one day cannot be represented without loss.")
            if target:
                if target in entry:
                    raise MigrationError("Duplicate native body-measurement field on one day.")
                entry[target] = value
            else:
                cid = stable_id(namespace, "measurement", selected, tid)
                if len(name) > 60 or any(o["id"] == cid for o in entry["other"]):
                    raise MigrationError("Custom body measurement cannot be represented safely.")
                custom[cid] = {"id": cid, "name": name, "enabled": True, "unit": length_unit}
                entry["other"].append({"id": cid, "name": name, "value": value, "unit": length_unit})
            stats["body_measurement_readings"] += 1
        keep_note(day, at, name + ": " + text(row["comment"]) if row["comment"] else "")
        stats["source_body_readings_migrated"] += 1
    stats["body_measurement_days"] = len(measurements)
    stats["custom_measurement_fields"] = len(custom)
    return {"bodyweight": [bodyweight[k] for k in sorted(bodyweight)],
            "measurements": [measurements[k] for k in sorted(measurements)],
            "customMeasurements": list(custom.values()), "dayNotes": day_notes}


def convert(db, *, timezone_name, time_unit=None, distance_unit=None, unit=None,
            user_id=None, namespace="sqlite-workouts", bodyweight_ids=(), catalogue=None,
            measurement_catalogue=None, length_unit=None, all_programs=False, source_fields=None):
    try:
        tz = ZoneInfo(timezone_name)
    except (ZoneInfoNotFoundError, ValueError):
        raise MigrationError("Unknown IANA timezone.") from None
    src = read_tables(db)
    stats = Counter()
    profiles = {r["_id"] for r in src["user"]}
    profiles.update(r["user_id"] for r in src["training"])
    profiles.update(r["user_id"] for r in src["program"] if r["isAddedByUser"] == 1)
    profiles.update(r["user_id"] for r in src["bparam"] + src["fixday"])
    if not profiles:
        profiles = {None}
    selected = None if user_id == "default" else int(user_id) if user_id is not None else None
    if user_id is None and len(profiles) > 1:
        raise MigrationError("Multiple source profiles: select --user-id (or 'default' for unassigned records).")
    if user_id is None:
        selected = next(iter(profiles))
    elif selected not in profiles:
        raise MigrationError("Selected source profile is absent.")
    stats["source_profiles"] = len(profiles)
    training = [t for t in src["training"] if t["user_id"] == selected]
    stats["excluded_other_profile_sessions"] = len(src["training"]) - len(training)
    source_unit = {"metric": "kg", "imperial": "lb"}.get(src["unit_system"])
    if unit and source_unit and unit != source_unit:
        raise MigrationError("--unit conflicts with explicit source unit metadata.")
    source_unit = unit or source_unit
    if source_unit not in ("kg", "lb"):
        raise MigrationError("Source weight unit is unknown; supply --unit kg or --unit lb.")
    if time_unit is not None and time_unit not in TIME_FACTORS:
        raise MigrationError("Unknown time unit.")
    if distance_unit is not None and distance_unit not in DISTANCE_FACTORS:
        raise MigrationError("Unknown distance unit.")
    programs = {p["_id"]: p for p in src["program"]}
    days = {d["_id"]: d for d in src["day"]}
    templates = {t["_id"]: t for t in src["th_exercise"]}
    session_ids = {t["_id"] for t in training}
    all_session_ids = {t["_id"] for t in src["training"]}
    all_workout_ids = {w["_id"] for w in src["workout"]}
    if any(w["training_id"] not in all_session_ids for w in src["workout"]):
        raise MigrationError("Missing session reference for source workout entries.")
    if any(s["workout_id"] not in all_workout_ids for s in src["set_"]):
        raise MigrationError("Missing exercise reference for source sets.")
    exercises_by_day, entries_by_session, sets_by_entry = defaultdict(list), defaultdict(list), defaultdict(list)
    for e in src["exercise"]:
        if e["day_id"] not in days:
            raise MigrationError("Missing source plan day reference.")
        exercises_by_day[e["day_id"]].append(e)
    for w in src["workout"]:
        if w["training_id"] in session_ids:
            entries_by_session[w["training_id"]].append(w)
    for s in src["set_"]:
        sets_by_entry[s["workout_id"]].append(s)
    referenced_programs = {days[t["day_id"]]["program_id"] for t in training if t["day_id"] in days}
    chosen_programs = {p["_id"] for p in src["program"]
                       if (p["isAddedByUser"] == 1 and p["user_id"] == selected) or p["_id"] in referenced_programs
                       or (all_programs and p["user_id"] in (None, selected))}
    for pid in chosen_programs:
        if pid not in programs or programs[pid]["user_id"] not in (None, selected):
            raise MigrationError("Plan reference crosses source profiles or is missing.")
    resolve_source_fields(src, chosen_programs, source_fields, stats)
    chosen_days = sorted((d for d in src["day"] if d["program_id"] in chosen_programs),
                         key=lambda d: (d["program_id"], number(d["order_num"], "day order"), d["_id"]))
    stats["excluded_unused_programs"] = len(programs) - len(chosen_programs)
    stats["excluded_unused_plan_days"] = len(days) - len(chosen_days)
    bodyweight_ids = set(bodyweight_ids)
    if bodyweight_ids - templates.keys():
        raise MigrationError("Unknown --bodyweight-exercise-id.")
    custom = {}
    catalogue = catalogue or {}

    def resolve(row):
        tid = row["th_exercise_id"]
        if tid not in templates:
            raise MigrationError("Missing source exercise template reference.")
        template = templates[tid]
        name = text(template["name"])
        from_catalogue = not name.strip()
        if from_catalogue:
            name = text(catalogue.get(tid))
        if not name.strip():
            raise MigrationError("Source exercises have no names; supply a verified --catalogue source-ID-to-name JSON file.")
        eid = stable_id(namespace, "ex", selected, tid)
        if eid not in custom:
            if from_catalogue:
                stats["custom_exercises_named_from_catalogue"] += 1
            metadata, description = exercise_metadata(template, stats)
            custom[eid] = {"id": eid, "n": name, "custom": True, **metadata,
                           "desc": notes(text(template["guide"]), text(template["userComment"]), description)}
            if tid in bodyweight_ids:
                custom[eid]["eq"] = "body weight"
        return eid

    def group_notes(group):
        if not group:
            return ""
        return notes("Source exercise group.", text(group.get("comment")),
                     "Source group rule: " + text(group["rule"]) if group["rule"] else "",
                     source_metadata(group, ["restTime", "restTimeAfterWarming", "restTimeAfterExercise", "hard_sense"]))

    def convert_set(row):
        weight = number(row["weight"], "set weight")
        reps = number(row["reps"], "set reps")
        if reps != int(reps):
            raise MigrationError("Fractional repetitions cannot be represented safely.")
        k1 = number(row["koef1"], "load coefficient", default=1)
        k2 = number(row["koef2"], "load coefficient", negative=True)
        effective = weight * k1 + k2
        if effective < 0 or not math.isfinite(effective):
            raise MigrationError("Unsupported negative or non-finite effective load.")
        raw_time = number(row["time"], "set duration")
        raw_distance = number(row["distance"], "set distance")
        if raw_time and not time_unit:
            raise MigrationError("Measured durations require explicit --time-unit.")
        if raw_distance and not distance_unit:
            raise MigrationError("Measured distances require explicit --distance-unit.")
        sec = raw_time * TIME_FACTORS.get(time_unit, 1)
        km = raw_distance * DISTANCE_FACTORS.get(distance_unit, 1)
        if not math.isfinite(sec) or not math.isfinite(km) or (sec and not math.isfinite(km * 3600 / sec)):
            raise MigrationError("Converted duration or distance is outside finite numeric bounds.")
        end = timestamp(row["finishDateTime"])
        done = end is not None
        stats["sets_source_finished" if done else "sets_source_unfinished"] += 1
        out = {"done": done}
        if end is not None:
            out["at"] = end
        if reps or not (sec or km):
            out.update(mode="reps", w=effective, r=int(reps))
        elif km:
            out.update(mode="cardio", min=sec / 60, speed=km * 3600 / sec if sec else 0)
        else:
            out.update(mode="time", w=effective, sec=sec)
        annotate(out, text(row["comment"]), source_metadata(row, ["hard_sense", "bindTime"]))
        if k1 != 1 or k2 != 0:
            stats["sets_effective_load_applied"] += 1
            annotate(out, f"Source load: weight={weight} {source_unit}; koef1={k1}; koef2={k2}. Effective load = weight × koef1 + koef2.")
        if (reps and (sec or km)) or (km and (not sec or effective)):
            stats["sets_extra_measurements_in_notes"] += 1
            annotate(out, f"Additional source measurements: duration={raw_time} {time_unit}; distance={raw_distance} {distance_unit}; load={effective} {source_unit}.")
        if not (effective or reps or sec or km):
            stats["sets_without_measurements"] += 1
            annotate(out, "Source set contains no measured load, repetitions, duration or distance.")
        if effective == 0:
            stats["sets_zero_external_load"] += 1
        stats["sets"] += 1
        return out, end, effective * reps if done else 0

    routines, routine_ids = [], {}
    for day in chosen_days:
        p = programs[day["program_id"]]
        rid = stable_id(namespace, "routine", selected, day["_id"])
        configs = []
        for row, group in ordered(exercises_by_day[day["_id"]]):
            cfg = {"id": resolve(row), "sets": 1, "mode": "reps", "reps": 0, "weight": 0}
            rule = text(row["rule"])
            match = RULE.fullmatch(rule)
            if match and row["isMeasureReps"] == 1:
                count, count_max = int(match[1]), int(match[2] or match[1])
                low, high = int(match[3]), int(match[4] or match[3])
                if not (1 <= count <= count_max <= 100 and 1 <= low <= high <= 10000):
                    raise MigrationError("Unsupported planned set/repetition bounds.")
                cfg.update(sets=count, reps=high)
                if count_max != count:
                    cfg["setsMax"] = count_max
                    stats["planned_set_ranges_parsed"] += 1
                if low != high:
                    cfg["repsMin"] = low
                stats["planned_rules_parsed"] += 1
            else:
                stats["planned_rules_retained_as_notes"] += 1
                if row["isMeasureDistance"] == 1:
                    cfg = {"id": cfg["id"], "sets": 1, "mode": "cardio", "min": 0, "speed": 0}
                elif row["isMeasureTime"] == 1 and row["isMeasureReps"] != 1:
                    cfg = {"id": cfg["id"], "sets": 1, "mode": "time", "sec": 0, "weight": 0}
                annotate(cfg, "Source prescription was not interpreted. Placeholder target: review before starting this routine.")
            annotate(cfg, text(p["comment"]), text(p["userComment"]), text(day["comment"]), text(day["userComment"]),
                     text(p.get("info")), resource_notes(p), resource_notes(day), resource_notes(row),
                     "Source rule: " + rule if rule else "", group_notes(group),
                     source_metadata(row, ["restTime", "restTimeAfterWarming", "restTimeAfterExercise"]))
            if row["th_exercise_id"] in bodyweight_ids:
                cfg["bodyweight"] = True
            if group:
                cfg["sg"] = stable_id(namespace, "plan-group", selected, group["_id"])
            configs.append(cfg)
        if not configs and any(text(x) for x in (p["comment"], p["userComment"], day["comment"], day["userComment"])):
            raise MigrationError("A plan day with notes but no exercises cannot be represented safely.")
        routine_ids[day["_id"]] = rid
        routines.append({"id": rid, "name": notes(text(p["name"]), text(day["name"])).replace("\n\n", " / ") or "Imported plan", "emoji": "figureStrength", "ex": configs})
    workouts = []
    for session in training:
        start = timestamp(session["startDateTime"], required=True)
        finish = timestamp(session["finishDateTime"])
        if finish is not None and finish < start:
            raise MigrationError("Session finish precedes its start.")
        entries, observed_ends, volume = [], [start], 0
        for row, group in ordered(entries_by_session[session["_id"]]):
            entry = {"id": resolve(row), "sets": [], "topW": None}
            entry_end = timestamp(row["finishDateTime"])
            stats["entries_source_finished" if entry_end else "entries_source_unfinished"] += 1
            if entry_end:
                observed_ends.append(entry_end)
            entry_volume = 0
            for source_set in sets_by_entry[row["_id"]]:
                s, end, set_volume = convert_set(source_set)
                entry["sets"].append(s)
                entry_volume += set_volume
                if end:
                    observed_ends.append(end)
                if s["done"] and "w" in s:
                    entry["topW"] = max(entry["topW"] or 0, s["w"])
            if not entry["sets"]:
                stats["entries_without_sets"] += 1
            annotate(entry, text(row["comment"]), "Source rule: " + text(row["rule"]) if row["rule"] else "", group_notes(group),
                     source_metadata(row, ["restTime", "restTimeAfterWarming", "restTimeAfterExercise", "hard_sense"]))
            if row["th_exercise_id"] in bodyweight_ids:
                entry["target"] = {"bodyweight": True}
            if group:
                entry["sg"] = stable_id(namespace, "history-group", selected, group["_id"])
            stored_volume = row.get("tonnage")
            if stored_volume is not None and not math.isclose(number(stored_volume, "source volume"), entry_volume, rel_tol=1e-7, abs_tol=0.01):
                stats["entries_source_volume_discrepancies"] += 1
                annotate(entry, "Source aggregate tonnage=" + str(stored_volume) + "; migrated volume is recomputed from finished sets.")
            entries.append(entry)
            volume += entry_volume
            stats["entries"] += 1
        if any(end < start for end in observed_ends):
            raise MigrationError("An exercise/set timestamp precedes its session start.")
        rid = routine_ids.get(session["day_id"])
        if session["day_id"] is not None and not rid:
            stats["sessions_without_resolvable_plan"] += 1
        name = text(session["name"])
        if not name and session["day_id"] in days:
            day = days[session["day_id"]]
            program = programs.get(day["program_id"])
            name = " / ".join(x for x in [text(program["name"]) if program else "", text(day["name"])] if x)
            stats["sessions_named_from_plan"] += 1
        w = {"id": stable_id(namespace, "workout", selected, session["_id"]),
             "d": datetime.fromtimestamp(start / 1000, timezone.utc).astimezone(tz).date().isoformat(),
             "start": start, "end": finish if finish is not None else max(observed_ends),
             "routineId": rid, "name": name or "Imported", "entries": entries, "prs": [], "vol": volume}
        annotate(w, text(session["comment"]), source_metadata(session, ["avgPulse", "calories", "hard_sense"]))
        stats["sessions_source_finished" if finish else "sessions_source_unfinished"] += 1
        if finish is None:
            annotate(w, "Source session has no finish timestamp. History retained; end is the latest recorded exercise/set finish, or start when none exists. This does not assert source completion.")
            stats["sessions_end_inferred_from_records" if len(observed_ends) > 1 else "sessions_end_equal_start"] += 1
        workouts.append(w)
    exported_set_count = sum(len(sets_by_entry[row["_id"]]) for rows in entries_by_session.values() for row in rows)
    if stats["sets"] != exported_set_count:
        raise MigrationError("Source group containers carry sets that cannot be represented safely; no output written.")
    workouts.sort(key=lambda w: (w["start"], w["id"]))
    stats.update(sessions=len(workouts), routines=len(routines), custom_exercises=len(custom), programs=len(chosen_programs))
    body = convert_measurements(src, selected, source_unit, tz, namespace, measurement_catalogue or {}, length_unit, stats)
    report = {"format": "opengym-sqlite-migration-v1", "counts": dict(sorted(stats.items())),
              "source_table_counts": {table: len(src[table]) for table in list(REQUIRED) + list(OPTIONAL)},
              "units": {"weight": source_unit, "source_time": time_unit, "source_distance": distance_unit},
              "timezone": timezone_name, "all_programs": all_programs, "excluded_table_counts": src["excluded"],
              "limitations": ["Backup import replaces the target profile; export its backup first.",
                              "Unparsed prescriptions use placeholder targets; original rules and plan notes remain in exercise notes.",
                              "Shipped GymUp muscle/equipment enum labels are preserved; undrawable muscles and broad equipment categories remain documented. Bodyweight flags require an explicit exercise-id selection.",
                              "Media, standalone notebook notes, schedules, quiz/default photo-pose catalogues and app/account preferences are not migrated; the original database remains the full archive.",
                              "Body-reading comments use day notes; unknown measurement types/units or same-day collisions stop conversion rather than discard readings.",
                              "Source load coefficients are applied; volume is recomputed from finished sets, not stale source aggregates."]}
    return {"unit": source_unit, "workouts": workouts, "routines": routines, "customEx": list(custom.values()), **body}, report


def check_destination(path, source, overwrite):
    if path.is_symlink() or path.resolve() == source.resolve():
        raise MigrationError("Refusing source overwrite or symlink output.")
    if path.exists():
        if os.path.samefile(path, source):
            raise MigrationError("Refusing to overwrite the source database.")
        if not overwrite:
            raise MigrationError("Output exists; choose another path or use --overwrite.")
        if not path.is_file():
            raise MigrationError("Output must be a regular file.")


def atomic_json(path, payload, overwrite):
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    descriptor, tmp = tempfile.mkstemp(prefix=".workout-migration-", dir=str(path.parent))
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, ensure_ascii=False, allow_nan=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        if overwrite:
            os.replace(tmp, path)
        else:
            # Unlike rename/replace, link fails atomically if a competing writer created output.
            os.link(tmp, path)
            os.unlink(tmp)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, help="Private aggregate-only report; defaults beside output.")
    parser.add_argument("--catalogue", type=Path, help="Verified source exercise IDs to original names, as a local JSON object.")
    parser.add_argument("--measurement-catalogue", type=Path, help="Verified default GymUp res_thBParam IDs to titles.")
    parser.add_argument("--source-fields", type=Path, help="Verified resource-family bundle for stored GymUp program/day/rule references.")
    parser.add_argument("--length-unit", choices=("cm", "in"), help="Explicit source unit for length measurements; no inference from metric settings.")
    parser.add_argument("--all-programs", action="store_true", help="Include every source program/day, including bundled routines.")
    parser.add_argument("--timezone", required=True, help="IANA timezone used to derive history calendar days.")
    parser.add_argument("--time-unit", choices=TIME_FACTORS)
    parser.add_argument("--distance-unit", choices=DISTANCE_FACTORS)
    parser.add_argument("--unit", choices=("kg", "lb"), help="Source unit only when metadata is absent; output keeps this unit.")
    parser.add_argument("--user-id", help="Select a profile; 'default' selects unassigned source records.")
    parser.add_argument("--namespace", default="sqlite-workouts", help="Keep the same namespace for repeated exports of one source.")
    parser.add_argument("--bodyweight-exercise-id", type=int, action="append", default=[])
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(argv)
    try:
        source = args.source.expanduser().resolve(strict=True)
        if not source.is_file():
            raise MigrationError("Source must be an existing regular SQLite file.")
        output = args.output.expanduser().absolute()
        report_path = Path(args.report).expanduser().absolute() if args.report else output.with_suffix(".report.json")
        if output.resolve() == report_path.resolve():
            raise MigrationError("Backup and report must have different destinations.")
        check_destination(output, source, args.overwrite)
        check_destination(report_path, source, args.overwrite)
        catalogue = None
        measurement_catalogue = None
        source_fields = None
        if args.catalogue:
            catalogue_path = args.catalogue.expanduser().resolve(strict=True)
            check_destination(output, catalogue_path, args.overwrite)
            check_destination(report_path, catalogue_path, args.overwrite)
            catalogue = read_catalogue(catalogue_path)
        if args.measurement_catalogue:
            measurement_path = args.measurement_catalogue.expanduser().resolve(strict=True)
            check_destination(output, measurement_path, args.overwrite)
            check_destination(report_path, measurement_path, args.overwrite)
            measurement_catalogue = read_catalogue(measurement_path)
        if args.source_fields:
            fields_path = args.source_fields.expanduser().resolve(strict=True)
            check_destination(output, fields_path, args.overwrite)
            check_destination(report_path, fields_path, args.overwrite)
            source_fields = read_source_fields(fields_path)
        with closing(sqlite3.connect(source.as_uri() + "?mode=ro", uri=True)) as db:
            db.row_factory = sqlite3.Row
            db.execute("PRAGMA query_only=ON")
            db.execute("BEGIN")  # One consistent snapshot, including source tables and metadata.
            if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                raise MigrationError("Source SQLite integrity check failed.")
            backup, report = convert(db, timezone_name=args.timezone, time_unit=args.time_unit,
                                     distance_unit=args.distance_unit, unit=args.unit, user_id=args.user_id,
                                     namespace=args.namespace, bodyweight_ids=args.bodyweight_exercise_id, catalogue=catalogue,
                                     measurement_catalogue=measurement_catalogue, length_unit=args.length_unit,
                                     all_programs=args.all_programs, source_fields=source_fields)
        atomic_json(report_path, report, args.overwrite)
        atomic_json(output, backup, args.overwrite)
        print(json.dumps({"counts": report["counts"]}, sort_keys=True))
        return 0
    except MigrationError as error:
        print("Migration failed: " + str(error), file=sys.stderr)
    except (OSError, sqlite3.Error, ValueError, OverflowError):
        # SQL errors, paths and source values can carry private text. Never echo them.
        print("Migration failed: could not read or convert the source, or write the private output.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
