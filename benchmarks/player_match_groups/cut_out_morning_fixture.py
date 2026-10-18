"""Finite next-morning evidence, common-kernel/publication boundary only."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from .cut_out_model_a import adapt_model_a
from .cut_out_morning import CutOutMorning


def main():
    tests=[]
    for pattern in ('test_cut_out_morning.py','test_cut_out_day_night.py'):
        command=[sys.executable,'-B','-m','unittest','discover','-s','tests','-p',pattern,'-v']
        run=subprocess.run(command,capture_output=True,text=True,timeout=20)
        log=Path('.artifacts')/(pattern.removesuffix('.py')+'-morning-final.log')
        log.parent.mkdir(exist_ok=True);log.write_text(run.stdout+run.stderr,encoding='utf-8')
        if run.returncode:
            print(run.stdout+run.stderr);raise SystemExit(run.returncode)
        tests.append(dict(pattern=pattern,count=4,exit=run.returncode,log=str(log),seconds_limit=20))
    sys.path.insert(0,str(Path('tests').resolve()))
    from test_cut_out_model_a import cases
    from test_cut_out_morning import medium_spec
    rows=[]
    for name,spec in (('terminal-four',cases(4)['same_reports']),('single-seer',cases()['single']),('two-seer-co',cases()['same_reports']),('true-fake-medium',medium_spec())):
        engine=adapt_model_a(spec);grouped=CutOutMorning(engine);g=grouped.evaluate()
        full=CutOutMorning(engine);f=full.evaluate(representatives=False)
        assert g.terminal_mass==f.terminal_mass
        gs=dict(grouped.stats);physical_stats=grouped.upstream.stats.copy()
        for target in engine.start().alive:
            a=grouped.labelled_paths(g,target);b=full.labelled_paths(f,target)
            assert [(t,q,c.board,c.law,c.past) for t,q,c in a]==[(t,q,c.board,c.law,c.past) for t,q,c in b]
        rows.append(dict(case=name,players=spec.players,grouped_morning_stats=gs,full_labelled_morning_stats=dict(full.stats),
            day_night_stats=dict(physical_stats),optional_label_transport=dict(grouped.upstream.stats-physical_stats),
            grouped_leaves=sum(len(b.paths) for a in g.classes for b in a.branches),
            full_labelled_leaves=sum(len(b.paths) for a in f.classes for b in a.branches),
            terminal_mass=[dict(winner=w,mass=str(q)) for w,q in g.terminal_mass],
            complete_labelled_board_law_past_mass_equal=True))
    paths=('benchmarks/player_match_groups/cut_out_morning.py','benchmarks/player_match_groups/cut_out_day_night.py','tests/test_cut_out_morning.py')
    result=dict(recorded_utc=datetime.now(timezone.utc).isoformat(),
        head_before_evidence_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        sources_sha256={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in paths},tests=tests,cases=rows,
        full_record_mode='existing retire_uninformative_scans=False, uniform policies unchanged',
        common_boundary='morning/report_flow/publications -> observer_report_weights -> representative GeneratedBoard.roles readback',
        limitations='KernelOrigin for representative morning recipes; transported-label recipe registration and SavedOrigin chain not connected',
        preserve_acquired_dead_owner_results=True,dead_reporter_new_publication=False,corpse_target_result_published=True,
        ordinary_route_changed=False,full_future_solver=False,performance_claim=False)
    out=Path('benchmarks/player_match_groups/cut-out-morning-results.json')
    out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(tests=8,cases=len(rows),all_labels_equal=True,result=str(out))))


if __name__=='__main__':main()