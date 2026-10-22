"""Fresh-browser, temporary-app smoke proving the joined boundary is exercised."""
from pathlib import Path
import subprocess,tempfile,threading
from unittest.mock import patch
from werkzeug.serving import make_server
from app import create_app
import werewolf.anonymous_materialization as materialization

with tempfile.TemporaryDirectory(prefix='wwgg-materialization-') as directory:
 app=create_app(dict(GAME_TREE_PREVIEW=True,HYBRID_TABLE_PREVIEW=True,ANONYMOUS_NIGHT_PREVIEW=True,PERSISTENT_TREE_PREVIEW=True,NAVIGATION_DIRECTORY=directory,MANUAL_CALC_MAX_WORK=500000,MANUAL_CALC_MAX_SECONDS=15))
 original=materialization.expand_laws;calls=[]
 def measured(laws,groups):
  rows=original(laws,groups);calls.append(tuple(len(row) for row in rows));return rows
 server=make_server('127.0.0.1',0,app,threaded=True);worker=threading.Thread(target=server.serve_forever,daemon=True)
 with patch.object(materialization,'expand_laws',measured):
  worker.start()
  try:
   text=Path('dev_previews/verify_role_stages.cjs').read_text(encoding='utf-8').replace('http://127.0.0.1:18821','http://127.0.0.1:'+str(server.server_port))
   old="citizens:'${kind==='medium'?3:2}',seers:'0',mediums:'${kind==='medium'?1:0}',hunters:'${kind==='hunter'?1:0}'"
   assert old in text;text=text.replace(old,"citizens:'3',seers:'1',mediums:'0',hunters:'0'")
   text=text.replace("kind==='hunter'?'guard_target':'medium_result'","kind==='hunter'?'guard_target':'seer_target'")
   text=text.replace("assert.equal(result.stats.ability_adapters,true);assert.ok(result.stats.relational_families<result.stats.named_prior_atoms)","assert.equal(result.stats.belief_owned,true);assert.equal(result.stats.named_prior_atoms,0)")
   text=text.replace("kind==='hunter'?'護衛位置':'霊能結果'","kind==='hunter'?'護衛位置':'占い位置'")
   probe=Path(directory)/'verify.cjs';probe.write_text(text,encoding='utf-8');subprocess.run(['node',str(probe),'seer'],check=True)
   assert calls,'Joined source boundary was not exercised';print('joined_boundary_requests',len(calls),'largest_named_law',max(max(row) for row in calls))
  finally:server.shutdown();server.server_close();worker.join()
