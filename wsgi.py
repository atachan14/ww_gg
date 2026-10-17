"""Vercel entrypoint; requires a user-configured stable signing key."""
from app import create_app

app = create_app({"REQUEST_LIFECYCLE_DIAGNOSTICS":False,"HYBRID_TABLE_PREVIEW":True,"SEER_UNIFORM_FUTURE_PREVIEW":True,"DAWN_BOARD_PREVIEW":True}, deployment=True)
