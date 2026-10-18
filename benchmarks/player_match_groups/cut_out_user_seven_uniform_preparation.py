"""Preparation-only7/W2 user snapshot. No forecast, max, UI or source capability."""
from dataclasses import dataclass
from types import SimpleNamespace
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
from .constructive_cut_out import ConstructiveCutOutGroups
from .partitioned_match_groups import Observation,UnsupportedPartition
from .cut_out_inherited_groups import InheritedGroups
from .cut_out_six_source_bridge import _ReplayGroups
from werewolf.board_flow import BoardData
from werewolf.board_future import SavedOrigin
from werewolf.exact import Rules,Strategy
from werewolf.information_set_forecast import Pending

INPUT=Path('benchmarks/player_match_groups/actual-seven-max-results.json')
CLAIMS=('seer','seer','medium','latent','latent','latent','latent')
REPORTS=((1,4,'white',1),(2,4,'white',1))


def comparison_game():
    original=json.loads(INPUT.read_text(encoding='utf-8'))['game']
    game=deepcopy(original)
    for key in ('day','night','fake_reports'):game['policy'][key]='random'
    check=deepcopy(game)
    for key in ('day','night','fake_reports'):check['policy'][key]=original['policy'][key]
    assert check==original # Only these three explicit strategy fields changed.
    return original,game


class _BatchRefiner(ConstructiveCutOutGroups):
    def __init__(self):self.baseline=SimpleNamespace(players=7);self.stats=Counter()


@dataclass(frozen=True)
class PreparedSeven:
    data:object
    origin:object
    source:object
    groups:tuple
    events:tuple


def _scope(game):
    if tuple(game.get(k) for k in ('players','wolves','mediums','seers','hunters'))!=(7,2,1,1,0):raise Pending('user_seven_exact_cast_required')
    if tuple(game.get('claims',()))!=CLAIMS or game.get('history'):raise Pending('user_seven_initial_public_snapshot_required')
    if game.get('rules')!={'allow_repeat_guard':True,'allow_self_bite':False,'initial_seer':'random_white'}:raise Pending('user_seven_saved_rules_required')
    strategy=Strategy(**game.get('policy',{}))
    if (strategy.day,strategy.night,strategy.fake_reports)!=('random',)*3:raise Pending('user_seven_explicit_uniform_required_not_initial_max')
    original,_=comparison_game();restored=deepcopy(game)
    for key in ('day','night','fake_reports'):restored['policy'][key]=original['policy'][key]
    if restored!=original:raise Pending('user_seven_strategy_only_input_required')
    if strategy.include_self_bite or strategy.disclosure_for('seer')!='all' or strategy.disclosure_for('medium')!='all':raise Pending('user_seven_saved_configuration_required')
    rows=tuple(sorted((r['reporter'],r['target'],r['color'],r['day']) for r in game.get('seer_inputs',())))
    if rows!=REPORTS or game.get('reports'):raise Pending('user_seven_same_day_white4_reports_required')
    batches=game.get('public_log',{}).get('batches',())
    if len(batches)!=1 or batches[0].get('mode')!='simultaneous' or batches[0].get('slot')!=0:raise Pending('user_seven_initial_simultaneous_batch_required')
    events=batches[0]['events']
    co=tuple(sorted((e['player'],e['role']) for e in events if e['kind']=='co'))
    reports=tuple(sorted((e['player'],e['target'],e['color'],e['day']) for e in events if e['kind']=='seer'))
    if co!=((1,'seer'),(2,'seer'),(3,'medium')) or reports!=REPORTS or len(events)!=5:raise Pending('user_seven_batch_manifest_mismatch')


def prepare(game):
    try:
        _scope(game)
        data=BoardData.from_game(game);origin=SavedOrigin(data,Rules(**game['rules']),Strategy(**game['policy']),False);source=origin()
        if source.public.alive!=tuple(range(1,8)):raise Pending('user_seven_all_alive_required')
        refiner=_BatchRefiner();groups=(tuple(range(1,8)),)
        events=(Observation('co',((1,'seer'),(2,'seer'),(3,'medium'))),Observation('report',REPORTS))
        for event in events:groups=refiner._refine_groups(SimpleNamespace(groups=groups),event)
        return PreparedSeven(data,origin,source,groups,events)
    except (Pending,ValueError,KeyError,TypeError) as error:return UnsupportedPartition(getattr(error,'reason','user_seven_invalid_input:'+str(error)))


def forecast(*args,**kwargs):return UnsupportedPartition('user_seven_preparation_only_full_search_not_enabled')


class _InitialBatchReplay(_ReplayGroups):
    def __init__(self,prepared):super().__init__(prepared.groups,CLAIMS);self.initial_past=prepared.source.past;self.initial_hypotheses=prepared.source.public_state.hypotheses
    def record(self,event,branch,detail):
        if event=='snapshot' and detail==0:
            # The exact initial public batch was proved as a multiset above.
            # Do not destroy its reporter1/2 symmetry by point-fixing rows.
            if len(self.contexts)!=1 or branch.past!=self.initial_past or branch.public_law.hypotheses!=self.initial_hypotheses:
                raise Pending('user_seven_initial_batch_replay_mismatch')
            parent=self.contexts[-1]
            self.contexts.append(InheritedGroups(branch.public,branch.public_law,branch.past,parent.groups,parent,'saved-initial-simultaneous',(),parent.depth+1))
            self.branches.append(branch);return
        return super().record(event,branch,detail)


def probe_first_night(prepared):
    """Synthetic observations, NOT a history supplied by the user."""
    from werewolf.public_log import migrate
    from werewolf.public_log_changes import upgrade
    from werewolf.root_secret_flow import replay_root_secrets
    from werewolf.seer_future_uniform import FuturePending
    game=deepcopy(prepared.data.to_game());game.pop('public_log',None)
    game['revision']=0 # New synthetic timeline, not a borrowed user revision.
    game['history']=[{k:deepcopy(game[k]) for k in ('claims','claim_policy','policy','seer_options','result_disclosure_model')}|{'target':p} for p in (7,6)]
    game['seer_inputs']+= [dict(day=2,reporter=p,target=7,color='white') for p in (1,2)]
    game['reports']=[dict(day=2,reporter=3,target=7,color='white')]
    # This separate synthetic saved timeline uses existing legacy observation
    # semantics. Only the initial batch has an explicit simultaneous proof.
    game['public_log']=upgrade(migrate(game))
    owner=game['public_log']['board_graph'];assert owner['nodes'][owner['current']]['input_revision']==game['revision']==0
    data=BoardData.from_game(game);origin=SavedOrigin(data,Rules(**game['rules']),Strategy(**game['policy']),False)
    expected=origin();collector=_InitialBatchReplay(prepared)
    branch=replay_root_secrets(game,expected.public,origin.rules,origin.strategy,max_work=300000,max_seconds=10,_group_observer=collector)
    if isinstance(branch,FuturePending):return UnsupportedPartition(branch.reason)
    from werewolf.evaluation_branch import ContinuationInputs
    actual=ContinuationInputs(branch.public,branch.public_law,branch.past,branch.physical_law,None,branch.physical)
    if not collector.finished or actual!=expected:return UnsupportedPartition('user_seven_partial_replay_source_mismatch')
    return actual,tuple(collector.contexts),tuple(collector.branches)
