"""Vercel entrypoint; requires a user-configured stable signing key."""
import os
from app import create_app

app = create_app({"HYBRID_TABLE_PREVIEW":True,"SEER_UNIFORM_FUTURE_PREVIEW":True,"DAWN_BOARD_PREVIEW":os.environ.get("VERCEL_ENV")=="preview"}, deployment=True)
