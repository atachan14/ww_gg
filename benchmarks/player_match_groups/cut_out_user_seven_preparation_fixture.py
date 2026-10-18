"""Small prior/batch/prefix probe. Solve/act and old matching fail if called."""
import sys,time,json,subprocess,threading,os
from pathlib import Path
from dataclasses import replace
from copy import deepcopy
from unittest.mock import patch
from fractions import Fraction as F
from .cut_out_candidate_context_fixture import zero_legacy
from .cut_out_user_seven_uniform_preparation import comparison_game,prepare,probe_first_night,forecast
from .cut_out_day_night import moved_law
from .partitioned_match_groups import UnsupportedPartition


def audit():
    from werewolf.information_set_forecast import InformationSetForecast
    from werewolf.actor_information import wolf_information_groups
    from .cut_out_six_source_bridge import issue
    original,game=comparison_game();stack,mocks=zero_legacy()
    with stack,patch.object(InformationSetForecast,'solve',side_effect=AssertionError('full solve not authorized')) as solve,patch.object(InformationSetForecast,'act',side_effect=AssertionError('full action value not authorized')) as act:
        initial=prepare(game);assert not isinstance(initial,UnsupportedPartition),initial
        assert initial.groups==((1,2),(3,),(4,),(5,6,7))
        assert len(initial.source.public.worlds)==len(initial.source.public_state.hypotheses)==6
        assert initial.source.public.role_probability(3,'medium')==1
        assert initial.source.public.role_probability(4,'villager')==1
        assert initial.source.public.role_probability(1,'seer')==initial.source.public.role_probability(2,'seer')==F(1,2)
        assert initial.source.public.wolf_probability(1)==initial.source.public.wolf_probability(2)==F(1,2)
        infos=wolf_information_groups(initial.source.public_state)
        assert len(infos)==6 and all(info.initial_roster.bit_count()==2 for info,mass,law in infos)
        probed=probe_first_night(initial);assert not isinstance(probed,UnsupportedPartition),probed
        current,contexts,branches=probed
        assert solve.call_count==act.call_count==0 and all(m.call_count==0 for m in mocks)
    swaps=0
    for group in initial.groups:
        for p in group[1:]:
            assert moved_law(initial.source.public_state,group[0],p,7)==initial.source.public_state
            assert moved_law(initial.source.private,group[0],p,7)==initial.source.private
            swaps+=1
    for c,b in zip(contexts,branches):
        for group in c.groups:
            for p in group[1:]:
                assert moved_law(b.public_law,group[0],p,7)==b.public_law
                assert moved_law(b.physical_law,group[0],p,7)==b.physical_law
                swaps+=1
    nights=[(c,b) for c,b in zip(contexts,branches) if c.event=='saved-observed-action' and b.public.day==2]
    assert len(nights)==1
    night_context,night=nights[0]
    assert (1,2) in night_context.groups and night.public_law!=night.physical_law
    assert night.public.role_probability(7,'wolf')==F(1,2)
    actual_dead_wolf=sum((h.mass for h in night.physical_law.hypotheses if h.roles[0]&(1<<6)),F())
    assert actual_dead_wolf==F(4,9)
    assert (1,2) not in contexts[-1].groups # Conservative unknown new report-batch stabilizer.
    assert current.public.day==2 and len(current.public.worlds)==2
    assert isinstance(prepare(original),UnsupportedPartition)
    assert isinstance(forecast(initial),UnsupportedPartition)
    assert isinstance(issue(initial),UnsupportedPartition) # Never masquerade as a6-player issued witness.
    bad=deepcopy(game);bad['wolves']=1;assert isinstance(prepare(bad),UnsupportedPartition)
    bad=deepcopy(game);bad['claim_policy']['villager']='none';assert isinstance(prepare(bad),UnsupportedPartition)
    return dict(scope='7/W2 user public snapshot; strategy-only uniform comparison; preparation only',
        original_strategy=original['policy'],comparison_strategy=game['policy'],strategy_only_fields_changed=['policy.day','policy.night','policy.fake_reports'],
        initial_worlds=6,initial_hypotheses=6,initial_groups=initial.groups,initial_tracked=initial.source.public_state.tracked,
        wolf_owned_information_sets=6,wolf_initial_roster_bits=2,initial_and_prefix_joint_swaps=swaps,
        synthetic_prefix=dict(execution=7,bite=6,new_seer_reports='P1/P2 Day2 white7',medium_report='P3 Day2 white7',
            saved_replay_contexts=len(contexts),post_night_before_reports_groups=night_context.groups,
            Q_dead_wolf7='1/2',P_dead_wolf7=str(actual_dead_wolf),Q_P_kept_separate=True,
            final_worlds=len(current.public.worlds),final_hypotheses=len(current.public_state.hypotheses),final_tracked=current.public_state.tracked,
            final_conservative_groups=contexts[-1].groups),
        canonical_calls=0,CandidateRules_calls=0,solve_calls=0,act_value_calls=0,
        full_forecast_enabled=False,seven_source_capability_issued=False,initial_max_supported=False,
        missing=['explicit7/W2 cast descriptor instead of W1-fixed adapter','typed7 source issuer owner/revision scope','new simultaneous snapshot batch witness if reporter symmetry should survive publication','initial trackedCO metadata vs replay full-tracking metadata must not be replaced'],
        ordinary_UI_changed=False,speed_measurement_executed=False)


def main():
    from .cut_out_uniform_game_fixture import peak_bytes
    start=time.monotonic()
    def watch():
        while True:
            if time.monotonic()-start>30 or peak_bytes()>1500000000:os._exit(124)
            time.sleep(.1)
    threading.Thread(target=watch,daemon=True).start()
    result=audit();result.update(worker_seconds=time.monotonic()-start,peak_working_set_bytes=peak_bytes())
    Path('benchmarks/player_match_groups/cut-out-user-seven-preparation-results.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result),flush=True)

if __name__=='__main__':main()
