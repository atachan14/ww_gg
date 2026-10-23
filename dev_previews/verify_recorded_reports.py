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
  await evaluate(`(async()=>{await fetch('/start',{method:'POST',body:new URLSearchParams({citizens:'3',seers:'1',mediums:'0',hunters:'0',wolves:'1',day:'random',night:'random',fake_reports:'random',win_cutoff:'0'})});const r=await fetch('/navigation/public-input',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({revision:0,claims:['seer','latent','latent','latent','latent'],reports:[{acquired_day:1,published_day:1,player:1,target:2,color:'white'}]})});if(!r.ok)throw Error(await r.text());})()`);
  await navigate('http://127.0.0.1:18821/main');await wait(()=>evaluate(`document.querySelector('main')?.dataset.tableInitialized==='true'`));
  await wait(()=>evaluate(`document.querySelector('[data-calculation-tree]')?.dataset.treeAuto==='complete'`),180000);
  await evaluate(`document.querySelector('[data-status-target="5"]').click()`);await wait(()=>evaluate(`!document.querySelector('#advance-button').disabled`));await evaluate(`document.querySelector('#advance-button').click()`);
  await wait(()=>evaluate(`document.querySelector('main')?.dataset.navigationOccurrence==='h2'&&document.querySelector('main')?.dataset.tableInitialized==='true'`));
  await wait(()=>evaluate(`document.querySelector('[data-calculation-tree]')?.dataset.navigationUpdate==='complete'`),180000);
  const night=await evaluate(`(async()=>{const r=await fetch('/game-tree?node=h2~0&expand=1');if(!r.ok)throw Error(await r.text());return await r.json()})()`);
  assert.equal(night.evaluation_trace.owner,'evaluator');assert.equal(night.evaluation_trace.public_projection,'evaluated');
  const arrival=Object.values(night.items).find(d=>d.day_start&&d.alive.includes(1)&&d.public_updates?.some(u=>night.items[u.node]?.reports.length>d.reports.length));assert.ok(arrival);assert.equal(arrival.evaluation_trace.owner,'evaluator');assert.equal(arrival.reports.length,1);
  assert.ok(arrival.public_updates.some(u=>night.items[u.node]?.reports.length>arrival.reports.length));
  const labels=await evaluate(`document.querySelector('[data-calculation-tree]').innerText`);assert.ok(labels.includes('盤面更新'));assert.ok(labels.includes('占い結果'));
  await wait(()=>evaluate(`!!document.querySelector('[data-tree-item="${arrival.node}"] .compact-tree-go')`));await evaluate(`document.querySelector('[data-tree-item="${arrival.node}"] .compact-tree-go').click()`);
  await wait(()=>evaluate(`document.querySelector('main')?.dataset.navigationOccurrence==='h3'&&document.querySelector('main')?.dataset.tableInitialized==='true'`));
  const nav=await evaluate(`(async()=>{return await(await fetch('/navigation')).json()})()`);assert.equal(nav.board.day,2);assert.ok(!nav.board.alive.includes(5));
  await evaluate(`document.querySelector('[data-calculation-tree]').scrollIntoView({block:'start'});const frame=document.querySelector('.tree-flow-frame'),card=document.querySelector('.compact-tree-item.current');frame.scrollLeft=card?Math.max(0,card.getBoundingClientRect().left-frame.getBoundingClientRect().left+frame.scrollLeft-200):Math.max(0,frame.scrollWidth-frame.clientWidth)`);await new Promise(r=>setTimeout(r,200));
  await fs.writeFile('.artifacts/recorded-reports-desktop.png',Buffer.from((await call('Page.captureScreenshot',{format:'png'})).data,'base64'));
  await call('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});
  await fs.writeFile('.artifacts/recorded-reports-mobile.png',Buffer.from((await call('Page.captureScreenshot',{format:'png'})).data,'base64'));
  assert.deepEqual(errors,[]);console.log('recorded morning reports browser PASS: manual0,representative5,pre-report Current,update columns');await call('Browser.close',{},null).catch(()=>{});
"""
  text=(prefix+body+suffix).replace('http://127.0.0.1:18821','http://127.0.0.1:'+str(server.server_port));probe=Path(directory)/'verify.cjs';probe.write_text(text,encoding='utf-8');subprocess.run(['node',str(probe)],check=True)
 finally:server.shutdown();server.server_close();worker.join()
