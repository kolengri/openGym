# Local SQLite workout migration

`scripts/migrate-workouts.py` converts the supported SQLite export schema into an openGym
JSON backup. It runs locally with Python 3.9+ and the standard library; it has no network
calls or app/runtime dependencies. It does not identify the exporting app by guessing its schema.

Keep the original export outside the repository. Put generated backups and reports in the
ignored `artifacts/workout-migration/` directory, or another private destination. Never commit
an actual database, converted backup, report, names, measurements, or other personal records.
The checked-in tests use invented fixtures only.

```sh
python3 scripts/migrate-workouts.py /private/path/source.db \
  --output artifacts/workout-migration/converted-backup.json \
  --timezone Europe/Prague \
  --time-unit minutes \
  --distance-unit meters \
  --all-programs
```

The example explicitly declares minutes and meters; confirm the source's representation before
using those options. `--timezone` is required: epoch timestamps remain unchanged, and this timezone
determines the workout's calendar day, including daylight saving time and sessions across midnight.
The machine's timezone does not affect conversion. This converter requires source epoch milliseconds
between 1980 and 2100 and refuses missing session starts.

`shared_prefs.unitSystem=metric` means kg; `imperial` means lb. The output keeps that weight unit,
including the load offset described below. If that metadata is absent or unknown, supply `--unit kg`
or `--unit lb`. A conflicting override is rejected. Durations and distances require explicit units
whenever present; supported units are seconds/minutes/milliseconds and meters/kilometers/miles.
The supported schema stores set weight and the additive load offset in the declared weight unit;
exports with mixed per-set units require a separate, verified mapping.

The source is opened with SQLite `mode=ro` and `query_only=ON`, checked for integrity, and read in
one transaction. Required tables/columns and record references are validated. Existing destinations,
symlinks, hard links to the source, and overwriting the source are refused. `--overwrite` permits
replacing an existing regular destination. Each JSON file is written atomically with permissions
`0600`; newly created destination directories use `0700`. Existing directory permissions are preserved.
The backup and aggregate report are separate atomic files, not a transactional two-file bundle.
If the second write fails, a report may already exist; no partially written backup is exposed.

## Restore in openGym

1. Export a backup of the target openGym profile first.
2. Choose **Settings → Data & backup → Import backup** and select the converted JSON.
3. Review the restored history and exercise notes. Review placeholder plan targets before training.

Backup import **replaces the target profile**, including its routines and settings. The existing UI
may offer to merge local or remote workouts discovered during its conflict check. This converter
does not implement an incremental merge with an existing openGym backup. On a signed-in openGym
profile, the app's existing sync behavior can send the imported data to its configured server;
use a local signed-out profile if that is not wanted. Conversion itself never uploads anything.

Repeated conversions with the same `--namespace` produce deterministic workout, routine, exercise,
and group IDs. Reimporting the same backup replaces those records without duplication. Keep the
namespace stable for exports from one source; set a different `--namespace` for a different source
database if their records may eventually be merged. IDs do not depend on filenames, conversion time,
or display names. More than one source profile requires `--user-id`; `--user-id default` selects
unassigned records. Profiles are never silently merged.

Some exports omit every bundled exercise name and expect the source app's installed catalogue.
Conversion stops when a referenced exercise has no name. Supply an independently verified local
catalogue with `--catalogue /private/path/source-exercises.json`; it must be a JSON object mapping
original numeric source IDs to original names, for example `{"100": "Synthetic exercise"}`. Those
keys are source IDs, not openGym catalogue IDs. This file fills missing names only; it does not
guess exercise equivalence or overwrite names present in the database. The converter reports how
many referenced exercises needed this catalogue. It never emits unnamed exercise placeholders.

For a verified GymUp export, `scripts/extract-gymup-catalogue.py` can produce this mapping from
an Android SDK `aapt2` text dump of the matching source app APK. Obtain the APK from the app's
official distribution, verify its package/version, and confirm its source IDs cover your export.
The extractor uses exact `string/res_thExName<ID>` resource names as the source IDs; it does not
match exercise titles. It accepts one-line quoted resource values, requires the exact requested
locale for every name, and rejects duplicate IDs/locales or unsupported formatting.

