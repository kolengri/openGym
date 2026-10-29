# Per-exercise generation contexts

These example packets are generated from the complete catalogue, the production contract and current atlas mapping:

```sh
python3 artifacts/exercise-animation-briefs/prepare_generation.py --exercise 0001 0004 5915
```

The preparer accepts every existing catalogue ID, resolves aliases and retains source evidence, all 21 baseline requirements, selected authoring choices, relevant mappings, known issues and input hashes. It does not generate motion or approve anatomy. Read the full packet before authoring.

`0001.json` is blocked on pelvic/floor contact and hand/head pose findings. `0004.json` resolves to canonical 5266. `5915.json` requires review; the outstanding real-app/device playback evidence does not itself block clip authoring. Add `--require-ready` to return exit code 2 when source or known blocking issues remain; the packet is still written for remediation.

The authoritative rules and remediation evidence are in [production-guide.md](../exercise-animation-briefs/production-guide.md) and [generation-contract.json](../exercise-animation-briefs/generation-contract.json). The source corpus covers all 6,554 IDs; these three files are examples, not a claim that every exercise has been visually or biomechanically reviewed.
