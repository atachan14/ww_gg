"""Initial day/night/fake-report max boundary matrix; no new strategy rule."""
import json,time,sys,subprocess,threading,os
from pathlib import Path
from fractions import Fraction as F
from dataclasses import replace


def active_report_diagnostic():
    from werewolf.exact import initial_board,condition_claims,ClaimPolicy,Rules,Strategy,report_actions
    from werewolf.root_secret_flow import prepare_root_secrets,root_scope
    from werewolf.information_set_forecast import InformationSetForecast
    from werewolf.evaluation_branch import ActionInputs
    from werewolf.action_flow import resolve_action
    from werewolf.calculation_budget import calculation_budget
    from werewolf.morning_flow import report_flow,continuation_value
    from .cut_out_model_a import InitialModelASpec,adapt_no_read_night_max_model_a,adapt_latent_max_model_a
    from .partitioned_match_groups import UnsupportedPartition
    rules=Rules(initial_seer='none');strategy=Strategy()
    claims=('medium','medium','latent','latent','latent')
    spec=InitialModelASpec(5,claims,True,rules=rules,strategy=strategy)
    rejected=adapt_no_read_night_max_model_a(spec)
    assert isinstance(rejected,UnsupportedPartition) and rejected.reason=='active_medium_report_max_outside_comparison_scope'
    b=condition_claims(initial_board(5,1,1,1,0,experimental_cast=True),claims,ClaimPolicy())
    root=prepare_root_secrets(b,rules)
    formal_reason=root_scope(root,rules,strategy)
    isolated_fake_reason=root_scope(root,rules,Strategy(day='random',night='random',fake_reports='max'))
    e=InformationSetForecast(rules,strategy,exact_renaming=False,retire_uninformative_scans=False)
    c=ActionInputs(root.public_law,(),root.physical_law,None,root.physical)
    with calculation_budget(100000,max_seconds=15):
        for target in (3,4):
            acquired,outcomes=resolve_action(b,c,target,e.action_policy)
            assert len(outcomes)==1
            result=e.action_policy.project(b,acquired,outcomes[0],target)
            b=result.public;c=ActionInputs(result.public_state,result.past,result.private,None,result.physical)
        scores=[]
        for action in report_actions(b):
            value=continuation_value(report_flow(action.outcomes,c.public_state,c.past,e,source_board=b,fake_colors=action.fake_colors),e.scalar)
            scores.append(dict(fake_colors=action.fake_colors,value=str(value)))
        selected=e.morning(b,c.public_state,c.past)
        selected_colors=tuple((r.reporter,r.color) for r in selected[0][1].reports)
        assert len(selected)==1 and selected[0][0]==1 and selected_colors==((1,'white'),(2,'white'))
        assert min(F(row['value']) for row in scores)==F(1,2)
    return dict(case='active-medium-report',comparison_first_boundary=rejected.reason,formal_full_root_first_boundary=formal_reason,
        formal_fake_only_root_boundary=isolated_fake_reason,counterfactual_execution=3,counterfactual_bite=4,
        existing_report_action_scores=scores,existing_selected_colors=selected_colors,existing_report_min_value='1/2',
        fake_seer_policy=list(strategy.fake_seer_policy),active_report_entry_adopted=False)


def audit(case):
    from werewolf.exact import Strategy,Rules
    from .cut_out_model_a import adapt_no_read_night_max_model_a
    from .cut_out_no_read_night_max import graph as no_read
    if case=='active':return active_report_diagnostic()
    if case=='residual':
        spec=replace(no_read(fake_reports='max').engine.baseline.spec,mediums=1,rules=Rules(initial_seer='random_white'))
        refusal=adapt_no_read_night_max_model_a(spec)
        assert refusal.reason=='five_player_no_read_requires_M0_initial_none_all_latent'
        return dict(case=case,first_boundary=refusal.reason,fake_report_setting_preserved='max',approximation_used=False)
    if case=='sealed':
        from .cut_out_max_fixture import audit as complete
        from .cut_out_max_game import graph
        source=graph(5,1,'max',fake_reports='max')
        result=complete(5,1,'max',True,_fake_reports='max')
    else:
        from .cut_out_latent_max_fixture import audit as complete
        if case=='terminal':
            from .cut_out_terminal_night_max import graph
            source=graph(1,'random_white',fake_reports='max')
            result=complete(4,1,'random_white','white',_terminal_night_max=True,_fake_reports='max')
        else:
            source=no_read(fake_reports='max')
            result=complete(5,0,'none','role',_no_read_night_max=True,_fake_reports='max')
    assert source.engine.baseline.strategy==Strategy()
    assert source.data.to_game()['policy']['fake_reports']=='max'
    assert 'medium' not in source.origin().public.claims
    result.update(case=case,three_max_preserved=True,medium_report_selection_inactive=True,fake_seer_policy=list(source.engine.baseline.strategy.fake_seer_policy))
    return result


def worker(case):
    from .cut_out_uniform_game_fixture import peak_bytes
    started=time.monotonic()
    def watch():
        while True:
            if time.monotonic()-started>60 or peak_bytes()>1500000000:os._exit(124)
            time.sleep(.1)
    threading.Thread(target=watch,daemon=True).start()
    result=audit(case);result.update(worker_seconds=time.monotonic()-started,peak_working_set_bytes=peak_bytes())
    print(json.dumps(result),flush=True)


def main():
    if len(sys.argv)>1:return worker(sys.argv[1])
    started=time.monotonic();rows=[];logs=[]
    for case in ('terminal','no-read','sealed','active','residual'):
        run=subprocess.run([sys.executable,'-B','-m',__spec__.name,case],capture_output=True,text=True,timeout=min(60,300-(time.monotonic()-started)))
        if run.returncode:raise RuntimeError(run.stdout+run.stderr)
        rows.append(json.loads(run.stdout));print('passed '+case,flush=True)
    previous=json.loads(Path('benchmarks/player_match_groups/withdraw-standard-results.json').read_text(encoding='utf-8'))
    checks=[(c['kind'],c['target']) for c in previous['checks']]+[('pattern','test_cut_out_seven_minimal.py'),('pattern','test_cut_out_max_game.py'),('pattern','test_cut_out_latent_max.py'),('pattern','test_cut_out_terminal_night_max.py'),('pattern','test_cut_out_no_read_night_max.py'),('pattern','test_cut_out_triple_max.py')]
    for kind,target in checks:
        run=subprocess.run([sys.executable,'-B','-m','benchmarks.player_match_groups.withdraw_prefix_diagnostic_fixture',kind,target],capture_output=True,text=True,timeout=min(60,300-(time.monotonic()-started)))
        if run.returncode:raise RuntimeError(run.stdout+run.stderr)
        logs.append(run.stdout+run.stderr)
    Path('.artifacts/triple-max-regressions-final.log').write_text('\n'.join(logs),encoding='utf-8')
    result=dict(cases=rows,checks=checks,existing53_preserved=True,regression_tests=56,timing_interpretation='bounded correctness run; not a speed comparison',overall_seconds=time.monotonic()-started)
    Path('benchmarks/player_match_groups/cut-out-triple-max-results.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(overall_seconds=result['overall_seconds'])),flush=True)

if __name__=='__main__':main()
