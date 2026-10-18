"""Terminal night-max bridge and bounded existing-certificate diagnostic."""
import json,time,sys,subprocess,threading,os
from pathlib import Path
from fractions import Fraction as F


def certify_context(context,rules,strategy):
    from werewolf.wolf_profile_certificate import WolfProfileResolver
    from werewolf.calculation_budget import calculation_budget
    resolver=WolfProfileResolver(rules,strategy,max_profiles=1,max_work=100000,max_seconds=12,canonical_certificates=False)
    with calculation_budget(100000,max_seconds=12):result=resolver.resolve(context.public,context.public_state,context.past)
    return result,resolver


def audit(case):
    from .cut_out_latent_max_fixture import audit as finite
    from .cut_out_terminal_night_max import graph,evaluate
    from .cut_out_latent_max import graph as uniform_graph,evaluate as uniform_evaluate
    from werewolf.exact import Strategy
    if case=='five-feedback':
        source=uniform_graph(5,0,'none');_,engine=uniform_evaluate(source)
        context=next(c for c in engine.projected if c.public.phase=='night' and c.observer is None)
        result,resolver=certify_context(context,source.engine.baseline.rules,Strategy(day='max',night='max',fake_reports='random'))
        assert result.status=='budget_unfinished' and result.reason=='dependency_feedback_limit'
        assert result.selected is None and not resolver.cache
        # Diagnose the conservative dependency graph without expanding profiles.
        from werewolf.wolf_profile_certificate import FixedPublicWolfProfile
        from werewolf.actor_information import wolf_information_groups
        from werewolf.policy_choice import uniform_policy
        from werewolf.candidate_policy import CandidateRules
        from werewolf.calculation_budget import calculation_budget
        groups=wolf_information_groups(context.public_state)
        strategy=Strategy(day='max',night='max',fake_reports='random')
        profile=tuple((info,uniform_policy(tuple(p for p in context.public.alive if not info.initial_roster&(1<<(p-1))))) for info,mass,group in groups)
        rules=CandidateRules(context.public,context.public_state,context.past,source.engine.baseline.rules,strategy)
        rows=[];reads=0
        with calculation_budget(100000,max_seconds=12):
            for info,mass,group in groups:
                scores=[]
                for target in rules.actions[info]:
                    candidate=rules.candidate(profile,info,target)
                    old=FixedPublicWolfProfile(context.public,context.public_state,context.past,source.engine.baseline.rules,strategy,candidate,stop_on_policy_read=True,max_work=100000)
                    value=old.act(context.public,context.public_state,context.past,target,group,None)
                    assert value==F(1,3) and old.policy_reads==0
                    reads+=old.policy_reads;scores.append([target,str(value)])
                rows.append(dict(wolf_mask=info.initial_roster,owned_hypotheses=len(group.hypotheses),scores=scores))
        return dict(case=case,status=result.status,reason=result.reason,proof=result.proof,theoretical_profiles=result.total,
            complete_profiles_evaluated=result.evaluated,profile_work_spent=resolver.profiles_evaluated,numeric_policy_installed=False,
            guarded_common_flow_profile_reads=reads,guarded_candidate_rows=rows,diagnosis='conservative_dependency_classification_not_demonstrated_actual_feedback')
    mediums,initial,kind=json.loads(case)
    result=finite(4,mediums,initial,kind,_terminal_night_max=True)
    source=graph(mediums,initial);forecast,engine=evaluate(source)
    contexts={(c.public,c.public_state,c.past):c for c in engine.projected if c.public.phase=='night' and c.observer is None}
    certificates=[]
    for context in contexts.values():
        certificate,resolver=certify_context(context,source.engine.baseline.rules,source.engine.baseline.strategy)
        assert certificate.status=='unique' and certificate.evaluated==1 and certificate.proof=='policy_independent_scores'
        assert all(v==0 for info,row in certificate.selected.scores for target,v in row)
        for info,policy in certificate.selected.profile:
            assert policy==engine.wolf_policy(context.public,context.public_state,context.past,info.initial_roster,info.attacks)
            assert len(policy)==2 and all(q==F(1,2) for target,q in policy)
        certificates.append(dict(theoretical_profiles=certificate.total,evaluated=certificate.evaluated,proof=certificate.proof,
            profile_work_spent=resolver.profiles_evaluated))
    assert certificates
    result.update(case=case,old_complete_certificates=certificates,old_night_max_exact_policy_equal=True)
    return result


def worker(case):
    from .cut_out_uniform_game_fixture import peak_bytes
    started=time.monotonic()
    def watch():
        while True:
            if time.monotonic()-started>60 or peak_bytes()>1500000000:os._exit(124)
            time.sleep(.1)
    threading.Thread(target=watch,daemon=True).start()
    result=audit(case);result.update(seconds=time.monotonic()-started,peak_working_set_bytes=peak_bytes())
    print(json.dumps(result),flush=True)


def main():
    if len(sys.argv)>1:return worker(sys.argv[1])
    started=time.monotonic();rows=[];logs=[]
    cases=[json.dumps(c) for c in [(0,'none','public'),(1,'random_white','public'),(1,'random_white','role'),(1,'random_white','white')]]+['five-feedback']
    for case in cases:
        run=subprocess.run([sys.executable,'-B','-m',__spec__.name,case],capture_output=True,text=True,timeout=min(60,300-(time.monotonic()-started)))
        if run.returncode:raise RuntimeError(run.stdout+run.stderr)
        rows.append(json.loads(run.stdout));print('passed '+case,flush=True)
    previous=json.loads(Path('benchmarks/player_match_groups/withdraw-standard-results.json').read_text(encoding='utf-8'))
    checks=[(c['kind'],c['target']) for c in previous['checks']]+[('pattern','test_cut_out_seven_minimal.py'),('pattern','test_cut_out_max_game.py'),('pattern','test_cut_out_latent_max.py'),('pattern','test_cut_out_terminal_night_max.py')]
    for kind,target in checks:
        run=subprocess.run([sys.executable,'-B','-m','benchmarks.player_match_groups.withdraw_prefix_diagnostic_fixture',kind,target],capture_output=True,text=True,timeout=min(60,300-(time.monotonic()-started)))
        if run.returncode:raise RuntimeError(run.stdout+run.stderr)
        logs.append(run.stdout+run.stderr)
    Path('.artifacts/terminal-night-max-regressions-final.log').write_text('\n'.join(logs),encoding='utf-8')
    result=dict(cases=rows,checks=checks,existing47_preserved=True,regression_tests=50,overall_seconds=time.monotonic()-started)
    Path('benchmarks/player_match_groups/cut-out-terminal-night-max-results.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(overall_seconds=result['overall_seconds'])),flush=True)

if __name__=='__main__':main()
