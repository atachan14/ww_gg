"""Local public-Board analysis. No role assignment/sampling, dotenv, or database."""

import argparse
from decimal import Decimal
from fractions import Fraction
import secrets

from werewolf.comparison import compare_initial

from flask import Flask, redirect, render_template, request, session, url_for

from werewolf.exact import (ClaimPolicy, Progress, Rules, Strategy, Values, advance, build_tree,
                            condition_claims, group_initial_board, co_group_compositions, legal_targets, ROLES, VILLAGE_ROLES, ROLE_LABELS, MediumReport, condition_reports, available_medium_opportunities,
                            evaluate_tree, initial_board, validate_strategy)


def percent(value: Fraction) -> str:
    displayed = (Decimal(value.numerator) * 100 / Decimal(value.denominator)).quantize(Decimal("0.01"))
    return format(displayed, "f").rstrip("0").rstrip(".")


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.update(SECRET_KEY=secrets.token_bytes(32), MAX_CONTENT_LENGTH=4096,
                      SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax")
    if test_config:
        app.config.update(test_config)
    app.jinja_env.filters["percent"] = percent
    app.jinja_env.filters["fraction"] = str
    app.jinja_env.globals.update(role_labels=ROLE_LABELS, role_order=ROLES)

    def with_claims(progress, claims, policy, initial_group=False):
        board = (group_initial_board(progress.board, claims, policy) if initial_group else condition_claims(progress.board, claims, policy))
        return Progress(board, progress.settled_village, progress.settled_wolf,
                        progress.last_board, progress.last_outcomes)

    def with_reports(progress, reports):
        board=condition_reports(progress.board,tuple(MediumReport(**r) for r in reports))
        return Progress(board,progress.settled_village,progress.settled_wolf,progress.last_board,progress.last_outcomes)

    def replay(state):
        rules = Rules(**state["rules"])
        progress = Progress(initial_board(state["players"], state.get("wolves", 1), state.get("mediums", 0), state.get("seers",0), state.get("hunters",0)))
        if len(state["history"]) > state["players"] - 2:
            raise ValueError("Too much history")
        for index, step in enumerate(state["history"]):
            if set(step) not in ({"target", "policy"}, {"target", "policy", "claims", "claim_policy"}, {"target","policy","claims","claim_policy","reports"}):
                raise ValueError("Invalid history")
            if "claims" in step:
                progress = with_claims(progress, tuple(step["claims"]), ClaimPolicy(**step["claim_policy"]), initial_group=index==0 and state.get("model","equal")=="group")
            if not progress.finished and step.get('reports'):
                progress = with_reports(progress, step['reports'])
            progress = advance(progress, step["target"], rules, Strategy(**step["policy"]))
        validate_strategy(rules, Strategy(**state["policy"]))
        if not progress.finished:
            progress = with_claims(progress, tuple(state.get("claims", ['latent'] * state["players"])),
                                   ClaimPolicy(**state.get("claim_policy", {})), initial_group=not state["history"] and state.get("model","equal")=="group")
            if state.get('reports'):
                progress = with_reports(progress, state['reports'])
        return rules, progress

    def game():
        state = session.get("game")
        try:
            required = {"players", "rules", "policy", "history", "selection", "revision"}
            if not isinstance(state, dict) or not required <= set(state) or not set(state) <= required | {"wolves", "mediums", "claims", "claim_policy", "model", "seers", "hunters", "reports"}:
                return None
            if type(state["revision"]) is not int or state["revision"] < 0 or not isinstance(state["history"], list):
                return None
            if state.get("model","equal") not in ("equal","group"):
                return None
            _, progress = replay(state)
            target = state["selection"]
            if target is not None and (type(target) is not int or not 1 <= target <= state["players"]):
                return None
            if not progress.finished and target is not None and target not in progress.board.alive:
                return None
        except (ValueError, TypeError, KeyError):
            return None
        return state

    def revision_matches(state):
        return request.form.getlist("revision") == [str(state["revision"])]

    def parse_policy(rules, state=None):
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
        strategy = Strategy(one("day"), one("night"), inclusion == ["1"],report_mode)
        validate_strategy(rules, strategy)
        return {"day":strategy.day,"night":strategy.night,"include_self_bite":strategy.include_self_bite,**({"fake_reports":strategy.fake_reports} if reports or state and "fake_reports" in state["policy"] else {})}

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

    def render_main(state, error=None, status=200):
        rules, progress = replay(state)
        strategy = Strategy(**state["policy"])
        finished = progress.finished
        board = progress.last_board if finished else progress.board
        if finished:
            primary = Values(sum((outcome.probability * int(outcome.board.winner == "village") for outcome in progress.last_outcomes), Fraction(0)),
                             sum((outcome.probability * int(outcome.board.winner == "wolf") for outcome in progress.last_outcomes), Fraction(0)))
            cumulative = progress.total_values()
            action_values = {}
            event_history = progress.last_outcomes[0].board.history
            alive = progress.last_outcomes[0].board.alive
        else:
            root = build_tree(board, rules, strategy)
            evaluation = evaluate_tree(root, strategy)
            primary = evaluation.board_value(root)
            cumulative = progress.total_values(primary)
            action_values = {target: evaluation.action_value(root, target) for target in legal_targets(board, rules, strategy)}
            event_history, alive = board.history, board.alive
        deaths = {event.target: "処刑" if event.phase == "day" else "襲撃" for event in event_history}
        players = []
        for player in range(1, state["players"] + 1):
            wolf = (sum((outcome.probability * outcome.board.wolf_probability(player) for outcome in progress.last_outcomes), Fraction(0))
                    if finished else board.wolf_probability(player))
            medium = (sum((outcome.probability * outcome.board.role_probability(player, 'medium') for outcome in progress.last_outcomes), Fraction(0))
                      if finished else board.role_probability(player, 'medium'))
            players.append({"medium_probability": medium, "citizen_probability": (sum((o.probability*o.board.role_probability(player,"villager") for o in progress.last_outcomes),Fraction(0)) if finished else board.role_probability(player,"villager")),
                            "extra_probabilities": {r:(sum((o.probability*o.board.role_probability(player,r) for o in progress.last_outcomes),Fraction(0)) if finished else board.role_probability(player,r)) for r in ("seer","hunter")},
                            "claim": board.claims[player - 1], "legal": player in action_values,
                            "id": player, "name": f"Player {player}", "status": deaths.get(player, "生存"),
                            "alive": player in alive, "wolf_probability": wolf, "village_probability": 1 - wolf,
                            "action": action_values.get(player)})
        display_selection = state['selection']
        if not finished and display_selection is None and getattr(strategy, board.phase) == 'max':
            score = 'village_win' if board.phase == 'day' else 'wolf_win'
            best = max(getattr(value, score) for value in action_values.values())
            display_selection = min(target for target, value in action_values.items() if getattr(value, score) == best)
        return render_template("main.html", state=state, display_selection=display_selection, report_opportunities=available_medium_opportunities(board) if not finished else (), report_colors={(r.day,r.reporter,r.target):r.color for r in board.reports}, rules=rules, progress=progress,
                               board=board, finished=finished, rates=primary, cumulative=cumulative,
                               players=players, error=error, co_groups=co_group_compositions(board) if not finished and state.get("model")=="group" else [], claim_policy=ClaimPolicy(**state.get("claim_policy", {})), counts=(progress.last_outcomes[0].board.wolf_count_distribution if finished else board.wolf_count_distribution)), status

    @app.after_request
    def no_stale_pages(response):
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

    @app.get("/")
    def top():
        return render_template("top.html", error=None)

    @app.post("/start")
    def start():
        try:
            allowed = {"players", "wolves", "citizens", "mediums", "seers", "hunters", "day", "night", "allow_self_bite", "include_self_bite", "fake_reports", "cco_villager", "cco_medium", "model"}
            allowed |= {'cco_'+role for role in VILLAGE_ROLES}
            allowed |= {'cco_present_' + role for role in VILLAGE_ROLES} | {'cco_conditions_' + role for role in VILLAGE_ROLES}
            if not set(request.form) <= allowed:
                raise ValueError("配役と計算条件を確認してください。")
            def count(key, default=None):
                values = request.form.getlist(key)
                if not values and default is not None:
                    return default
                if len(values) != 1 or values[0] not in {str(n) for n in range(10)}:
                    raise ValueError("配役の人数は0〜9の整数で指定してください。")
                return int(values[0])
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
            initial_board(players, wolves, mediums, seers, hunters)
            claim_policy = parse_claim_policy()
            models=request.form.getlist("model")
            if models not in ([],["group"]):
                raise ValueError("計算モデルを確認してください。")
            model="group"
            permission = request.form.getlist("allow_self_bite")
            if permission not in ([], ["1"]):
                raise ValueError("自噛みのルールが不正です。")
            rules = Rules(bool(permission))
            policy = parse_policy(rules)
        except ValueError as exc:
            return render_template("top.html", error=str(exc)), 400
        previous = game()
        session["game"] = {**({"seers":seers,"hunters":hunters} if seers or hunters else {}), "players": players, "wolves": wolves, "mediums": mediums,
                           "model": model, "claims": ['latent'] * players, "claim_policy": claim_policy, "rules": {"allow_self_bite": rules.allow_self_bite},
                           "policy": policy, "history": [], "selection": None,
                           "revision": previous["revision"] + 1 if previous else 0}
        return redirect(url_for("main"), code=303)

    @app.get("/main")
    def main():
        state = game()
        if state is None:
            return redirect(url_for("top"), code=303)
        if replay(state)[1].finished:
            return redirect(url_for("result"), code=303)
        return render_main(state)

    def change(advancing):
        state = game()
        if state is None:
            return redirect(url_for("top"), code=303)
        rules, progress = replay(state)
        if progress.finished:
            return redirect(url_for("result"), code=303)
        if not revision_matches(state):
            return render_main(state, "画面が更新されています。現在の画面で選び直してください。", 409)
        try:
            allowed = {"revision", "target", "day", "night", "include_self_bite", "fake_reports", "cco_villager", "cco_medium", "model"} | {'co_' + str(i) for i in range(1, state['players'] + 1)}
            allowed |= {'cco_'+role for role in VILLAGE_ROLES}
            allowed |= {'cco_present_' + role for role in VILLAGE_ROLES} | {'cco_conditions_' + role for role in VILLAGE_ROLES}
            allowed |= {f'report_{day}_{reporter}_{target}' for day,reporter,target in available_medium_opportunities(progress.board)}
            if not set(request.form) <= allowed:
                raise ValueError("この画面では対象と戦略を指定してください。")
            models=request.form.getlist('model')
            if models not in ([],['equal'],['group']):
                raise ValueError('計算モデルを確認してください。')
            model=models[0] if models else state.get('model','equal')
            if model!=state.get('model','equal'):
                raise ValueError('このBoardのモデルは変更できません。TOPから新規開始してください。')
            policy = parse_policy(rules,state)
            claims = parse_claims(state)
            claim_policy = parse_claim_policy(state)
            reports=parse_reports(state,progress.board)
            proposed={**state,'model':model,'policy':policy,'claims':claims,'claim_policy':claim_policy}
            if reports or 'reports' in state:proposed['reports']=reports
            _, progress = replay(proposed)
            target = parse_target(progress, advancing)
            if advancing and target not in legal_targets(progress.board, rules, Strategy(**policy)):
                raise ValueError("この計算条件では、その対象への襲撃は実行できません。")
            if not advancing and target is None:
                target = state["selection"]
        except ValueError as exc:
            return render_main(state, str(exc), 400)
        history = state["history"]
        if advancing:
            history = history + [{"target": target, "policy": policy.copy(), "claims": claims.copy(), "claim_policy": claim_policy.copy(), **({"reports":reports} if reports or "reports" in state else {})}]
            progress = advance(progress, target, rules, Strategy(**policy))
        session["game"] = {**state, **({"reports":reports} if reports or "reports" in state else {}), "model": model, "policy": policy, "claims": claims, "claim_policy": claim_policy, "history": history,
                           "selection": (target if progress.finished or not advancing else None),
                           "revision": state["revision"] + 1}
        return redirect(url_for("result" if progress.finished else "main"), code=303)

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
        if not replay(state)[1].finished:
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
                               **({"reports":step.get("reports",[])} if "reports" in state else {}), "selection": step["target"], "revision": state["revision"] + 1}
        return redirect(url_for("main"), code=303)

    return app


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ww_gg local public Board v0.4")
    parser.add_argument("--port", type=int, default=8771)
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error("Choose a port between 1024 and 65535")
    create_app().run(host="127.0.0.1", port=args.port, debug=False,
                     use_reloader=False, load_dotenv=False)
