"""Run the normal local UI on a separate cookie-isolated port; no old session reset."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import create_app
create_app({'GAME_TREE_PREVIEW':True,'SESSION_COOKIE_NAME':'wwgg_current_local'}).run(host='127.0.0.1',port=18803,debug=False,use_reloader=False,load_dotenv=False)
