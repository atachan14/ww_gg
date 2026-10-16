"""Frozen v0.5.1 replay oracle from ec513c2; do not use in production.

Each request starts from the game's initial cast and replays the effective
history. No parent calculated Board is accepted as an authoritative prior.
Compatibility entry points delegate here; cached results are not the baseline.
"""
from dataclasses import replace
from werewolf.exact import (Progress,Rules,Strategy,ClaimPolicy,MediumReport,initial_board,
    group_initial_board,condition_claims,condition_reports,validate_strategy)
from werewolf.setup import complete_rules
from werewolf.dawn import advance_step
from werewolf.result_disclosure import MODEL as DISCLOSURE_MODEL,condition_observed

def with_claims(progress, claims, policy, initial_group=False):
        board = (group_initial_board(progress.board, claims, policy) if initial_group else condition_claims(progress.board, claims, policy))
        return Progress(board, progress.settled_village, progress.settled_wolf,
                        progress.last_board, progress.last_outcomes)

def with_reports(progress, reports, history=None):
        from werewolf.report_publication import condition_published_medium
        board=(condition_published_medium(progress.board,tuple(MediumReport(**r) for r in reports),history) if history is not None else condition_reports(progress.board,tuple(MediumReport(**r) for r in reports)))
        return Progress(board,progress.settled_village,progress.settled_wolf,progress.last_board,progress.last_outcomes)

def reconstruct_standard(state):
        rules = complete_rules(state["rules"])
        progress = Progress.initial(initial_board(state["players"], state.get("wolves", 1), state.get("mediums", 0), state.get("seers",0), state.get("hunters",0)))
        if len(state["history"]) > max(0, 2*state["players"] - 2):
            raise ValueError("Too much history")
        for index, step in enumerate(state["history"]):
            if step.get('result_disclosure_model') not in (None,DISCLOSURE_MODEL):raise ValueError('Invalid disclosure model')
            if set(step)-{'result_disclosure_model','observation','deaths'} not in ({"target", "policy"}, {"target", "policy", "claims", "claim_policy"}, {"target","policy","claims","claim_policy","reports"}, {"target","policy","claims","claim_policy","strategy_ui"}, {"target","policy","claims","claim_policy","reports","strategy_ui"}):
                raise ValueError("Invalid history")
            if "claims" in step:
                progress = with_claims(progress, tuple(step["claims"]), ClaimPolicy(**step["claim_policy"]), initial_group=index==0 and state.get("model","equal")=="group")
            if not progress.finished and step.get('reports'):
                progress = with_reports(progress, step['reports'],state['history'])
            if not progress.finished:
                b=condition_observed({**state,'result_disclosure_model':step.get('result_disclosure_model')},progress.board,tuple(step.get('claims',['latent']*state['players'])),ClaimPolicy(**step.get('claim_policy',{})),step['policy']);progress=Progress(b,progress.settled_village,progress.settled_wolf,progress.last_board,progress.last_outcomes)
            progress = advance_step(progress, step, rules)
        validate_strategy(rules, Strategy(**state["policy"]))
        if not progress.finished:
            progress = with_claims(progress, tuple(state.get("claims", ['latent'] * state["players"])),
                                   ClaimPolicy(**state.get("claim_policy", {})), initial_group=not state["history"] and state.get("model","equal")=="group")
            if state.get('reports'):
                progress = with_reports(progress, state['reports'],state['history'])
        if not progress.finished:
            b=condition_observed(state,progress.board,tuple(state.get('claims',['latent']*state['players'])),ClaimPolicy(**state.get('claim_policy',{})),state['policy']);progress=Progress(b,progress.settled_village,progress.settled_wolf,progress.last_board,progress.last_outcomes)
        return rules, progress

