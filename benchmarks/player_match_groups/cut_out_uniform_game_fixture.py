"""Fresh-process small runs; timeout30 each /180 seconds overall, no escalation."""
from datetime import datetime,timezone
from pathlib import Path
from dataclasses import replace
import ctypes,hashlib,json,subprocess,sys,time


def peak_bytes():
    class Counters(ctypes.Structure):
        _fields_=[('cb',ctypes.c_ulong),('PageFaultCount',ctypes.c_ulong)]+[(k,ctypes.c_size_t) for k in ('PeakWorkingSetSize','WorkingSetSize','QuotaPeakPagedPoolUsage','QuotaPagedPoolUsage','QuotaPeakNonPagedPoolUsage','QuotaNonPagedPoolUsage','PagefileUsage','PeakPagefileUsage')]
    counters=Counters();counters.cb=ctypes.sizeof(counters)
    api=ctypes.windll.psapi.GetProcessMemoryInfo
    api.argtypes=[ctypes.c_void_p,ctypes.POINTER(Counters),ctypes.c_ulong]
    if not api(ctypes.c_void_p(-1),ctypes.byref(counters),counters.cb):raise ctypes.WinError()
    return counters.PeakWorkingSetSize


def worker(case):
    sys.path.insert(0,str(Path('tests').resolve()))
    from test_cut_out_uniform_game import audit
    from test_cut_out_model_a import cases
    from test_cut_out_morning import medium_spec
    from .cut_out_uniform_game import OwnView
    from .cut_out_model_a import adapt_model_a
    from .cut_out_morning import CutOutMorning
    from .cut_out_saved_recipes import SavedCutOutGraph
    spec=cases(4 if case=='four-single' else 5)['single'];view=None
    if case=='latent':spec=replace(spec,claims=('latent',)*5,reports=())
    if case=='medium':spec=medium_spec()
    if case=='same-reports':spec=cases()['same_reports']
    if case=='own-seer':
        from werewolf.seer_acquisition import Acquisition
        view=OwnView(1,'seer',(Acquisition(1,1,3,'white'),))
    if case=='own-wolf':view=OwnView(2,'wolf')
    before=peak_bytes();start=time.perf_counter();forecast,grouped,full=audit(spec,view)
    checked=time.perf_counter()-start
    # Optional ALL original-label joint-law restoration is measured separately;
    # scalar solve itself only restores the target values used in the Table.
    start=time.perf_counter();graph=SavedCutOutGraph(adapt_model_a(spec));runner=CutOutMorning(graph.engine)
    generated=runner.evaluate();generation_seconds=time.perf_counter()-start
    start=time.perf_counter();bindings=graph.register_all(runner,generated)
    for binding,_,expected in bindings:assert binding.read().inputs.public_state==expected.law
    restoration_seconds=time.perf_counter()-start
    row=dict(case=case,view='public' if view is None else view.role,village_win=str(forecast.village_win),
        grouped=dict(grouped.costs),official_labelled=dict(full.costs),speed_ratio=full.costs['total_seconds']/grouped.costs['total_seconds'],
        complete_table_action_dawn_win_equal=True,representative_branch_mass_equal=True,origin_count=grouped.costs['saved_origins'],
        checked_seconds=checked,optional_public_generation_seconds=generation_seconds,
        optional_all_label_joint_restore_seconds=restoration_seconds,optional_public_labels=len(bindings),
        process_peak_working_set_bytes=peak_bytes(),process_peak_before_bytes=before,
        memory_scope='one fresh process containing both engines, assertions and optional public restoration; not per-engine attribution')
    print(json.dumps(row))


def main():
    if len(sys.argv)>1:return worker(sys.argv[1])
    started=time.monotonic();rows=[]
    for case in ('four-single','five-single','latent','medium','same-reports','own-seer','own-wolf'):
        remaining=180-(time.monotonic()-started)
        if remaining<=0:raise SystemExit('overall180s budget exhausted')
        run=subprocess.run([sys.executable,'-B','-m',__spec__.name,case],capture_output=True,text=True,timeout=min(30,remaining))
        if run.returncode:print(run.stdout+run.stderr);raise SystemExit(run.returncode)
        rows.append(json.loads(run.stdout));print(case,rows[-1]['grouped']['total_seconds'],rows[-1]['official_labelled']['total_seconds'],flush=True)
    paths=('benchmarks/player_match_groups/cut_out_uniform_game.py','tests/test_cut_out_uniform_game.py','benchmarks/player_match_groups/cut_out_uniform_game_fixture.py')
    record=dict(recorded_utc=datetime.now(timezone.utc).isoformat(),head_before_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        cases=rows,wall_seconds=time.monotonic()-started,timeout_per_process=30,total_budget=180,
        source_sha256={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in paths},
        ordinary_factory_connected=False,heavy_worker=False,unsupported=['max','hunter','7 players','multiple nights','CO policy changes'],
        notes='single run per case; phase counters are wall instrumentation, optional public label restoration separate; inclusive_action_seconds nests recursive calls and is not additive')
    Path('benchmarks/player_match_groups/cut-out-uniform-game-results.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

if __name__=='__main__':main()
