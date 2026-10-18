"""Small cold-source adapter ledger and regression tests; no game benchmark."""
import hashlib
import json
import subprocess
import sys
from datetime import datetime,timezone
from pathlib import Path
from .cut_out_model_a import adapt_model_a,ModelAOneStepExecution
from werewolf.public_prior import clear_public_prior_cache


def main():
    sys.path.insert(0,str(Path('tests').resolve()))
    from test_cut_out_model_a import cases
    tests=[]
    for pattern,count in (('test_cut_out_model_a.py',6),('test_cut_out_independent.py',4)):
        command=[sys.executable,'-B','-m','unittest','discover','-s','tests','-p',pattern,'-v']
        run=subprocess.run(command,capture_output=True,text=True,timeout=20)
        log=Path('.artifacts')/(pattern.removesuffix('.py')+'-adapter-final.log')
        log.parent.mkdir(exist_ok=True);log.write_text(run.stdout+run.stderr,encoding='utf-8')
        if run.returncode:
            print(run.stdout+run.stderr);raise SystemExit(run.returncode)
        tests.append(dict(pattern=pattern,count=count,exit=run.returncode,seconds_limit=20,log=str(log)))
    rows=[]
    for n in (4,5):
        for name,spec in cases(n).items():
            clear_public_prior_cache()
            engine=adapt_model_a(spec);context=engine.start()
            evaluator=ModelAOneStepExecution(engine);result=evaluator.evaluate(context)
            reference=ModelAOneStepExecution(engine).evaluate(context,representatives=False)
            assert result.aggregate==reference.aggregate
            evaluation_stats=evaluator.stats.copy()
            for target in context.alive:
                assert evaluator.materialize(result,target)==ModelAOneStepExecution(engine).materialize(reference,target)
            rows.append(dict(players=n,case=name,seers=spec.seers,mediums=spec.mediums,
                claims=spec.claims,groups=context.groups,tracked_seers=context.public.tracked,
                observed_prefix=context.public.observed_prefix,past_order=[r.player for r in engine.baseline.past],
                construction_stats=dict(engine.stats),evaluation_stats=dict(evaluation_stats),
                optional_transport_stats=dict(evaluator.stats-evaluation_stats),
                wolf_rates={str(p):str(engine.baseline.board.wolf_probability(p)) for p in context.alive},
                joint_total_mass=str(sum(h.mass for h in context.public.hypotheses)),
                weighted_worlds=[[list(w[:-1]),str(w[-1])] for w in engine.baseline.board.worlds],
                aggregate=[dict(winner=k[0],role=k[1],mass=str(q)) for k,q in result.aggregate],
                law_semantics=result.law_semantics,complete_step_branches_equal=True))
    paths=('benchmarks/player_match_groups/cut_out_model_a.py','benchmarks/player_match_groups/cut_out_one_step.py','tests/test_cut_out_model_a.py')
    result=dict(recorded_utc=datetime.now(timezone.utc).isoformat(),
        head_before_evidence_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        source_sha256={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in paths},
        tests=tests,cases=rows,formal_source='board_roles.reconstruct_saved + public_prior.prepare_public_prior',
        proof_scope='constructed simultaneous initial public joint law and one day execution only',
        arbitrary_distribution_accepted=False,upstream_permutation_audit=False,
        private_or_future_connected=False,ordinary_route_changed=False,performance_claim=False)
    out=Path('benchmarks/player_match_groups/cut-out-model-a-results.json')
    out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(tests=10,cases=len(rows),p5_wolf=next(r['wolf_rates']['5'] for r in rows if r['players']==5 and r['case']=='witness'),result=str(out))))


if __name__=='__main__':main()