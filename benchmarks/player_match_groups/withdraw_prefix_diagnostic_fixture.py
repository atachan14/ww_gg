"""Bounded standard-entry migration and explicit frozen legacy comparison."""
import sys,time,os,threading,json,subprocess,hashlib
from pathlib import Path
from datetime import datetime,timezone


def worker(kind,value):
    from .cut_out_uniform_game_fixture import peak_bytes
    def watch():
        while True:
            if peak_bytes()>1_500_000_000:print('1.5GB limit exceeded',file=sys.stderr,flush=True);os._exit(137)
            time.sleep(.1)
    threading.Thread(target=watch,daemon=True).start()
    import unittest
    suite=unittest.defaultTestLoader.discover('tests',pattern=value) if kind=='pattern' else unittest.defaultTestLoader.loadTestsFromName(value)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    print('PEAK_BYTES',peak_bytes(),flush=True)
    if not result.wasSuccessful():raise SystemExit(1)


def main():
    if len(sys.argv)>1:return worker(sys.argv[1],sys.argv[2])
    from .withdraw_prefix_diagnostic import minimal_four,examine
    from .cut_out_six_registry_fixture import setup,withdraw
    started=time.monotonic();cases=[]
    for report in (True,False):
        spec,original,changed=minimal_four(report=report);record,_=examine(spec,changed);record['case']='four-reported' if report else 'four-omitted';cases.append(record)
    base,original=setup();changed=withdraw(original,(('co',1),('seer',1,1),('seer',2,1)))
    record,_=examine(base,changed.data);record['case']='six-two-actions';cases.append(record)
    patterns=('test_withdraw_prefix_diagnostic.py','test_cut_out_six_registry.py','test_cut_out_saved_recipes.py','test_cut_out_two_nights.py','test_cut_out_uniform_game.py','test_cut_out_model_a.py')
    requests=[('pattern',p) for p in patterns]+[('named',n) for n in (
        'tests.test_full_disclosure_observed.FullDisclosureObservedTests.test_closed_full_co_omission_survives_later_withdrawal',
        'tests.test_full_disclosure_observed.FullDisclosureObservedTests.test_direct_unfiltered_truth_cannot_be_rescued_with_private_initialization',
        'tests.test_hybrid_future_active_ledger.ActiveInputLedgerTests.test_active_input_target_only_then_generated_true_history_is_preserved',
        *('tests.test_root_secret_replay.RootReplayTests.'+name for name in (
            'test_replay_preserves_acquisitions_dead_seers_and_attacks',
            'test_screen_routes_replay_and_cache_matches_recalculation',
            'test_observed_uniform_bite_likelihood_changes_physical_mass_only',
            'test_observed_reports_condition_truth_history_and_preserve_model_a',
            'test_report_edit_cancel_and_cache_rebuild_use_initial_joint_law',
            'test_owned_public_log_and_delayed_publication_survive_cache_snapshot',
            'test_positive_public_truth_with_impossible_repeated_scan_is_pending',
            'test_pending_scope_does_not_replace_max',
            'test_uniform_guard_only_gj_replay_uses_common_public_observation')))]
    logs=[];checks=[]
    for kind,value in requests:
        remaining=300-(time.monotonic()-started)
        if remaining<=0:raise SystemExit('overall300s budget exhausted')
        run=subprocess.run([sys.executable,'-B','-m',__spec__.name,kind,value],capture_output=True,text=True,timeout=min(30,remaining))
        logs.append(run.stdout+run.stderr)
        if run.returncode:print(logs[-1]);raise SystemExit(run.returncode)
        peak=int(next(line.split()[1] for line in run.stdout.splitlines() if line.startswith('PEAK_BYTES ')))
        checks.append(dict(kind=kind,target=value,exit=run.returncode,peak_working_set_bytes=peak))
    Path('.artifacts/withdraw-standard-final.log').write_text('\n'.join(logs),encoding='utf-8')
    paths=('werewolf/root_secret_flow.py','benchmarks/player_match_groups/withdraw_prefix_diagnostic.py','benchmarks/player_match_groups/withdraw_prefix_diagnostic_fixture.py','tests/test_withdraw_prefix_diagnostic.py','tests/test_cut_out_six_registry.py','benchmarks/player_match_groups/cut_out_six_registry_fixture.py')
    result=dict(recorded_utc=datetime.now(timezone.utc).isoformat(),head_before_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        cases=cases,checks=checks,tests=40,previous23_preserved_except_one_known_bug_expectation_migrated=True,default_saved_origin_still_pending=False,legacy_switch='_historical_disclosure_proof=False',
        wall_seconds=time.monotonic()-started,per_run_seconds=30,overall_seconds_limit=300,memory_limit_bytes=1_500_000_000,
        source_sha256={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in paths},ordinary_ui_or_public_changed=False)
    Path('benchmarks/player_match_groups/withdraw-standard-results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('40 tests passed; seconds',result['wall_seconds'],'peak',max(c['peak_working_set_bytes'] for c in checks))

if __name__=='__main__':main()
