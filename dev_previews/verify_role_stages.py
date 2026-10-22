"""Bounded temporary app/browser; preserve normal18821 and its sessions."""
from pathlib import Path
import subprocess,tempfile,threading
from werkzeug.serving import make_server
from app import create_app
with tempfile.TemporaryDirectory(prefix='wwgg-counts-') as directory:
 app=create_app(dict(GAME_TREE_PREVIEW=True,HYBRID_TABLE_PREVIEW=True,ANONYMOUS_NIGHT_PREVIEW=True,PERSISTENT_TREE_PREVIEW=True,NAVIGATION_DIRECTORY=directory,MANUAL_CALC_MAX_WORK=500000,MANUAL_CALC_MAX_SECONDS=15))
 server=make_server('127.0.0.1',0,app,threaded=True);worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
 try:
  text=Path('dev_previews/verify_role_stages.cjs').read_text(encoding='utf-8').replace('http://127.0.0.1:18821','http://127.0.0.1:'+str(server.server_port));probe=Path(directory)/'verify.cjs';probe.write_text(text,encoding='utf-8')
  for n in ("hunter","medium"):subprocess.run(['node',str(probe),str(n)],check=True)
 finally:server.shutdown();server.server_close();worker.join()
