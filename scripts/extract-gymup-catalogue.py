#!/usr/bin/env python3
"""Extract verified GymUp exercise names from an Android SDK aapt2 resource dump.

Accepts text from `aapt2 dump resources APP.apk`, not an APK or a resource table.
Does not parse ARSC, download anything, or infer equivalence with openGym exercises.
"""

import argparse
import importlib.util
import json
from pathlib import Path
import re
import sys


# Share the migration's private, atomic output and input-overwrite safeguards.
_spec = importlib.util.spec_from_file_location("workout_migration", Path(__file__).with_name("migrate-workouts.py"))
_migration = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_migration)
MigrationError = _migration.MigrationError
HEADER = re.compile(r"^\s*resource\s+0x[0-9a-fA-F]+\s+(\S+)\s*$")
PREFIXES = {"exercises": "string/res_thExName", "measurements": "string/res_thBParam"}
SOURCE_FAMILIES = {"exercise_rules": "string/res_exerciseRule", "day_names": "string/res_dayName",
                   "day_comments": "string/res_dayComment", "program_names": "string/res_programName",
                   "program_comments": "string/res_programComment", "program_info": "string/res_programInfo"}
VALUE = re.compile(r'^\s*\(([^)]*)\)\s+("(?:[^"\\]|\\.)*")\s*$')


def extract(lines, locale, kind="exercises", fallback_locale=None, prefix=None):
    """Require one exact locale entry per named source exercise resource."""
    if not isinstance(locale, str) or not re.fullmatch(r"[A-Za-z0-9+_-]+", locale):
        raise MigrationError("Use an explicit aapt2 locale token or 'default'.")
    locale = "" if locale == "default" else locale
    if prefix is None and kind not in PREFIXES:
        raise MigrationError("Unknown catalogue kind.")
    prefix = prefix or PREFIXES[kind]
    if fallback_locale is not None and not re.fullmatch(r"[A-Za-z0-9+_-]+", fallback_locale):
        raise MigrationError("Invalid fallback locale token.")
    fallback_locale = "" if fallback_locale == "default" else fallback_locale
    name_pattern = re.compile(re.escape(prefix) + r"([1-9][0-9]*)$")
    resources = {}
    active = None
    for line in lines:
        header = HEADER.fullmatch(line.rstrip("\r\n"))
        if header:
            key = header[1]
            active = None
            # Measurement descriptions use res_thBParamGuide<ID>, not title resources.
            if not key.startswith(prefix) or key.startswith("string/res_thBParamGuide"):
                continue
            match = name_pattern.fullmatch(key)
            if not match:
                raise MigrationError("Unsupported exercise resource name; positive numeric source IDs are required.")
            active = match[1]
            if active in resources:
                raise MigrationError("Duplicate exercise resource ID in the dump.")
            resources[active] = {}
            continue
        if prefix in line and "string/res_thBParamGuide" not in line:
            raise MigrationError("Unsupported aapt2 exercise resource header format.")
        if active is None or not line.strip():
            continue
        value = VALUE.fullmatch(line.rstrip("\r\n"))
        if not value:
            raise MigrationError("Unsupported aapt2 exercise value; require one-line quoted strings.")
        config = value[1]
        if config in resources[active]:
            raise MigrationError("Duplicate locale entry for an exercise resource.")
        try:
            name = json.loads(value[2])
        except (ValueError, TypeError):
            raise MigrationError("Unparseable quoted exercise resource string.") from None
        if not isinstance(name, str) or (prefix in PREFIXES.values() and
                                         (not name.strip() or any(ord(c) < 32 for c in name))):
            raise MigrationError("Exercise names must be nonempty single-line strings.")
        resources[active][config] = name
    if not resources:
        raise MigrationError("No GymUp source exercise name resources were found.")
    if any(locale not in configs and fallback_locale not in configs for configs in resources.values()):
        raise MigrationError("Requested locale is missing for one or more exercise resources.")
    return {key: resources[key][locale] if locale in resources[key] else resources[key][fallback_locale]
            for key in sorted(resources, key=int)}


