"""Closed five-player no-read proof, full labels, and genuine read control."""
import json,time,sys,subprocess,os,threading
from pathlib import Path
from fractions import Fraction as F


def read_control():
    from dataclasses import replace
    from werewolf.exact import initial_board,Rules,Strategy
    from werewolf.root_secret_flow import prepare_root_secrets
    from .cut_out_no_read_night_max import guarded_profile_probe,certify_night
    rules=Rules(initial_seer='none');strategy=Strategy(day='max',night='max',fake_reports='random')
    seed=initial_board(3,1,0,0,1,experimental_cast=True)
    root=prepare_root_secrets(seed,rules);b=replace(seed,phase='night')
    structural,_=certify_night(b,root.public_law,(),rules,strategy)
    assert structural.selected is None and structural.reason=='five_player_no_read_structure_unproved'
    guarded,diagnostics=guarded_profile_probe(b,root.public_law,(),rules,strategy,legacy_reference=True)
    assert guarded.selected is None and guarded.reason=='fixed_public_profile_read' and diagnostics['profile_reads']==1
    return dict(structural_refusal=structural.reason,guarded_refusal=guarded.reason,diagnostics=diagnostics,numeric_certificate=False)


def audit(kind='public'):
    if kind=='read-control':return read_control()
    from .cut_out_latent_max_fixture import audit as complete
    from .cut_out_no_read_night_max import graph,evaluate
    from .cut_out_uniform_game import OwnView
    result=complete(5,0,'none',kind,_no_read_night_max=True)
    source=graph();forecast,engine=evaluate(source,view=OwnView(1,'seer') if kind=='role' else None)
    reference,full=evaluate(source,view=OwnView(1,'seer') if kind=='role' else None,official_reference=True)
    assert forecast==reference and engine.no_read_certificates
    probes=[]
    for key,certificate in engine.no_read_certificates.items():
        rules,strategy,b,s,past=key
        search,diagnostics=engine.no_read_diagnostics[key]
        assert search.proof=='guarded_no_policy_reads' and search.evaluated==1
        assert diagnostics['profile_reads']==0 and diagnostics['complete_candidate_scores']==12
        for info,row in certificate.scores:
            assert all(v==F(1,3) for target,v in row)
        for info,policy in certificate.profile:
            assert all(q==F(1,3) for target,q in policy)
            assert policy==full.wolf_policy(b,s,past,info.initial_roster,info.attacks)
        probes.append(diagnostics)
    result.update(connected_complete_proofs=probes,certified_policy_matches_existing_exact=True)
    return result


def worker(case):
    from .cut_out_uniform_game_fixture import peak_bytes
    started=time.monotonic()
    def watch():
        while True:
            if time.monotonic()-started>60 or peak_bytes()>1500000000:os._exit(124)
            time.sleep(.1)
    threading.Thread(target=watch,daemon=True).start()
    result=audit(case);result.update(case=case,worker_seconds=time.monotonic()-started,peak_working_set_bytes=peak_bytes())
    print(json.dumps(result),flush=True)


def main():
    if len(sys.argv)>1:return worker(sys.argv[1])
    started=time.monotonic();rows=[];logs=[]
    for case in ('public','role','read-control'):
        run=subprocess.run([sys.executable,'-B','-m',__spec__.name,case],capture_output=True,text=True,timeout=min(60,300-(time.monotonic()-started)))
        if run.returncode:raise RuntimeError(run.stdout+run.stderr)
        rows.append(json.loads(run.stdout));print('passed '+case,flush=True)
    previous=json.loads(Path('benchmarks/player_match_groups/withdraw-standard-results.json').read_text(encoding='utf-8'))
    checks=[(c['kind'],c['target']) for c in previous['checks']]+[('pattern','test_cut_out_seven_minimal.py'),('pattern','test_cut_out_max_game.py'),('pattern','test_cut_out_latent_max.py'),('pattern','test_cut_out_terminal_night_max.py'),('pattern','test_cut_out_no_read_night_max.py')]
    for kind,target in checks:
        run=subprocess.run([sys.executable,'-B','-m','benchmarks.player_match_groups.withdraw_prefix_diagnostic_fixture',kind,target],capture_output=True,text=True,timeout=min(60,300-(time.monotonic()-started)))
        if run.returncode:raise RuntimeError(run.stdout+run.stderr)
        logs.append(run.stdout+run.stderr)
    Path('.artifacts/no-read-night-max-regressions-final.log').write_text('\n'.join(logs),encoding='utf-8')
    result=dict(cases=rows,checks=checks,existing50_preserved=True,regression_tests=53,timing_interpretation='budget verification only; not an uncontended speed comparison',overall_seconds=time.monotonic()-started)
    Path('benchmarks/player_match_groups/cut-out-no-read-night-max-results.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(overall_seconds=result['overall_seconds'])),flush=True)

if __name__=='__main__':main()
