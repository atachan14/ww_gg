"""Vercel entrypoint; requires a user-configured stable signing key."""
from app import create_app

app = create_app({"HYBRID_TABLE_PREVIEW":True}, deployment=True)
