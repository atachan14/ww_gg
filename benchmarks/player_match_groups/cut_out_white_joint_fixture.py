"""Full-support white-joint entry and nearby evidence/scope refusals."""
import json,sys,subprocess,time,threading,os
from pathlib import Path
from fractions import Fraction as F
from dataclasses import replace


def support_refusals():
    from .cut_out_white_joint_max import graph
    from .cut_out_no_read_night_max import WhiteJointNightMaxEngine,certify_night
    from .cut_out_model_a import adapt_white_joint_night_max_model_a
    from .cut_out_max_game import graph as co_graph,evaluate as co_evaluate
    from .partitioned_match_groups import UnsupportedPartition
    from werewolf.action_flow import resolve_action
    from werewolf.evaluation_branch import ActionInputs
    from werewolf.information_set_forecast import InformationSetForecast,Pending
    from werewolf.seer_acquisition import normalize,SeerReport
    source=graph();root=source.origin();spec=source.engine.baseline.spec
    e=InformationSetForecast(spec.rules,spec.strategy,exact_renaming=False,retire_uninformative_scans=False)
    payload,outcomes=resolve_action(root.public,ActionInputs(root.public_state,(),root.private,None,root.physical),1,e.action_policy)
    c=e.action_policy.project(root.public,payload,next(o for o in outcomes if not o.board.winner),1)
    s=c.public_state
    from .cut_out_no_read_night_max import white_joint_support
    assert white_joint_support(c.public,s)
    by_roles={}
    for h in s.hypotheses:by_roles.setdefault(h.roles,[]).append(h)
    partial=replace(s,hypotheses=normalize(h for hs in by_roles.values() for h in hs[1:]))
    assert partial.public_roles==s.public_roles
    skew=replace(s,hypotheses=normalize(replace(h,mass=h.mass*factor) for hs in by_roles.values() for h,factor in zip(hs,(1,2,3))))
    assert skew.public_roles==s.public_roles
    refusals=[]
    for name,law in [('missing_white_support',partial),('skewed_white_mixture',skew),('bad_tracking',replace(s,tracked=tuple(range(1,6)))),('missing_world',replace(s,hypotheses=normalize(s.hypotheses[3:])) )]:
        result,diagnostic=certify_night(c.public,law,c.past,spec.rules,spec.strategy,white_joint=True)
        assert result.selected is None and result.reason=='white_joint_complete_support_unproved' and not diagnostic
        engine=WhiteJointNightMaxEngine(source)
        try:engine.wolf_policy(c.public,law,c.past,2)
        except Pending:pass
        else:raise AssertionError('invalid support produced policy')
        assert not engine.no_read_certificates
        refusals.append(name)
    co_spec=replace(spec,claims=('seer',)+('latent',)*4,reports=(SeerReport(1,1,1,3,'white'),))
    assert isinstance(adapt_white_joint_night_max_model_a(co_spec),UnsupportedPartition)
    assert isinstance(adapt_white_joint_night_max_model_a(replace(spec,claims=('medium',)+('latent',)*4)),UnsupportedPartition)
    assert isinstance(adapt_white_joint_night_max_model_a(replace(spec,mediums=0)),UnsupportedPartition)
    co=co_graph(5,1,'max',fake_reports='max')
    a,_=co_evaluate(co);b,_=co_evaluate(co,official_reference=True)
    assert a==b and a.village_win==F(2,3)
    # A NEW explicit simultaneous latent snapshot owns its full public prior.
    restored=graph()
    assert restored.origin().public_state==root.public_state and len(root.public_state.hypotheses)==180
    return dict(refusals=refusals,partial_support_same_public_marginals=True,skew_same_public_marginals=True,
        no_partial_certificate_installed=True,public_seer_CO_legacy_value='2/3',latent_root_reconstructed_hypotheses=180,
        CO_history_replay_adopted=False)


