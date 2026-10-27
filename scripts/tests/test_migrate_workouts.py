"""Synthetic-only migration checks, including the real openGym backup importer."""

from contextlib import closing
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("migrate_workouts", ROOT / "scripts/migrate-workouts.py")
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)
EXTRACT_SPEC = importlib.util.spec_from_file_location("extract_gymup_catalogue", ROOT / "scripts/extract-gymup-catalogue.py")
EXTRACT = importlib.util.module_from_spec(EXTRACT_SPEC)
EXTRACT_SPEC.loader.exec_module(EXTRACT)
START = 1761435000000  # Synthetic fixture: evening UTC before Prague's DST transition day.


def fixture(path=":memory:"):
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    for table, fields in {**M.REQUIRED, **M.OPTIONAL}.items():
        db.execute('CREATE TABLE "' + table + '" (' + ','.join('"' + f + '"' for f in fields.split()) + ')')
    db.executescript("""
        CREATE TABLE shared_prefs (name, value);
        INSERT INTO shared_prefs VALUES ('unitSystem', 'metric');
        CREATE TABLE user (_id);
    """)

    def insert(table, **values):
        db.execute('INSERT INTO "' + table + '" (' + ','.join('"' + k + '"' for k in values) + ') VALUES ('
                   + ','.join('?' for _ in values) + ')', list(values.values()))
    insert("th_bparam", _id=1, title="Weight", isAddedByUser=0)
    insert("bparam", _id=1, fixDateTime=START, th_bparam_id=1, size=75.5)
    insert("program", _id=1, name="Synthetic program", comment="Program note", userComment="Personal plan note", isAddedByUser=1)
    insert("program", _id=2, name="Unused built-in")
    insert("day", _id=10, program_id=1, name="Fixture day", comment="Day note", order_num=0)
    insert("day", _id=11, program_id=2, name="Unused day", order_num=0)
    for tid, name in [(100, "Fixture lift"), (101, "Fixture run"), (102, "Fixture hold")]:
        insert("th_exercise", _id=tid, name=name, guide="Original guidance", userComment="Standing note")
    insert("exercise", _id=1, day_id=10, th_exercise_id=100, rule="3×8-12", order_num=1, isMeasureWeight=1, isMeasureReps=1, restTime=90)
    insert("exercise", _id=2, day_id=10, th_exercise_id=101, rule="unparsed prescription", order_num=0, isMeasureDistance=1, isMeasureTime=1)
    insert("training", _id=1, startDateTime=START, finishDateTime=START + 3600000, name="Fixture session", comment="Session note", day_id=10)
    insert("workout", _id=1, training_id=1, th_exercise_id=100, order_num=1, comment="Lift note", rule="3×8", finishDateTime=START + 60000)
    insert("workout", _id=2, training_id=1, th_exercise_id=101, order_num=0, finishDateTime=START + 1800000)
    insert("workout", _id=3, training_id=1, th_exercise_id=102, order_num=2, finishDateTime=START + 2000000)
    insert("set_", _id=2, workout_id=1, weight=20, reps=8, koef1=2, koef2=15, finishDateTime=START + 60000, comment="Set note")
    insert("set_", _id=1, workout_id=1, weight=10, reps=5, finishDateTime=START + 30000)
    insert("set_", _id=3, workout_id=2, time=10, distance=2000, finishDateTime=START + 1800000)
    insert("set_", _id=4, workout_id=3, time=0.5, finishDateTime=START + 2000000)
    db.commit()
    return db


def convert(db, **kwargs):
    return M.convert(db, **dict({"timezone_name": "Europe/Prague", "time_unit": "minutes", "distance_unit": "meters"}, **kwargs))


