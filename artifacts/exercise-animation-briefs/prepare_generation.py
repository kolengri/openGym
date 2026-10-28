"""Assemble source evidence, constraints and open findings before authoring a clip."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]

def document(path):
    return json.loads(path.read_text())

def known_open_issues(exercise_ids):
    requested=set(exercise_ids)
    return [issue for issue in document(HERE/'generation-contract.json')['known_open_issues']
            if issue['status']=='open' and
            (not issue.get('exercise_ids') or '*' in issue['exercise_ids'] or requested.intersection(issue['exercise_ids']))]

def prepare(exercise_ids,output_dir):
    aliases={row['id']:row for row in document(HERE/'aliases.json')}
    resolved={key:aliases.get(key,{}).get('canonical_id',key) for key in exercise_ids}
    needed=set(exercise_ids)|set(resolved.values());records={}
    with gzip.open(HERE/'briefs.jsonl.gz','rt') as source:
        for line in source:
            row=json.loads(line)
            if row['id'] in needed:records[row['id']]=row
    missing=needed-records.keys()
    if missing:raise ValueError('Unknown exercise IDs: '+', '.join(sorted(missing)))
    contract=document(HERE/'generation-contract.json')
    atlas=document(ROOT/'artifacts/mannequin-muscle-atlas/region-map.json')
    pilots=document(HERE/'selected-first-five.json').get('authoring_overrides',{})
    paths=[HERE/'briefs.jsonl.gz',HERE/'generation-contract.json',HERE/'selected-first-five.json',
           ROOT/'artifacts/mannequin-muscle-atlas/region-map.json']
    inputs=[dict(path=str(path.relative_to(ROOT)),sha256=hashlib.sha256(path.read_bytes()).hexdigest()) for path in paths]
    results=[]
    for requested,canonical_id in resolved.items():
        brief=records[canonical_id]
        names={item['name'] for role in ['primary','secondary'] for item in brief['muscles'][role]}
        display=brief['muscles'].get('catalogue_display_map',{}).get('value',{})
        names.update(display.get('primaries',[]));names.update(display.get('secondaries',[]))
        issues=known_open_issues([canonical_id])
        blockers=brief['storyboard_readiness']['blockers']
        blocking=[issue for issue in issues if issue.get('blocks_generation',True)]
        unmapped=names-atlas['mappings'].keys()
        if unmapped:raise ValueError('Unmapped muscle labels for '+canonical_id+': '+', '.join(sorted(unmapped)))
        packet=dict(schema_version='1.0.0',requested_id=requested,canonical_id=canonical_id,
            alias_resolution=aliases.get(requested),not_production_approved=True,
            readiness={'status':'blocked' if blocking or blockers else 'requires_review',
                       'source_blockers':blockers,'known_open_issue_ids':[issue['id'] for issue in issues],
                       'blocking_issue_ids':[issue['id'] for issue in blocking]},
            source_brief=brief,selected_pilot_authoring_override=pilots.get(canonical_id),
            baseline_requirements=contract['baseline_requirements'],
            evidence_status_policy=contract['evidence_status_policy'],
            per_exercise_intake_template=contract['per_exercise_intake_template'],
            per_exercise_overrides=contract.get('per_exercise_overrides',{}).get(canonical_id),
            known_open_issues=issues,
            muscle_name_mappings={name:atlas['mappings'].get(name) for name in sorted(names)},
            contract_source_registry=contract['sources'],input_files=inputs)
        output_dir.mkdir(parents=True,exist_ok=True)
        path=output_dir/(requested+'.json');path.write_text(json.dumps(packet,ensure_ascii=False,indent=2)+'\n')
        results.append(dict(requested_id=requested,canonical_id=canonical_id,status=packet['readiness']['status'],
                            known_open_issue_ids=packet['readiness']['known_open_issue_ids'],path=str(path)))
    return results

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--exercise',nargs='+',required=True,help='Catalogue IDs, including aliases')
    parser.add_argument('--output-dir',type=Path,default=ROOT/'artifacts/exercise-generation')
    parser.add_argument('--require-ready',action='store_true',help='Exit 2 after writing packets if any has a known/source blocker; never implies production approval')
    args=parser.parse_args()
    try:results=prepare(args.exercise,args.output_dir)
    except ValueError as error:parser.error(str(error))
    print(json.dumps(results,indent=2))
    if args.require_ready and any(row['status']=='blocked' for row in results):raise SystemExit(2)

if __name__=='__main__':main()