def audit(kind='public',target=3,scan=True):
    if kind=='boundaries':return support_refusals()
    from .cut_out_latent_max_fixture import audit as complete
    from .cut_out_white_joint_max import graph,evaluate
    from .cut_out_uniform_game import OwnView
    from .cut_out_no_read_night_max import white_joint_support
    result=complete(5,1,'random_white',kind,_white_joint=True,_white_target=target,_scan_interventions=scan,_fake_reports='max')
    source=graph();view=None if kind=='public' else OwnView(1,kind) if kind in ('medium','wolf') else OwnView(1,'seer')
    # Public and role-only runs cover ALL labelled root executions' public inputs.
    forecast,engine=evaluate(source,view=view)
    proof_sources=[]
    for (rules,strategy,b,s,past),certificate in engine.no_read_certificates.items():
        search,diagnostics=engine.no_read_diagnostics[rules,strategy,b,s,past]
        assert white_joint_support(b,s) and len(s.hypotheses)==144
        assert diagnostics['profile_reads']==0 and diagnostics['complete_candidate_scores']==12
        assert all(v==F(1,3) for info,row in certificate.scores for p,v in row)
        proof_sources.append(dict(execution=b.history[0].target,public_hypotheses=len(s.hypotheses),complete_candidates=12,profile_reads=0))
    assert {p['execution'] for p in proof_sources}==set(range(1,6))
    result.update(full_public_proof_sources=proof_sources,all_root_labels_verified=True)
    return result


def worker(case):
    from .cut_out_uniform_game_fixture import peak_bytes
    started=time.monotonic()
    def watch():
        while True:
            if time.monotonic()-started>60 or peak_bytes()>1500000000:os._exit(124)
            time.sleep(.1)
    threading.Thread(target=watch,daemon=True).start()
    args=json.loads(case);result=audit(*args)
    result.update(worker_seconds=time.monotonic()-started,peak_working_set_bytes=peak_bytes())
    print(json.dumps(result),flush=True)


def main():
    if len(sys.argv)>1:return worker(sys.argv[1])
    started=time.monotonic();rows=[];logs=[]
    cases=[('public',),('role',),('medium',),('white',2,False),('white',3,True),('white',4,False),('white',5,False),('boundaries',)]
    for case in cases:
        remaining=300-(time.monotonic()-started)
        if remaining<=0:raise SystemExit('overall300s budget exhausted')
        run=subprocess.run([sys.executable,'-B','-m',__spec__.name,json.dumps(case)],capture_output=True,text=True,timeout=min(60,remaining))
        if run.returncode:raise RuntimeError(run.stdout+run.stderr)
        rows.append(json.loads(run.stdout));print('passed '+str(case),flush=True)
    previous=json.loads(Path('benchmarks/player_match_groups/withdraw-standard-results.json').read_text(encoding='utf-8'))
    checks=[(c['kind'],c['target']) for c in previous['checks']]+[('pattern','test_cut_out_seven_minimal.py'),('pattern','test_cut_out_max_game.py'),('pattern','test_cut_out_latent_max.py'),('pattern','test_cut_out_terminal_night_max.py'),('pattern','test_cut_out_no_read_night_max.py'),('pattern','test_cut_out_triple_max.py'),('pattern','test_cut_out_active_report_max.py'),('pattern','test_cut_out_white_joint_max.py')]
    for kind,target in checks:
        remaining=300-(time.monotonic()-started)
        if remaining<=0:raise SystemExit('overall300s budget exhausted')
        run=subprocess.run([sys.executable,'-B','-m','benchmarks.player_match_groups.withdraw_prefix_diagnostic_fixture',kind,target],capture_output=True,text=True,timeout=min(60,remaining))
        if run.returncode:raise RuntimeError(run.stdout+run.stderr)
        logs.append(run.stdout+run.stderr)
    Path('.artifacts/white-joint-max-regressions-final.log').write_text('\n'.join(logs),encoding='utf-8')
    result=dict(cases=rows,checks=checks,existing59_preserved=True,regression_tests=62,timing_interpretation='bounded correctness only',overall_seconds=time.monotonic()-started)
    Path('benchmarks/player_match_groups/cut-out-white-joint-max-results.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(overall_seconds=result['overall_seconds'])),flush=True)

if __name__=='__main__':main()
