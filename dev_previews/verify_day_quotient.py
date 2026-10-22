"""Isolated real-browser check of representative day action generation."""
from pathlib import Path
import subprocess,tempfile,threading
from werkzeug.serving import make_server
from app import create_app
with tempfile.TemporaryDirectory(prefix='wwgg-quotient-') as directory:
 app=create_app(dict(GAME_TREE_PREVIEW=True,HYBRID_TABLE_PREVIEW=True,ANONYMOUS_NIGHT_PREVIEW=True,PERSISTENT_TREE_PREVIEW=True,NAVIGATION_DIRECTORY=directory,MANUAL_CALC_MAX_WORK=1500000,MANUAL_CALC_MAX_SECONDS=180))
 server=make_server('127.0.0.1',0,app,threaded=True);worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
 try:
  original=Path('dev_previews/verify_role_stages.cjs').read_text(encoding='utf-8')
  prefix=original.split("  const kind=process.argv[2]")[0]
  suffix=original[original.index(' }finally{if(ws)'):]
  body="""
  await navigate('http://127.0.0.1:18821/');
  await evaluate(`(async()=>{await fetch('/start',{method:'POST',body:new URLSearchParams({citizens:'3',seers:'1',mediums:'1',hunters:'0',wolves:'2',day:'random',night:'random',fake_reports:'random',win_cutoff:'0'})});})()`);
  const result=await evaluate(`(async()=>{const r=await fetch('/game-tree?expand=1');return {status:r.status,tree:await r.json()}})()`);
  assert.equal(result.status,200);assert.equal(result.tree.actions.length,1);
  const action=result.tree.actions[0];assert.deepEqual(action.targets,[1,2,3,4,5,6,7]);assert.equal(action.branches.length,1);assert.equal(action.branches[0].probability,'1');
  const night=await evaluate(`(async()=>{const r=await fetch('/game-tree?node=${action.branches[0].node}&expand=1');return {status:r.status,tree:await r.json()}})()`);
  assert.equal(night.status,200);const branches=night.tree.night_stages.branches;
  assert.equal(branches.find(b=>b.kind==='medium_result'&&b.value[1]==='black').probability,'2/7');assert.equal(branches.find(b=>b.kind==='medium_result'&&b.value[1]==='white').probability,'4/7');const skipped=branches.find(b=>b.kind==='ability_dead'&&b.value==='medium_result');assert.equal(skipped.probability,'1/7');assert.equal(skipped.label,'死亡済み');assert.equal(skipped.stage_column,0);
  assert.deepEqual(errors,[]);console.log('seven-player browser HTTP path passed: one execution, one night; medium 2/7,4/7,1/7');await call('Browser.close',{},null).catch(()=>{});
"""
  text=(prefix+body+suffix).replace('http://127.0.0.1:18821','http://127.0.0.1:'+str(server.server_port));probe=Path(directory)/'verify.cjs';probe.write_text(text,encoding='utf-8');subprocess.run(['node',str(probe)],check=True)
 finally:server.shutdown();server.server_close();worker.join()
