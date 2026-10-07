"""Local-only V2/W1 web UI. No dotenv, database, external API, or role sampling."""

import argparse
from decimal import Decimal
from fractions import Fraction
import secrets

from flask import Flask, redirect, render_template, request, session, url_for

from werewolf.exact import PLAYERS, evaluate_execution, evaluate_uniform_strategy, initial_belief


def percent(value: Fraction) -> str:
    return str((Decimal(value.numerator) * 100 / Decimal(value.denominator)).quantize(Decimal("0.1")))


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=secrets.token_bytes(32),
        MAX_CONTENT_LENGTH=4096,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
    )
    if test_config:
        app.config.update(test_config)
    app.jinja_env.filters["percent"] = percent
    app.jinja_env.filters["fraction"] = str

    def game():
        value = session.get("game")
        if not isinstance(value, dict) or value.get("phase") not in ("day", "finished"):
            return None
        if type(value.get("revision")) is not int or value.get("strategy") != "uniform":
            return None
        target = value.get("target")
        if target is not None and (type(target) is not int or target not in PLAYERS):
            return None
        if value["phase"] == "finished" and target is None:
            return None
        return value

    def revision_matches(state):
        return request.form.getlist("revision") == [str(state["revision"])]

    def render_main(state, error=None, status=200):
        prior = initial_belief()
        finished = state["phase"] == "finished"
        chosen = evaluate_execution(prior, state["target"]) if finished else None
        rates = chosen or evaluate_uniform_strategy(prior)
        players = [{
            "id": player,
            "name": f"Player {player}",
            "status": "処刑" if finished and player == state["target"] else "生存",
            "village_probability": prior.role_probability(player, "village"),
            "wolf_probability": prior.role_probability(player, "wolf"),
            "action": evaluate_execution(prior, player),
        } for player in PLAYERS]
        return render_template("main.html", state=state, finished=finished, rates=rates,
                               chosen=chosen, players=players, error=error), status

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
        expected = {"villagers": "2", "wolves": "1", "strategy": "uniform"}
        if set(request.form) != set(expected) or any(request.form.getlist(key) != [value] for key, value in expected.items()):
            return render_template("top.html", error="最初の基準例は村人2・狼1、全生存者から等確率の処刑です。"), 400
        previous = game()
        session["game"] = {"phase": "day", "target": None, "strategy": "uniform",
                           "revision": previous["revision"] + 1 if previous else 0}
        return redirect(url_for("main"), code=303)

    @app.get("/main")
    def main():
        state = game()
        if state is None:
            return redirect(url_for("top"), code=303)
        if state["phase"] == "finished":
            return redirect(url_for("result"), code=303)
        return render_main(state)

    @app.post("/execute")
    def execute():
        state = game()
        if state is None:
            return redirect(url_for("top"), code=303)
        if state["phase"] == "finished":
            return redirect(url_for("result"), code=303)
        if not revision_matches(state):
            return render_main(state, "画面が更新されています。現在の画面からもう一度選んでください。", 409)
        if set(request.form) != {"revision", "target", "strategy"} or request.form.getlist("strategy") != ["uniform"]:
            return render_main(state, "この基準例の戦略・公開情報は固定です。", 400)
        target_values = request.form.getlist("target")
        if len(target_values) != 1 or target_values[0] not in {str(player) for player in PLAYERS}:
            return render_main(state, "処刑対象を1人選んでください。", 400)
        target = int(target_values[0])
        evaluation = evaluate_execution(initial_belief(), target)
        if not all(outcome.posterior.finished for outcome in evaluation.outcomes):
            raise RuntimeError("Nonterminal progression is outside the agreed three-player implementation")
        session["game"] = {**state, "target": target, "phase": "finished"}
        return redirect(url_for("result"), code=303)

    @app.get("/result")
    def result():
        state = game()
        if state is None:
            return redirect(url_for("top"), code=303)
        if state["phase"] != "finished":
            return redirect(url_for("main"), code=303)
        return render_main(state)

    @app.post("/back")
    def back():
        state = game()
        if state is None:
            return redirect(url_for("top"), code=303)
        if not revision_matches(state):
            return render_main(state, "画面が更新されています。現在の画面を確認してください。", 409)
        if state["phase"] == "finished":
            # Revisit the pre-execution analysis, without editing a real game history.
            session["game"] = {**state, "phase": "day", "revision": state["revision"] + 1}
        return redirect(url_for("main"), code=303)

    return app


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ww_gg local three-player baseline")
    parser.add_argument("--port", type=int, default=8771)
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error("Choose a port between 1024 and 65535")
    create_app().run(host="127.0.0.1", port=args.port, debug=False,
                     use_reloader=False, load_dotenv=False)
