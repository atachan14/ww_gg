"""Local-only UI fault injection. Never imported by wsgi.py or deployed."""
import sys,time,argparse
from pathlib import Path
from threading import Lock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from flask import request,session
from app import create_app
from werewolf.navigation_evaluation import NavigationEvaluation
from werewolf.calculation_budget import calculation_budget,tick

def create_probe(mode):
 app=create_app(dict(SECRET_KEY='browser-history-local-fixture-not-production',SESSION_COOKIE_NAME='wwgg_ui_probe_'+mode,BROWSER_HISTORY_PREVIEW=True,GAME_TREE_PREVIEW=True,PERSISTENT_TREE_PREVIEW=True,HYBRID_TABLE_PREVIEW=True,ANONYMOUS_NIGHT_PREVIEW=True,ANONYMOUS_OWNERSHIP_PREVIEW=True))
 original=NavigationEvaluation.forecast;seen=set();lock=Lock()
 def forecast(self,*a,**kw):
  if request.path=='/navigation/calculation':
   owner=session.get('co_display_game')
   with lock:first=owner not in seen;seen.add(owner)
   if mode=='fail' and first:raise ValueError('UI probe: recoverable failure')
   if mode=='time' and first:
    with calculation_budget(max_seconds=.05):
     for _ in range(100):time.sleep(.005);tick(0)
   if mode=='delay' and self.current.roles.board.phase=='night':
    for _ in range(100):time.sleep(.05);tick(0)
  return original(self,*a,**kw)
 NavigationEvaluation.forecast=forecast
 return app
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--mode',choices=['time','fail','delay'],required=True);parser.add_argument('--port',type=int,default=18824);args=parser.parse_args()
 create_probe(args.mode).run(host='127.0.0.1',port=args.port,threaded=True,debug=False,use_reloader=False,load_dotenv=False)
