"""Local public-Board analysis. No role assignment/sampling, dotenv, or database."""

import argparse
from copy import deepcopy
from decimal import Decimal
from fractions import Fraction
import secrets
from threading import BoundedSemaphore
from time import monotonic
import os
import json
from werewolf.calculation_budget import DEFAULT_MAX_WORK, DEFAULT_MAX_SECONDS, calculation_budget, CalculationBudgetExceeded, CalculationCancelled, tick, reset_diagnostics, budget_stop, stop_message, log_result
from werewolf.dawn import FLOW as DAWN_FLOW, enabled as dawn_enabled, advance_step
from werewolf.strategy_ui import co_editor, resolve_co_editor
from werewolf.result_disclosure import MODEL as DISCLOSURE_MODEL, DisclosureInconsistent, condition_observed

from werewolf.co_ui import CO_LABELS, CO_RENDERERS
from werewolf.setup import GameConfig, SetupDraft, setup_count, complete_rules, preset_data
from werewolf.comparison import compare_initial

from flask import g, jsonify, Flask, redirect, render_template, request, session, url_for, make_response, send_from_directory, abort
from werkzeug.http import dump_cookie

from werewolf.exact import (ClaimPolicy, Progress, Rules, Strategy, Values, advance,
                            condition_claims, group_initial_board, co_group_compositions, legal_targets, ROLES, VILLAGE_ROLES, ROLE_LABELS, MediumReport, condition_reports, available_medium_opportunities,
                            initial_board, validate_strategy)


def percent(value: Fraction) -> str:
    displayed = (Decimal(value.numerator) * 100 / Decimal(value.denominator)).quantize(Decimal("0.01"))
    return format(displayed, "f").rstrip("0").rstrip(".")


