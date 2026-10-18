"""Bounded small-fixture evidence only; no game solver or app integration."""
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from .partitioned_match_groups import PartitionedMatchGroups, make_baseline, Observation


def main():
    command=[sys.executable,'-B','-m','unittest','discover','-s','tests','-p','test_partitioned_match_groups.py','-v']
    run=subprocess.run(command,capture_output=True,text=True,timeout=20)
    log=Path('.artifacts/partitioned-fixture-tests.log')
    log.parent.mkdir(exist_ok=True)
    log.write_text(run.stdout+run.stderr,encoding='utf-8')
    if run.returncode:
        print(run.stdout+run.stderr)
        raise SystemExit(run.returncode)
    engine=PartitionedMatchGroups(make_baseline(mediums=1))
    context=engine.start();steps=[]
    def capture(name,c):
        steps.append(dict(name=name,groups=c.groups,public_roles=len({h.roles for h in c.public.hypotheses}),
            public_secrets=len(c.public.hypotheses),private_secrets=len(c.private.hypotheses),
            public_support_mass=str(c.public_support_mass),private_support_mass=str(c.private_support_mass),
            alive=c.alive))
    capture('symmetric baseline',context)
    program=(Observation('co',((1,'seer'),(2,'seer'))),Observation('report',((1,3,'white',1),(2,3,'white',1))))
    for name,event in zip(('simultaneous CO','simultaneous P3 white'),program):
        context=engine.update(context,event);capture(name,context)
    rows={r.player:r for r in engine.rows(context)}
    before=engine.stats.copy()
    for _ in range(100):
        assert engine.equivalent(rows[1],rows[2])
        assert not engine.equivalent(rows[1],rows[3])
    comparison_delta=dict(engine.stats-before)
    assert comparison_delta=={'comparisons':200}
    choices=[dict(targets=c.targets,multiplicity=c.multiplicity,mass=str(c.mass))for c in engine.uniform_choices(context,context.alive)]
    cells=[dict(composition=c.composition,world_multiplicity=c.world_multiplicity,secret_multiplicity=c.secret_multiplicity,mass=str(c.mass))for c in engine.role_cells(context)]
    selected=engine.update(context,Observation('select',((4,1),)));capture('P4 selects P1',selected)
    own=engine.update(context,Observation('private_role',((1,'seer'),)))
    own=engine.update(own,Observation('private_result',((1,3,'white',1),)))
    own=engine.update(own,Observation('death',((1,),),phase='night'));capture('private P1 seer and own result; later death',own)
    withdrawn=engine.rebuild((Observation('co',((1,'seer'),)),));capture('withdraw P2 and reports by rebuilding active program',withdrawn)
    capture('withdraw all by rebuilding',engine.rebuild(()))
    result=dict(recorded_utc=datetime.now(timezone.utc).isoformat(),
        head_before_evidence_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        source_sha256=hashlib.sha256(Path('benchmarks/player_match_groups/partitioned_match_groups.py').read_bytes()).hexdigest(),
        test_command=command,test_exit=run.returncode,tests=9,test_log=str(log),
        test_seconds_limit=20,scope='4/5 player W1 S1 H0, M0/1, constructed uniform initial law; joint-support observations only',
        legacy_oracle='complete labelled allocation/secret enumeration; n! state_signature audit; existing full canonical target keys',
        initial_variants=12,all_report_position_fixtures=42,
        comparison_delta=comparison_delta,stats=dict(engine.stats),steps=steps,
        p3_white_uniform_choices=choices,p3_white_role_cells=cells,
        ordinary_factory_changed=False,full_game_solver=False,performance_claim=False)
    out=Path('benchmarks/player_match_groups/partitioned-fixture-results.json')
    out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(tests=result['tests'],test_exit=run.returncode,comparison_delta=comparison_delta,
                         full_permutation_searches=engine.stats['full_permutation_searches'],result=str(out))))


if __name__=='__main__':main()