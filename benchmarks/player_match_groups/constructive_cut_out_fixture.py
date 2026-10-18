"""Small constructive-vs-generator work ledger; not a performance benchmark."""
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from .partitioned_match_groups import PartitionedMatchGroups, make_baseline, Observation
from .constructive_cut_out import ConstructiveCutOutGroups


def run_fixture(engine_type,n,medium):
    engine=engine_type(make_baseline(n,mediums=medium))
    program=(Observation('co',((1,'seer'),(2,'seer'))),
             Observation('report',((1,3,'white',1),(2,3,'white',1))),
             Observation('death',((4,),),phase='night'))
    steps=[];contexts=[]
    def save(name,context):
        contexts.append(context)
        rows=engine.rows(context)
        steps.append(dict(name=name,groups=context.groups,alive=context.alive,
            role_rates={str(r.player):list(map(str,r.role_rates)) for r in rows},
            public_support_mass=str(context.public_support_mass),private_support_mass=str(context.private_support_mass),
            joint_hypotheses=len(context.public.hypotheses),joint_roles=len(context.public.public_roles)))
        return rows
    context=engine.start();save('baseline',context)
    for event in program:
        context=engine.update(context,event);rows=save(event.kind,context)
        if event.kind=='report':
            rows={r.player:r for r in rows};before=engine.stats.copy()
            for _ in range(100):
                assert engine.equivalent(rows[1],rows[2])
                assert not engine.equivalent(rows[1],rows[3])
            delta=dict(engine.stats-before)
            assert delta=={'comparisons':200}
    # Explicit active-program reconstruction; no implicit CCO/event reordering.
    corrected_program=program[:1]+(Observation('report',((1,n,'white',1),(2,n,'white',1))),)+program[2:]
    save('corrected target from baseline',engine.rebuild(corrected_program))
    save('withdraw report/P2 CO from baseline',engine.rebuild((Observation('co',((1,'seer'),)),)))
    return dict(players=n,mediums=medium,steps=steps,stats=dict(engine.stats),comparison_delta=delta),contexts


def main():
    tests=[]
    for pattern,count in (('test_partitioned_match_groups.py',9),('test_constructive_cut_out.py',12)):
        command=[sys.executable,'-B','-m','unittest','discover','-s','tests','-p',pattern,'-v']
        run=subprocess.run(command,capture_output=True,text=True,timeout=20)
        log=Path('.artifacts')/(pattern.removesuffix('.py')+'-final.log')
        log.write_text(run.stdout+run.stderr,encoding='utf-8')
        if run.returncode:
            print(run.stdout+run.stderr);raise SystemExit(run.returncode)
        tests.append(dict(pattern=pattern,count=count,exit=run.returncode,log=str(log),seconds_limit=20))
    fixtures=[]
    for n in (4,5):
        for medium in (0,1):
            original,left=run_fixture(PartitionedMatchGroups,n,medium)
            constructive,right=run_fixture(ConstructiveCutOutGroups,n,medium)
            assert original['steps']==constructive['steps']
            assert all((a.public,a.private,a.public_support_mass,a.private_support_mass)==
                       (b.public,b.private,b.public_support_mass,b.private_support_mass) for a,b in zip(left,right))
            assert constructive['stats']['generator_checks']==0
            assert constructive['stats']['symmetry_history_rows_read']==0
            assert constructive['stats']['full_permutation_searches']==0
            fixtures.append(dict(generator=original,constructive=constructive,complete_laws_equal=True))
    sources={name:hashlib.sha256(Path(name).read_bytes()).hexdigest() for name in (
        'benchmarks/player_match_groups/partitioned_match_groups.py',
        'benchmarks/player_match_groups/constructive_cut_out.py')}
    result=dict(recorded_utc=datetime.now(timezone.utc).isoformat(),
        head_before_evidence_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        sources_sha256=sources,tests=tests,fixtures=fixtures,
        scopes='4/5 W1 S1 H0 M0/1 constructed joint-support law; explicit CO/report/death/correction fixtures',
        timing_note='single tiny-fixture diagnostic scopes, no speedup claim; update includes event_execution and partition and support_mass; event_execution includes law_condition; row build separately',
        count_note='normalization/support-mass/role-rate input sizes, not every internal iteration; full explicit joint laws remain',
        ordinary_factory_changed=False,full_game_solver=False,performance_claim=False)
    out=Path('benchmarks/player_match_groups/constructive-cut-out-results.json')
    out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(tests=21,fixtures=len(fixtures),complete_laws_equal=True,result=str(out))))


if __name__=='__main__':main()