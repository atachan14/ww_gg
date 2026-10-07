"""Local public-Board analysis. No role assignment/sampling, dotenv, or database."""

import argparse
from decimal import Decimal
from fractions import Fraction
import secrets

from flask import Flask, redirect, render_template, request, session, url_for

from werewolf.exact import (Progress, Rules, Strategy, Values, advance, build_tree,
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

    def replay(state):
        rules = Rules(**state["rules"])
        progress = Progress(initial_board(state["players"]))
        if len(state["history"]) > 3:
            raise ValueError("Too much history")
        for step in state["history"]:
            if set(step) != {"target", "policy"}:
                raise ValueError("Invalid history")
            progress = advance(progress, step["target"], rules, Strategy(**step["policy"]))
        validate_strategy(rules, Strategy(**state["policy"]))
        return rules, progress

    def game():
        state = session.get("game")
        try:
            if not isinstance(state, dict) or set(state) != {"players", "rules", "policy", "history", "selection", "revision"}:
                return None
            if type(state["revision"]) is not int or state["revision"] < 0 or not isinstance(state["history"], list):
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

    def parse_policy(rules):
        def one(key):
            values = request.form.getlist(key)
            if len(values) != 1:
                raise ValueError("戦略を昼・夜それぞれ1つ指定してください。")
            return values[0]
        inclusion = request.form.getlist("include_self_bite")
        if inclusion not in ([], ["1"]):
            raise ValueError("自噛みの設定が不正です。")
        strategy = Strategy(one("day"), one("night"), bool(inclusion))
        validate_strategy(rules, strategy)
        return {"day": strategy.day, "night": strategy.night, "include_self_bite": strategy.include_self_bite}

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
            action_values = {action.target: evaluation.action_value(root, action.target) for action in root.actions}
            event_history, alive = board.history, board.alive
        deaths = {event.target: "処刑" if event.phase == "day" else "襲撃" for event in event_history}
        players = []
        for player in range(1, state["players"] + 1):
            wolf = (sum((outcome.probability * outcome.board.wolf_probability(player) for outcome in progress.last_outcomes), Fraction(0))
                    if finished else board.wolf_probability(player))
            players.append({"id": player, "name": f"Player {player}", "status": deaths.get(player, "生存"),
                            "alive": player in alive, "wolf_probability": wolf, "village_probability": 1 - wolf,
                            "action": action_values.get(player)})
        return render_template("main.html", state=state, rules=rules, progress=progress,
                               board=board, finished=finished, rates=primary, cumulative=cumulative,
                               players=players, error=error), status

    @app.after_request
    def no_stale_pages(response):
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @app.get("/")
    def top():
        return render_template("top.html", error=None)

    @app.post("/start")
    def start():
        try:
            allowed = {"players", "day", "night", "allow_self_bite", "include_self_bite"}
            if not set(request.form) <= allowed or request.form.getlist("players") not in (["3"], ["4"], ["5"]):
                raise ValueError("人数は3・4・5人から選んでください。")
            permission = request.form.getlist("allow_self_bite")
            if permission not in ([], ["1"]):
                raise ValueError("自噛みのルールが不正です。")
            rules = Rules(bool(permission))
            policy = parse_policy(rules)
        except ValueError as exc:
            return render_template("top.html", error=str(exc)), 400
        previous = game()
        session["game"] = {"players": int(request.form["players"]), "rules": {"allow_self_bite": rules.allow_self_bite},
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
            if not set(request.form) <= {"revision", "target", "day", "night", "include_self_bite"}:
                raise ValueError("この画面では対象と戦略を指定してください。")
            policy = parse_policy(rules)
            target = parse_target(progress, advancing)
            if not advancing and target is None:
                target = state["selection"]
        except ValueError as exc:
            return render_main(state, str(exc), 400)
        history = state["history"]
        if advancing:
            history = history + [{"target": target, "policy": policy.copy()}]
            progress = advance(progress, target, rules, Strategy(**policy))
        session["game"] = {**state, "policy": policy, "history": history,
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
                               "selection": step["target"], "revision": state["revision"] + 1}
        return redirect(url_for("main"), code=303)

    return app


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ww_gg local public Board v0.1")
    parser.add_argument("--port", type=int, default=8771)
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error("Choose a port between 1024 and 65535")
    create_app().run(host="127.0.0.1", port=args.port, debug=False,
                     use_reloader=False, load_dotenv=False)