class ConversionTests(unittest.TestCase):
    def setUp(self):
        self.db = fixture()
        self.addCleanup(self.db.close)

    def test_dates_ordering_sets_units_and_effective_load(self):
        backup, report = convert(self.db)
        w = backup["workouts"][0]
        self.assertEqual(w["d"], "2025-10-26")
        self.assertEqual(w["start"], START)
        self.assertEqual(w["end"] - w["start"], 3600000)
        self.assertEqual([e["sets"][0]["mode"] for e in w["entries"]], ["cardio", "reps", "time"])
        self.assertEqual(w["entries"][0]["sets"][0]["min"], 10)
        self.assertEqual(w["entries"][0]["sets"][0]["speed"], 12)
        self.assertEqual([s["w"] for s in w["entries"][1]["sets"]], [10, 55])
        self.assertEqual(w["entries"][2]["sets"][0]["sec"], 30)
        self.assertEqual(w["vol"], 490)
        self.assertEqual(w["entries"][1]["topW"], 55)
        self.assertEqual(backup["unit"], "kg")
        self.assertEqual(report["counts"]["sets"], 4)
        self.assertEqual(report["counts"]["excluded_unused_programs"], 1)
        self.assertEqual(report["excluded_table_counts"], {})

    def test_source_notes_names_and_rules_are_preserved(self):
        backup, report = convert(self.db)
        w = backup["workouts"][0]
        self.assertIn("Session note", w["note"])
        self.assertIn("Lift note", w["entries"][1]["note"])
        s = w["entries"][1]["sets"][1]
        self.assertIn("Set note", s["note"])
        self.assertIn("koef1=2", s["note"])
        self.assertEqual({e["n"] for e in backup["customEx"]}, {"Fixture lift", "Fixture run", "Fixture hold"})
        self.assertTrue(all(e["custom"] for e in backup["customEx"]))
        planned = backup["routines"][0]["ex"]
        self.assertEqual((planned[1]["sets"], planned[1]["reps"], planned[1]["repsMin"]), (3, 12, 8))
        for fragment in ["Program note", "Personal plan note", "Day note", "unparsed prescription", "Placeholder target"]:
            self.assertIn(fragment, planned[0]["note"])
        self.assertEqual(report["counts"]["planned_rules_retained_as_notes"], 1)

    def test_set_completion_instants_are_retained_without_inventing_unfinished_ticks(self):
        self.db.execute('UPDATE set_ SET finishDateTime=NULL WHERE _id=1')
        after_session = START + 3660000
        self.db.execute('UPDATE set_ SET finishDateTime=? WHERE _id=2', (after_session,))
        out, _ = convert(self.db)
        lift = out["workouts"][0]["entries"][1]
        self.assertFalse(lift["sets"][0]["done"])
        self.assertNotIn("at", lift["sets"][0])
        self.assertEqual(lift["sets"][1]["at"], after_session)
        self.assertEqual(out["workouts"][0]["end"], START + 3600000)
        self.assertEqual(out["workouts"][0]["entries"][2]["sets"][0]["at"], START + 2000000)

    def test_explicit_set_and_rep_ranges_use_existing_supported_target_fields(self):
        self.db.execute('UPDATE exercise SET rule=? WHERE _id=1', ("2-4×8-12",))
        out, report = convert(self.db)
        cfg = out["routines"][0]["ex"][1]
        self.assertEqual((cfg["sets"], cfg["setsMax"], cfg["repsMin"], cfg["reps"]), (2, 4, 8, 12))
        self.assertNotIn("prog", cfg)  # A source target range does not prescribe a progression policy.
        self.assertEqual(report["counts"]["planned_set_ranges_parsed"], 1)
        self.db.execute('UPDATE exercise SET rule=? WHERE _id=1', ("4-2×8-12",))
        with self.assertRaisesRegex(M.MigrationError, "planned set/repetition bounds"):
            convert(self.db)

    def test_bodyweight_reading_preserves_native_time_day_unit_and_comments(self):
        self.db.execute('UPDATE bparam SET comment=?', ("Fixture weigh-in note",))
        out, report = convert(self.db)
        self.assertEqual(out["bodyweight"], [{"d": "2025-10-26", "t": START, "w": 75.5, "src": "import"}])
        self.assertIn("Fixture weigh-in note", out["dayNotes"]["2025-10-26"]["text"])
        self.assertEqual(report["counts"]["source_body_readings_migrated"], 1)
        self.assertEqual(out["measurements"], [])
        self.db.execute('UPDATE th_bparam SET title=NULL')
        with self.assertRaisesRegex(M.MigrationError, "measurement-catalogue"):
            convert(self.db)
        self.assertEqual(convert(self.db, measurement_catalogue={1: "Weight"})[0]["bodyweight"], out["bodyweight"])

    def test_native_and_distinct_custom_lengths_require_explicit_unit(self):
        self.db.execute('INSERT INTO th_bparam (_id,title) VALUES (5,"Waist"),(2,"Height")')
        self.db.execute('INSERT INTO bparam (_id,fixDateTime,th_bparam_id,size) VALUES (2,?,5,81.3),(3,?,2,180.4)', (START, START))
        with self.assertRaisesRegex(M.MigrationError, "--length-unit"):
            convert(self.db)
        out, report = convert(self.db, length_unit="cm")
        self.assertEqual(out["measurements"][0]["waist"], 81.3)
        self.assertEqual(out["measurements"][0]["other"][0]["value"], 180.4)
        self.assertEqual(out["customMeasurements"][0]["name"], "Height")
        self.assertEqual(out["customMeasurements"][0]["unit"], "cm")
        self.assertEqual(report["counts"]["source_body_readings_migrated"], 3)
        inches, _ = convert(self.db, length_unit="in")
        self.assertAlmostEqual(inches["measurements"][0]["waist"], 81.3 * 2.54)

    def test_invalid_or_colliding_body_readings_block_conversion(self):
        mutations = ['UPDATE bparam SET size=-1', 'UPDATE bparam SET th_bparam_id=999',
                     'UPDATE bparam SET fixDateTime=NULL', 'UPDATE bparam SET fixday_id=999',
                     'INSERT INTO bparam SELECT 2,fixDateTime,th_bparam_id,size,comment,fixday_id,user_id FROM bparam']
        for sql in mutations:
            with self.subTest(sql=sql), closing(fixture()) as db:
                db.execute(sql)
                with self.assertRaises(M.MigrationError):
                    convert(db)

    def test_all_programs_includes_unreferenced_bundled_days_without_duplicating_history(self):
        default, _ = convert(self.db)
        all_plans, report = convert(self.db, all_programs=True)
        self.assertEqual(len(default["routines"]), 1)
        self.assertEqual(len(all_plans["routines"]), 2)
        self.assertEqual(all_plans["workouts"], default["workouts"])
        self.assertEqual(report["counts"]["excluded_unused_programs"], 0)

    def test_resource_reference_values_resolve_bundled_fields_and_keep_user_text(self):
        self.db.execute('UPDATE program SET name="101" WHERE _id=2')
        self.db.execute('UPDATE day SET name="2",comment="3" WHERE _id=11')
        self.db.execute('INSERT INTO exercise (_id,day_id,th_exercise_id,rule,isMeasureReps) VALUES (3,11,100,"100",1)')
        self.db.execute('UPDATE exercise SET rule="100" WHERE _id=1')
        bundle = {key: {} for key in M.SOURCE_FIELD_FAMILIES}
        bundle.update(program_names={"101": "Bundled fixture program"}, day_names={"2": "Bundled fixture day"},
                      day_comments={"3": "Bundled fixture day note"}, exercise_rules={"100": "4x10-15"},
                      program_comments={"101": "Bundled fixture program note"}, program_info={"101": "Fixture info"})
        out, report = convert(self.db, all_programs=True, source_fields=bundle)
        built = out["routines"][1]
        self.assertEqual(built["name"], "Bundled fixture program / Bundled fixture day")
        self.assertEqual((built["ex"][0]["sets"], built["ex"][0]["repsMin"], built["ex"][0]["reps"]), (4, 10, 15))
        for part in ["Fixture info", "Bundled fixture day note", "rule=100"]:
            self.assertIn(part, built["ex"][0]["note"])
        self.assertIn("Source rule: 100", out["routines"][0]["ex"][1]["note"])
        self.assertEqual(report["counts"]["source_resource_exercise_rules_resolved"], 1)
        del bundle["exercise_rules"]["100"]
        with self.assertRaisesRegex(M.MigrationError, "Unresolved bundled source resource"):
            convert(self.db, all_programs=True, source_fields=bundle)

    def test_verified_muscle_and_equipment_enums_keep_primary_secondary_and_unknowns_honest(self):
        for column, kind in [("mainMuscleWorked", "INTEGER"), ("otherMuscles", "TEXT"), ("equipment", "INTEGER")]:
            self.db.execute('ALTER TABLE th_exercise ADD COLUMN '+column+' '+kind)
        self.db.execute('UPDATE th_exercise SET mainMuscleWorked=6,otherMuscles="7;8",equipment=3 WHERE _id=100')
        self.db.execute('UPDATE th_exercise SET mainMuscleWorked=1,equipment=1 WHERE _id=101')
        out, report = convert(self.db)
        lift = next(c for c in out["customEx"] if c["n"] == "Fixture lift")
        self.assertEqual(lift["primaries"], ["biceps"])
        self.assertEqual(lift["secondaries"], ["triceps", "forearm"])
        self.assertEqual(lift["bp"], "upper arms")
        self.assertEqual(lift["eq"], "dumbbell")
        no_equipment = next(c for c in out["customEx"] if c["n"] == "Fixture run")
        self.assertEqual(no_equipment["eq"], "custom")
        self.assertEqual(no_equipment["bp"], "")  # Neck is inert in openGym's diagram; do not credit traps.
        self.assertIn("Source equipment: None", no_equipment["desc"])
        self.assertEqual(report["counts"]["custom_exercises_primary_muscle_not_drawable"], 1)

    def test_stable_output_ids_and_separate_sessions_on_same_day(self):
        first, _ = convert(self.db)
        again, _ = convert(self.db)
        self.assertEqual(first, again)
        self.db.execute('INSERT INTO training (_id,startDateTime,finishDateTime,name) VALUES (2,?,?,?)', (START + 5000000, START + 6000000, "Fixture evening"))
        after, _ = convert(self.db)
        self.assertEqual(len(after["workouts"]), 2)
        self.assertEqual(first["workouts"][0]["id"], after["workouts"][0]["id"])
        self.assertNotEqual(after["workouts"][0]["id"], after["workouts"][1]["id"])
        self.assertNotEqual(convert(self.db, namespace="other-source")[0]["workouts"][0]["id"], first["workouts"][0]["id"])

    def test_timezone_changes_calendar_day_without_changing_instant(self):
        utc, _ = convert(self.db, timezone_name="UTC")
        prague, _ = convert(self.db, timezone_name="Europe/Prague")
        self.assertNotEqual(utc["workouts"][0]["d"], prague["workouts"][0]["d"])
        self.assertEqual(utc["workouts"][0]["start"], prague["workouts"][0]["start"])
        with self.assertRaisesRegex(M.MigrationError, "timezone"):
            convert(self.db, timezone_name="invalid-zone")

    def test_unfinished_sessions_and_sets_keep_completion_information(self):
        self.db.execute('UPDATE training SET finishDateTime=NULL')
        self.db.execute('UPDATE set_ SET finishDateTime=NULL WHERE _id=2')
        out, report = convert(self.db)
        w = out["workouts"][0]
        self.assertEqual(w["end"], START + 2000000)
        self.assertFalse(w["entries"][1]["sets"][1]["done"])
        self.assertEqual(w["vol"], 50)
        self.assertIn("does not assert source completion", w["note"])
        self.assertEqual(report["counts"]["sets_source_unfinished"], 1)

    def test_empty_history_entries_and_sessions_are_not_dropped(self):
        self.db.execute('DELETE FROM set_')
        self.db.execute('UPDATE training SET finishDateTime=NULL')
        self.db.execute('UPDATE workout SET finishDateTime=NULL')
        out, report = convert(self.db)
        self.assertEqual(len(out["workouts"]), 1)
        self.assertEqual(len(out["workouts"][0]["entries"]), 3)
        self.assertEqual(out["workouts"][0]["end"], START)
        self.assertEqual(report["counts"]["entries_without_sets"], 3)

    def test_zero_weight_does_not_invent_body_mass_and_bodyweight_is_explicit(self):
        self.db.execute('UPDATE set_ SET weight=0,koef1=NULL,koef2=NULL WHERE workout_id=1')
        out, _ = convert(self.db, bodyweight_ids=[100])
        e = out["workouts"][0]["entries"][1]
        self.assertTrue(e["target"]["bodyweight"])
        self.assertTrue(all(s["w"] == 0 for s in e["sets"]))
        self.assertNotIn("bw", out["workouts"][0])
        self.assertEqual(next(c for c in out["customEx"] if c["id"] == e["id"])["eq"], "body weight")

    def test_explicit_units_required_and_conflicts_rejected(self):
        for option in [dict(time_unit=None), dict(distance_unit=None), dict(unit="lb")]:
            with self.subTest(option=option), self.assertRaises(M.MigrationError):
                convert(self.db, **option)
        self.db.execute('DELETE FROM shared_prefs')
        with self.assertRaisesRegex(M.MigrationError, "unit is unknown"):
            convert(self.db)
        self.assertEqual(convert(self.db, unit="lb")[0]["unit"], "lb")

    def test_multi_profile_selection_does_not_merge_histories(self):
        self.db.execute('INSERT INTO user VALUES (7)')
        self.db.execute('INSERT INTO training (_id,startDateTime,finishDateTime,user_id) VALUES (2,?,?,7)', (START, START + 1000))
        with self.assertRaisesRegex(M.MigrationError, "Multiple source profiles"):
            convert(self.db)
        out, report = convert(self.db, user_id="7")
        self.assertEqual(len(out["workouts"]), 1)
        self.assertEqual(report["counts"]["excluded_other_profile_sessions"], 1)
        self.assertEqual(convert(self.db, user_id="default")[1]["counts"]["sessions"], 1)

    def test_missing_day_is_reported_but_history_survives(self):
        self.db.execute('UPDATE training SET day_id=999')
        out, report = convert(self.db)
        self.assertIsNone(out["workouts"][0]["routineId"])
        self.assertEqual(report["counts"]["sessions_without_resolvable_plan"], 1)

    def test_missing_references_and_invalid_measurements_block_output(self):
        mutations = [
            'UPDATE workout SET th_exercise_id=999 WHERE _id=1',
            'UPDATE workout SET training_id=999 WHERE _id=1',
            'UPDATE set_ SET workout_id=999 WHERE _id=1',
            'UPDATE set_ SET weight=-1 WHERE _id=1',
            'UPDATE set_ SET reps=1.5 WHERE _id=1',
            "UPDATE set_ SET weight='PRIVATE SENTINEL' WHERE _id=1",
            'UPDATE training SET startDateTime=NULL',
            'UPDATE training SET startDateTime=1761435000',
            'UPDATE training SET finishDateTime=startDateTime-1',
            'UPDATE exercise SET parent_id=999 WHERE _id=1',
            'UPDATE exercise SET parent_id=2 WHERE _id=1; UPDATE exercise SET parent_id=1 WHERE _id=2',
        ]
        for mutation in mutations:
            with self.subTest(mutation=mutation), closing(fixture()) as db:
                db.executescript(mutation)
                with self.assertRaises(M.MigrationError) as error:
                    convert(db)
                self.assertNotIn("PRIVATE SENTINEL", str(error.exception))

    def test_groups_flatten_in_sibling_order_and_preserve_adjacency(self):
        self.db.execute('INSERT INTO exercise (_id,day_id,hasChild,order_num,rule) VALUES (3,10,1,0,?)', ("Group prescription",))
        self.db.execute('UPDATE exercise SET parent_id=3')
        self.db.execute('UPDATE exercise SET parent_id=NULL WHERE _id=3')
        out, _ = convert(self.db)
        slots = out["routines"][0]["ex"]
        self.assertEqual(slots[0]["sg"], slots[1]["sg"])
        self.assertIn("Group prescription", slots[0]["note"])

    def test_schema_mismatch_is_safe_and_specific(self):
        self.db.execute('DROP TABLE set_')
        with self.assertRaisesRegex(M.MigrationError, "required table set_"):
            convert(self.db)

    def test_missing_names_require_verified_catalogue_and_do_not_create_placeholders(self):
        self.db.execute('UPDATE th_exercise SET name=NULL')
        with self.assertRaisesRegex(M.MigrationError, "verified --catalogue"):
            convert(self.db)
        names = {100: "Verified fixture lift", 101: "Verified fixture run", 102: "Verified fixture hold"}
        out, report = convert(self.db, catalogue=names)
        self.assertEqual({c["n"] for c in out["customEx"]}, set(names.values()))
        self.assertEqual(report["counts"]["custom_exercises_named_from_catalogue"], 3)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "catalogue.json"
            path.write_text(json.dumps({str(k): v for k, v in names.items()}))
            self.assertEqual(M.read_catalogue(path), names)
            for invalid in [[], {"100": ""}, {"__proto__": "Fixture"}, {"01": "Fixture", "1": "Conflicting fixture"}]:
                path.write_text(json.dumps(invalid))
                with self.subTest(invalid=invalid), self.assertRaises(M.MigrationError):
                    M.read_catalogue(path)

    def test_nonrepresentable_measurements_are_retained_in_notes_and_counted(self):
        self.db.execute('UPDATE set_ SET time=0 WHERE _id=3')
        out, report = convert(self.db)
        self.assertIn("distance=2000", out["workouts"][0]["entries"][0]["sets"][0]["note"])
        self.assertEqual(report["counts"]["sets_extra_measurements_in_notes"], 1)

    def test_sets_on_group_containers_are_blocked_rather_than_silently_dropped(self):
        self.db.execute('UPDATE workout SET hasChild=1,th_exercise_id=NULL WHERE _id=1')
        with self.assertRaisesRegex(M.MigrationError, "group containers carry sets"):
            convert(self.db)


