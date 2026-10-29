# Exercise and apparatus reuse plan

The catalogue contains **6,554 records: 5,632 canonical exercises and 922 figure aliases**. Reuse the original CC0 mannequin, its 51-bone rig, shared scene/material/muscle-cue system and view controls. Configure main/additional muscle surfaces in the approved soft warm palette, stretches cyan and inactive surfaces neutral. These are shared infrastructure, not a new clip per body, muscle or view.

## Confirmed references and editorial duplication

- The **922 figure aliases** resolve to canonical IDs. Do not author 922 extra movement specifications. An alias may still need per-record presentation metadata.
- **2 exact canonical pairs** can share one resolved specification: **0576/0577** (lever chest press), **0655/0656** (push-up on stability ball). Comparison includes every original field except ID, figure links and provenance; muscle maps, equipment, needs, hold, description and all ordered instructions are included. These save **2 specification authoring tasks**, leaving **5,630** canonical specifications.
- Both pairs retain source review gaps. **Zero identical production clips have been validated by this report.** Resolve missing geometry once for each pair before reuse; preserve each ID and its metadata.
- Identical ordered instructions alone occur in **37 groups**, suggesting **51 unsafe reductions**. These are review leads, not savings. For example 0001/0260/0508/0634 share instruction text across different named sit-up/crunch mechanics; 0367/1441 use the same instructions despite opposite wrist-curl intent. Do not merge.

## Three different layers of reuse

1. **Shared generator/template:** the expensive motion scaffolding (pose setup, world-bone targets, two-joint IK, support constraints, repetition/hold/side-switch sequencing) is authored once per compatible contract. A curl generator can retain separate hand/load paths without requiring independent animation code for every curl. Existing world-bone pose/two-joint IK helpers are compatible reusable infrastructure; this report does not modify or certify them.
2. **Distinct parameter/contact profile:** every exercise retains its exact movement subtype, support contacts, grip, load location, amplitude, timing, muscle map and ordered source guards. These profiles are configuration/validation work, not necessarily independent hand-authored animations. The conservative profile comparison yields **5,616–5,620 candidate distinct profiles**; semantic name residue is retained so a pike push-up cannot accidentally become an ordinary push-up or a punch become a kick.
3. **Exact identical final clip:** none is validated here. 922 references and two source-identical pairs establish specification reuse, not geometry-correct ready clips. Separate final baked clips can be exported from a shared generator for every ID.

### Conditional base seed / generator workload

For planning the **initial authored generator demonstrations**, budget **1,609–3,010 candidate tasks**, rather than 5,632 independent scaffold implementations. The lower scenario groups by family + supported pose + exercise category; the upper also separates resistance type and apparatus bases. Both retain one individual task for each unclassified ID. The potential saving is **2,622–4,023 repeated scaffold/seed authoring tasks**, not hours, costs, per-ID review tasks or a reduction in final export count. This bracket assumes a parameterized procedural authoring system; it is not a validated number of interchangeable base clips. Supporting a new subtype may still require new generator logic or a split. The fallback is **5,630** separately resolved specifications if modular parameterization cannot satisfy the guards. A narrower production-clip forecast would require representative motion/contact validation, which this text-only plan does not provide.

The literal profile scenario retains detected contact/range/load-position wording; the parameterized profile scenario moves some such literal wording into per-ID settings. Both retain semantic title subtypes, pose, category, resistance, scene bases, machine identity, laterality, inclination, grip and timing modes. Neither is a sufficient mathematical description of motion. Exact ordered instructions, description, review reasons and evidence pointers accompany **every ID** in the gzip mapping. Non-detected distinctions remain authoritative in that source text. Every differing guard must become an explicit parameter, distinct opcode/sub-generator, or a split. No automatic merges or clips are produced.

There are **67 family buckets**, including **784 individual-review IDs** with no supported family rule. All family matches are title-pattern candidates (medium confidence); unmatched items remain individual (low confidence). A family is a reusable controller/scaffold, not an identical clip. Numeric family sizes below count affected exercises, not base clips.

| Candidate controller/scaffold | Affected canonical IDs | Pose templates | Apparatus templates |
| --- | ---: | ---: | ---: |
| individual_review | 784 | 784 | 784 |
| squat | 401 | 24 | 147 |
| elbow_flexion | 293 | 22 | 105 |
| horizontal_pull | 279 | 23 | 112 |
| trunk_flexion | 230 | 21 | 87 |
| push_up | 163 | 13 | 51 |
| elbow_extension | 155 | 20 | 72 |
| chest_press | 154 | 11 | 61 |
| hip_leg_mobility | 153 | 33 | 80 |
| trunk_rotation | 152 | 34 | 80 |
| hip_hinge | 152 | 9 | 47 |
| lunge | 147 | 11 | 40 |
| vertical_pull | 144 | 21 | 65 |
| overhead_press | 107 | 13 | 48 |
| shoulder_arm_mobility | 106 | 24 | 61 |
| leg_raise | 99 | 28 | 57 |
| yoga_balance | 97 | 21 | 30 |
| plank | 94 | 26 | 47 |

