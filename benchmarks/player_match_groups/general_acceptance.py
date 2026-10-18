"""Corrected-rule local integration; finite sequential comparisons."""
import copy,json,time
from pathlib import Path
from .extension_cases import fixture,publish,game_of,prepare_game
from .checkpoint_audit import encode,digest
from werewolf.board_flow import BoardData
from werewolf.exact import Strategy
from werewolf.model_a_public import evaluate_public_game,clear_public_cache
from werewolf.local_reuse import reuse_scope
from werewolf.seer_future_uniform import FuturePending
from werewolf.calculation_budget import calculation_budget


def evaluate(game,mode):
    source=copy.deepcopy(game);data=BoardData.from_game(game);roles=data.roles();clear_public_cache()
    started=time.perf_counter()
    with reuse_scope(mode):r=evaluate_public_game(game,roles.board,roles.rules,Strategy(**game['policy']),max_seconds=15)
    assert not isinstance(r,FuturePending),r
    assert source==game
    return encode(r),time.perf_counter()-started


def run():
    rows=[];c,g=fixture()
    def compare(label,game=None):
        game=game or game_of(c);a,ta=evaluate(game,False);b,tb=evaluate(game,True)
        assert a==b,label
        rows.append(dict(case=label,equal=True,original_seconds=ta,local_seconds=tb,result=a,input_digest=digest(game)))
    compare('initial-uniform-five');publish(c,4);compare('correct-white-target')
    publish(c,4,withdraw=True);compare('withdraw-root');publish(c,3);compare('restore')
    g=game_of(c);assert c.post('/advance',data={'revision':g['revision'],'target':1,'day':'random','night':'random'}).status_code==303
    compare('owner-death-root');g=game_of(c);assert c.post('/back',data={'revision':g['revision']}).status_code==303;compare('back')
    import tests.test_guard_no_repeat as guard
    import tests.test_root_guard_max as maxim
    for repeat in(False,True):
        compare('two-GJ-repeat-'+str(repeat),guard.NoRepeatGuardTests().fixture(repeat=repeat))
        compare('root-hunter-max-repeat-'+str(repeat),maxim.RootGuardMaxTests().game(repeat))
    from .general_reuse import GeneralReuseForecast
    from werewolf.information_set_forecast import InformationSetForecast
    _,_,b,s,past,rules,strategy,_=prepare_game(fixture()[1])
    engine=GeneralReuseForecast(rules,strategy,future_reuse=True,compact_keys=True,fast_parts=True)
    with calculation_budget(1000000,max_seconds=15):
        public=engine.scalar(b,s,past);own=engine.evaluate(b,s,past,mask=s.hypotheses[0].roles[0]);reference=InformationSetForecast(rules,strategy).evaluate(b,s,past,mask=s.hypotheses[0].roles[0])
        assert own==reference and engine.scalar(b,s,past)==public
        assert engine.retirement_proof_hits==0
    out=dict(rule='corpse scans; owner-only pre-acquisition exemption',reference='same corrected semantics; local mode OFF, original factories; not pre-fix engine',cases=rows,public_private_public_stable=True,private_values_match=True,private_new_retirement_proof_disabled=True,private_key_stats=engine.reuse_stats,all_equal=True)
    Path('benchmarks/player_match_groups/general-integration-results.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({k:v for k,v in out.items()if k not in('cases','private_key_stats')}),flush=True)
    print(json.dumps([{k:r[k]for k in('case','original_seconds','local_seconds')}for r in rows]),flush=True)
    return out
if __name__=='__main__':run()
