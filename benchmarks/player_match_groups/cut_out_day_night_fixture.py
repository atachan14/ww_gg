"""Finite small two-transition evidence; no heavy/performance benchmark."""
from dataclasses import asdict
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from .cut_out_model_a import adapt_model_a
from .cut_out_day_night import CutOutDayNight


def main():
    command=[sys.executable,'-B','-m','unittest','discover','-s','tests','-p','test_cut_out_day_night.py','-v']
    run=subprocess.run(command,capture_output=True,text=True,timeout=20)
    log=Path('.artifacts/cut-out-day-night-final.log');log.parent.mkdir(exist_ok=True)
    log.write_text(run.stdout+run.stderr,encoding='utf-8')
    if run.returncode:
        print(run.stdout+run.stderr);raise SystemExit(run.returncode)
    sys.path.insert(0,str(Path('tests').resolve()))
    from test_cut_out_model_a import cases
    rows=[]
    for n,name in ((4,'witness'),(5,'witness'),(5,'same_reports'),(5,'single')):
        engine=adapt_model_a(cases(n)[name])
        grouped=CutOutDayNight(engine);g=grouped.evaluate()
        labelled=CutOutDayNight(engine);f=labelled.evaluate(representatives=False)
        gs=grouped.stats.copy();fs=labelled.stats.copy()
        assert g.terminal_mass==f.terminal_mass
        for target in engine.start().alive:
            a=grouped.labelled_paths(g,target);b=labelled.labelled_paths(f,target)
            assert [(t,q,c.board,c.law) for t,q,c in a]==[(t,q,c.board,c.law) for t,q,c in b]
        rows.append(dict(players=n,case=name,initial_adapter_stats=dict(engine.stats),
            grouped_stats=dict(gs),full_labelled_stats=dict(fs),
            optional_day_label_transport=dict(grouped.stats-gs),
            terminal_mass=[dict(winner=w,mass=str(q)) for w,q in g.terminal_mass],
            day_classes=[dict(targets=c.targets,multiplicity=len(c.targets),selection_mass=str(c.selection_mass)) for c in g.classes],
            night_choice_classes=[dict(**asdict(c),multiplicity=c.multiplicity) for c in g.night_choice_classes],
            complete_labelled_paths_equal=True))
    paths=('benchmarks/player_match_groups/cut_out_day_night.py','tests/test_cut_out_day_night.py')
    result=dict(recorded_utc=datetime.now(timezone.utc).isoformat(),
        head_before_evidence_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        sources_sha256={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in paths},
        tests=4,test_seconds_limit=20,test_log=str(log),cases=rows,
        reference='exact.action_outcomes + project_private + wolf_information_groups + wolf_policy + physical_actor_outcomes; full labels, no sharing',
        scope='4/5 initial public uniform W1 H0, execution + one night, stop before next publication',
        initial_prior_reallocated=False,exchange_audit_in_runtime=False,full_future_solver=False,
        ordinary_route_changed=False,performance_claim=False)
    out=Path('benchmarks/player_match_groups/cut-out-day-night-results.json')
    out.write_text(json.dumps(result,indent=2,default=str)+'\n',encoding='utf-8')
    print(json.dumps(dict(tests=4,cases=len(rows),complete_labelled_paths_equal=True,result=str(out))))


if __name__=='__main__':main()