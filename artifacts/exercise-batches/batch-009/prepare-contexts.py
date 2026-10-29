"""Prepare batch-local intake using the existing preparer and a frozen policy.

Run: python3 artifacts/exercise-batches/batch-009/prepare-contexts.py
This reads the existing working-tree policy path through an explicit snapshot
adapter; it never modifies that policy or its pending changes.
"""
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PREPARER = ROOT / 'artifacts/exercise-animation-briefs/prepare_generation.py'
POLICY = ROOT / 'artifacts/exercise-animation-briefs/generation-contract.json'
SNAPSHOT_SOURCE = HERE.parent / 'batch-008/intake-contract.json'
SNAPSHOT = HERE / 'intake-contract.json'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    selection = json.loads((HERE / 'selection.json').read_text())
    SNAPSHOT.write_bytes(SNAPSHOT_SOURCE.read_bytes())
    spec = importlib.util.spec_from_file_location('existing_intake_preparer', PREPARER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    original_document = module.document
    module.document = lambda path: original_document(SNAPSHOT if path == POLICY else path)
    results = module.prepare(selection['exercise_ids'], HERE / 'contexts')
    resolutions = json.loads((HERE / 'source-resolutions.json').read_text())
    for row in results:
        path = Path(row['path'])
        packet = json.loads(path.read_text())
        for entry in packet['input_files']:
            if entry['path'] == str(POLICY.relative_to(ROOT)):
                entry.update(path=str(SNAPSHOT.relative_to(ROOT)), sha256=sha(SNAPSHOT))
        packet['batch_followup_constraints'] = {
            'path': str((HERE / 'authoring-handoff.md').relative_to(ROOT)),
            'note': 'User feedback, actual motion and natural hand/arm staging take priority over endpoint-only metrics.',
        }
        packet['authored_batch_staging'] = resolutions[row['requested_id']]
        path.write_text(json.dumps(packet, ensure_ascii=False, indent=2) + '\n')
    (HERE / 'intake-provenance.json').write_text(json.dumps({
        'policy_source_path': str(POLICY.relative_to(ROOT)),
        'policy_source_commit': 'c7d44162be89c6220a65f24e3e8ce141d8d727bd',
        'snapshot_path': str(SNAPSHOT.relative_to(ROOT)),
        'snapshot_sha256': sha(SNAPSHOT),
        'preparer': str(PREPARER.relative_to(ROOT)),
        'preparer_sha256': sha(PREPARER),
        'working_tree_policy_modified': False,
        'method': 'Reuse the existing intake preparer with a frozen-policy read adapter; preserve pending global policy edits.',
    }, indent=2) + '\n')
    print(json.dumps({'batch': selection['batch'], 'prepared_ids': selection['exercise_ids']}))


if __name__ == '__main__':
    main()
