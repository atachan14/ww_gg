"""Finite independent audits + tiny one-step work counts; no speed benchmark."""
import hashlib
import json
import re
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from .partitioned_match_groups import make_baseline,Observation
from .constructive_cut_out import ConstructiveCutOutGroups
from .cut_out_one_step import OneStepExecution


def main():
    command=[sys.executable,'-B','-m','unittest','discover','-s','tests','-p','test_cut_out_independent.py','-v']
    run=subprocess.run(command,capture_output=True,text=True,timeout=20)
    logs=Path('.artifacts');logs.mkdir(exist_ok=True)
    log=logs/'cut-out-independent-final.log';log.write_text(run.stdout+run.stderr,encoding='utf-8')
    if run.returncode:
        print(run.stdout+run.stderr);raise SystemExit(run.returncode)
    exhaustive=json.loads(re.search(r'EVENT_EXHAUSTIVE (\{.*\})',run.stdout).group(1))
    random_audit=json.loads(re.search(r'EVENT_RANDOM (\{.*\})',run.stdout).group(1))
    rows=[]
    for n in (4,5):
        for medium in (0,1):
            engine=ConstructiveCutOutGroups(make_baseline(n,mediums=medium))
            base=engine.start();base_setup=dict(engine.stats)
            public=engine.rebuild((Observation('co',((1,'seer'),(2,'seer'))),Observation('report',((1,3,'white',1),(2,3,'white',1)))))
            public_setup=dict(engine.stats)
            private=engine.update(public,Observation('private_role',((1,'seer'),)));private_setup=dict(engine.stats)
            for name,context,view,setup in (('initial',base,'public',base_setup),('co-report',public,'public',public_setup),('own-seer',private,'private',private_setup)):
                grouped=OneStepExecution(engine);full=OneStepExecution(engine)
                result=grouped.evaluate(context,view=view)
                reference=full.evaluate(context,view=view,representatives=False)
                assert result.aggregate==reference.aggregate
                gs=grouped.stats.copy();fs=full.stats.copy()
                for target in context.alive:
                    assert grouped.materialize(result,target)==full.materialize(reference,target)
                rows.append(dict(players=n,mediums=medium,case=name,view=view,groups=context.groups,
                    context_construction_stats=setup,
                    role_worlds=len((context.public if view=='public' else context.private).public_roles),
                    joint_hypotheses=len((context.public if view=='public' else context.private).hypotheses),
                    representative_evaluation=dict(gs),full_labelled_same_kernel=dict(fs),
                    optional_grouped_materialization=dict(grouped.stats-gs),
                    complete_branches_equal=True,aggregate_equal=True,
                    aggregate=[dict(winner=key[0],role_index=key[1],mass=str(q)) for key,q in result.aggregate]))
    sources={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in (
        'benchmarks/player_match_groups/cut_out_one_step.py','tests/test_cut_out_independent.py')}
    result=dict(recorded_utc=datetime.now(timezone.utc).isoformat(),
        head_before_evidence_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        source_sha256=sources,tests=4,test_seconds_limit=20,test_log=str(log),
        exhaustive=exhaustive,random_audit=random_audit,one_step_cases=rows,
        independent_oracle='old labelled joint enumeration + existing full state_signature audit + exact.action_outcomes',
        weight_witness=dict(players=5,mediums=1,claim_policy='all none',p5_only_seer_co=True,prototype_p5_wolf='1/2',existing_group_model_p5_wolf='1/5'),
        model_a_connected=False,normal_route_changed=False,full_game_solver=False,performance_claim=False,
        note='same-kernel full-labelled reference demonstrates candidate work reduction; legacy action_outcomes is separately audited in tests. Tiny single-run timing, not production performance.')
    out=Path('benchmarks/player_match_groups/cut-out-independent-results.json')
    out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(tests=4,exhaustive=exhaustive,random_audit=random_audit,one_step_cases=len(rows),result=str(out))))


if __name__=='__main__':main()