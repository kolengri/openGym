# Exercise props production inventory

The requested separate research agent examined the full English exercise text
catalog. The primary agent saved its parser, reproduced the outputs and checked
record coverage, unique counts, CSV rows and alias targets.

- `report.md`: readable table with Russian labels, examples and priorities.
- `inventory.csv`: production planning table, one canonical prop per row.
- `inventory.json`: all exercise IDs, evidence tiers and source examples per prop.
- `exercise-coverage.json`: every independent exercise and its extracted evidence.
- `aliases.json`: figure aliases linked to their independent exercises.
- `summary.json`: counts, ambiguities, limitations and source corpus checksum.
- `inventory.py`: reproducible standard-library-only extraction and mapping.

All 6,554 source records are accounted for: 5,632 independent exercises plus 922
figure aliases. There are 206 buildable planning rows: 164 bases, 31 variants and
11 attachments; six additional rows retain unresolved equipment types.

Coverage is 4,053 exercises with mapped props, 92 with unresolved prop geometry,
and 1,487 with no prop identified in the available text. The last group is not
proof of equipment-free performance. No licensed exercise media was inspected or
used by this inventory process. Names, descriptions, instructions and `needs`
were examined, rather than relying solely on the coarse `equipment` field.

P0/P1/P2 rank usage frequency for planning. They do not measure modeling effort.
Optional and alternative props are tagged from sentence-level text; source
ambiguities need owner review before production. Variants and attachments can
share geometry with a reusable base, so 206 does not mean 206 independent models.
Detailed machine dimensions, mechanisms and grip/attachment geometry cannot
always be inferred from text alone.

Rebuild from the repository root:

```sh
python3 artifacts/exercise-props-inventory/inventory.py --output artifacts/exercise-props-inventory
```

Source schema and alias semantics are documented in `catalogue/README.md`; the
application resolves aliases in `frontend/src/lib/exercises.js`. Exercise text
licensing is documented in the repository `NOTICE.md`.
