"""Verify canonical/alias context preparation and known-defect preflight refusal."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
OUT=ROOT/'artifacts/exercise-generation'
def invoke(args):return subprocess.run(args,cwd=ROOT,text=True,capture_output=True)
result=invoke([sys.executable,str(HERE/'prepare_generation.py'),'--exercise','0001','0004','5915'])
assert result.returncode==0,result.stderr
packets={key:json.loads((OUT/(key+'.json')).read_text()) for key in ['0001','0004','5915']}
assert packets['0004']['canonical_id']=='5266'
assert packets['0004']['source_brief']['id']=='5266'
assert packets['0004']['alias_resolution']['resolution_chain']==['0004','5266']
assert packets['0001']['readiness']['status']=='blocked'
assert set(packets['0001']['readiness']['blocking_issue_ids'])=={'OPEN-0001-CONTACTS','OPEN-0001-HAND-HEAD-POSE'}
assert packets['5915']['readiness']['status']=='requires_review'
assert all(len(packet['baseline_requirements'])==21 and packet['not_production_approved'] for packet in packets.values())
for packet in packets.values():
    for source in packet['input_files']:
        assert hashlib.sha256((ROOT/source['path']).read_bytes()).hexdigest()==source['sha256']
strict=invoke([sys.executable,str(HERE/'prepare_generation.py'),'--exercise','0001','--require-ready'])
assert strict.returncode==2,(strict.returncode,strict.stderr)
unknown=invoke([sys.executable,str(HERE/'prepare_generation.py'),'--exercise','unknown-exercise'])
assert unknown.returncode==2 and 'Unknown exercise IDs' in unknown.stderr,unknown.stderr
body=ROOT/'artifacts/bodyweight-five'
before=hashlib.sha256((body/'bodyweight-five.blend').read_bytes()).hexdigest()
guard=invoke(['/opt/homebrew/bin/blender','-b','-t','4','--python-exit-code','1','-P',str(body/'build_motion.py')])
(HERE/'generation-preflight.log').write_text(guard.stdout+guard.stderr)
assert guard.returncode==1,(guard.returncode,guard.stdout,guard.stderr)
assert 'Known animation defects require remediation' in guard.stdout+guard.stderr
assert all(key in guard.stdout+guard.stderr for key in ['OPEN-0001-CONTACTS','OPEN-0001-HAND-HEAD-POSE'])
assert before==hashlib.sha256((body/'bodyweight-five.blend').read_bytes()).hexdigest()
report=dict(ok=True,canonical_and_alias_packets=True,baseline_requirements=21,
            source_hashes_match=True,unknown_id_rejected=True,require_ready_exit_code=strict.returncode,
            known_defect_blender_preflight_exit_code=guard.returncode,existing_motion_asset_unchanged=True,
            blocking_issue_ids=packets['0001']['readiness']['blocking_issue_ids'])
(HERE/'generation-verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
