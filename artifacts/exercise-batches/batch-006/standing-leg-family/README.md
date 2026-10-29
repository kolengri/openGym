# Shared standing-leg family — feedback repair

The current canonical3479 action is an eight-second bilateral squat/kick/touch cycle. The user rejected the old five-second overlap: kick takeoff occurred during the rise from the deepest squat. This one revision completes the squat and full stand, transfers weight with both soles planted, then runs the accepted kick/contact/retract method. No shape bank, weight, topology or deep-squat/contact geometry revision. Root inspected the actual GPU stages and accepted the sequence.

Canonical runtime asset is `../assets/3479/motion.glb` under key `standing-leg-family`. The original full GLB BIN prefix and physical-body records remain exact. Only3479 animation sampler data is appended and its animation object replaced.3480's animation/accessors remain byte-exact, all64 existing3480 files remain unchanged, and all151 native bone/skin fingerprints compare bit-exact. The standalone3480 source/GLB retain their original hashes and receipts; the two per-ID containers now intentionally differ.

Four original capped local POSITION/NORMAL keys remain unchanged. Unkeyed pose-bone scale defaults are explicitly preserved during action authoring; otherwise matrix decomposition can perturb shared finger defaults by float ULPs despite identical untouched curves.

Affected3479 verification covers all241 native/decoded30Hz frames, five full-source references, mandatory game QA and selected actual GPU motion stages. Local self-fold/normal diagnostics and residual joint creases remain disclosed. `motion-repair-report.json` distinguishes visible acceptance from transport checks.

Repair from the preserved3480 baseline, from workspace root:

```sh
/opt/homebrew/bin/blender -b --factory-startup --offline-mode -t 2 --python-exit-code 1 --python artifacts/exercise-batches/batch-006/standing-leg-family/squat-feedback/revise_source.py
/opt/homebrew/bin/blender -b --factory-startup --offline-mode -t 2 --python-exit-code 1 --python artifacts/exercise-batches/batch-006/standing-leg-family/squat-feedback/export_replacement.py
python3 artifacts/exercise-batches/batch-006/standing-leg-family/squat-feedback/pack_replacement.py
/opt/homebrew/bin/blender -b --factory-startup --offline-mode -t 2 --python-exit-code 1 --python artifacts/exercise-batches/batch-006/standing-leg-family/squat-feedback/verify_3480_unchanged.py
/opt/homebrew/bin/blender -b --factory-startup --offline-mode -t 2 --python-exit-code 1 --python artifacts/exercise-batches/batch-006/standing-leg-family/verify_invariants.py
/opt/homebrew/bin/blender -b --factory-startup --offline-mode -t 2 --python-exit-code 1 --python artifacts/exercise-batches/batch-006/standing-leg-family/verify_native.py -- --only-3479
node artifacts/exercise-batches/batch-006/standing-leg-family/verify_export.mjs 3479
node artifacts/exercise-batches/batch-006/standing-leg-family/verify_runtime_stream.mjs 3479
/opt/homebrew/bin/blender -b --factory-startup --offline-mode -t 2 --python-exit-code 1 --python artifacts/exercise-batches/batch-006/standing-leg-family/proof_final.py -- --only-3479
python3 artifacts/exercise-batches/batch-006/standing-leg-family/curate.py
```

The old body/binding/target construction scripts remain provenance for the preserved baseline. Use the repair entrypoint above for current3479; do not regenerate its accepted target bank or overwrite3480. Root owns shared viewer/presentation/camera fitting and publication. Logs, candidate bundles, temporary blend/GLB copies and caches are excluded from curated publication.