class FilesystemTests(unittest.TestCase):
    def test_cli_is_read_only_private_atomic_and_refuses_overwrites(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "fixture.db"
            fixture(source).close()
            original = source.read_bytes()
            output = root / "private" / "backup.json"
            args = [str(source), "--output", str(output), "--timezone", "Europe/Prague", "--time-unit", "minutes", "--distance-unit", "meters"]
            self.assertEqual(M.main(args), 0)
            self.assertEqual(source.read_bytes(), original)
            self.assertEqual(output.stat().st_mode & 0o777, 0o600)
            self.assertEqual(output.with_suffix(".report.json").stat().st_mode & 0o777, 0o600)
            self.assertEqual(output.parent.stat().st_mode & 0o777, 0o700)
            self.assertEqual(M.main(args), 1)
            self.assertEqual(M.main(args + ["--overwrite"]), 0)
            with self.assertRaises(M.MigrationError):
                M.check_destination(source, source, True)
            link = root / "linked-output.json"
            link.symlink_to(source)
            with self.assertRaises(M.MigrationError):
                M.check_destination(link, source, True)
            hardlink = root / "hardlinked-output.json"
            os.link(source, hardlink)
            with self.assertRaises(M.MigrationError):
                M.check_destination(hardlink, source, True)
            self.assertFalse(list(output.parent.glob(".workout-migration-*")))

    def test_existing_output_is_untouched_after_conversion_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "fixture.db"
            with closing(fixture(source)) as db:
                db.execute('UPDATE set_ SET weight=-1')
                db.commit()
            output = Path(directory) / "backup.json"
            output.write_text("sentinel")
            self.assertEqual(M.main([str(source), "--output", str(output), "--timezone", "UTC", "--overwrite"]), 1)
            self.assertEqual(output.read_text(), "sentinel")


class FrontendCompatibilityTests(unittest.TestCase):
    def test_actual_backup_reader_store_custom_registry_and_reimport(self):
        runner = ROOT / "frontend/node_modules/vitest/vitest.mjs"
        if not runner.exists() or not shutil.which("node"):
            self.skipTest("Frontend dev dependencies and Node are required for importer compatibility check")
        # All contents below are synthetic. The test never accepts a real database path.
        artifact_root = ROOT / "artifacts/workout-migration"
        artifact_root.mkdir(mode=0o700, parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="synthetic-compatibility-", dir=artifact_root) as directory:
            tmp = Path(directory)
            with closing(fixture()) as db:
                db.execute('INSERT INTO th_bparam (_id,title) VALUES (5,"Waist"),(2,"Height")')
                db.execute('INSERT INTO bparam (_id,fixDateTime,th_bparam_id,size) VALUES (2,?,5,81.3),(3,?,2,180.4)', (START, START))
                db.execute('ALTER TABLE th_exercise ADD COLUMN mainMuscleWorked INTEGER')
                db.execute('ALTER TABLE th_exercise ADD COLUMN otherMuscles TEXT')
                db.execute('ALTER TABLE th_exercise ADD COLUMN equipment INTEGER')
                db.execute('UPDATE th_exercise SET mainMuscleWorked=6,otherMuscles="7;8",equipment=3 WHERE _id=100')
                backup, _ = convert(db, length_unit="cm")
            (tmp / "fixture.json").write_text(json.dumps(backup))
            test = tmp / "migration.test.jsx"
            module = lambda path: json.dumps(str(ROOT / path))
            test.write_text('''import { readFileSync } from 'node:fs';
vi.mock(''' + module("frontend/src/lib/api.js") + ''', () => ({ api: vi.fn(), setRemoteAuth: vi.fn() }));
import { readBackupFile } from ''' + module("frontend/src/lib/backup-media.js") + ''';
import { DEF, useStore } from ''' + module("frontend/src/store/useStore.js") + ''';
import { EXIDX } from ''' + module("frontend/src/lib/exercises.js") + ''';
import { modeForSet } from ''' + module("frontend/src/lib/workout-model.js") + ''';
import { normalizeMeasurementsState } from ''' + module("frontend/src/lib/measurements.js") + ''';
import { muscleWeightsOf } from ''' + module("frontend/src/lib/muscles.js") + ''';
import { workoutFitMessages, MSG } from ''' + module("frontend/src/lib/fit-export.js") + ''';
const backupText = readFileSync(''' + json.dumps(str(tmp / "fixture.json")) + ''', 'utf8');
afterEach(() => { localStorage.clear(); useStore.setState({ S: structuredClone(DEF), user: null, ready: false }); });
it('restores converted history/plans, registers custom exercises, and replaces twice without duplicates', async () => {
  localStorage.clear();
  useStore.setState({ S: structuredClone(DEF), user: null, ready: true });
  const read = await readBackupFile(new File([backupText], 'fixture.json', { type: 'application/json' }));
  const input = JSON.parse(backupText);
  useStore.getState().importBackup(read.state);
  useStore.getState().importBackup(structuredClone(input));
  const state = useStore.getState().S;
  expect(state.workouts).toHaveLength(1);
  expect(state.routines).toHaveLength(1);
  expect(state.customEx).toHaveLength(3);
  expect(state.bodyweight).toEqual(input.bodyweight);
  expect(state.measurements).toEqual(input.measurements);
  expect(state.customMeasurements).toEqual(input.customMeasurements);
  const normalized = normalizeMeasurementsState(structuredClone(state));
  expect(normalized.measurements).toHaveLength(1);
  expect(normalized.measurements[0].waist).toBe(81.3);
  expect(normalized.measurements[0].other[0].value).toBe(180.4);
  expect(normalized.customMeasurements[0].unit).toBe('cm');
  const lift = state.customEx.find(c => c.n === 'Fixture lift');
  expect(muscleWeightsOf(EXIDX[lift.id])).toEqual({ biceps: 1, triceps: 0.4, forearm: 0.4 });
  expect(state.workouts[0].entries).toEqual(input.workouts[0].entries);
  expect(state.routines.map(({ _ts, ...r }) => r)).toEqual(input.routines);
  expect(state.routines[0]._ts).toBeGreaterThan(0);
  for (const entry of state.workouts[0].entries) expect(EXIDX[entry.id]?.custom).toBe(true);
  for (const cfg of state.routines[0].ex) expect(EXIDX[cfg.id]?.n).toBeTruthy();
  expect(state.workouts[0].entries.map(e => modeForSet(e.sets[0]))).toEqual(['cardio', 'reps', 'time']);
  const ticks = state.workouts[0].entries.flatMap(e => e.sets.map(s => s.at));
  expect(ticks).toEqual([1800000, 30000, 60000, 2000000].map(offset => input.workouts[0].start + offset));
  const fields = m => Object.fromEntries(m.fields.filter(Boolean).map(([n, , value]) => [n, value]));
  const active = workoutFitMessages(state.workouts[0]).filter(m => m.global === MSG.set).map(fields).filter(f => f[5] === 1);
  expect(active.map(f => f[0])).toEqual([600000, 15000, 24000, 30000]);
});
''')
            config = tmp / "vitest.config.mjs"
            config.write_text("export default " + json.dumps({"root": str(ROOT / "frontend"), "test": {"globals": True, "environment": "happy-dom", "setupFiles": [str(ROOT / "frontend/src/test-setup.js")], "include": [str(test)]}}))
            result = subprocess.run(["node", str(runner), "run", "--config", str(config)], cwd=ROOT / "frontend", text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


class CatalogueExtractionTests(unittest.TestCase):
    DUMP = '''Package name=synthetic.package
    resource 0x7f000001 string/res_thExName2
      () "Fixture two"
      (ru) "Fixture translated two"
    resource 0x7f000002 string/res_thExName1
      () "Fixture one"
      (ru) "Fixture \\"translated\\" one"
    resource 0x7f000003 string/unrelated
      (ru) "Unrelated fixture string"
'''

    def test_exact_source_id_mapping_locale_and_escaped_strings(self):
        translated = EXTRACT.extract(self.DUMP.splitlines(), "ru")
        self.assertEqual(translated, {"1": 'Fixture "translated" one', "2": "Fixture translated two"})
        self.assertEqual(list(translated), ["1", "2"])
        self.assertEqual(EXTRACT.extract(self.DUMP.splitlines(), "default"), {"1": "Fixture one", "2": "Fixture two"})

    def test_measurement_kind_uses_verified_title_prefix_and_ignores_guidance(self):
        dump = self.DUMP.replace("string/res_thExName", "string/res_thBParam")
        dump += '    resource 0x7f000004 string/res_thBParamGuide1\n      () "Fixture guidance"\n'
        self.assertEqual(EXTRACT.extract(dump.splitlines(), "default", "measurements"), {"1": "Fixture one", "2": "Fixture two"})

    def test_source_bundle_has_exact_families_and_explicit_locale_fallback(self):
        lines = []
        for family, prefix in EXTRACT.SOURCE_FAMILIES.items():
            lines.extend(['    resource 0x7f000001 '+prefix+'1', '      () "Fixture source value"'])
        with self.assertRaises(EXTRACT.MigrationError):
            EXTRACT.extract_source_fields(lines, "ru")
        bundle = EXTRACT.extract_source_fields(lines, "ru", "default")
        self.assertEqual(set(bundle), set(M.SOURCE_FIELD_FAMILIES))
        self.assertEqual(bundle["exercise_rules"], {"1": "Fixture source value"})
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bundle.json"
            path.write_text(json.dumps(bundle))
            self.assertEqual(M.read_source_fields(path), bundle)

    def test_source_fields_preserve_aapt2_literal_quotes_and_multiline_source_text(self):
        lines = []
        for family, prefix in EXTRACT.SOURCE_FAMILIES.items():
            lines.extend(['    resource 0x7f000001 '+prefix+'1', '      () "Fixture value"'])
        lines[lines.index('      () "Fixture value"', lines.index('    resource 0x7f000001 string/res_programName1'))] = '      () "Fixture "quoted" name"'
        lines[-1:] = ['      () "First fixture line', 'Second fixture line"']
        bundle = EXTRACT.extract_source_fields(lines, "default")
        self.assertEqual(bundle["program_names"]["1"], 'Fixture "quoted" name')
        self.assertEqual(bundle["program_info"]["1"], "First fixture line\nSecond fixture line")
        with self.assertRaisesRegex(EXTRACT.MigrationError, "Unclosed"):
            EXTRACT.extract_source_fields(lines[:-1], "default")

    def test_duplicate_missing_locale_and_unsupported_formats_are_rejected(self):
        bad = [
            self.DUMP + '    resource 0x7f000001 string/res_thExName2\n      (ru) "Duplicate"\n',
            self.DUMP.replace('(ru) "Fixture translated two"', '(uk) "Other locale"'),
            self.DUMP.replace('(ru) "Fixture translated two"', '(ru) "First"\n      (ru) "Duplicate"'),
            self.DUMP.replace('res_thExName2', 'res_thExName0'),
            self.DUMP.replace('(ru) "Fixture translated two"', '(ru) "Unclosed'),
            self.DUMP.replace('(ru) "Fixture translated two"', '(ru) "Invalid\\qescape"'),
            self.DUMP.replace('(ru) "Fixture translated two"', '(ru) "Multi\\nline"'),
            self.DUMP.replace('(ru) "Fixture translated two"', '(ru) ""'),
            'resource 0x7f000001 string/unrelated\n  (ru) "Fixture"',
        ]
        for dump in bad:
            with self.subTest(dump=dump), self.assertRaises(EXTRACT.MigrationError):
                EXTRACT.extract(dump.splitlines(), "ru")

    def test_cli_uses_private_atomic_output_and_preserves_input(self):
        with tempfile.TemporaryDirectory() as directory:
            source, output = Path(directory) / "fixture.txt", Path(directory) / "private/catalogue.json"
            source.write_text(self.DUMP)
            args = [str(source), "--locale", "ru", "--output", str(output)]
            self.assertEqual(EXTRACT.main(args), 0)
            self.assertEqual(source.read_text(), self.DUMP)
            self.assertEqual(output.stat().st_mode & 0o777, 0o600)
            self.assertEqual(len(json.loads(output.read_text())), 2)
            self.assertEqual(EXTRACT.main(args), 1)
            self.assertEqual(EXTRACT.main([str(source), "--locale", "ru", "--output", str(source), "--overwrite"]), 1)


if __name__ == "__main__":
    unittest.main()
