"""Isolated browser verification of evaluator-recorded morning publication."""
from pathlib import Path
import subprocess,tempfile,threading
from werkzeug.serving import make_server
from app import create_app
with tempfile.TemporaryDirectory(prefix='wwgg-recorded-reports-') as directory:
 app=create_app(dict(GAME_TREE_PREVIEW=True,HYBRID_TABLE_PREVIEW=True,ANONYMOUS_NIGHT_PREVIEW=True,PERSISTENT_TREE_PREVIEW=True,NAVIGATION_DIRECTORY=directory,MANUAL_CALC_MAX_WORK=4000000,MANUAL_CALC_MAX_SECONDS=90))
 server=make_server('127.0.0.1',0,app,threaded=True);worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
 try:
  original=Path('dev_previews/verify_role_stages.cjs').read_text(encoding='utf-8');prefix=original.split("  const kind=process.argv[2]")[0];suffix=original[original.index(' }finally{if(ws)'):]
  body="""
  await navigate('http://127.0.0.1:18821/');
  await evaluate(`(async()=>{await fetch('/start',{method:'POST',body:new URLSearchParams({citizens:'3',seers:'1',mediums:'0',hunters:'0',wolves:'1',day:'max',night:'max',fake_reports:'max',win_cutoff:'0'})});const r=await fetch('/navigation/public-input',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({revision:0,claims:['seer','seer','latent','latent','latent'],reports:[{acquired_day:1,published_day:1,player:1,target:3,color:'white'},{acquired_day:1,published_day:1,player:2,target:4,color:'white'}]})});if(!r.ok)throw Error(await r.text());})()`);
  await navigate('http://127.0.0.1:18821/main');await wait(()=>evaluate(`document.querySelector('main')?.dataset.tableInitialized==='true'`));
  await wait(()=>evaluate(`document.querySelector('[data-calculation-tree]')?.dataset.treeAuto==='complete'`),180000);
  const tree=await evaluate(`(async()=>{const r=await fetch('/game-tree?node=h1~0&expand=1');if(!r.ok)throw Error(await r.text());return r.json()})()`);
  assert.equal(tree.evaluation_trace.transition,'evaluated');assert.equal(tree.evaluation_trace.selection,'evaluated-public-MAX');
  assert.ok(tree.actions.some(a=>a.policy_probability==='0'&&a.branches.length));assert.ok(tree.actions.some(a=>a.policy_probability==='1'));
  await evaluate(`document.querySelector('[data-status-target="4"]').click()`);await wait(()=>evaluate(`!document.querySelector('#advance-button').disabled`));await evaluate(`document.querySelector('#advance-button').click()`);
  await wait(()=>evaluate(`document.querySelector('main')?.dataset.navigationOccurrence==='h2'&&document.querySelector('main')?.dataset.tableInitialized==='true'`));
  let nav=await evaluate(`(async()=>{return (await fetch('/navigation')).json()})()`);assert.ok(!nav.board.alive.includes(4));assert.equal(nav.occurrences.find(o=>o.key==='h2').selection_weight,'0');
  await evaluate(`(async()=>{let n=await(await fetch('/navigation')).json();let r=await fetch('/navigation/back',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({revision:n.revision})});if(!r.ok)throw Error(await r.text());})()`);
  await navigate('http://127.0.0.1:18821/main');await wait(()=>evaluate(`document.querySelector('main')?.dataset.tableInitialized==='true'`));
  await evaluate(`document.querySelector('[data-status-target="2"]').click()`);await wait(()=>evaluate(`!document.querySelector('#advance-button').disabled`));await evaluate(`document.querySelector('#advance-button').click()`);
  await wait(()=>evaluate(`document.querySelector('main')?.dataset.navigationOccurrence==='h3'&&document.querySelector('main')?.dataset.tableInitialized==='true'`));
  nav=await evaluate(`(async()=>{return (await fetch('/navigation')).json()})()`);assert.ok(!nav.board.alive.includes(2));assert.equal(nav.occurrences.find(o=>o.key==='h3').selection_weight,'1/2');
  await wait(()=>evaluate(`document.querySelector('[data-calculation-tree]')?.dataset.navigationUpdate==='complete'`),180000);
  await evaluate(`document.querySelector('[data-calculation-tree]').scrollIntoView({block:'start'})`);
  await fs.writeFile('.artifacts/max-day-transition-desktop.png',Buffer.from((await call('Page.captureScreenshot',{format:'png'})).data,'base64'));
  await call('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});await fs.writeFile('.artifacts/max-day-transition-mobile.png',Buffer.from((await call('Page.captureScreenshot',{format:'png'})).data,'base64'));
  assert.deepEqual(errors,[]);console.log('MAX day browser PASS: evaluator transition, manual CO, zero choice4, back, representative2 tied1/2');await call('Browser.close',{},null).catch(()=>{});
"""
  text=(prefix+body+suffix).replace('http://127.0.0.1:18821','http://127.0.0.1:'+str(server.server_port));probe=Path(directory)/'verify.cjs';probe.write_text(text,encoding='utf-8');subprocess.run(['node',str(probe)],check=True)
 finally:server.shutdown();server.server_close();worker.join()
