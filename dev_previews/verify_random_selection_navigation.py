"""Actual Footer random selection/back/alternative representative browser smoke."""
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
from werkzeug.serving import make_server
from app import create_app
import subprocess
with TemporaryDirectory() as directory:
 app=create_app(dict(TESTING=True,SECRET_KEY='isolated-random-selection',PERSISTENT_TREE_PREVIEW=True,GAME_TREE_PREVIEW=True,HYBRID_TABLE_PREVIEW=True,ANONYMOUS_NIGHT_PREVIEW=True,NAVIGATION_DIRECTORY=directory))
 server=make_server('127.0.0.1',0,app,threaded=True);worker=Thread(target=server.serve_forever,daemon=True);worker.start()
 try:
  original=Path('dev_previews/verify_role_stages.cjs').read_text(encoding='utf-8');prefix=original.split("  const kind=process.argv[2]")[0];suffix=original[original.index(' }finally{if(ws)'):]
  body=r"""
  await navigate('http://127.0.0.1:18821/');
  await evaluate(`fetch('/start',{method:'POST',body:new URLSearchParams({citizens:'2',seers:'1',hunters:'1',wolves:'1',day:'random',night:'random',fake_reports:'random',win_cutoff:'0'})})`);
  await navigate('http://127.0.0.1:18821/main');
  await wait(()=>evaluate(`document.querySelector('main')?.dataset.tableInitialized==='true'`));
  const before=await evaluate(`fetch('/game-tree?expand=1').then(r=>r.json())`);assert.equal(before.current_node,'h0~0');
  await evaluate(`document.querySelector('[data-status-target="3"]').click();document.querySelector('#advance-button').click()`);
  await wait(()=>evaluate(`document.querySelector('main')?.dataset.navigationOccurrence!=='h0'&&document.querySelector('main')?.dataset.tableInitialized==='true'`),90000);
  const first=await evaluate(`fetch('/navigation').then(r=>r.json())`);assert.equal(first.board.phase,'night');assert.ok(!first.board.alive.includes(3));
  await evaluate(`document.querySelector('#back-button').click()`);
  await wait(()=>evaluate(`document.querySelector('main')?.dataset.navigationOccurrence==='h0'&&document.querySelector('main')?.dataset.tableInitialized==='true'`),90000);
  await evaluate(`document.querySelector('[data-status-target="2"]').click();document.querySelector('#advance-button').click()`);
  await wait(()=>evaluate(`document.querySelector('main')?.dataset.navigationOccurrence!=='h0'&&document.querySelector('main')?.dataset.tableInitialized==='true'`),90000);
  const second=await evaluate(`fetch('/navigation').then(r=>r.json())`);assert.equal(second.board.phase,'night');assert.ok(!second.board.alive.includes(2));assert.ok(second.board.alive.includes(3));
  const after=await evaluate(`fetch('/game-tree?expand=1').then(r=>r.json())`);assert.equal(after.village_win,before.village_win);
  assert.deepEqual(errors,[]);console.log('PASS actual random Footer execute3 -> back -> execute2; correct representative/dead identities and unchanged root value');
  await call('Browser.close',{},null).catch(()=>{});
"""
  probe=Path(directory)/'verify.cjs';probe.write_text((prefix+body+suffix).replace('http://127.0.0.1:18821','http://127.0.0.1:'+str(server.server_port)),encoding='utf-8')
  subprocess.run(['node',str(probe)],check=True,timeout=180)
 finally:server.shutdown();server.server_close();worker.join()
