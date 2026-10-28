# Exercise animation briefs

All **5,632 canonical exercises** and **922 aliases** are covered (6,554 unique IDs).
The source checks find **1,290 source-complete storyboards** and **4,342 canonical briefs with source gaps**. Separately, **5,473 staging proposals are ready for owner review** and **159 need source/motion resolution**. Missing initial limb cues alone do not block a proposal when a reversible posture-based placement is available. **Zero are certified animation-ready**.

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