def reconstruct_manual(g,guard_priors):
    from werewolf.seer_manual import MODE,cast_scope,options,input_rows,condition
    guard_priors=dict(guard_priors)
    if g.get('seer_mode')!=MODE or not cast_scope(g):raise ValueError('手動開発版は1～9人・非負の役職数・合計人数の範囲で指定してください。')
    opt=options(g.get('seer_options',{}));rows=input_rows(g)
    rules=Rules(**g['rules']);seed=initial_board(g['players'],g.get('wolves',1),g.get('mediums',0),g.get('seers',0),g.get('hunters',0),experimental_cast=True);p=Progress.initial(seed);initial=seed.alive
    medium_rows=tuple(MediumReport(**r) for r in g.get('reports',()))
    medium_applied=set()
    from werewolf.report_publication import publication_slot,condition_published_medium
    history=g['history']
    if type(history) is not list or len(history)>max(0,2*g['players']-2):raise ValueError('保存された進行を確認してください。')
    if history and history[0].get('seer_options')!=opt:raise ValueError('初日ルール・報告尤度の変更は初日へ戻って行ってください。')
    applied=set();scan={1:initial}
    def apply(p,claims,cp,policy,observed_model,group=False):
        if p.finished:return p
        board=group_initial_board(p.board,claims,cp) if group else condition_claims(p.board,claims,cp)
        slot=2*(board.day-1)+(board.phase=='night')
        selected_medium=tuple(r for r in medium_rows if publication_slot(g,'medium',{'day':r.day,'reporter':r.reporter,'target':r.target})<=slot and (r.day,r.reporter,r.target) not in medium_applied)
        if selected_medium:
            board=condition_published_medium(board,selected_medium,history)
            medium_applied.update((r.day,r.reporter,r.target) for r in selected_medium)
        if board.phase=='night':scan[board.day+1]=board.alive
        selected=tuple(r for r in rows if publication_slot(g,'seer',r)<=slot and (r['day'],r['reporter']) not in applied)
        for row in selected:
            if row['reporter'] not in board.alive or claims[row['reporter']-1]!='seer':raise ValueError('結果の公開時点に生存・占いCOしている報告者を指定してください。')
            if row['target'] is not None and row['target'] not in scan[row['day']]:raise ValueError('取得時点に生存していた対象を指定してください。')
        complete=tuple(r for r in selected if r['target'] is not None and r['color'] is not None)
        if opt['initial_rule'] is not None and opt['likelihood'] is not None:board=condition(board,complete,opt,initial)
        applied.update((r['day'],r['reporter']) for r in selected)
        from werewolf.result_disclosure import condition_observed
        board=condition_observed({**g,'result_disclosure_model':observed_model},board,claims,cp,policy)
        return Progress(board,p.settled_village,p.settled_wolf,p.last_board,p.last_outcomes)
    for i,step in enumerate(history):
        if p.finished:raise ValueError('入力結果と保存済みの進行が不整合です。戻って確認してください。')
        allowed={'target','policy','claims','claim_policy','strategy_ui','reports','seer_options','result_disclosure_model','observation','deaths'}
        if not isinstance(step,dict) or set(step)-allowed or not {'target','policy','claims','claim_policy','seer_options'}<=set(step):raise ValueError('手動占いの保存履歴を確認してください。')
        if step.get('result_disclosure_model') not in (None,'full-observed-v1'):raise ValueError('Invalid disclosure observation model')
        p=apply(p,tuple(step['claims']),ClaimPolicy(**step['claim_policy']),step['policy'],step.get('result_disclosure_model'),i==0 and g.get('model','equal')=='group')
        from werewolf.dawn import advance_step
        p=advance_step(p,step,rules,guard_state=guard_priors.get(i))
    if not p.finished:p=apply(p,tuple(g['claims']),ClaimPolicy(**g['claim_policy']),g['policy'],g.get('result_disclosure_model'),not history and g.get('model','equal')=='group')
    if any((r['day'],r['reporter']) not in applied for r in rows):raise ValueError('まだ到達していない日の結果は入力できません。')
    if any((r.day,r.reporter,r.target) not in medium_applied for r in medium_rows):raise ValueError('霊能報告と保存された公開機会が一致しません。')
    validate_strategy(rules,Strategy(**g['policy']))
    return rules,replace(p,guard_state=guard_priors.get(len(history)))

def reconstruct_saved(game, *, guard_priors=None):
    """3a baseline: rebuild from effective inputs, not a prior calculation."""
    if game.get('seer_mode') != 'information-fixed-v1':
        return reconstruct_standard(game)
    from werewolf.seer_manual import migrate_game
    g=migrate_game(game)
    rules=Rules(**g['rules'])
    saved=g.get('history',())
    joint_max=(g.get('hunters')==1 and all(Strategy(**x.get('policy',{})).day=='random' for x in saved)
               and (Strategy(**g.get('policy',{})).night=='max' or
                    any(Strategy(**x.get('policy',{})).night=='max' for x in saved)))
    if guard_priors is None and g.get('hunters',0) and (not rules.allow_repeat_guard or joint_max):
        from werewolf.root_secret_flow import root_guard_night_priors
        from werewolf.seer_future_uniform import FuturePending
        guard_priors=root_guard_night_priors(g,rules)
        if isinstance(guard_priors,FuturePending):raise ValueError('No-repeat history replay: '+guard_priors.reason)
    return reconstruct_manual(g,tuple(sorted((guard_priors or {}).items())))
