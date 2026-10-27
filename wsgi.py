"""Vercel entrypoint; requires a user-configured stable signing key."""
import os
from app import create_app

config={"REQUEST_LIFECYCLE_DIAGNOSTICS":False,"HYBRID_TABLE_PREVIEW":True,"SEER_UNIFORM_FUTURE_PREVIEW":True,"DAWN_BOARD_PREVIEW":True}
# Only the explicitly approved Preview candidate enables browser-owned history.
# Production keeps its existing entrypoint behavior and signing configuration.
if os.environ.get('VERCEL_ENV')=='preview':
    config.update(BROWSER_HISTORY_PREVIEW=True,GAME_TREE_PREVIEW=True,PERSISTENT_TREE_PREVIEW=True,ANONYMOUS_NIGHT_PREVIEW=True,ANONYMOUS_OWNERSHIP_PREVIEW=True)
app=create_app(config,deployment=True)