def extract_source_fields(lines, locale, fallback_locale=None):
    # aapt2's text dump is not JSON: these source resources contain literal embedded quotes
    # and comments/info contain physical newlines. Keep their outer quote framing verbatim.
    for token in [locale] + ([fallback_locale] if fallback_locale is not None else []):
        if not isinstance(token, str) or not re.fullmatch(r"[A-Za-z0-9+_-]+", token):
            raise MigrationError("Invalid source-field locale token.")
    locale = "" if locale == "default" else locale
    fallback_locale = "" if fallback_locale == "default" else fallback_locale
    resources = {family: {} for family in SOURCE_FAMILIES}
    active, current_locale, parts = None, None, []

    def finish_value():
        if current_locale is None:
            return
        raw = "\n".join(parts)
        if not raw.endswith('"'):
            raise MigrationError("Unclosed quoted source-field resource value.")
        if len(parts) > 1 and active[0] not in ("program_names", "day_comments", "program_comments", "program_info"):
            raise MigrationError("Multiline source names/rules are unsupported.")
        values = resources[active[0]][active[1]]
        if current_locale in values:
            raise MigrationError("Duplicate source-field resource locale.")
        values[current_locale] = raw[:-1]

    for raw_line in lines:
        line = raw_line.rstrip("\r\n")
        header = HEADER.fullmatch(line)
        if header:
            finish_value()
            active, current_locale, parts = None, None, []
            for family, prefix in SOURCE_FAMILIES.items():
                if header[1].startswith(prefix):
                    match = re.fullmatch(re.escape(prefix) + r"([1-9][0-9]*)", header[1])
                    if not match:
                        raise MigrationError("Unsupported source-field resource identifier.")
                    identifier = match[1]
                    if identifier in resources[family]:
                        raise MigrationError("Duplicate source-field resource ID.")
                    resources[family][identifier] = {}
                    active = (family, identifier)
                    break
            continue
        if active is None:
            continue
        start = re.fullmatch(r'\s*\(([^)]*)\)\s+"(.*)', line)
        if start:
            finish_value()
            current_locale, parts = start[1], [start[2]]
        elif current_locale is not None:
            parts.append(line)
        elif line.strip():
            raise MigrationError("Unsupported source-field value framing.")
    finish_value()
    out = {}
    for family, entries in resources.items():
        if not entries or any(locale not in configs and fallback_locale not in configs for configs in entries.values()):
            raise MigrationError("Source-field family or requested locale is missing.")
        out[family] = {key: entries[key][locale] if locale in entries[key] else entries[key][fallback_locale]
                       for key in sorted(entries, key=int)}
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dump", type=Path)
    parser.add_argument("--locale", required=True, help="Exact aapt2 config token, e.g. ru, or 'default'. No fallback.")
    parser.add_argument("--kind", choices=[*PREFIXES, "source-fields"], default="exercises")
    parser.add_argument("--fallback-locale", help="Explicit locale fallback, e.g. default for untranslated bundled rules.")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(argv)
    try:
        source = args.dump.expanduser().resolve(strict=True)
        if not source.is_file():
            raise MigrationError("Input must be a regular aapt2 text dump.")
        output = args.output.expanduser().absolute()
        _migration.check_destination(output, source, args.overwrite)
        with source.open(encoding="utf-8") as stream:
            catalogue = (extract_source_fields(stream, args.locale, args.fallback_locale) if args.kind == "source-fields"
                         else extract(stream, args.locale, args.kind, args.fallback_locale))
        _migration.atomic_json(output, catalogue, args.overwrite)
        count = sum(len(v) for v in catalogue.values()) if args.kind == "source-fields" else len(catalogue)
        print(json.dumps({"catalogue_values": count}))
        return 0
    except MigrationError as error:
        print("Catalogue extraction failed: " + str(error), file=sys.stderr)
    except (OSError, ValueError):
        print("Catalogue extraction failed: could not read the dump or write the private catalogue.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
