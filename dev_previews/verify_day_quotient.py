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
  assert.equal(night.tree.night_stages.method,'evaluation-recorded-v1');assert.equal(night.tree.evaluation_trace.owner,'evaluator');assert.deepEqual(night.tree.stage_roles,{seers:0,mediums:0,hunters:0});assert.equal(branches.length,1);assert.equal(branches[0].kind,'public_attack');assert.equal(branches[0].probability,'1');

  await navigate('http://127.0.0.1:18821/main');
  await wait(()=>evaluate(`document.querySelector('main')?.dataset.tableInitialized==='true'`));
  await wait(()=>evaluate(`['complete','error'].includes(document.querySelector('[data-calculation-tree]')?.dataset.treeAuto)`),90000);console.log('tree state',await evaluate(`document.querySelector('[data-calculation-tree]').dataset.treeAuto`),errors);assert.equal(await evaluate(`document.querySelector('[data-calculation-tree]').dataset.treeAuto`),'complete');
  const text=await evaluate(`document.querySelector('[data-calculation-tree]').innerText`);
  assert.ok(text.includes('襲撃位置'));assert.ok(text.includes('死亡通知'));assert.ok(!text.includes('霊能結果'));assert.ok(!text.includes('占い位置'));assert.ok(!text.includes('占い結果'));
  // Choose a concrete noncanonical execution through the real Board Table/Footer.
  await evaluate(`document.querySelector('[data-status-target="6"]').click()`);
  console.log('selection',await evaluate(`document.querySelector('#advance-button').outerHTML`));
  await wait(()=>evaluate(`!document.querySelector('#advance-button').disabled`));await evaluate(`document.querySelector('#advance-button').click()`);
  await wait(()=>evaluate(`document.querySelector('main')?.dataset.navigationOccurrence==='h1'&&document.querySelector('main')?.dataset.tableInitialized==='true'`));
  await wait(()=>evaluate(`document.querySelector('[data-calculation-tree]')?.dataset.navigationUpdate==='complete'`),180000);
  const mapped=await evaluate(`(async()=>{return await(await fetch('/game-tree?node=h1~0&expand=1')).json()})()`);
  assert.ok(!mapped.alive.includes(6));assert.ok(!mapped.night_stages.branches[0].targets.includes(6));
  const destination=mapped.night_stages.branches[0].children.branches[0].children.leaves[0].node;
  await wait(()=>evaluate(`!!document.querySelector('[data-tree-item="${destination}"] .compact-tree-go')`));
  await evaluate(`document.querySelector('[data-tree-item="${destination}"] .compact-tree-go').click()`);
  await wait(()=>evaluate(`document.querySelector('main')?.dataset.navigationOccurrence==='h2'&&document.querySelector('main')?.dataset.tableInitialized==='true'`));
  const nav=await evaluate(`(async()=>{return await(await fetch('/navigation')).json()})()`);assert.equal(nav.board.day,2);assert.ok(!nav.board.alive.includes(6));
  await evaluate(`document.querySelector('[data-calculation-tree]').scrollIntoView({block:'start'})`);
  await fs.writeFile('.artifacts/evaluator-graph-desktop.png',Buffer.from((await call('Page.captureScreenshot',{format:'png'})).data,'base64'));
  await call('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});
  await fs.writeFile('.artifacts/evaluator-graph-mobile.png',Buffer.from((await call('Page.captureScreenshot',{format:'png'})).data,'base64'));
  assert.deepEqual(errors,[]);console.log('seven-player evaluator-graph browser: dynamic columns, representative6, Footer/Current PASS');await call('Browser.close',{},null).catch(()=>{});

"""
  text=(prefix+body+suffix).replace('http://127.0.0.1:18821','http://127.0.0.1:'+str(server.server_port));probe=Path(directory)/'verify.cjs';probe.write_text(text,encoding='utf-8');subprocess.run(['node',str(probe)],check=True)
 finally:server.shutdown();server.server_close();worker.join()
