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
  await evaluate(`(async()=>{await fetch('/start',{method:'POST',body:new URLSearchParams({citizens:'2',seers:'1',mediums:'0',hunters:'1',wolves:'1',day:'random',night:'random',fake_reports:'random',win_cutoff:'0'})});const r=await fetch('/navigation/public-input',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({revision:0,claims:['seer','latent','latent','latent','latent'],reports:[{acquired_day:1,published_day:1,player:1,target:2,color:'white'}]})});if(!r.ok)throw Error(await r.text());})()`);
  await navigate('http://127.0.0.1:18821/main');await wait(()=>evaluate(`document.querySelector('main')?.dataset.tableInitialized==='true'`));
  await wait(()=>evaluate(`document.querySelector('[data-calculation-tree]')?.dataset.treeAuto==='complete'`),180000);
  await evaluate(`document.querySelector('[data-status-target="3"]').click()`);await wait(()=>evaluate(`!document.querySelector('#advance-button').disabled`));await evaluate(`document.querySelector('#advance-button').click()`);
  await wait(()=>evaluate(`document.querySelector('main')?.dataset.navigationOccurrence==='h2'&&document.querySelector('main')?.dataset.tableInitialized==='true'`));
  const night=await evaluate(`(async()=>{const r=await fetch('/game-tree?node=h2~0&expand=1');if(!r.ok)throw Error(await r.text());return r.json()})()`);
  assert.equal(night.evaluation_trace.owner,'evaluator');assert.equal(night.evaluation_trace.ability_program,'factored-evaluated-flow');assert.equal(night.evaluation_trace.public_projection,'evaluated');assert.equal(night.night_stages.stats.generated_actions,0);
  const kinds=new Set();function walk(stage){for(const b of stage?.branches||[]){kinds.add(b.kind);walk(b.children);}}walk(night.night_stages);assert.ok(kinds.has('guard_target'));assert.ok(kinds.has('death_notice'));assert.ok(kinds.has('publication'));
  const arrival=Object.values(night.items).find(item=>item.day_start&&item.alive.length===4&&item.public_updates?.some(u=>night.items[u.node]?.reports.length>item.reports.length));assert.ok(arrival);
  const select=async node=>evaluate(`(async()=>{const n=await(await fetch('/navigation')).json();const r=await fetch('/game-tree/current',{method:'POST',body:new URLSearchParams({node:${JSON.stringify(node)},snapshot:${JSON.stringify(night.snapshot)},revision:String(n.revision)})});if(!r.ok)throw Error(await r.text());})()`);
  await select(arrival.node);await navigate('http://127.0.0.1:18821/main');await wait(()=>evaluate(`document.querySelector('main')?.dataset.tableInitialized==='true'`));
  let nav=await evaluate(`(async()=>{return(await fetch('/navigation')).json()})()`);assert.equal(nav.board.day,2);assert.equal(nav.board.alive.length,4);
  const publication=arrival.public_updates.find(u=>night.items[u.node]?.reports.length>arrival.reports.length);await select(publication.node);await navigate('http://127.0.0.1:18821/main');await wait(()=>evaluate(`document.querySelector('main')?.dataset.tableInitialized==='true'`));
  nav=await evaluate(`(async()=>{return(await fetch('/navigation')).json()})()`);assert.equal(nav.board.day,2);assert.equal(nav.board.alive.length,4);assert.ok(nav.path.length>=4);
  const ordinary=Object.values(night.items).find(item=>item.day_start&&item.alive.length===3&&item.public_current!==false);assert.ok(ordinary);await select(ordinary.node);await navigate('http://127.0.0.1:18821/main');await wait(()=>evaluate(`document.querySelector('main')?.dataset.tableInitialized==='true'`));
  nav=await evaluate(`(async()=>{return(await fetch('/navigation')).json()})()`);assert.equal(nav.board.day,2);assert.equal(nav.board.alive.length,3);
  await wait(()=>evaluate(`document.querySelector('[data-calculation-tree]')?.dataset.treeAuto==='complete'`),180000);await evaluate(`document.querySelector('[data-calculation-tree]').scrollIntoView({block:'start'})`);
  await fs.writeFile('.artifacts/hunter-record-desktop.png',Buffer.from((await call('Page.captureScreenshot',{format:'png'})).data,'base64'));
  await call('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});await fs.writeFile('.artifacts/hunter-record-mobile.png',Buffer.from((await call('Page.captureScreenshot',{format:'png'})).data,'base64'));
  assert.deepEqual(errors,[]);console.log('hunter record browser PASS: Table/CO, actual guard detail, no-death Current, report update/history');await call('Browser.close',{},null).catch(()=>{});
"""
  text=(prefix+body+suffix).replace('http://127.0.0.1:18821','http://127.0.0.1:'+str(server.server_port));probe=Path(directory)/'verify.cjs';probe.write_text(text,encoding='utf-8');subprocess.run(['node',str(probe)],check=True)
 finally:server.shutdown();server.server_close();worker.join()
