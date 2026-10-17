"""Independent count-law reference for the completed uniform/no-ability fixture.

Acceptance-only, never a forecast fallback or application dispatch. Reports are
normalized chance observations, and fixed random actions cannot depend on them.
Thus summing observations leaves only n,w,phase for subsequent terminal payoff.
"""
import json
from functools import lru_cache
from fractions import Fraction as F
from pathlib import Path
from . import checkpoint_audit as base
from werewolf.exact import Values
from werewolf.player_view import build_public_view,ResultFrame
from werewolf.by_dawn import HorizonValues


@lru_cache(None)
def count_value(n,w,phase):
    if not w:return F(1)
    if w*2>=n:return F(0)
    if phase=='night':return count_value(n-1,w,'day')
    return F(w,n)*count_value(n-1,w-1,'night')+F(n-w,n)*count_value(n-1,w,'night')


def root_value(board,target):
    assert board.phase=='day' and target in board.alive
    return sum((q*count_value(len(board.alive)-1,(wolf&board.alive_mask).bit_count()-bool(wolf&(1<<(target-1))),'night')for wolf,q in board.belief),F())


def validate():
    game=base.read(Path('benchmarks/player_match_groups/checkpoint-seven-input.json'))
    data,roles,b,s,past,rules,strategy,view=base.prepared_game(game)
    # Deliberately narrow numerical reference, not a new production model.
    assert b.player_count==7 and len(b.alive)==7 and b.day==1 and b.phase=='day'
    assert not b.initial_medium_count and not b.initial_hunter_count
    assert b.initial_seer_count==1 and b.claims==('seer','seer')+('latent',)*5
    assert strategy.day==strategy.night==strategy.fake_reports=='random'
    assert not strategy.include_self_bite and not rules.allow_self_bite
    assert tuple(strategy.seer_position)==('unvisited','uniform')
    assert tuple(strategy.fake_seer_policy)==('noncontradictory','uniform')
    assert all((h.roles[2]&3).bit_count()==1 for h in s.hypotheses)
    assert len(past)==2 and all(r.acquired_day==r.published_day==1 and r.target==3 and r.color=='white'for r in past)
    values={t:root_value(b,t)for t in b.alive}
    # From n=7,w=2 a vote and the next non-self bite cannot reach 0 wolves or
    # parity. This horizon metric is independently zero for every root target.
    assert set(b.wolf_count_distribution)=={2}
    dawn={t:HorizonValues(F(0),F(0))for t in b.alive}
    table=build_public_view(data,roles,b,ResultFrame(view.scope,'complete'),state=game,event_history=b.history,alive=b.alive,action_values={t:Values(v,1-v)for t,v in values.items()},by_dawn_values=dawn)
    trial=base.read(Path('benchmarks/player_match_groups/retirement-proof-seven-attempt.json'))['trial']
    result=base.encode(dict(value=sum(values.values(),F())/len(values),table=[p.to_legacy_row()for p in table.players]))
    assert (result['value'],result['table'])==(trial['value'],trial['table'])
    return dict(reference='independent fixed-random count recurrence, complete root wolf joint; shared presentation adapter only',scope='exact guarded seven-player fixture; no max/medium/hunter dispatch',all_table_rows_equal=True,terminal_equal=True,value=result['value'],actions={str(t):str(v)for t,v in values.items()},table=result['table'],original_unmodified_engine_full_run=False)

if __name__=='__main__':
    result=validate();Path('benchmarks/player_match_groups/retirement-proof-count-reference.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items()if k!='table'}),flush=True)