High-value production approach: author a reusable controller for elbow flexion, pushing, pulling, squat/hinge and trunk motion, then author supported pose/contact variants. Keep shoulder/elbow coordination, body support and load paths editable rather than copying an entire animation into every ID. Reuse a timed hold stage and side-switch scaffolding for stretches, without assuming stretch and contraction share a motion. Generic dynamic, ballistic, eccentric-only and static forms remain distinct configurations or seeds. Reuse a mirror operation only after verifying handedness, apparatus symmetry and unilateral supports; this report claims no confirmed mirror savings.

### Concrete generator contracts and affected exercises

The counts below are candidates for sharing implementation scaffolds, with source examples and all member IDs in `generator-recipes.json`. They are not validated interchangeable motions. Each contract defines explicit per-ID parameters and split conditions, rather than treating similar names as identical animations.

**elbow_flexion — 293 candidates** (99 source-complete for storyboard). Reuse: Elbow-flexion phase curve, fixed upper-arm frame option, coupled or independent hand targets, return/pause/side sequencing. Parameters: Supported pose, upper-arm direction, shoulder contribution, elbow ROM, forearm rotation, grip width, load contact, left/right timing, preacher/incline supports. Split/review: Standing/seated/preacher/spider/incline support or shoulder frames; shared-bar vs independent loads; hammer/supinated/reverse grips; alternating vs simultaneous; stretch-only forms.

**squat — 401 candidates** (85 source-complete for storyboard). Reuse: Pelvis trajectory and knee/hip bend scaffold, planted-foot IK, lowering/rising/hold/landing stages. Parameters: Stance width/toe direction, depth, trunk lean, load location, foot supports, unilateral balance, machine constraints, timing. Split/review: Split/pistol/assisted and bilateral supports; front/back/goblet loads; jump/landing vs slow squat; Smith/hack/pendulum/belt axes; painful or unspecified range is never invented.

**horizontal_pull — 279 candidates** (84 source-complete for storyboard). Reuse: Scapula/shoulder/elbow target coordination, pull/return phase scaffold and resistance endpoint connection. Parameters: Torso inclination, seat/chest support, hand spacing/orientation, elbow plane, endpoint height, anchor, cable routing and bilateral coupling. Split/review: Chest-supported/seated/bent-over/inverted support; unilateral vs bilateral; free load vs cable vs lever; axis or contact changes. Upright rows belong to a separate family.

**chest_press — 154 candidates** (44 source-complete for storyboard). Reuse: Coordinated upper-arm/forearm press/return targets with torso support frame and optional shared-load constraint. Parameters: Bench angle, elbow plane, grip, ROM, hand spacing, independent/shared load, torso/feet supports, machine handle path. Split/review: Flat/incline/decline/floor/standing frames; bar vs independent dumbbells; one-arm stability; machine pivot vs free path; reverse/neutral/wide grip and pauses remain explicit profiles.

**overhead_press — 107 candidates** (25 source-complete for storyboard). Reuse: Overhead shoulder/elbow trajectory scaffold, torso stabilization, lockout/return phase sequencing. Parameters: Seat/standing support, scapular/shoulder path, grip, front/behind load path, independent hand timing, machine axes and ROM. Split/review: Seated/standing and one-/two-arm frames; behind-neck paths; Arnold rotation; push-press/jerk ballistic leg drive are a separate family, never implicit retiming.

**hip_hinge — 152 candidates** (45 source-complete for storyboard). Reuse: Hip-hinge/trunk-frame scaffold with pelvis trajectory, planted-foot constraints and linked hand/load targets. Parameters: Knee bend, stance, hip depth, torso angle, hand/load location, ROM endpoint, unilateral support and resistance path. Split/review: Romanian/stiff/conventional/sumo/trap/behind-back/good-morning and single-leg mechanics need explicit sub-generators; rack pulls retain partial range; lever/cable axes remain distinct.

**push_up — 163 candidates** (6 source-complete for storyboard). Reuse: Closed-chain hand/foot support solving, torso frame and elbow-flexion press phases. Parameters: Hand/foot surfaces and heights, support count, body line, hand orientation/width, elbow plane, tempo and transition phases. Split/review: Pike/planche/hindu/cobra/kneeling/decline/incline/ball forms retain distinct paths/support graphs; hand-release/plyometric variants require explicit release/landing events.

**vertical_pull — 144 candidates** (26 source-complete for storyboard). Reuse: Hanging or seated torso setup, shoulder/elbow pull/return phases and hand-anchor constraints. Parameters: Grip, hand spacing, body support/assistance, torso lean, load path, leg placement, ROM and side coordination. Split/review: Pull-up body travel vs pulldown handle travel; assisted support; unilateral loading, kipping/ballistic and static hangs; pulley/machine axes are explicit.