```sh
# Example SDK location on macOS; use an installed build-tools version.
AAPT2="$HOME/Library/Android/sdk/build-tools/35.0.0/aapt2"
mkdir -p artifacts/workout-migration
chmod 700 artifacts/workout-migration
(umask 077; "$AAPT2" dump resources /private/path/gymup.apk \
  > artifacts/workout-migration/gymup-resources.txt)
python3 scripts/extract-gymup-catalogue.py \
  artifacts/workout-migration/gymup-resources.txt --locale ru \
  --output artifacts/workout-migration/gymup-exercises-ru.json
```

Pass the resulting JSON with the converter's `--catalogue` option. `--locale default` selects
the APK's default strings, with no fallback between locales. The extractor requires no Python
dependencies and does not parse APK/ARSC itself. The Android SDK is needed only for the dump;
the converter and extractor do not require the SDK at runtime. APKs, resource dumps, and generated
catalogues should stay in private ignored artifacts as well. Record the official APK origin,
version and checksum privately; an older catalogue needs explicit ID-coverage verification and
does not establish that every title stayed unchanged in a newer app version.

GymUp also stores bundled program/day names, day comments and exercise rules as numeric **resource
reference values**. These values are not the source table's primary keys or literal rep targets.
Extract their exact resource families into a separate bundle:

```sh
python3 scripts/extract-gymup-catalogue.py \
  artifacts/workout-migration/gymup-resources.txt --kind source-fields \
  --locale ru --fallback-locale default \
  --output artifacts/workout-migration/gymup-source-fields.json
```

Pass it with `--source-fields artifacts/workout-migration/gymup-source-fields.json`. The six supported
families are `res_exerciseRule`, `res_dayName`, `res_dayComment`, `res_programName`, `res_programComment`
and `res_programInfo`. Only bundled programs resolve numeric reference values; user-added programs
keep their literal fields, and nonnumeric source text is always authoritative. Original numeric
references stay in routine exercise notes. Missing bundled program comments/info can use the same
verified program-name reference. Rules without a selected translation use the explicitly requested
default fallback. Source-field extraction accepts aapt2's literal embedded quotes and outer-framed
multiline program titles/comments/info; exercise and measurement names retain the stricter one-line
parser. Duplicate identifiers/locales, unclosed values and missing requested locales are rejected.
No exercise guide library or image files are copied.

Body-reading titles use a separate verified resource prefix, `string/res_thBParam<ID>`. Extract
the default catalogue to establish the source types without guessing translated names:

```sh
python3 scripts/extract-gymup-catalogue.py \
  artifacts/workout-migration/gymup-resources.txt --kind measurements --locale default \
  --output artifacts/workout-migration/gymup-measurements-default.json
```

Pass it with `--measurement-catalogue artifacts/workout-migration/gymup-measurements-default.json`.
It is required when the export omits body-reading titles. The verified `res_thBParam1` default title
is `Weight`, so those records become native weigh-ins in the profile's confirmed kg/lb unit. Their
original `fixDateTime` becomes `t`; their calendar date uses `--timezone`. Other verified fields use
native body-measurement keys where equivalent, or registered custom fields when the source distinguishes
relaxed/strained circumferences or height. Length readings require explicit `--length-unit cm` or
`--length-unit in`; a metric preference alone is not taken as proof of the stored length unit.
Lengths use canonical cm in `measurements`, custom fields retain their selected display unit, and
body-fat readings use percent. Native measurement editing rounds lengths/percentages to one decimal.
Unknown custom types or units stop conversion instead of assigning an arbitrary dimension.

Measurement/calendar comments use the existing day-note model, with its 500-character limit; these
notes can also affect the app's day-note/nudge behavior. Oversized notes, multiple weigh-ins on one
date, duplicate measurement fields, or different measurement timestamps on one date stop conversion
because the native model cannot represent them without losing detail. The original database remains
the complete archive, including source-only preferences, catalogues, binary media, and unsupported
state; no credential-bearing copy or hidden runtime archive is added to the openGym backup.

## Preserved data and limits

- Every selected training session is retained, including sessions and exercise entries with no sets.
  Finished sessions retain their recorded start and finish. A missing finish is explicitly noted;
  the end uses the latest actual exercise/set finish, or the start if there is none. This does not
  invent a duration or assert source completion. A set is `done` only when it has a source finish.
  If a session has no title, its current referenced program/day title is used when available.
