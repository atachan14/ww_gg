"""Run the normal local UI on a separate cookie-isolated port; no old session reset."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import create_app
import argparse
p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=18803);args=p.parse_args()
create_app({'GAME_TREE_PREVIEW':True,'HYBRID_TABLE_PREVIEW':True,'ANONYMOUS_NIGHT_PREVIEW':True,'SESSION_COOKIE_NAME':'wwgg_current_local' if args.port==18803 else 'wwgg_current_local_'+str(args.port)}).run(host='127.0.0.1',port=args.port,debug=False,use_reloader=False,load_dotenv=False)
