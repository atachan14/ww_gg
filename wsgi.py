"""Vercel entrypoint; requires a user-configured stable signing key."""
from app import create_app

app = create_app(deployment=True)
