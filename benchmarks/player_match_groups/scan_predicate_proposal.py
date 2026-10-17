"""REVIEW-ONLY scan predicate alignment. Never selected by app or factories."""
import inspect,json
from pathlib import Path
from .extension_cases import fixture,prepare_game
from werewolf.seer_view_forecast import seer_forecast


def candidate():
    source=inspect.getsource(seer_forecast)
    old='len(state.rosters) < day or\n                        any('
    new='len(state.rosters) < day or\n                        player not in state.rosters[day-1] or target not in state.rosters[day-1] or\n                        any('
    assert source.count(old)==1
    namespace=dict(seer_forecast.__globals__)
    exec(compile(source.replace(old,new),'<review-only-root-scan-predicate>','exec'),namespace)
    return namespace['seer_forecast']


def run():
    proposal=candidate();rows=[]
    for mediums in(0,1):
        _,game=fixture(mediums=mediums,day='max',night='max',fake='max')
        _,_,b,s,past,rules,strategy,_=prepare_game(game)
        h=next(h for h in s.hypotheses if h.roles[2]&1);own=tuple(a for a in h.acquisitions if a.player==1)
        old=seer_forecast(b,1,own,rules,strategy,scan_state=s,past=past,max_seconds=10)
        changed=proposal(b,1,own,rules,strategy,scan_state=s,past=past,max_seconds=10)
        rows.append(dict(mediums=mediums,old=repr(old),proposal=[(p,str(v))for p,v in changed]if isinstance(changed,tuple)else repr(changed)))
    from tests.test_seer_view_forecast import fixture as control
    from werewolf.exact import Rules,Strategy
    b,s=control();rules=Rules(initial_seer='none');strategy=Strategy('max','random')
    old=seer_forecast(b,1,(),rules,strategy,scan_state=s,max_seconds=10)
    changed=proposal(b,1,(),rules,strategy,scan_state=s,max_seconds=10)
    assert old==changed
    return dict(review_only=True,app_unchanged=True,root_existing_semantics='Do not force an acquisition when actor or target is absent from the acquisition roster',rows=rows,supported_existing_control_equal=True,decision='Align fixed-CO observer with existing root semantics, or intentionally preserve strict executed-scan conditioning? No production change applied.')
if __name__=='__main__':
    result=run();Path('benchmarks/player_match_groups/scan-predicate-proposal-results.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result),flush=True)