**trunk_flexion — 230 candidates** (113 source-complete for storyboard). Reuse: Segmented trunk-flexion curve and controlled return/hold stages with supported pelvis frame. Parameters: Hip flexion, foot/leg supports, hand position, torso range, load placement, bench angle, tempo and side order. Split/review: Crunch vs sit-up vs reverse-crunch/leg-driven action; planted vs raised legs; shortened/negative/weighted variants. Identical instruction boilerplate does not erase name/description differences.

**ninety_ninety_hip_stretch — 2 candidates** (1 source-complete for storyboard). Reuse: Seated 90/90 hip setup, forward-hinge hold and side-switch scaffold. Parameters: Front/side leg geometry, trunk hinge range, hand support graph, hold duration and transition order. Split/review: 10565 has unspecified hands, 6560 explicitly hands on floor. Do not silently use a floor hand constraint for both.



### Explicit distinctions that block naive reuse

- **4007 vs 6428:** same heel-touch scaffold, but 4007 holds the legs raised at 90 degrees; 6428 keeps the feet planted. They have separate parameter/contact profiles.
- **10565 vs 6560:** reusable 90/90 hip setup and forward hinge are plausible, but 6560 explicitly places hands on the floor and 10565 does not specify that contact. Keep separate pending adjudication; never fill the unspecified hand position by copying.
- Incline/decline, seated/standing, alternating/bilateral/unilateral, full/partial ROM, hold/tempo/ballistic, grip/palm orientation, support contacts, cable anchor/path, machine pivot/travel and load position are review axes. All are carried in the source guards; extracted flags are incomplete by design.
- Matching equipment enum or muscle target does not establish matching kinematics. Title/description vs instruction contradictions require review even when the upstream brief labels the source complete (e.g. 0454 spider curl description vs standing preacher-style steps).

## Apparatus reuse

The inventory partitions exactly into **164 buildable base assets + 31 variants + 11 attachments + 6 unresolved = 212 rows**. Upstream calls 170 rows `base`; six of those are unresolved, so 170 is not the buildable base count. A sensible production backlog is **164 base contracts, 31 variant configurations/adaptations and 11 attachment modules**, with six blocked identities. Treating variants as configuration can avoid **up to 31 standalone base-model tasks**, subject to geometry review; it does not remove variant contact/axis work. Attachments are reusable assets but still require their own modeling and connection definitions.

**67 machine base contracts remain distinct.** Share pads, seats, plates, stack parts, fasteners and materials, but do not claim one generic machine. Vertical/horizontal/angled leg press, seated/lying/kneeling leg curl, incline/flat/decline chest press, chest-supported/seated/T-bar row, cable tower and Smith rails have different axes, support geometry or load paths. Each is listed in `summary.json:props.distinct_machine_contract_ids`. Plate-loaded/stack/outdoor variants are candidate component reuse; a stack and lever's mechanics are not interchangeable by appearance.

| Reusable prop | Canonical exercises referencing it | Relationship |
| --- | ---: | --- |
| Adjustable utility bench | 780 | base |
| Dumbbell pair | 775 | base |
| Adjustable cable station | 446 | base |
| Straight Olympic barbell | 428 | base |
| Resistance band base family | 421 | base |
| Band anchor point | 226 | base |
| Wall surface | 197 | base |
| Kettlebell | 190 | base |
| Household chair | 149 | base |
| Raised platform/deficit block | 145 | base |
| Overhead suspension anchor | 141 | base |
| Swiss/stability ball | 140 | base |

These prop counts overlap. **6,528 prop/exercise incidences cover 4,145 distinct canonical exercises**; never sum the table as exercise coverage. A shared bench supports flat/incline/decline settings; separately preserve preacher/hyperextension/GHD supports. A cable station is reusable, with height, anchor, cable routing and handle contacts explicitly configured; rope, straight/V/lat handles and ankle cuff are separate modules. Dumbbell/barbell/kettlebell assets are reused across many exercises, but changing a load does not prove the movement can share a clip. Inventory title/description/inferred matches remain candidates; the mapping separately lists instruction-supported props.

Unresolved prop identities: **weight_unspecified, ball_unspecified, rope_unspecified, strongman_carry_handles, wheel_unspecified, machine_unspecified**. Keep all 92 exercises with unresolved geometry blocked from final apparatus sign-off, even where another prop in their scene is known. No-prop-documented is a text status, not proof of no apparatus. Floors are shared scene geometry, not 1,487 independent models.

## Gaps and acceptance

**4,342 / 5,632** canonical briefs have source review reasons; 1,290 are source-complete for storyboard, which still does not mean production-ready. **159** authored storyboards are blocked on source resolution; 5,473 have proposals ready for review. Authored staging remains a proposal. Named poses, unsupported apparatus geometry, missing limb placements and ambiguous terms are carried through unchanged. All upstream prop issues are preserved in `summary.json`. No licensed GymVisual media, video/frame sequence, paid API, embeddings or network upload was used.

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