- Separate sessions on the same day stay separate. Source exercise order is preserved; set order
  follows its monotonically assigned source `_id` because this schema has no set-order column.
  Explicit parent groups are flattened contiguously and retained as openGym exercise groups.
- Each referenced source exercise becomes a registered custom exercise, retaining its exact name,
  guide, and standing notes. No translation or exercise-equivalence guess changes identity. Unknown
  muscle and equipment enum values are retained in descriptions. Verified GymUp `muscleArray`/
  `muscleIdArray` and equipment array bindings preserve primary and secondary muscles in openGym's
  existing `primaries`/`secondaries`/`tg`/`sm` fields. Equivalent equipment uses native identifiers;
  broad `Machine`, `Other` and `None` categories remain documented custom equipment. `None` does
  not establish bodyweight semantics. Neck is retained as source metadata but receives no invented
  trapezius credit: the current body diagram treats the neck as an inert region. Source Lats and
  Middle Back share openGym's existing upper-back region, and Abductors use its existing gluteal alias.
- Effective weight is `weight × koef1 + koef2`, with absent coefficients treated as `1` and `0`.
  Nonidentity coefficients and the original weight are preserved in set notes. This mapping must
  match the source export's semantics; do not apply this converter to unrelated schemas merely
  because the table names match. Workout volume and top weight are recomputed from finished sets.
  Discrepancies with stored source tonnage are counted and the original aggregate retained in notes.
- Repetitions and timed holds use openGym's reps and seconds modes. Cardio uses minutes and speed
  in km/h. Distance without duration, or compound measures openGym cannot represent in one set,
  remain in set notes and are counted as extra measurements. Empty measured sets are retained and
  counted. Invalid/negative measurements, fractional repetitions, missing exercise references,
  broken groups, and unsupported timestamps stop conversion; history is not silently discarded.
- Zero external load remains zero. Body mass is never substituted into a set's weight. Source
  equipment numbers do not establish bodyweight/assistance semantics. For verified bodyweight
  exercises, repeat `--bodyweight-exercise-id SOURCE_ID` to set the supported bodyweight config and
  equipment flag; additional load remains additional load. Assistance and per-side flags require
  manual review and are not inferred from names.
- Reusable routines include all days of user-added programs and programs referenced by selected
  history by default. `--all-programs` includes every source program/day, including bundled plans;
  otherwise unused bundled programs are excluded and counted. Bundled plans may carry only partial
  prescriptions, which stay verbatim in notes and need target review like any other ambiguous rule.
  Program/day order and their names
  are retained; program and day notes are attached to each routine exercise because the current
  model has no routine-level notes. Deleted/missing historical day references are counted while
  the session remains in history without a routine link.
- Unambiguous `sets × reps`, `sets × min-max reps`, and `min-max sets × reps/range`
  prescriptions are parsed. Set ranges use the existing `sets` and `setsMax` target fields;
  they do not enable a progression policy. Other rules,
  including isolated numbers whose meaning is ambiguous, remain verbatim in exercise notes.
  Those routine slots have one placeholder set and a zero target with an explicit review note.
  Original rest settings and source effort fields remain in notes; no RPE/RIR scale is guessed.
- Photos, equipment photos, standalone notebook entries, quiz state/default photo-pose catalogues,
  scheduling, app/account preferences, credentials, and unrelated tables are not migrated. Counts
  for known excluded record tables are in the report. The original database remains the archive.

The default report is `converted-backup.report.json` beside the backup. It contains counts, declared
units, timezone, and generic limitations, without names, timestamps, source IDs, or individual
measurements. Terminal output contains counts only. Errors do not print source rows or SQL values.

## Verification

```sh
python3 -m unittest discover -s scripts/tests -p 'test_migrate_workouts.py' -v
```

The synthetic suite checks source safety, permissions, deterministic IDs, ordering, DST/calendar
dates, unit handling, notes, load coefficients, profile selection, failures, and repeated import.
It also checks native weigh-ins, explicit length units, native/custom measurements, verified title
resources, same-day loss boundaries, and complete-program selection.
With the existing frontend dev dependencies installed, it also executes the actual `readBackupFile`,
store `importBackup`, and custom-exercise registry in Vitest. Temporary synthetic compatibility
files live under ignored artifacts and are removed afterward. Without Node/frontend dependencies,
that compatibility check is explicitly skipped; conversion itself does not require them.
