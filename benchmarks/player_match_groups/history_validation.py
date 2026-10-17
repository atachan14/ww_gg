"""Finite actual-API correction/withdrawal/death and personal-switch controls."""
import json,copy,time
from pathlib import Path
from unittest.mock import patch
from .extension_cases import fixture,publish,game_of
from .retirement_proof import RetirementProofForecast
from .checkpoint_audit import encode,digest
from werewolf.board_flow import BoardData
from werewolf.board_roles import prepare_evaluation
from werewolf.exact import Strategy,Values
from werewolf.model_a_public import evaluate_prepared_public
from werewolf.player_view import build_public_view,ViewScope,ResultFrame
from werewolf.seer_future_uniform import FuturePending
from werewolf.information_set_forecast import InformationSetForecast
from werewolf.calculation_budget import calculation_budget


def evaluate(game,enabled):
    before=copy.deepcopy(game);data=BoardData.from_game(game);roles=data.roles();b=roles.board;strategy=Strategy(**game['policy'])
    prepared=prepare_evaluation(game,b,roles.rules,strategy,max_work=500000,max_seconds=10)
    engines=[]
    def factory(*args,**kwargs):
        e=RetirementProofForecast(*args,retirement_proof=enabled,future_reuse=enabled,physical_reuse=enabled,retired_reuse=enabled,compact_keys=enabled,fast_parts=enabled,**kwargs);engines.append(e);return e
    with patch('werewolf.model_a_public.InformationSetForecast',factory):
        result=evaluate_prepared_public(prepared,b,roles.rules,strategy,max_work=500000,max_seconds=10)
    assert not isinstance(result,FuturePending),result
    view=build_public_view(data,roles,b,ResultFrame(ViewScope.public(data),'complete'),state=game,event_history=b.history,alive=b.alive,action_values={p:Values(v,1-v)for p,v in result.action_values},by_dawn_values=dict(result.by_dawn_values))
    assert game==before
    return encode(dict(kind=prepared[0],input_signature=digest(prepared),value=result.village_win,table=[p.to_legacy_row()for p in view.players],proof_hits=sum(e.retirement_proof_hits for e in engines),engines=len(engines)))


def run():
    c,_=fixture();rows=[]
    def compare(label):
        game=game_of(c);old=evaluate(game,False);new=evaluate(game,True)
        assert (old['value'],old['table'])==(new['value'],new['table']),label
        rows.append(dict(stage=label,old=old,new=new,equal=True));return new
    initial=compare('initial')
    publish(c,4);corrected=compare('correct-white-target-4')
    assert initial['input_signature']!=corrected['input_signature']
    publish(c,4,withdraw=True);compare('withdraw-all-CO-root-fallback')
    publish(c,3);restored=compare('restore-white-target-3')
    assert initial['table']==restored['table']
    g=game_of(c);r=c.post('/advance',data={'revision':g['revision'],'target':'1','day':'random','night':'random'});assert r.status_code==303
    compare('death-P1-root-replay-fallback')
    g=game_of(c);assert c.post('/back',data={'revision':g['revision']}).status_code==303
    back=compare('back-to-initial-Board')
    assert initial['table']==back['table']
    # Same solver switches public -> own wolf -> public; compare the private
    # result with an original engine and ensure the public result/cache survives.
    from .extension_cases import prepare_game
    _,_,b,s,past,rules,strategy,_=prepare_game(game_of(c))
    e=RetirementProofForecast(rules,strategy,retirement_proof=True,future_reuse=True,physical_reuse=True,retired_reuse=True,compact_keys=True,fast_parts=True)
    with calculation_budget(1000000,max_seconds=10):
        public=e.scalar(b,s,past);hits=e.retirement_proof_hits
        own=e.evaluate(b,s,past,mask=s.hypotheses[0].roles[0])
        assert e.retirement_proof_hits==hits
        expected=InformationSetForecast(rules,strategy).evaluate(b,s,past,mask=s.hypotheses[0].roles[0])
        assert own==expected and e.scalar(b,s,past)==public and e.reuse_public_entry
    return dict(stages=rows,private_value=str(own),private_matches_original=True,public_private_public_stable=True)

if __name__=='__main__':
    result=run();Path('benchmarks/player_match_groups/retirement-history-results.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items()if k!='stages'}),flush=True)
