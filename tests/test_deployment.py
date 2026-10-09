import hashlib
import importlib
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import create_app
from build_vercel import build

# Deliberately public test fixture, never a deployment credential.
TEST_KEY = "0123456789abcdef" * 4

class DeploymentTests(unittest.TestCase):
    def test_hosted_missing_and_invalid_key_fail_closed(self):
        for value in ("", "short", "x" * 64):
            with patch.dict(os.environ, {"WW_GG_SECRET_KEY": value}):
                with self.assertRaisesRegex(RuntimeError, "WW_GG_SECRET_KEY"):
                    create_app(deployment=True)
        with patch.dict(os.environ, {"VERCEL": "1", "WW_GG_SECRET_KEY": ""}):
            with self.assertRaises(RuntimeError):
                create_app()

    def test_entrypoint_stable_signed_cookie_across_instances(self):
        with patch.dict(os.environ, {"WW_GG_SECRET_KEY": TEST_KEY}):
            sys.modules.pop("wsgi", None)
            exported = importlib.import_module("wsgi").app
            other = create_app(deployment=True)
        self.assertTrue(exported.config["SESSION_COOKIE_SECURE"])
        first = exported.test_client()
        response = first.post("/start", base_url="https://example.test", data={"players":"5", "day":"max", "night":"max"})
        cookie = first.get_cookie("session", domain="example.test")
        second = other.test_client()
        second.set_cookie("session", cookie.value, domain="example.test")
        html = second.get("/main", base_url="https://example.test").get_data(as_text=True)
        self.assertIn('data-fraction="7/15"', html)
        self.assertIn("Secure", response.headers["Set-Cookie"])
        self.assertIn("HttpOnly", response.headers["Set-Cookie"])
        self.assertIn("SameSite=Lax", response.headers["Set-Cookie"])

    def test_tampered_cookie_has_no_board(self):
        app = create_app({"TESTING":True, "SECRET_KEY":TEST_KEY})
        c = app.test_client()
        c.post("/start", data={"players":"5", "day":"max", "night":"max"})
        original = c.get_cookie("session").value
        parts = original.split(".")
        parts[-1] = ("A" if parts[-1][0] != "A" else "B") + parts[-1][1:]
        c.set_cookie("session", ".".join(parts))
        response = c.get("/main")
        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.location, "/")

    def test_oversized_update_retains_previous_cookie(self):
        app = create_app({"TESTING":True, "SECRET_KEY":TEST_KEY})
        from flask import session
        @app.post("/test-large-update")
        def large_update():
            session["padding"] = "".join(hashlib.sha256(str(i).encode()).hexdigest() for i in range(200))
            return "updated"
        c = app.test_client()
        c.post("/start", data={"players":"5", "day":"max", "night":"max"})
        previous = c.get_cookie("session").value
        response = c.post("/test-large-update")
        self.assertEqual(response.status_code, 400)
        self.assertNotIn("Set-Cookie", response.headers)
        self.assertEqual(c.get_cookie("session").value, previous)
        self.assertEqual(c.get("/main").status_code, 200)

    def test_body_limits_cross_site_and_duplicate_fields(self):
        app = create_app({"TESTING":True, "SECRET_KEY":TEST_KEY})
        c = app.test_client()
        valid = {"players":"5", "day":"max", "night":"max"}
        self.assertEqual(c.post("/start", data=valid, headers={"Origin":"https://unrelated.test"}).status_code, 403)
        self.assertEqual(c.post("/start", data=valid, headers={"Sec-Fetch-Site":"cross-site"}).status_code, 403)
        self.assertEqual(c.post("/start", data=valid, headers={"Origin":"http://localhost"}).status_code, 303)
        self.assertEqual(c.post("/start", data="x=" + "a" * 4096, content_type="application/x-www-form-urlencoded").status_code, 413)
        from werkzeug.datastructures import MultiDict
        self.assertEqual(c.post("/start", data=MultiDict([*valid.items(), ("players","9")])).status_code, 400)
        self.assertEqual(c.post("/start", data={**valid, "players":"10"}).status_code, 400)

    def test_build_copies_only_first_party_css_js_to_public_static(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/"static").mkdir()
            (root/"static/app.js").write_text("fixture", encoding="utf-8")
            (root/"static/private.txt").write_text("excluded", encoding="utf-8")
            build(root)
            self.assertEqual((root/"public/static/app.js").read_text(), "fixture")
            self.assertFalse((root/"public/static/private.txt").exists())
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/"static").mkdir()
            for asset in Path("static").glob("*"):
                if asset.is_file():
                    (root/"static"/asset.name).write_bytes(asset.read_bytes())
            build(root)
            for name in ("styles.css", "app.js", "strategy.js", "parallel.js"):
                self.assertEqual((root/"public/static"/name).read_bytes(), (Path("static")/name).read_bytes())

    def test_vercel_uv_project_metadata_and_dependency_contract(self):
        import tomllib
        config = tomllib.loads(Path('pyproject.toml').read_text(encoding='utf-8'))
        project = config['project']
        self.assertEqual(project['name'], 'ww-gg')
        self.assertEqual(project['requires-python'], '>=3.12,<3.13')
        self.assertEqual(project['dependencies'], Path('requirements.txt').read_text().splitlines())
        self.assertEqual(config['tool']['vercel']['entrypoint'], 'wsgi:app')
        self.assertEqual(config['tool']['vercel']['scripts']['build'], 'python build_vercel.py')
