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
  await evaluate(`(async()=>{await fetch('/start',{method:'POST',body:new URLSearchParams({citizens:'1',seers:'1',mediums:'1',hunters:'1',wolves:'1',day:'random',night:'random',fake_reports:'random',win_cutoff:'0'})});const r=await fetch('/navigation/public-input',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({revision:0,claims:['seer','latent','latent','latent','latent'],reports:[{acquired_day:1,published_day:1,player:1,target:2,color:'white'}]})});if(!r.ok)throw Error(await r.text());})()`);
  await call('Page.addScriptToEvaluateOnNewDocument',{source:`window.__treeRecords={};const oldFetch=window.fetch;window.fetch=async(...a)=>{const r=await oldFetch(...a);if(String(a[0]).includes('/game-tree?'))r.clone().json().then(d=>{for(const v of [d,...Object.values(d.items||{})])window.__treeRecords[v.node]={node:v.node,day:v.column_day,phase:v.column_phase,roles:v.stage_roles,method:v.night_stages?.method};}).catch(()=>{});return r;};`});
  await navigate('http://127.0.0.1:18821/main');await wait(()=>evaluate(`document.querySelector('main')?.dataset.tableInitialized==='true'`));
  await wait(()=>evaluate(`document.querySelector('[data-calculation-tree]')?.dataset.treeAuto==='complete'`),180000);
  await evaluate(`document.querySelector('[data-status-target="3"]').click()`);await wait(()=>evaluate(`!document.querySelector('#advance-button').disabled`));await evaluate(`document.querySelector('#advance-button').click()`);
  await wait(()=>evaluate(`document.querySelector('main')?.dataset.navigationOccurrence==='h2'&&document.querySelector('main')?.dataset.tableInitialized==='true'`));
  const night=await evaluate(`(async()=>{const r=await fetch('/game-tree?node=h2~0&expand=1');if(!r.ok)throw Error(await r.text());return r.json()})()`);
  assert.equal(night.evaluation_trace.ability_program,'factored-evaluated-flow');assert.equal(night.night_stages.stats.medium_stage_omitted,true);assert.equal(night.stage_roles.mediums,0);
  await wait(()=>evaluate(`document.querySelector('[data-calculation-tree]')?.dataset.treeAuto==='complete'`),180000);
  const initial=await evaluate(`(()=>{const h=[...document.querySelectorAll('h3[data-phase="1"]')].find(e=>e.textContent.includes('霊能結果'));return h?{column:h.dataset.column,items:document.querySelectorAll('.compact-action-item[data-action-column="'+h.dataset.column+'"]') .length}:null;})()`);
  if(initial)assert.ok(initial.items>0,'medium header without actual visible stage');
  // Other execution alternatives can still use explicit legacy medium detail.
  // Close only those alternatives; do not hide their real occupied column.
  await evaluate(`(()=>{for(const d of Object.values(window.__treeRecords)){if(d.day!==1||d.phase!=='night'||!d.roles?.mediums||!d.method)continue;const item=[...document.querySelectorAll('[data-tree-item]')].find(e=>e.dataset.treeItem===d.node);const hit=[...document.querySelectorAll('[data-tree-toggle]')].find(e=>e.dataset.treeToggle===item?.dataset.treeKey);if(hit?.getAttribute('aria-expanded')==='true')hit.dispatchEvent(new MouseEvent('click',{bubbles:true}));}})()`);
  const text=await evaluate(`[...document.querySelectorAll('[data-calculation-tree] h3[data-phase="1"]')].map(e=>e.textContent).join('|')`);console.log('current evaluated path headers',JSON.stringify(text));assert.ok(!text.includes('霊能結果'));assert.ok(text.includes('護衛位置'));assert.ok(text.includes('占い位置'));
  assert.deepEqual(errors,[]);console.log('globally unused medium DOM column omitted PASS');await call('Browser.close',{},null).catch(()=>{});
"""
  text=(prefix+body+suffix).replace('http://127.0.0.1:18821','http://127.0.0.1:'+str(server.server_port));probe=Path(directory)/'verify.cjs';probe.write_text(text,encoding='utf-8');subprocess.run(['node',str(probe)],check=True)
 finally:server.shutdown();server.server_close();worker.join()
