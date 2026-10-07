from fractions import Fraction
import re
import unittest

from werkzeug.datastructures import MultiDict

from app import create_app, percent


class MinimalWebTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app({"TESTING": True, "SECRET_KEY": "local-test-key"})
        self.client = self.app.test_client()

    def start(self, client=None):
        client = client or self.client
        return client.post("/start", data={"villagers": "2", "wolves": "1"}, follow_redirects=True)

    def state(self):
        with self.client.session_transaction() as session:
            return dict(session["game"])

    def execute(self, target, revision=None, client=None):
        client = client or self.client
        if revision is None:
            with client.session_transaction() as session:
                revision = session["game"]["revision"]
        return client.post("/execute", data={"revision": str(revision), "target": str(target)}, follow_redirects=True)

    def test_top_main_execution_and_result_for_every_target(self):
        for target in (1, 2, 3):
            with self.subTest(target=target):
                client = self.app.test_client()
                self.assertIn('data-screen="top"', client.get("/").get_data(as_text=True))
                main = self.start(client)
                self.assertIn('data-screen="main"', main.get_data(as_text=True))
                result = self.execute(target, client=client)
                html = result.get_data(as_text=True)
                self.assertEqual(result.status_code, 200)
                self.assertIn('data-screen="result"', html)
                self.assertRegex(html, r'id="village-rate"[^>]*data-fraction="1/3"[^>]*>33\.33%')
                self.assertRegex(html, r'id="wolf-rate"[^>]*data-fraction="2/3"[^>]*>66\.67%')
                self.assertIn(f"処刑対象：Player {target}", html)
                self.assertIn("すべての分岐で決着", html)
                self.assertIn("夜の襲撃は行いません", html)
                self.assertEqual(html.count('name="target"'), 3)
                self.assertEqual(len(re.findall(r'<input type="radio"[^>]*disabled', html)), 3)
                self.assertIn('id="advance-button" disabled', html)

    def test_main_starts_with_fixed_public_information_and_no_role_input(self):
        html = self.start().get_data(as_text=True)
        self.assertIn("全員生存・役職未確定", html)
        self.assertEqual(html.count('class="status alive"'), 3)
        self.assertEqual(html.count('<td class="muted">未確定</td>'), 3)
        self.assertNotIn('name="wolf_id"', html)
        self.assertNotIn('name="co"', html)
        self.assertEqual(self.state(), {"phase": "day", "revision": 0, "target": None})

    def test_information_panel_precedes_the_table_and_strategy(self):
        html = self.start().get_data(as_text=True)
        self.assertLess(html.index('id="information-panel"'), html.index('id="player-panel"'))
        self.assertLess(html.index('id="player-panel"'), html.index('id="strategy-panel"'))

    def test_fixed_cast_rejects_invalid_cast_and_injected_policy(self):
        for data in ({"villagers": "3", "wolves": "0"},
                     {"villagers": "2", "wolves": "1", "strategy": "max"},
                     {"villagers": "2", "wolves": "1", "wolf_id": "1"},
                     {"villagers": "2", "wolves": "1", "strategy": "uniform"}):
            with self.subTest(data=data):
                response = self.client.post("/start", data=data)
                self.assertEqual(response.status_code, 400)
                with self.client.session_transaction() as session:
                    self.assertNotIn("game", session)

    def test_invalid_target_keeps_the_initial_state(self):
        self.start()
        before = self.state()
        for target in ("", "0", "4", "-1", "1.0", "true", "<script>"):
            with self.subTest(target=target):
                response = self.execute(target)
                self.assertEqual(response.status_code, 400)
                self.assertIn("処刑対象を1人選んで", response.get_data(as_text=True))
                self.assertEqual(self.state(), before)

    def test_duplicate_target_fields_are_rejected(self):
        self.start()
        response = self.client.post("/execute", data=MultiDict([("revision", "0"), ("target", "1"), ("target", "2")]))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.state()["phase"], "day")

    def test_execution_cannot_inject_true_roles_or_another_strategy(self):
        self.start()
        for extra in ({"wolf_id": "1"}, {"strategy": "max"}, {"strategy": "uniform"}):
            response = self.client.post("/execute", data={"revision": "0", "target": "1", **extra})
            self.assertEqual(response.status_code, 400)
            self.assertEqual(self.state()["phase"], "day")

    def test_double_submission_is_idempotent_even_if_target_changes(self):
        self.start()
        self.execute(1)
        before = self.state()
        response = self.execute(3, revision=0)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.state(), before)
        self.assertIn("処刑対象：Player 1", response.get_data(as_text=True))

    def test_result_refresh_and_browser_back_do_not_execute_again(self):
        self.start()
        self.execute(2)
        before = self.state()
        for _ in range(3):
            response = self.client.get("/result")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(self.state(), before)
        response = self.client.get("/main")
        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers["Location"], "/result")

    def test_explicit_back_restores_pre_execution_analysis_and_rejects_stale_forms(self):
        self.start()
        self.execute(1)
        response = self.client.post("/back", data={"revision": "0"}, follow_redirects=True)
        html = response.get_data(as_text=True)
        self.assertIn('data-screen="main"', html)
        self.assertEqual(html.count('class="status alive"'), 3)
        self.assertEqual(self.state()["target"], 1)
        self.assertEqual(self.state()["revision"], 1)
        stale = self.execute(3, revision=0)
        self.assertEqual(stale.status_code, 409)
        self.assertEqual(self.state()["phase"], "day")
        self.assertIn("処刑対象：Player 3", self.execute(3).get_data(as_text=True))

    def test_result_is_unavailable_before_action_and_night_has_no_route(self):
        self.assertEqual(self.client.get("/result").headers["Location"], "/")
        self.start()
        self.assertEqual(self.client.get("/result").headers["Location"], "/main")
        self.execute(1)
        self.assertEqual(self.client.get("/night").status_code, 404)
        self.assertEqual(self.client.post("/night").status_code, 404)

    def test_request_without_a_started_game_does_not_create_a_state(self):
        response = self.client.post("/execute", data={"revision": "0", "target": "1"})
        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers["Location"], "/")
        with self.client.session_transaction() as session:
            self.assertNotIn("game", session)

    def test_pages_have_no_stale_cache_and_percent_is_only_display_rounding(self):
        response = self.start()
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        fraction = Fraction(1, 3)
        self.assertEqual(percent(fraction), "33.33")
        self.assertEqual(fraction, Fraction(1, 3))

    def test_no_equal_action_mixture_is_shown_or_stored(self):
        for page in (self.client.get("/"), self.start()):
            html = page.get_data(as_text=True)
            self.assertNotIn("全生存者から等確率", html)
            self.assertNotIn('name="strategy"', html)
        self.assertNotIn("strategy", self.state())
        self.assertIn("どの処刑対象でも同じ勝率", self.client.get("/main").get_data(as_text=True))

    def test_percentage_is_default_and_fraction_format_is_only_display_data(self):
        html = self.start().get_data(as_text=True)
        self.assertIn('id="display-panel"', html)
        self.assertIn('name="probability-format" value="percent" checked', html)
        self.assertIn('name="probability-format" value="fraction"', html)
        self.assertRegex(html, r'data-fraction="1/3" data-percent="33\.33%">33\.33%')
        self.assertIn("配役：村人 2 / 狼 1", html)
        before = self.state()
        self.client.get("/main")
        self.assertEqual(self.state(), before)
        self.assertEqual(percent(Fraction(1)), "100")
        self.assertEqual(percent(Fraction(0)), "0")
        self.assertEqual(percent(Fraction(1, 4)), "25")

    def test_two_browser_sessions_keep_their_selected_actions_separate(self):
        other = self.app.test_client()
        self.start()
        self.start(other)
        self.execute(1)
        self.execute(3, client=other)
        self.assertIn("処刑対象：Player 1", self.client.get("/result").get_data(as_text=True))
        self.assertIn("処刑対象：Player 3", other.get("/result").get_data(as_text=True))


if __name__ == "__main__":
    unittest.main()
