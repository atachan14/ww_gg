"""Public-owned acquisition inputs and complete prior cache, never viewer data."""
from functools import lru_cache
import json
from .public_observed_prior import prepare_game
from .seer_acquisition import from_board
from .seer_future_uniform import TrueScanState, FuturePending
from .phase_updates import acquisition_rosters


def public_history_key(game):
    log=game.get('public_log',{})
    public={
        'players':game.get('players'),
        'wolves':game.get('wolves'),'mediums':game.get('mediums'),'seers':game.get('seers'),
        'hunters':game.get('hunters'),'model':game.get('model'),
        'history':[{k:v for k,v in step.items() if k in ('target','policy','claims','claim_policy','observation','deaths','reports','seer_options','result_disclosure_model')}
                   for step in game.get('history',())],
        'claims':game.get('claims',()),'claim_policy':game.get('claim_policy',{}),'policy':game.get('policy',{}),
        'seer_mode':game.get('seer_mode'),'result_disclosure_model':game.get('result_disclosure_model'),
        'reports':game.get('reports',()),
        'rules':{k:v for k,v in game.get('rules',{}).items() if k in ('initial_seer','allow_self_bite','allow_repeat_guard')},
        'seer_options':{'initial_rule':game.get('seer_options',{}).get('initial_rule')},
        'seer_inputs':[{k:r[k] for k in ('day','reporter','target','color')} for r in game.get('seer_inputs',())],
        'public_log':{'version':log.get('version'),
            **{k:log.get(k,[]) for k in ('base_claims','base_seer','base_medium','batches')},
            'report_publications':
            {k:{field:value for field,value in v.items() if field in ('slot','published_day')}
             for k,v in log.get('report_publications',{}).items()}}
    }
    return json.dumps(public,sort_keys=True,separators=(',',':'),allow_nan=False)


class PriorPending(Exception):
    def __init__(self,reason):self.reason=reason


@lru_cache(maxsize=16)
def _complete_prior(history_key,board,rules,track_live_seers,max_work):
    if track_live_seers:
        result=prepare_game(json.loads(history_key),board,max_work=max_work)
        if isinstance(result,FuturePending):raise PriorPending(result.reason)
        return result
    return (TrueScanState(from_board(board),acquisition_rosters(board),rules.initial_seer,
                          tracked=(),observed_prefix=board.day),())


def prepare_public_prior(game,board,rules,*,track_live_seers=True,max_work=250000):
    try:return _complete_prior(public_history_key(game),board,rules,track_live_seers,max_work)
    except PriorPending as error:return FuturePending(error.reason)


def clear_public_prior_cache():_complete_prior.cache_clear()
def public_prior_cache_info():return _complete_prior.cache_info()