def create_app(test_config=None, *, deployment=False):
    app = Flask(__name__)
    hosted = deployment or os.environ.get("VERCEL") == "1"
    if hosted:
        # User supplies this through the project's sensitive environment settings.
        # Never fall back to a per-worker random key on a hosted deployment.
        key = os.environ.get("WW_GG_SECRET_KEY", "")
        if len(key) != 64 or any(c not in "0123456789abcdefABCDEF" for c in key):
            raise RuntimeError("WW_GG_SECRET_KEY must be a 64-character hexadecimal key")
    else:
        key = (test_config or {}).get("SECRET_KEY") or secrets.token_bytes(32)
    app.config.update(SECRET_KEY=key, MAX_CONTENT_LENGTH=4096,
                      MAX_FORM_PARTS=100, MAX_FORM_MEMORY_SIZE=4096,
                      SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax",
                      SESSION_COOKIE_SECURE=hosted, MAX_COOKIE_SIZE=4093)
    if test_config:
        app.config.update(test_config)
    if hosted:
        app.config.update(SECRET_KEY=key, SESSION_COOKIE_SECURE=True)
    app.jinja_env.filters["percent"] = percent
    app.jinja_env.filters["fraction"] = str
    app.jinja_env.globals.update(role_labels=ROLE_LABELS, role_order=ROLES)

    from werewolf.game_runtime import GameRuntimes
    game_runtimes=GameRuntimes()
    calculation_slot=BoundedSemaphore(1)
    app.extensions['board_game_runtimes']=game_runtimes

    def board_data(state):
        from werewolf.board_flow import BoardData
        game_id=session.setdefault('co_display_game',secrets.token_hex(8))
        return BoardData.from_game(state,runtime=game_runtimes.get(game_id,state))

    def replay(state):
        from werewolf.board_flow import BoardData
        return board_data(state).roles().replay_result

    def structural_roles(state):
        from werewolf.board_flow import BoardData
        try:return board_data(state).roles()
        except DisclosureInconsistent:
            return board_data({**state,'result_disclosure_model':None,
                'history':[{k:v for k,v in step.items() if k!='result_disclosure_model'}
                           for step in state['history']]}).roles()

    def structural_replay(state):return structural_roles(state).replay_result

    def game(*,validate_roles=True):
        state = session.get("game")
        try:
            required = {"players", "rules", "policy", "history", "selection", "revision"}
            if not isinstance(state, dict) or not required <= set(state) or not set(state) <= required | {"wolves", "mediums", "claims", "claim_policy", "model", "seers", "hunters", "reports", "strategy_ui", "seer_mode", "seer_options", "seer_inputs", "public_log", "public_draft", "result_disclosure_model", "board_flow"}:
                return None
            from werewolf.seer_manual import migrate_game
            original_state=state
            if state.get('board_flow') not in (None, DAWN_FLOW):return None
            if state.get('result_disclosure_model') not in (None,DISCLOSURE_MODEL):return None
            state=migrate_game(state)
            if app.config.get('SEER_UNIFORM_FUTURE_PREVIEW'):state={**state,'result_disclosure_model':DISCLOSURE_MODEL}
            if type(state["revision"]) is not int or state["revision"] < 0 or not isinstance(state["history"], list):
                return None
            if state.get("model","equal") not in ("equal","group"):
                return None
            if 'strategy_ui' in state:
                _, resolved = resolve_co_editor(state['strategy_ui'])
                if any(set(ClaimPolicy(**resolved).conditions(r)) != set(ClaimPolicy(**state['claim_policy']).conditions(r)) for r in VILLAGE_ROLES):
                    return None
            if "seer_mode" in state and state["seer_mode"] != "information-fixed-v1":return None
            if "public_log" in state or app.config.get("HYBRID_TABLE_PREVIEW"):
                from werewolf.public_log import migrate,project
                draft=state.get("public_draft")
                log=migrate({**state,"_owner_game_id":session.setdefault("co_display_game",secrets.token_hex(8))})
                if app.config.get("HYBRID_TABLE_PREVIEW"):
                    from werewolf.public_log_changes import upgrade
                    log=upgrade(log)
                state=project(state,log)
                if draft is not None:state["public_draft"]=draft
            progress = structural_replay(state)[1] if validate_roles else None
            target = state["selection"]
            if target is not None and (type(target) is not int or not 1 <= target <= state["players"]):
                return None
            if progress is not None and not progress.finished and target is not None and target not in progress.board.alive:
                return None
        except (ValueError, TypeError, KeyError):
            return None
        if state.get("public_draft"):
            draft=state["public_draft"]
            if draft.get("board_id",state["public_log"]["board_id"])!=state["public_log"]["board_id"]:state.pop("public_draft",None)
            else:draft["board_id"]=state["public_log"]["board_id"]
        if state!=original_state:
            session["game"]=state
        return state

    def revision_matches(state):
        bid=state.get("public_log",{}).get("board_id")
        return request.form.getlist("revision") == [str(state["revision"])] and (bid is None or request.form.getlist("board_id") in ([],[bid]))

    def parse_policy(rules, state=None,*,hunters=None,require_supported=False):
        def one(key):
            values = request.form.getlist(key)
            if len(values) != 1:
                raise ValueError("戦略を昼・夜それぞれ1つ指定してください。")
            return values[0]
        inclusion = request.form.getlist("include_self_bite")
        if inclusion not in ([], ["0"], ["1"]):
            raise ValueError("自噛みの設定が不正です。")
        reports=request.form.getlist('fake_reports')
        if reports not in ([],['max'],['random']):raise ValueError('偽霊能の報告方針を確認してください。')
        report_mode=reports[0] if reports else (state or {}).get('policy',{}).get('fake_reports','max')
        extra={}
        for key in ('disclosure_common','seer_disclosure','medium_disclosure','seer_position','guard_position','fake_seer_policy'):
            values=request.form.getlist(key)
            if len(values)>1:raise ValueError('結果開示・占い位置は一つ選択してください。')
            if values:
                try:extra[key]=json.loads(values[0]) if key in ('seer_position','guard_position','fake_seer_policy') else values[0]
                except json.JSONDecodeError as exc:raise ValueError('占い位置を確認してください。') from exc
            elif state and key in state['policy']:extra[key]=state['policy'][key]
        strategy = Strategy(one("day"), one("night"), inclusion == ["1"],report_mode,**extra)
        validate_strategy(rules, strategy)
        if not rules.allow_repeat_guard and (hunters if hunters is not None else (state or {}).get('hunters',0)):
            if (hunters if hunters is not None else state.get('hunters',0))!=1:
                raise ValueError('連続護衛なしは狩人1人に対応しています。複数狩人は未対応です。')
            from werewolf.root_secret_flow import root_policy_supported
            if require_supported and not root_policy_supported(strategy,hunters=1,
                    seers=(state or {}).get('seers',0),mediums=(state or {}).get('mediums',0)):
                raise ValueError('この配役・方針の連続護衛なし評価は未対応です。対応する設定を選んでください。')
            if require_supported and rules.allow_self_bite and not strategy.include_self_bite:
                raise ValueError('連続護衛なしで自噛み可能の場合は、自噛みを含む均等襲撃に対応しています。')
        return {"day":strategy.day,"night":strategy.night,"include_self_bite":strategy.include_self_bite,**{k:getattr(strategy,k) for k in extra},**({"fake_reports":strategy.fake_reports} if reports or state and "fake_reports" in state["policy"] else {})}

    def parse_claim_policy(state=None):
        defaults = state.get('claim_policy', {}) if state else {}
        result = {}
        for role in VILLAGE_ROLES:
            if role in ('seer','hunter') and not any(request.form.getlist(key+role) for key in ('cco_present_','cco_conditions_','cco_')) and role not in defaults:
                continue
            marker = request.form.getlist('cco_present_' + role)
            if marker:
                values = request.form.getlist('cco_conditions_' + role)
                if marker != ['1'] or request.form.getlist('cco_' + role) or not ClaimPolicy.valid_conditions(values):
                    raise ValueError('CO必須条件を確認してください。')
                result[role] = sorted(values)
                continue
            if request.form.getlist('cco_conditions_' + role):
                raise ValueError('CO必須条件の入力形式を確認してください。')
            values = request.form.getlist('cco_' + role)
            if len(values) > 1:
                raise ValueError("CO必須条件を1つ選んでください。")
            result[role] = values[0] if values else defaults.get(role, 'filled')
        result['wolf'] = 'none'
        ClaimPolicy(**result)
        return result

    def parse_claims(state):
        claims = list(state.get('claims', ['latent'] * state['players']))
        for i in range(1, state['players'] + 1):
            values = request.form.getlist('co_' + str(i))
            if len(values) > 1 or values and values[0] not in ('latent', *ROLES):
                raise ValueError("COの入力が不正です。")
            if values:
                claims[i - 1] = values[0]
        return claims

    def parse_reports(state, board):
        previous={(r['day'],r['reporter'],r['target']):r for r in state.get('reports',[])}
        for day,reporter,target in available_medium_opportunities(board):
            name=f'report_{day}_{reporter}_{target}';values=request.form.getlist(name)
            if not values:continue
            if len(values)!=1 or values[0] not in ('','white','black'):raise ValueError('霊能結果は未入力・白・黒から選んでください。')
            key=(day,reporter,target)
            if values[0]:previous[key]={'day':day,'reporter':reporter,'target':target,'color':values[0]}
            else:previous.pop(key,None)
        return [previous[key] for key in sorted(previous)]

    def parse_target(progress, required):
        values = request.form.getlist("target")
        if not values and not required:
            return None
        if len(values) != 1 or values[0] not in {str(player) for player in progress.board.alive}:
            raise ValueError("生存している対象を1人選んでください。")
        return int(values[0])

    def render_main(state, error=None, status=200, night_context=None, *, role_state=None, roles_only=False):
        disclosure_error=None
        guard_scope_pending=False
        by_dawn_values={}
        from werewolf.board_flow import BoardData
        try:
            role_state=role_state if role_state is not None else board_data(state).roles()
            rules,progress=role_state.replay_result
        except DisclosureInconsistent as exc:
            disclosure_error=str(exc);role_state=structural_roles(state);rules,progress=role_state.replay_result
        strategy = Strategy(**state["policy"])
        manual = state.get("seer_mode") == "information-fixed-v1"
        from werewolf.seer_manual import pending as manual_pending
        role_evidence_pending = manual_pending(state) if manual and not progress.finished else None
        seer_pending=role_evidence_pending
        if disclosure_error:
            from werewolf.seer_manual import Pending
            seer_pending=Pending(disclosure_error)
        finished = progress.finished
        board = progress.last_board if finished else progress.board
        if disclosure_error:
            primary=cumulative={'village_win':seer_pending,'wolf_win':seer_pending};action_values={};event_history=board.history;alive=board.alive
        elif finished:
            primary = Values(sum((outcome.probability * int(outcome.board.winner == "village") for outcome in progress.last_outcomes), Fraction(0)),
                             sum((outcome.probability * int(outcome.board.winner == "wolf") for outcome in progress.last_outcomes), Fraction(0)))
            cumulative = progress.total_values()
            action_values = {}
            event_history = progress.last_outcomes[0].board.history
            alive = progress.last_outcomes[0].board.alive
        elif roles_only and not seer_pending:
            from werewolf.seer_manual import Pending
            seer_pending=Pending('役職率を表示しています。勝率を計算中です。')
            primary=cumulative={'village_win':seer_pending,'wolf_win':seer_pending}
            action_values={};event_history,alive=board.history,board.alive
        elif seer_pending:
            primary = cumulative = {"village_win":seer_pending,"wolf_win":seer_pending}
            action_values = {}
            event_history, alive = board.history, board.alive
        else:
            from werewolf.calculation_budget import calculation_budget, CalculationBudgetExceeded, tick
            try:
                with calculation_budget(app.config.get('MANUAL_CALC_MAX_WORK',DEFAULT_MAX_WORK) if manual else None, max_seconds=app.config.get('MANUAL_CALC_MAX_SECONDS',DEFAULT_MAX_SECONDS) if manual else None):
                    from werewolf.seer_future_uniform import FuturePending
                    tick()  # Enforce the request deadline even when a complete snapshot is cached.
                    forecast=role_state.forecast(max_work=app.config.get('MANUAL_CALC_MAX_WORK',DEFAULT_MAX_WORK),max_seconds=app.config.get('MANUAL_CALC_MAX_SECONDS',DEFAULT_MAX_SECONDS))
                    if isinstance(forecast,FuturePending):
                        guard_scope_pending=forecast.reason.startswith(('guard_','root_guard_','root_actor_')) or (board.initial_hunter_count and forecast.reason=='information_set_budget_exceeded')
                        from werewolf.seer_manual import Pending
                        reasons={'initial_public_results_incomplete':'未公開結果を含む未来評価は現在Pendingです。','multiple_fake_report_correlation_unselected':'複数偽占いが生存する朝の共同報告は未対応のためPendingです。', 'current_morning_seer_reports_incomplete':'未公開結果を含む未来評価は現在Pendingです。','past_private_scan_history_missing':'過去の本人取得履歴が不足しているため未来評価できません。'}
                        reasons.update({'future_public_continuation_budget_exceeded':'未来の分岐が計算予算を超えました。公開情報を揃えるか、配役を絞ってください。','true_scan_generation_budget_exceeded':'未来占いの結果候補が計算予算を超えました。','observed_prior_private_ledger_budget_exceeded':'過去情報の再構成が計算予算を超えました。','future_fake_law_does_not_specify_initial_declarations':'初日の公開結果を入力してください。初日の偽報告自動生成は未設定です。'})
                        reasons.update({'information_set_budget_exceeded':'計算予算に達したためモデルAの評価はPendingです。旧モデルの数値には切り替えません。'})
                        reasons.update({'guard_hidden_attack_max_unimplemented':'狩人未確定の襲撃最大化は未対応です。襲撃位置「均等化」に対応しています。','guard_multiple_hunters_unimplemented':'複数狩人の能力計算は未対応です。','guard_no_repeat_max_unimplemented':'連続護衛なしのmaxは未対応です。処刑・襲撃の均等化に対応しています。','guard_no_repeat_history_missing':'前夜の護衛履歴を共同分布から再構成できません。'})
                        seer_pending=Pending(reasons.get(forecast.reason,'この情報・配役の未来評価はまだ計算できません。'))
                        if budget_stop() is not None:seer_pending=Pending(stop_message())
                        primary=cumulative={'village_win':seer_pending,'wolf_win':seer_pending}
                        action_values={}
                    else:
                        primary=Values(forecast.village_win,1-forecast.village_win)
                        cumulative=progress.total_values(primary)
                        action_values={p:Values(v,1-v) for p,v in forecast.action_values}
                        by_dawn_values=dict(forecast.by_dawn_values)
                    event_history, alive = board.history, board.alive
            except CalculationBudgetExceeded:
                from werewolf.seer_manual import Pending
                seer_pending=Pending('計算予算に到達したため勝率は未計算です。配役やCO、入力結果を絞ると計算できる場合があります。')
                primary=cumulative={'village_win':seer_pending,'wolf_win':seer_pending}
                action_values={}
                event_history,alive=board.history,board.alive
        if roles_only and night_context:night_context={**night_context,'pending':True}
        display_selection = (night_context['observation']['deaths'][0] if night_context and night_context['observation'] and len(night_context['observation']['deaths'])==1 else None) if night_context else state['selection']
        if not night_context and not finished and not seer_pending and display_selection is None and getattr(strategy, board.phase) == 'max':
            score = 'village_win' if board.phase == 'day' else 'wolf_win'
            best = max(getattr(value, score) for value in action_values.values())
            display_selection = min(target for target, value in action_values.items() if getattr(value, score) == best)
        from werewolf.public_log import migrate
        viewpoint_seed = None
        if night_context and not finished and not disclosure_error:
            from werewolf.private_adapter import viewpoint_roles, private_slots
            viewpoint_seed = {'roles': viewpoint_roles(board), 'revision': state['revision'],
                              'board_id': state['public_log']['board_id'],
                              'claims': list(board.claims), 'public_results': state.get('seer_inputs', []),
                              'slots': {str(p): private_slots(board, p, rules) for p in board.alive},
                              'guard_slots': {str(p): private_slots(board,p,rules,role='hunter') for p in board.alive},
                              'attack_slots': private_slots(board,1,rules,role='wolf'), 'allow_self_bite':rules.allow_self_bite,
                              'public_attacks': [{'day':e.day,'target':e.target,'color':None} for e in board.history if e.phase=='night']}
        from werewolf.player_view import ViewScope,ResultFrame,build_public_view
        view_source=board_data(state)
        view_stage='invalid'if disclosure_error else 'roles'if roles_only else 'pending'if seer_pending else 'complete'
        player_view=build_public_view(view_source,role_state,board,ResultFrame(ViewScope.public(view_source),view_stage,
            str(request.form.get('request_id','')),str(seer_pending.reason)if seer_pending else None),
            state=state,event_history=event_history,alive=alive,action_values=action_values,by_dawn_values=by_dawn_values,
            finished=finished,manual=manual,guard_scope_pending=guard_scope_pending,
            probability_pending=seer_pending if role_evidence_pending or disclosure_error else None)
        players=player_view.players
        return render_template("main.html", guard_scope_pending=guard_scope_pending, viewpoint_seed=viewpoint_seed, night_context=night_context, public_log=migrate(state), dawn_flow=dawn_enabled(state), disclosure_error=disclosure_error, future_preview=manual, future_active=manual and strategy.disclosure_for("seer")=="all", state=state, co_game=session.setdefault("co_display_game", secrets.token_hex(8)), co_labels=CO_LABELS, role_labels=({**ROLE_LABELS,"seer":("占い師（手動入力＋未来均等）" if manual and strategy.disclosure_for("seer")=="all" else "占い師（手動のみ）")} if manual else ROLE_LABELS), co_renderers=({**CO_RENDERERS,"seer":"co_roles/seer_manual.html"} if manual else CO_RENDERERS), seer_pending=seer_pending, display_selection=display_selection, report_opportunities=available_medium_opportunities(board) if not finished else (), report_colors={(r.day,r.reporter,r.target):r.color for r in board.reports}, rules=rules, progress=progress,
                               board=board, finished=finished, rates=primary, cumulative=cumulative,
                               players=players, player_view=player_view, error=error, strategy_seed={'co':state.get('strategy_ui',co_editor(state.get('claim_policy',{}))), 'model':state.get('model','equal'), 'policy':state['policy'], 'finished':finished or bool(night_context), 'model_locked':bool(state['history']), 'allow_self_bite':rules.allow_self_bite, 'board_key':str(state['players'])+'-'+str(state.get('wolves',1))+'-'+','.join(str(x['target']) for x in state['history']), 'future_available':manual, 'roles':[r for r in ('villager','medium','seer','hunter','wolf') if board.initial_role_counts[r]]}, co_groups=role_state.groups if not finished and not seer_pending and state.get("model")=="group" else [], claim_policy=ClaimPolicy(**state.get("claim_policy", {})), counts=({} if disclosure_error else role_state.counts)), status

    def wants_calculation_stream():
        return (request.path in ('/main','/table-preview','/private-view') and
                request.headers.get('Accept')=='application/x-ndjson')

    def calculation_stream(events,*,view='public'):
        # The iterator owns its budget and slot: Flask tears down the initial
        # request before the response body is consumed. Never extend that budget
        # by starting a new continuation request or an external background job.
        from flask import Response,stream_with_context,copy_current_request_context
        session.setdefault('co_display_game',secrets.token_hex(8))
        trace=request.environ.get('wwgg.lifecycle')
        def note(event,**fields):
            if trace is not None:trace.emit(event,**fields)
        def generate():
            reset_diagnostics()
            acquired=False;cancelled=False;stop_kind=None;completed=False
            with calculation_budget(app.config.get('MANUAL_CALC_MAX_WORK',DEFAULT_MAX_WORK),
                                    max_seconds=app.config.get('MANUAL_CALC_MAX_SECONDS',DEFAULT_MAX_SECONDS)):
                try:
                    note('stream_wait')
                    queue_deadline=monotonic()+(app.config.get('MANUAL_CALC_MAX_SECONDS',DEFAULT_MAX_SECONDS) or DEFAULT_MAX_SECONDS)
                    while not acquired:
                        tick(0)
                        if monotonic()>=queue_deadline:raise CalculationBudgetExceeded('Calculation queue time limit',kind='time')
                        acquired=calculation_slot.acquire(timeout=.2)
                    note('stream_acquired')
                    tick(0)
                    for event in events():
                        yield json.dumps(event,ensure_ascii=False)+'\n'
                    completed=True
                except (CalculationCancelled,GeneratorExit):
                    cancelled=True;raise
                except CalculationBudgetExceeded as exc:
                    stop_kind=exc.kind
                    yield json.dumps({'event':'error','error':stop_message(exc.kind),'budget_kind':exc.kind,'pending':True},ensure_ascii=False)+'\n'
                except (ValueError,TypeError,KeyError,DisclosureInconsistent) as exc:
                    yield json.dumps({'event':'error','error':str(exc)},ensure_ascii=False)+'\n'
                finally:
                    log_result(request.endpoint,200,'cancelled' if cancelled else stop_kind)
                    if acquired:
                        calculation_slot.release();note('stream_released')
                    note('stream_exit',reason='cancelled' if cancelled else stop_kind or ('complete' if completed else 'error'))
        if app.config.get('CALCULATION_POSITION_ENABLED',True):
            from werewolf.exploration_position import position_stream
            @copy_current_request_context
            def produce(send):
                source=generate()
                try:
                    for chunk in source:send(chunk)
                finally:source.close()
            iterator=position_stream(produce,view=view,diagnostic=trace)
        else:iterator=generate()
        return Response(stream_with_context(iterator),mimetype='application/x-ndjson',headers={'X-Content-Type-Options':'nosniff','Cache-Control':'no-store'})

    @app.before_request
    def begin_request_budget():
        if app.config.get('REQUEST_LIFECYCLE_DIAGNOSTICS',False) and request.endpoint in ('main','start','private_view','table_publish','table_preview','advance','comparison'):
            from werewolf.request_diagnostics import RequestTrace
            trace=RequestTrace(request.endpoint)
            request.environ['wwgg.lifecycle']=trace
            trace.emit('request_enter')
        if request.method=='POST':
            origin=request.headers.get('Origin')
            if request.headers.get('Sec-Fetch-Site')=='cross-site' or (origin and origin!=request.host_url.rstrip('/')):
                return 'Cross-site form submission is not allowed',403
        reset_diagnostics()
        if request.method=='POST':g.calculation_previous_session=deepcopy(dict(session))
        if request.endpoint in ('static','help_five_asset','help_medium_asset') or wants_calculation_stream():return
        scope=calculation_budget(app.config.get('MANUAL_CALC_MAX_WORK',DEFAULT_MAX_WORK),
                                 max_seconds=app.config.get('MANUAL_CALC_MAX_SECONDS',DEFAULT_MAX_SECONDS))
        scope.__enter__();g.calculation_scope=scope
        if request.method=='POST' or request.path in ('/main','/comparison'):
            trace=request.environ.get('wwgg.lifecycle')
            if trace is not None:trace.emit('request_wait')
            acquired=calculation_slot.acquire(timeout=app.config.get('MANUAL_CALC_MAX_SECONDS',DEFAULT_MAX_SECONDS) or DEFAULT_MAX_SECONDS)
            if not acquired:
                app.logger.warning('wwgg_budget_stop kind=time phase=request_queue')
                raise CalculationBudgetExceeded('Calculation queue time limit',kind='time')
            g.calculation_slot=True
            if trace is not None:trace.emit('request_acquired')
            tick(0)

    @app.teardown_request
    def finish_request_budget(error):
        if g.pop('calculation_slot',False):
            calculation_slot.release()
            trace=request.environ.get('wwgg.lifecycle')
            if trace is not None:trace.emit('request_released')
        scope=g.pop('calculation_scope',None)
        if scope is not None:scope.__exit__(None,None,None)

    @app.errorhandler(CalculationBudgetExceeded)
    def calculation_stopped(error):
        g.calculation_stop_kind=error.kind
        previous=g.get('calculation_previous_session')
        if previous is not None:
            session.clear();session.update(previous);session.modified=True
        message=stop_message(error.kind)
        if request.method=='POST' and request.path in ('/private-view','/table-preview','/table-publish','/public-log','/dawn-report'):
            return jsonify(error=message,budget_kind=(budget_stop() or {}).get('kind',error.kind),pending=True),503
        return render_template('budget_pending.html',message=message),503

    @app.before_request
    def same_origin_posts():
        if request.method == "POST":
            origin = request.headers.get("Origin")
            if request.headers.get("Sec-Fetch-Site") == "cross-site" or (origin and origin != request.host_url.rstrip("/")):
                return "Cross-site form submission is not allowed", 403

    @app.after_request
    def no_stale_pages(response):
        trace=request.environ.get('wwgg.lifecycle')
        if trace is not None:response.headers['X-WW-Diagnostic-Request']=trace.request_id
        if not wants_calculation_stream() and request.path in ('/main','/private-view','/comparison'):log_result(request.endpoint,response.status_code,g.get('calculation_stop_kind'))
        # Reject an oversized update before Flask emits Set-Cookie. Preserve the
        # previously accepted browser cookie rather than silently losing a Board.
        if session.modified and session:
            serializer = app.session_interface.get_signing_serializer(app)
            value = serializer.dumps(dict(session))
            header = dump_cookie(app.config["SESSION_COOKIE_NAME"], value,
                                 path=app.config["SESSION_COOKIE_PATH"] or "/",
                                 domain=app.config["SESSION_COOKIE_DOMAIN"],
                                 secure=app.config["SESSION_COOKIE_SECURE"],
                                 httponly=True, samesite="Lax", max_size=0)
            if len(header.encode("ascii")) > app.config["MAX_COOKIE_SIZE"]:
                session.modified = False
                response = make_response("Board settings exceed the browser cookie limit; reduce settings and retry.", 400)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @app.route('/comparison', methods=['GET', 'POST'])
    def comparison_route():
        state = game()
        inputs = {'citizens':5, 'mediums':2, 'wolves':2, 'claims':['latent']*9,
                  'claim_policy':{'villager':'filled','medium':'filled'}, 'mode':'trial','seers':0,'hunters':0}
        if state:
            inputs.update(citizens=state['players']-state.get('wolves',1)-state.get('mediums',0)-state.get('seers',0)-state.get('hunters',0),
                          mediums=state.get('mediums',0), wolves=state.get('wolves',1),seers=state.get('seers',0),hunters=state.get('hunters',0),
                          claim_policy=state.get('claim_policy', inputs['claim_policy']))
            if not state['history']:
                inputs['claims']=state.get('claims',['latent']*state['players'])+['latent']*(9-state['players'])
        try:
            if request.method=='POST':
                allowed={'mode','citizens','mediums','seers','hunters','wolves','cco_villager','cco_medium'} | {'co_'+str(i) for i in range(1,10)}
                allowed |= {'cco_'+role for role in VILLAGE_ROLES}
                allowed |= {'cco_present_' + role for role in VILLAGE_ROLES} | {'cco_conditions_' + role for role in VILLAGE_ROLES}
                if not set(request.form)<=allowed:
                    raise ValueError('比較用の入力を確認してください。')
                for key in ('citizens','mediums','seers','hunters','wolves'):
                    values=request.form.getlist(key)
                    if key in ('seers','hunters') and not values:
                        inputs[key]=0;continue
                    if len(values)!=1 or values[0] not in {str(n) for n in range(10)}:
                        raise ValueError('配役人数を0〜9の整数で指定してください。')
                    inputs[key]=int(values[0])
                modes=request.form.getlist('mode')
                if len(modes)!=1 or modes[0] not in ('current','trial','group'):
                    raise ValueError('比較モードを確認してください。')
                inputs['mode']=modes[0]
                inputs['claims']=parse_claims({'players':9,'claims':['latent']*9})
                inputs['claim_policy']=parse_claim_policy()
            n=inputs['citizens']+inputs['mediums']+inputs['seers']+inputs['hunters']+inputs['wolves']
            result=compare_initial(inputs['citizens'],inputs['mediums'],inputs['wolves'],
                                   tuple(inputs['claims'][:n]),ClaimPolicy(**inputs['claim_policy']),inputs['mode'],inputs['seers'],inputs['hunters'])
        except ValueError as exc:
            result=dict(mode=inputs['mode'], issues=[str(exc)], rows=[],totals={},rates=None,valid=False)
        if request.headers.get('X-Comparison')=='partial':
            return render_template('comparison_results.html',result=result)
        return render_template('comparison.html',inputs=inputs,result=result,claim_policy=ClaimPolicy(**inputs['claim_policy']),finished=False)

    def render_setup(draft, error=None):
        return render_template("top.html", future_preview=app.config.get("SEER_UNIFORM_FUTURE_PREVIEW",False), error=error, draft=draft, setup_presets=preset_data(), seer_mode=request.form.get("seer_mode",session.get("game",{}).get("seer_mode","")))

    @app.get('/help')
    def help_route():return render_template('help.html')

    @app.get('/help/program/')
    @app.get('/help/program/<page>')
    def help_program(page='index'):
        from werewolf.help_program import PAGES,TERMS,REFERENCES,FIVE_FIXTURE,AUDIT_VERSION,REVIEW_VERSION,PUBLIC_SHA
        if page not in PAGES:abort(404)
        return render_template('help_program.html',page=page,pages=PAGES,terms=TERMS,
                               references=REFERENCES,fixture=FIVE_FIXTURE,audit_version=AUDIT_VERSION,
                               review_version=REVIEW_VERSION,public_sha=PUBLIC_SHA)

    @app.get('/help/history/')
    @app.get('/help/history/<page>')
    def help_history(page='index'):
        from werewolf.help_history import VERSIONS
        entry=next((item for item in VERSIONS if item['id']==page),None)
        if page not in ('index','v0.5.2-design') and entry is None:abort(404)
        return render_template('help_history.html',page=page,entry=entry,versions=VERSIONS)

    @app.get('/help/history/materials/')
    @app.get('/help/history/materials/<page>')
    def help_materials(page='index'):
        from werewolf.help_materials import MATERIALS
        if page!='index' and page not in MATERIALS:abort(404)
        return render_template('help_materials.html',page=page,materials=MATERIALS)

    @app.get('/help/history/materials/raw/<page>')
    def help_material_raw(page):
        from werewolf.help_materials import MATERIALS
        if page not in MATERIALS:abort(404)
        response=send_from_directory(os.path.join(app.root_path,'help_assets','history'),page+'.html')
        response.headers['Content-Type']='text/html; charset=utf-8'
        response.headers['Content-Security-Policy']="default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data:; connect-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors 'self'; sandbox allow-scripts allow-popups allow-popups-to-escape-sandbox allow-top-navigation-by-user-activation"
        response.headers['X-Content-Type-Options']='nosniff'
        return response

    @app.get('/help/specs')
    def help_specs():return render_template('help_specs.html')

    @app.get('/help/examples')
    def help_examples():return render_template('help_examples.html')

    @app.get('/help/medium/')
    def help_medium():return render_template('help_medium.html')

    @app.get('/help/five/')
    def help_five():return render_template('help_five.html')

    @app.get('/help/five/<name>')
    def help_five_asset(name):
        if name not in ('tree-prototype.css','tree-prototype.js','help-shell.css','help-shell.js',
                        'help-header-integration.css','medium-co.css','medium-co.js'):abort(404)
        return send_from_directory(os.path.join(app.root_path,'help_assets'),name)

    @app.get("/")
    def top():
        state = game()
        config = GameConfig.from_game(state) if state else GameConfig.default()
        return render_setup(config.draft())

    @app.post("/start")
    def start():
        draft = SetupDraft.from_form(request.form)
        try:
            allowed = {"players", "wolves", "citizens", "mediums", "seers", "hunters", "day", "night", "allow_self_bite", "include_self_bite", "fake_reports", "cco_villager", "cco_medium", "model", "seer_mode", "initial_seer", "allow_repeat_guard", "disclosure_common", "seer_disclosure", "medium_disclosure", "seer_position", "guard_position", "fake_seer_policy"}
            allowed |= {'cco_'+role for role in VILLAGE_ROLES}
            allowed |= {'cco_present_' + role for role in VILLAGE_ROLES} | {'cco_conditions_' + role for role in VILLAGE_ROLES}
            if not set(request.form) <= allowed:
                raise ValueError("配役と計算条件を確認してください。")
            def count(key, default=None):
                values = request.form.getlist(key)
                if not values and default is not None:
                    return default
                if len(values) != 1:
                    raise ValueError("配役の人数は0〜9の整数で指定してください。")
                return setup_count(values[0])
            wolves = count('wolves', 1)
            mediums = count('mediums', 0)
            seers = count('seers',0)
            hunters = count('hunters',0)
            if 'citizens' in request.form:
                citizens = count('citizens')
                players = citizens + mediums + seers + hunters + wolves
                if 'players' in request.form and count('players') != players:
                    raise ValueError("合計人数が配役と一致しません。")
            else:
                players = count('players')
            modes=request.form.getlist("seer_mode")
            if modes not in ([],[""],["information-fixed-v1"]):raise ValueError("占い計算モデルを確認してください。")
            seer_mode="information-fixed-v1" if seers else (modes[0] if modes else "")
            initial_board(players, wolves, mediums, seers, hunters, experimental_cast=bool(seer_mode))
            claim_policy = parse_claim_policy()
            models=request.form.getlist("model")
            if models not in ([],["group"]):
                raise ValueError("計算モデルを確認してください。")
            model="group"
            permission = request.form.getlist("allow_self_bite")
            if permission not in ([], ["0"], ["1"]):
                raise ValueError("自噛みのルールが不正です。")
            first=request.form.getlist("initial_seer")
            if len(first)>1:raise ValueError("初日占いは一つ選んでください。")
            repeat=request.form.getlist('allow_repeat_guard')
            if repeat not in ([],['0'],['1']):raise ValueError('連続護衛のルールが不正です。')
            rules = Rules(permission == ["1"],first[0] if first else "random_white",repeat!=['0'])
            if hunters and not rules.allow_repeat_guard:seer_mode='information-fixed-v1'
            policy = parse_policy(rules,hunters=hunters)
        except ValueError as exc:
            return render_setup(draft, error=str(exc)), 400
        previous = game()
        game_runtimes.discard(session.get('co_display_game'))
        session["co_display_game"] = secrets.token_hex(8)
        session["game"] = {**({"seers":seers,"hunters":hunters} if seers or hunters else {}), "players": players, "wolves": wolves, "mediums": mediums,
                           "model": model, "claims": ['latent'] * players, "claim_policy": claim_policy, "rules": {"allow_self_bite": rules.allow_self_bite,"initial_seer":rules.initial_seer,"allow_repeat_guard":rules.allow_repeat_guard},
                           "policy": policy, "history": [], "selection": None,
                           "revision": previous["revision"] + 1 if previous else 0}
        if seer_mode:
            session["game"].update(seer_mode=seer_mode,seer_options={"initial_rule":rules.initial_seer,"likelihood":"compatibility"},seer_inputs=[])
            session.modified=True
        if app.config.get('SEER_UNIFORM_FUTURE_PREVIEW'):session['game']={**session['game'],'result_disclosure_model':DISCLOSURE_MODEL}
        if app.config.get('DAWN_BOARD_PREVIEW') or hunters and not rules.allow_repeat_guard:session['game']={**session['game'],'board_flow':DAWN_FLOW}
        if app.config.get('HYBRID_TABLE_PREVIEW') or app.config.get('DAWN_BOARD_PREVIEW') or hunters and not rules.allow_repeat_guard:
            from werewolf.public_log import migrate,project
            from werewolf.public_log_changes import upgrade
            created=session['game'];session['game']=project(created,upgrade(migrate({**created,'_owner_game_id':secrets.token_hex(8)})))
        return redirect(url_for("main"), code=303)

    @app.get("/main")
    def main():
        shell=request.headers.get('Sec-Fetch-Dest')=='document' and request.args.get('complete')!='1' and not wants_calculation_stream()
        state = game(validate_roles=not (wants_calculation_stream() or shell))
        if state is None:
            return redirect(url_for("top"), code=303)
        if shell:return render_template('main_loading.html')
        if wants_calculation_stream():
            def events():
                prepared=board_data(state).roles()
                if prepared.progress.finished:
                    yield {'event':'redirect','url':url_for('result')};return
                if state['selection'] is not None and state['selection'] not in prepared.board.alive:
                    raise ValueError('保存された選択対象を確認してください。')
                identity={'board_id':state.get('public_log',{}).get('board_id'),'revision':state['revision']}
                night=dawn_enabled(state) and prepared.board.phase=='night'
                context=dawn_context(state,prepared) if night else None
                for stage in ('roles','complete'):
                    html,status=render_main(state,night_context=context,role_state=prepared,roles_only=stage=='roles')
                    yield dict(event=stage,html=html,**identity)
            return calculation_stream(events)
        if structural_replay(state)[1].finished:
            return redirect(url_for('result'),code=303)
        if dawn_enabled(state) and structural_replay(state)[1].board.phase == 'night':
            return render_dawn(state)
        return render_main(state)

    def dawn_context(state,prepared=None):
        from werewolf.dawn import current_observation, validate_observation, unsupported_reason, observe
        rules,before=prepared.replay_result if prepared is not None else structural_replay(state)
        observation = validate_observation(current_observation(state), before.board.alive)
        pending = unsupported_reason(observation, before.board, rules)
        after = None
        if not pending:
            try:
                after = observe(before, observation, rules, Strategy(**state['policy']))
            except ValueError as exc:
                pending = str(exc)
        return {
            'observation': observation, 'pending': pending,
            'finished': after is not None and after.finished}

    def render_dawn(state,error=None,status=200,**render_options):
        return render_main(state,error,status,night_context=dawn_context(state,render_options.get('role_state')),**render_options)

    @app.post('/dawn-report')
    def dawn_report():
        from werewolf.dawn import validate_observation, record_observation
        state = game()
        if state is None or not dawn_enabled(state):
            abort(404)
        _, progress = structural_replay(state)
        if progress.finished or progress.board.phase != 'night':
            abort(409)
        if (not revision_matches(state) or request.form.getlist('board_id') != [state['public_log']['board_id']]):
            return render_dawn(state, '画面が更新されています。再読み込みしてください。', 409)
        try:
            if set(request.form) - {'revision', 'board_id', 'mode', 'deaths'} or len(request.form.getlist('mode')) != 1:
                raise ValueError('死体報告の入力形式を確認してください。')
            mode = request.form['mode']
            selected = request.form.getlist('deaths')
            if mode == 'deaths':
                if not selected or any(not p.isascii() or not p.isdecimal() for p in selected):
                    raise ValueError('死体となったプレイヤーを選んでください。')
                observation = {'deaths': [int(p) for p in selected]}
            elif mode in ('none', 'clear'):
                if selected:
                    raise ValueError('死体の選択を解除してください。')
                observation = {'deaths': []} if mode == 'none' else None
            else:
                raise ValueError('死体報告の種類を確認してください。')
            observation = validate_observation(observation, progress.board.alive)
            proposed = record_observation(state, observation)
            proposed['revision'] += 1
        except ValueError as exc:
            return render_dawn(state, str(exc), 400)
        session['game'] = proposed
        return redirect(url_for('main'), code=303)

    @app.post('/dawn-advance')
    def dawn_advance():
        from copy import deepcopy
        from werewolf.dawn import current_observation, observe, OBSERVATION
        state = game()
        if state is None or not dawn_enabled(state):
            abort(404)
        rules, progress = structural_replay(state)
        if progress.finished or progress.board.phase != 'night':
            abort(409)
        if (not revision_matches(state) or request.form.getlist('board_id') != [state['public_log']['board_id']]):
            return render_dawn(state, '画面が更新されています。再読み込みしてください。', 409)
        try:
            if set(request.form) != {'revision', 'board_id'}:
                raise ValueError('夜明けの進行操作を確認してください。')
            observation = current_observation(state)
            observe(progress, observation, rules, Strategy(**state['policy']))
            step = {k: deepcopy(state[k]) for k in ('policy', 'claims', 'claim_policy',
                    'strategy_ui', 'reports', 'seer_options', 'result_disclosure_model') if k in state}
            step.update(target=observation['deaths'][0] if observation['deaths'] else None, deaths=observation['deaths'], observation=OBSERVATION)
            proposed = {**state, 'history': state['history'] + [step],
                        'selection': None, 'revision': state['revision'] + 1}
            from werewolf.public_log import migrate, project
            proposed = project(proposed, migrate(proposed))
            _, after = structural_replay(proposed)
        except ValueError as exc:
            return render_dawn(state, str(exc), 400)
        session['game'] = proposed
        return redirect(url_for('result' if after.finished else 'main'), code=303)

    def change(advancing):
        state = game()
        if state is None:
            return redirect(url_for("top"), code=303)
        rules, progress = structural_replay(state)
        if progress.finished:
            return redirect(url_for("result"), code=303)
        if dawn_enabled(state) and progress.board.phase == 'night':
            return render_dawn(state, '死体報告を確定して昼へ進んでください。', 400)
        if not revision_matches(state):
            return render_main(state, "画面が更新されています。現在の画面で選び直してください。", 409)
        try:
            allowed = {"revision", "target", "day", "night", "include_self_bite", "fake_reports", "cco_villager", "cco_medium", "model", "strategy_ui", "disclosure_common", "seer_disclosure", "medium_disclosure", "seer_position", "guard_position", "fake_seer_policy"} | {'co_' + str(i) for i in range(1, state['players'] + 1)}
            allowed |= {'cco_'+role for role in VILLAGE_ROLES}
            allowed |= {'cco_present_' + role for role in VILLAGE_ROLES} | {'cco_conditions_' + role for role in VILLAGE_ROLES}
            if state.get("seer_mode") == "information-fixed-v1":
                allowed |= {"seer_initial_rule","seer_likelihood"} | {f"seer_{kind}_{d}_{p}" for kind in ("target","color") for d in range(1,progress.board.day+1) for p in range(1,state['players']+1)}
            allowed |= {f'report_{day}_{reporter}_{target}' for day,reporter,target in available_medium_opportunities(progress.board)}
            if not set(request.form) <= allowed:
                raise ValueError("この画面では対象と戦略を指定してください。")
            if "public_log" in state and any(k.startswith(("co_", "seer_target_", "seer_color_", "report_")) for k in request.form):
                raise ValueError("CO・結果の変更はSystemLogから公開してください。")
            models=request.form.getlist('model')
            if models not in ([],['equal'],['group']):
                raise ValueError('計算モデルを確認してください。')
            model=models[0] if models else state.get('model','equal')
            if state['history'] and model!=state.get('model','equal'):
                raise ValueError('このBoardのモデルは変更できません。TOPから新規開始してください。')
            policy = parse_policy(rules,state,require_supported=advancing)
            claims = parse_claims(state)
            editor_values=request.form.getlist('strategy_ui')
            if editor_values:
                if len(editor_values)!=1 or any(k.startswith(('cco_', 'cco_present_', 'cco_conditions_')) for k in request.form):
                    raise ValueError('CO設定の入力形式を確認してください。')
                try:
                    editor, claim_policy = resolve_co_editor(json.loads(editor_values[0]))
                except (json.JSONDecodeError, TypeError) as exc:
                    raise ValueError('CO設定の入力を確認してください。') from exc
            else:
                claim_policy = parse_claim_policy(state)
                editor = co_editor(claim_policy)
            reports=parse_reports(state,progress.board)
            proposed={**state,'model':model,'policy':policy,'claims':claims,'claim_policy':claim_policy,'strategy_ui':editor}
            if reports or 'reports' in state:proposed['reports']=reports
            if state.get('seer_mode')=='information-fixed-v1':
                from werewolf.seer_manual import parse_form, pending as manual_pending
                proposed=parse_form(request.form,proposed,progress.board)
            _, progress = replay(proposed)
            if (advancing and not rules.allow_repeat_guard and proposed.get('hunters')==1 and
                    policy['night']=='max'):
                from werewolf.model_a_public import evaluate_public_game
                from werewolf.seer_future_uniform import FuturePending
                checked=evaluate_public_game(proposed,progress.board,rules,Strategy(**policy))
                if isinstance(checked,FuturePending):
                    raise ValueError('この盤面のmax継続はまだ計算できません。設定を確認してください。')
            if advancing and proposed.get('seer_mode')=='information-fixed-v1' and manual_pending(proposed):raise ValueError('Pending: '+manual_pending(proposed).reason)
            target = parse_target(progress, advancing)
            if advancing and target not in legal_targets(progress.board, rules, Strategy(**policy)):
                raise ValueError("この計算条件では、その対象への襲撃は実行できません。")
            if not advancing and target is None:
                target = state["selection"]
        except ValueError as exc:
            return render_main(state, str(exc), 400)
        history = state["history"]
        if advancing:
            history = history + [{**({"result_disclosure_model":state["result_disclosure_model"]} if state.get("result_disclosure_model") else {}),**({"seer_options":proposed["seer_options"].copy()} if proposed.get("seer_mode")=="information-fixed-v1" else {}), "target": target, "policy": policy.copy(), "claims": claims.copy(), "claim_policy": claim_policy.copy(), "strategy_ui":editor, **({"reports":reports} if reports or "reports" in state else {})}]
            progress = advance(progress, target, rules, Strategy(**policy))
        next_state = {**proposed, **({"reports":reports} if reports or "reports" in state else {}), "model": model, "policy": policy, "claims": claims, "claim_policy": claim_policy, "strategy_ui":editor, "history": history,
                           "selection": (target if progress.finished or not advancing else None),
                           "revision": state["revision"] + 1}
        from werewolf.public_log import migrate,project
        try:
            if "public_log" in next_state:next_state=project(next_state,migrate(next_state))
            _,progress=structural_replay(next_state) if advancing else replay(next_state)
        except ValueError as exc:return render_main(state,str(exc),400)
        session["game"]=next_state
        return redirect(url_for("result" if progress.finished else "main"), code=303)

    def table_proposal(state, payload):
        if dawn_enabled(state) and len(state['history']) % 2:
            raise ValueError('夜明けBoardでは死体報告を入力してください。')
        from werewolf.public_log_changes import transaction_changes,upgrade,declarations
        from werewolf.public_log import migrate
        active,_=declarations(upgrade(migrate(state)))
        if not isinstance(payload,dict) or set(payload)!={'claims','seers','mediums'}:raise ValueError('下書きの形式を確認してください。')
        claims=payload['claims']
        if not isinstance(claims,list) or len(claims)!=state['players']:raise ValueError('COを確認してください。')
        events=[]
        for player,(old,new) in enumerate(zip(state['claims'],claims),1):
            if old!=new:
                old_event=active.get(('co',player))
                if new=='latent':
                    if old_event:events.append({**old_event[1],'action':'withdraw','ref':old_event[1]['id']})
                else:events.append({'kind':'co','player':player,'role':new,**({'action':'change','ref':old_event[1]['id']} if old_event else {})})
        for kind,name,source in (('seer','seers','seer_inputs'),('medium','mediums','reports')):
            old={((r['day'],r['reporter']) if kind=='seer' else (r['day'],r['reporter'],r['target'])):r for r in state.get(source,[])}
            proposed=payload[name]
            if not isinstance(proposed,list) or any(not isinstance(r,dict) or type(r.get('reporter'))is not int or not 1<=r['reporter']<=state['players'] for r in proposed):raise ValueError('能力結果を確認してください。')
            proposed=[r for r in proposed if not (state['claims'][r['reporter']-1]==kind and claims[r['reporter']-1]!=kind)]
            if not isinstance(proposed,list):raise ValueError('能力結果を確認してください。')
            new={}
            for r in proposed:
                if not isinstance(r,dict) or set(r)!={'day','reporter','target','color'}:raise ValueError('能力結果を確認してください。')
                key=(r['day'],r['reporter']) if kind=='seer' else (r['day'],r['reporter'],r['target'])
                if key in new:raise ValueError('能力結果が重複しています。')
                new[key]=r
            for k,r in old.items():
                ref_key=(kind,*k);previous=active.get(ref_key)
                if k not in new and previous:events.append({**previous[1],'action':'withdraw','ref':previous[1]['id']})
                elif k in new and new[k]!=r and previous:events.append({'kind':kind,'player':new[k]['reporter'],'day':new[k]['day'],'target':new[k]['target'],'color':new[k]['color'],'action':'change','ref':previous[1]['id']})
            for k,r in new.items():
                if k not in old:
                    if r['target'] is None or r['color'] is None:raise ValueError('対象と色を入力してください。')
                    events.append({'kind':kind,'player':r['reporter'],'day':r['day'],'target':r['target'],'color':r['color']})
        if not events:return state,None
        _,p=structural_replay(state)
        batch={'mode':'simultaneous','events':events}
        return transaction_changes(state,p.last_board if p.finished else p.board,batch,finished=p.finished),batch

    @app.post('/private-view')
    def private_view():
        from flask import jsonify
        state = game(validate_roles=not wants_calculation_stream())
        if state is None or not dawn_enabled(state):
            return jsonify(error='夜の視点表示はこのBoardでは利用できません。'), 404
        if (not revision_matches(state) or request.form.getlist('board_id') != [state['public_log']['board_id']]):
            return jsonify(error='Boardが変更されています。再読み込みしてください。'), 409
        try:
            if set(request.form) != {'revision', 'board_id', 'payload'} or len(request.form.getlist('payload')) != 1:
                raise ValueError('視点入力の形式が不正です。')
            payload = json.loads(request.form['payload'])
            if (type(payload) is not dict or set(payload) != {'role', 'players', 'results'} or
                    payload['role'] not in ('wolf', 'seer', 'hunter') or
                    type(payload['players']) is not list or type(payload['results']) is not list):
                raise ValueError('視点入力の形式が不正です。')
            if wants_calculation_stream():
                def events():
                    from werewolf.board_roles import prepare_private
                    from werewolf.private_adapter import prepared_private_role_rows
                    source=board_data(state).roles()
                    if source.progress.finished or source.board.phase!='night':
                        raise ValueError('夜のBoardで視点を選択してください。')
                    strategy=Strategy(**state['policy'])
                    prepared=prepare_private(source.board,payload['role'],payload['players'],payload['results'],
                        source.rules,strategy,game_state=state,
                        max_work=app.config.get('MANUAL_CALC_MAX_WORK',DEFAULT_MAX_WORK),
                        max_seconds=app.config.get('MANUAL_CALC_MAX_SECONDS',DEFAULT_MAX_SECONDS))
                    identity={'board_id':state['public_log']['board_id'],'revision':state['revision']}
                    yield dict(event='roles',**prepared_private_role_rows(source.board,payload['role'],payload['players'],prepared),**identity)
                    result=source.private(payload['role'],payload['players'],payload['results'],_prepared=prepared,
                        max_work=app.config.get('MANUAL_CALC_MAX_WORK',DEFAULT_MAX_WORK),
                        max_seconds=app.config.get('MANUAL_CALC_MAX_SECONDS',DEFAULT_MAX_SECONDS))
                    if budget_stop() is not None:result={**result,'reason':stop_message(),'budget_kind':budget_stop()['kind']}
                    yield dict(event='complete',**result,**identity)
                return calculation_stream(events,view=payload['role'])
            # Replay only public evidence; the private Board is confined to this adapter.
            from werewolf.board_flow import BoardData
            private_source=board_data(state).roles()
            rules, progress = private_source.replay_result
            if progress.finished or progress.board.phase != 'night':
                raise ValueError('夜のBoardで視点を選択してください。')
            result = private_source.private(payload['role'], payload['players'], payload['results'],
                                            max_work=app.config.get('MANUAL_CALC_MAX_WORK',DEFAULT_MAX_WORK),
                                            max_seconds=app.config.get('MANUAL_CALC_MAX_SECONDS',DEFAULT_MAX_SECONDS))
            if budget_stop() is not None:result={**result,'reason':stop_message(),'budget_kind':budget_stop()['kind']}
            return jsonify(**result, board_id=state['public_log']['board_id'], revision=state['revision'])
        except (ValueError, TypeError, KeyError, DisclosureInconsistent) as exc:
            return jsonify(error=str(exc)), 400

    @app.post('/table-preview')
    def table_preview():
        from flask import jsonify
        if not app.config.get('HYBRID_TABLE_PREVIEW'):return jsonify(error='Not enabled'),404
        state=game(validate_roles=not wants_calculation_stream())
        if state is None or not revision_matches(state):return jsonify(error='確定状態が変わりました。再読み込みしてください。'),409
        try:
            if wants_calculation_stream():
                payload=json.loads(request.form.get('payload',''))
                request_id=request.form.get('request_id')
                def events():
                    proposed,batch=table_proposal(state,payload)
                    identity={'batch':batch,'request_id':request_id,
                              'revision':state['revision'],'board_id':state['public_log']['board_id']}
                    prepared=board_data(proposed).roles()
                    for stage in ('roles','complete'):
                        html,status=render_main(proposed,role_state=prepared,roles_only=stage=='roles')
                        yield dict(event=stage,html=html,**identity)
                return calculation_stream(events)
            proposed,batch=table_proposal(state,json.loads(request.form.get('payload','')))
            replay(proposed)
            html,status=render_main(proposed)
            return jsonify(html=html,batch=batch,request_id=request.form.get('request_id'),revision=state['revision'],board_id=state['public_log']['board_id']),status
        except (ValueError,TypeError,KeyError) as exc:return jsonify(error=str(exc),request_id=request.form.get('request_id')),400

    @app.post('/table-publish')
    def table_publish():
        from flask import jsonify
        if not app.config.get('HYBRID_TABLE_PREVIEW'):return jsonify(error='Not enabled'),404
        state=game()
        if state is None or not revision_matches(state):return jsonify(error='確定状態が変わりました。再読み込みしてください。'),409
        try:
            proposed,batch=table_proposal(state,json.loads(request.form.get('payload','')))
            replay(proposed)
            if batch is None:return jsonify(error='変更がありません。'),400
            from werewolf.board_owned_log import commit_owned_change
            proposed=commit_owned_change(state,proposed)
            proposed['revision']=state['revision']+1
        except (ValueError,TypeError,KeyError) as exc:return jsonify(error=str(exc)),400
        session['game']=proposed
        return jsonify(ok=True,revision=proposed['revision'])

    @app.post("/public-log")
    def public_log_route():
        from werewolf.public_log import transaction, validate_draft
        from flask import jsonify
        state=game()
        if state is None:return jsonify(error="保存されたゲームがありません。"),400
        if not revision_matches(state):return jsonify(error="画面が更新されています。再読み込みして確認してください。"),409
        if set(request.form)-{'revision','operation','payload','board_id'} or not {'revision','operation','payload'}<=set(request.form):return jsonify(error="公開操作の形式が不正です。"),400
        operation=request.form.get('operation')
        if dawn_enabled(state) and len(state['history']) % 2 and operation != 'cancel':
            return jsonify(error='夜明けBoardでは死体報告を入力してください。'),400
        if "public_log" not in state:
            from werewolf.public_log import migrate,project
            state=project(state,migrate(state))
        try:
            payload=json.loads(request.form['payload'])
            if operation=='cancel':
                proposed={**state};proposed.pop('public_draft',None)
            elif operation=='draft':
                validate_draft(payload)
                if len(json.dumps(payload))>3000:raise ValueError('下書きが大きすぎます。')
                proposed={**state,'public_draft':{'revision':state['revision'],'board_id':state['public_log']['board_id'],'payload':payload}}
            elif operation=='publish':
                _,progress=structural_replay(state)
                board=progress.last_board if progress.finished else progress.board
                from werewolf.board_owned_log import check_item_owner
                check_item_owner(state,payload)
                proposed=transaction(state,board,payload,finished=progress.finished)
                replay(proposed) # Validate the entire batch before committing any part.
                from werewolf.board_owned_log import commit_owned_change
                proposed=commit_owned_change(state,proposed)
                proposed['revision']=state['revision']+1
            else:raise ValueError('未対応の公開操作です。')
        except (ValueError,TypeError,KeyError) as exc:return jsonify(error=str(exc)),400
        session['game']=proposed
        return jsonify(ok=True,revision=proposed['revision'])

    @app.post("/advance")
    def advance_route():
        return change(True)

    @app.post("/strategy")
    def strategy_route():
        return change(False)

    @app.get("/result")
    def result():
        state = game()
        if state is None:
            return redirect(url_for("top"), code=303)
        if not structural_replay(state)[1].finished:
            return redirect(url_for("main"), code=303)
        return render_main(state)

    @app.post("/back")
    def back():
        state = game()
        if state is None:
            return redirect(url_for("top"), code=303)
        if not revision_matches(state):
            return render_main(state, "画面が更新されています。現在の画面を確認してください。", 409)
        if set(request.form) != {"revision"}:
            return render_main(state, "戻る操作の入力が不正です。", 400)
        if state["history"]:
            step = state["history"][-1]
            session["game"] = {**state, "history": state["history"][:-1], "policy": step["policy"],
                               "claims": step.get('claims', ['latent'] * state['players']),
                               "claim_policy": step.get('claim_policy', {}),
                               "strategy_ui":step.get("strategy_ui",co_editor(step.get("claim_policy",{}))),
                               **({"reports":step.get("reports",[])} if "reports" in state else {}), "selection": step["target"], "revision": state["revision"] + 1}
        if state.get("seer_mode")=="information-fixed-v1":
            from werewolf.seer_manual import trim_back
            session["game"]=trim_back({**session["game"],**({"reports":state["reports"]} if "reports" in state else {})})
        if "public_log" in session["game"]:
            from werewolf.public_log import trim
            session["game"]=trim(session["game"])
        session["game"].pop("public_draft",None)
        session.modified=True
        return redirect(url_for("main"), code=303)

    return app


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ww_gg local public Board v0.5.2")
    parser.add_argument("--port", type=int, default=8771)
    parser.add_argument("--hybrid-table-preview", action="store_true", help="Enable unpublished table draft preview locally")
    parser.add_argument("--dawn-board", action="store_true", help="Preview public dawn Boards")
    parser.add_argument("--seer-future-uniform", action="store_true", help="Enable unpublished fixed-policy seer forecast locally")
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error("Choose a port between 1024 and 65535")
    create_app({"DAWN_BOARD_PREVIEW":args.dawn_board,"HYBRID_TABLE_PREVIEW":args.hybrid_table_preview,"SEER_UNIFORM_FUTURE_PREVIEW":args.seer_future_uniform}).run(host="127.0.0.1", port=args.port, debug=False,
                     use_reloader=False, load_dotenv=False)
