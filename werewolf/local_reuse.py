"""Local request-scoped opt-in. No saved evidence/config mutation."""
from contextvars import ContextVar
from contextlib import contextmanager
_mode=ContextVar('wwgg_local_exact_reuse',default=None)

def enabled():
    value=_mode.get()
    if value is not None:return value
    try:from flask import has_request_context,current_app
    except ImportError:return False
    return bool(has_request_context() and current_app.config.get('EXACT_FUTURE_REUSE_PREVIEW',False))
def set_mode(value):return _mode.set(bool(value))
def reset_mode(token):_mode.reset(token)
@contextmanager
def reuse_scope(value):
    token=set_mode(value)
    try:yield
    finally:reset_mode(token)

def _eligible(board,state,past,rules,strategy):
    if not(5<=board.player_count<=7 and board.day==1 and board.phase=='day'
        and board.alive==tuple(range(1,board.player_count+1)) and not board.history
        and not board.initial_hunter_count and board.initial_medium_count in(0,1)
        and board.initial_seer_count==1 and not rules.allow_self_bite
        and not strategy.include_self_bite and state.public_roles==tuple(sorted(board.worlds))
        and state.rosters==(board.alive,) and state.initial_rule=='random_white'
        and strategy.disclosure_for('seer')=='all'
        and tuple(strategy.seer_position)==('unvisited','uniform')
        and tuple(strategy.fake_seer_policy)in(('uniform',),('noncontradictory','uniform'))):return False
    claimants=tuple(p for p in board.alive if board.claims[p-1]=='seer')
    if len(claimants)!=2 or len(past)!=2:return False
    n=board.player_count;w=board.initial_role_counts['wolf'];m=board.initial_medium_count
    policies=(strategy.day,strategy.night,strategy.fake_reports)
    if(n,w)not in((5,1),(6,2),(7,2)):return False
    if n>=6 or m:
        if policies not in(('random',)*3,('max',)*3):return False
    if n==7 and policies!=(('max',)*3 if m else('random',)*3):return False
    if rules.initial_seer!='random_white' or state.tracked!=claimants or state.observed_prefix!=1:return False
    mediums=tuple(p for p in board.alive if board.claims[p-1]=='medium')
    if len(mediums)!=m or any(board.role_probability(p,'medium')!=1 for p in mediums):return False
    from math import comb
    if len(state.hypotheses)!=2*comb(n-3-m,w-1):return False
    if len({h.roles for h in state.hypotheses})!=len(state.hypotheses):return False
    if len({h.mass for h in state.hypotheses})!=1:return False
    co=sum(1<<(p-1)for p in claimants)
    for h in state.hypotheses:
        if h.guards or h.attacks or len(h.acquisitions)!=1:return False
        if h.roles[2]&co!=h.roles[2]or h.roles[0]&co!=co^h.roles[2]:return False
        a=h.acquisitions[0]
        if(a.day!=1 or not h.roles[2]&(1<<(a.player-1))
           or a.target not in {r.target for r in past}or a.color!='white'):return False
    if any(c not in('seer','medium','latent')for c in board.claims):return False
    return(len({r.target for r in past})==1 and all(board.claims[r.target-1]=='latent'for r in past)
           and {r.player for r in past}==set(claimants)
           and all(r.acquired_day==r.published_day==1 and r.color=='white' for r in past))

def eligible(board,state,past,rules,strategy):
    try:return _eligible(board,state,past,rules,strategy)
    except (AttributeError,TypeError,ValueError,IndexError):return False

def make_public_engine(original,board,state,past,rules,strategy,**kwargs):
    if not enabled():return original(rules,strategy,**kwargs)
    if not eligible(board,state,past,rules,strategy):
        try:
            from .exact_renaming import record,Unsupported
            for r in past:record(r,tuple(range(1,board.player_count+1)))
        except (Unsupported,TypeError,AttributeError):return original(rules,strategy,**kwargs)
        return make_view_engine(original,board,rules,strategy,**kwargs)
    # The local prototype remains isolated until broader production acceptance.
    from benchmarks.player_match_groups.extension_reuse import ExtensionForecast
    return ExtensionForecast(rules,strategy,future_reuse=True,physical_reuse=True,
        retired_reuse=True,compact_keys=True,fast_parts=True,retirement_proof=True,
        medium_reuse=True,max_reuse=True,combined_reuse=True,extended_retirement=True,**kwargs)

def make_root_engine(original,board,rules,strategy,**kwargs):
    if (not enabled()or board.player_count>6 or board.initial_hunter_count>1
        or getattr(original,'__name__',None)!='RootSecretEngine'):return original(rules,strategy,**kwargs)
    from benchmarks.player_match_groups.local_root import LocalRootEngine
    return LocalRootEngine(rules,strategy,**kwargs)


def late_seven_admitted(board,rules,strategy):
    # Performance admission using PUBLIC input only. Complete-key equality,
    # record/observer validation and the 120-mapping cap still decide reuse.
    if (board.player_count!=7 or len(board.alive)!=5 or board.day!=2 or board.phase!='day'
        or board.initial_hunter_count or board.initial_medium_count not in(0,1)
        or board.initial_seer_count!=1 or board.initial_role_counts['wolf']!=1 or rules.initial_seer!='none'
        or (strategy.day,strategy.night,strategy.fake_reports)!=('random','random','max')
        or strategy.disclosure_for('seer')!='all' or rules.allow_self_bite or strategy.include_self_bite
        or tuple(strategy.seer_position)!=('unvisited','uniform')
        or tuple(strategy.fake_seer_policy)!=('noncontradictory','uniform')):return False
    worlds=board.worlds
    medium=board.initial_medium_count
    fixed_medium=(not medium or len({w[1]for w in worlds})==1
                  and worlds[0][1].bit_count()==1 and bool(worlds[0][1]&board.alive_mask))
    return (fixed_medium and len(worlds)==4-medium and len({w[-1]for w in worlds})==1
            and len({w[2]for w in worlds})==1
            and worlds[0][2].bit_count()==1 and bool(worlds[0][2]&board.alive_mask)
            and all(w[0]&board.alive_mask==w[0]for w in worlds))


def make_view_engine(original,board,rules,strategy,**kwargs):
    if not enabled():return original(rules,strategy,**kwargs)
    if board.player_count>6 and not late_seven_admitted(board,rules,strategy):
        return original(rules,strategy,**kwargs)
    # Complete-key construction dominates measured tiny private inputs.
    # This selects the same original evaluator, never another policy/model.
    tiny=(len(board.alive)<=4 and len(board.worlds)<=3 and not board.initial_hunter_count)
    if tiny:return original(rules,strategy,**kwargs)
    from benchmarks.player_match_groups.general_reuse import GeneralReuseForecast
    return GeneralReuseForecast(rules,strategy,future_reuse=True,compact_keys=True,fast_parts=True,**kwargs)
