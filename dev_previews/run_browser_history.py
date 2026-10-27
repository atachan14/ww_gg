"""Isolated browser-history prototype. Never production signing credentials."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import create_app
# Public local-only fixture key enables cold-process browser restoration tests.
app=create_app(dict(SECRET_KEY='browser-history-local-fixture-not-production',SESSION_COOKIE_NAME='wwgg_browser_prototype',BROWSER_HISTORY_PREVIEW=True,GAME_TREE_PREVIEW=True,PERSISTENT_TREE_PREVIEW=True,HYBRID_TABLE_PREVIEW=True,ANONYMOUS_NIGHT_PREVIEW=True,ANONYMOUS_OWNERSHIP_PREVIEW=True))
if __name__=='__main__':app.run(host='127.0.0.1',port=18823,threaded=True,debug=False,use_reloader=False,load_dotenv=False)
